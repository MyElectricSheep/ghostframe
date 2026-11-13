"""Demo-site API: input rules, queue, caps, stop and cancel, nothing kept, exact bytes."""
import datetime as dt
from importlib.util import find_spec
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import threading
import time
import unittest
from unittest import mock

if any(find_spec(name) is None for name in ("starlette", "httpx", "multipart", "cryptography", "reedsolo")):
    raise unittest.SkipTest("Install the server extra")

import numpy as np
from PIL import Image
from starlette.testclient import TestClient

from server import app as app_module
from server import jobs as jobs_module
from server.app import build_app
from server.engine import Refused
from server.jobs import Limits, Queue, Reservation, visitor_address

ROOT = Path(__file__).resolve().parents[1]
logging.getLogger("ghostframe.server").setLevel(logging.ERROR)  # the "local development" notice


def png(w=320, h=256, mode="RGB", **save):
    rng = np.random.default_rng(1)
    image = Image.fromarray(rng.integers(0, 256, (h, w, 3), dtype=np.uint8)).convert(mode)
    buffer = io.BytesIO()
    image.save(buffer, format=save.pop("format", "PNG"), **save)
    return buffer.getvalue()


class FakeEngine:
    """Stands in for the models: 'refuse' in the message refuses, 'slow' waits for release."""

    def __init__(self):
        self.ready = threading.Event()
        self.ready.set()
        self.release = threading.Event()
        self.decoding, self.decode_gate = threading.Event(), None

    def load(self):
        self.ready.set()

    def encode(self, cover, message, passphrase, mode, progress=None):
        for step in range(1, 5):
            if progress:
                progress(step / 5)
            if b"slow" in message:
                while not self.release.wait(0.01):
                    progress(step / 5)
        if b"refuse" in message:
            raise Refused("no")
        buffer = io.BytesIO()
        Image.fromarray(cover).save(buffer, format="PNG")
        return buffer.getvalue()

    def decode(self, data, passphrase, mode):
        self.decoding.set()
        if self.decode_gate is not None:
            self.decode_gate.wait(10)
        return b"hello" if passphrase == b"right" and mode == "subtle" else None


KEYS = dict(GF_ENGINE_KEY="engine-key-for-tests", GF_INTERNAL_KEY="internal-key-for-tests")


def client(engine=None, site_cap=None, visitor_cap=None, timeout=300, read_site=None, read_visitor=None,
           keys=False, max_waiting=jobs_module.MAX_WAITING):
    engine = engine or FakeEngine()
    queue = Queue(engine, Limits(site_cap, visitor_cap, read_site, read_visitor), timeout=timeout, max_waiting=max_waiting)
    env = dict(KEYS) if keys else {}
    with mock.patch.dict(os.environ, env):
        if not keys:
            for name in KEYS:
                os.environ.pop(name, None)
        app = build_app(engine=engine, queue=queue)
    return TestClient(app), engine, queue


def encode(c, data=None, mode="subtle", message="Meet at dawn.", passphrase="pw", headers=None):
    return c.post("/api/encode", data=dict(mode=mode, message=message, passphrase=passphrase),
                  files=dict(image=("photo.png", data if data is not None else png(), "image/png")), headers=headers)


def decode(c, data=None, passphrase="right", mode="auto", headers=None):
    return c.post("/api/decode", data=dict(passphrase=passphrase, mode=mode),
                  files=dict(image=("m.png", data if data is not None else png(), "image/png")), headers=headers)


def wait(c, job_id, states=("done", "refused", "timed_out", "cancelled", "failed"), limit=10):
    end = time.time() + limit
    while time.time() < end:
        view = c.get(f"/api/jobs/{job_id}").json()
        if view["state"] in states:
            return view
        time.sleep(0.02)
    raise AssertionError(f"job stuck in {view['state']}")


class InputRuleTests(unittest.TestCase):
    def setUp(self):
        self.c, _, _ = client()

    def issue(self, data, **kw):
        r = encode(self.c, data, **kw)
        self.assertEqual(r.status_code, 400, r.text)
        return r.json()["issue"]

    def test_rejections_match_the_copy(self):
        self.assertEqual(self.issue(b"GIF89a not really"), "type")
        self.assertEqual(self.issue(png(150, 100)), "small")
        self.assertEqual(self.issue(png(2001, 2000)), "big")
        rgba = Image.new("RGBA", (320, 256), (10, 20, 30, 128))
        buffer = io.BytesIO(); rgba.save(buffer, format="PNG")
        self.assertEqual(self.issue(buffer.getvalue()), "alpha")
        cmyk = io.BytesIO(); Image.new("CMYK", (320, 256)).save(cmyk, format="JPEG")
        self.assertEqual(self.issue(cmyk.getvalue()), "cmyk")
        deep = io.BytesIO(); Image.new("I;16", (320, 256)).save(deep, format="PNG")
        self.assertEqual(self.issue(deep.getvalue()), "deep")

    def test_message_limits_are_utf8_bytes(self):
        self.assertEqual(encode(self.c, mode="classic", message="é" * 7).json()["error"], "message_too_long")
        self.assertEqual(encode(self.c, mode="subtle", message="x" * 80).json(), dict(error="message_too_long", limit=79, bytes=80))
        self.assertEqual(encode(self.c, mode="long", message="x" * 495).json()["limit"], 494)
        self.assertEqual(encode(self.c, message="").json()["error"], "empty_message")
        self.assertEqual(encode(self.c, passphrase="").json()["error"], "empty_passphrase")

    def test_read_is_png_only(self):
        jpeg = png(format="JPEG", quality=95)
        r = self.c.post("/api/decode", data=dict(passphrase="right"), files=dict(image=("a.jpg", jpeg, "image/jpeg")))
        self.assertEqual(r.json()["issue"], "jpegRead")


class QueueTests(unittest.TestCase):
    def test_result_is_exact_no_store_and_released_after_download(self):
        c, _, _ = client()
        r = encode(c)
        self.assertEqual(r.status_code, 202)
        view = wait(c, r.json()["id"])
        self.assertEqual(view["state"], "done")
        self.assertEqual(view["progress"], 1.0)
        got = c.get(f"/api/jobs/{view['id']}/marked.png")
        self.assertEqual(got.headers["cache-control"], "no-store, no-transform")
        self.assertEqual(hashlib.sha256(got.content).hexdigest(), view["sha256"])
        self.assertEqual(c.get(f"/api/jobs/{view['id']}/marked.png").status_code, 404)
        self.assertEqual(c.get(f"/api/jobs/{view['id']}/difference.png").status_code, 200)

    def test_inputs_are_dropped_when_a_job_ends(self):
        c, _, queue = client()
        job_id = encode(c).json()["id"]
        wait(c, job_id)
        job = queue.jobs[job_id]
        self.assertIsNone(job.cover)
        self.assertEqual((job.message, job.passphrase), (b"", b""))

    def test_one_at_a_time_with_positions_and_cancel(self):
        c, engine, _ = client()
        first = encode(c, message="slow").json()["id"]
        wait(c, first, states=("encoding",))
        second = encode(c).json()["id"]
        third = encode(c).json()["id"]
        self.assertEqual(c.get(f"/api/jobs/{second}").json()["position"], 1)
        self.assertEqual(c.get(f"/api/jobs/{third}").json()["position"], 2)
        self.assertEqual(c.post(f"/api/jobs/{third}/cancel").json()["state"], "cancelled")
        self.assertEqual(c.post(f"/api/jobs/{first}/cancel").json()["state"], "encoding")
        self.assertEqual(wait(c, first)["state"], "cancelled")
        self.assertEqual(wait(c, second)["state"], "done")
        engine.release.set()

    def test_refusal_produces_nothing(self):
        c, _, _ = client()
        view = wait(c, encode(c, message="refuse").json()["id"])
        self.assertEqual(view["state"], "refused")
        self.assertEqual(c.get(f"/api/jobs/{view['id']}/marked.png").status_code, 404)

    def test_hard_stop(self):
        c, engine, _ = client(timeout=0.2)
        view = wait(c, encode(c, message="slow").json()["id"])
        self.assertEqual(view["state"], "timed_out")
        engine.release.set()

    def test_abandoned_queue_place_is_dropped(self):
        c, engine, queue = client()
        first = encode(c, message="slow").json()["id"]
        wait(c, first, states=("encoding",))
        second = encode(c).json()["id"]
        queue.jobs[second].last_poll -= jobs_module.ABANDON_AFTER + 1
        self.assertEqual(c.get(f"/api/jobs/{second}").json()["state"], "cancelled")
        engine.release.set()

    def test_daily_caps(self):
        c, _, _ = client(site_cap=3, visitor_cap=2)
        for _ in range(2):
            wait(c, encode(c).json()["id"])
        self.assertEqual(encode(c).json()["error"], "visitor_limit")
        self.assertFalse(c.get("/api/status").json()["visitor_open"])
        c2, engine, queue = client(site_cap=1, visitor_cap=None)
        wait(c2, encode(c2).json()["id"])
        self.assertEqual(encode(c2).status_code, 429)
        self.assertEqual(encode(c2).json()["error"], "site_limit")
        self.assertFalse(c2.get("/api/status").json()["site_open"])

    def test_quota_counts_site_encodes_only(self):
        c, _, _ = client(site_cap=3, visitor_cap=None)
        q = c.get("/api/quota")
        self.assertEqual(q.headers["cache-control"], "no-store, no-transform")
        tomorrow = (dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=1)).isoformat()
        self.assertEqual(q.json(), dict(left=3, limit=3, resets_at=tomorrow + "T00:00:00Z"))
        wait(c, encode(c).json()["id"])
        self.assertEqual(c.get("/api/quota").json()["left"], 2)
        # Reading never counts; a refused encode does (the engine ran), a cancelled one doesn't.
        c.post("/api/decode", data=dict(passphrase="pw", mode="auto"), files=dict(image=("m.png", png(), "image/png")))
        self.assertEqual(c.get("/api/quota").json()["left"], 2)
        wait(c, encode(c, message="refuse").json()["id"])
        self.assertEqual(c.get("/api/quota").json()["left"], 1)
        wait(c, encode(c).json()["id"])
        self.assertEqual(c.get("/api/quota").json()["left"], 0)
        self.assertEqual(encode(c).json()["error"], "site_limit")
        self.assertEqual(c.get("/api/quota").json()["left"], 0)
        self.assertEqual(client(site_cap=None)[0].get("/api/quota").status_code, 404)

    def test_site_count_can_be_persisted_and_restored(self):
        c, _, _ = client(site_cap=5, keys=True)
        auth, internal = {"x-gf-engine-key": KEYS["GF_ENGINE_KEY"]}, {"x-gf-internal-key": KEYS["GF_INTERNAL_KEY"]}
        wait(c, encode(c, headers=auth).json()["id"])
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        self.assertEqual(c.get("/api/internal/limits", headers=internal).json(), dict(day=today, site=1, read=0))
        # A restarted container gets today's count back; another day's count, or a lower one, is ignored.
        c2, _, _ = client(site_cap=5, keys=True)
        restore = lambda **body: c2.post("/api/internal/limits", json=body, headers=internal).json()
        self.assertEqual(restore(day="2000-01-01", site=4)["site"], 0)
        self.assertEqual(restore(day=today, site=4, read=7), dict(day=today, site=4, read=7))
        self.assertEqual(restore(day=today, site=2)["site"], 4)
        self.assertEqual(c2.get("/api/quota").json()["left"], 1)
        wait(c2, encode(c2, headers=auth).json()["id"])
        self.assertEqual(encode(c2, headers=auth).json()["error"], "site_limit")

    def test_cancelling_a_running_encode_keeps_it_counted(self):
        # Refunding a started encode would let cancel-and-resubmit run the encoder forever.
        c, engine, _ = client(visitor_cap=1)
        job_id = encode(c, message="slow").json()["id"]
        wait(c, job_id, states=("encoding",))
        c.post(f"/api/jobs/{job_id}/cancel")
        engine.release.set()
        self.assertEqual(wait(c, job_id)["state"], "cancelled")
        self.assertEqual(encode(c).json()["error"], "visitor_limit")

    def test_cancelling_a_queued_encode_gives_it_back(self):
        c, engine, _ = client(visitor_cap=2)
        first = encode(c, message="slow").json()["id"]
        wait(c, first, states=("encoding",))
        second = encode(c).json()["id"]
        self.assertEqual(c.post(f"/api/jobs/{second}/cancel").json()["state"], "cancelled")
        self.assertEqual(encode(c).status_code, 202)  # the cancelled one was given back
        self.assertEqual(encode(c).json()["error"], "visitor_limit")
        engine.release.set()

    def test_give_back_ignores_another_days_count(self):
        limits = Limits(5, 5)
        visitor = limits.visitor("192.0.2.1")
        today = limits.reserve(visitor)
        stale = Reservation("encode", visitor, today.day - dt.timedelta(days=1))
        limits.give_back(stale)
        self.assertEqual(limits.site_count()["site"], 1)
        limits.give_back(today)
        self.assertEqual(limits.site_count()["site"], 0)

    def test_caps_hold_under_parallel_submissions(self):
        limits = Limits(5, 3)
        queue = Queue(FakeEngine(), limits)
        visitors = [limits.visitor(f"192.0.2.{i % 4}") for i in range(64)]
        results, barrier = [], threading.Barrier(16)

        def worker(chunk):
            barrier.wait()
            results.extend(queue.reserve(v) for v in chunk)

        threads = [threading.Thread(target=worker, args=(visitors[i::16],)) for i in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        taken = [r for r in results if isinstance(r, Reservation)]
        self.assertEqual(len(taken), 5)
        self.assertTrue(all(sum(r.visitor == v for r in taken) <= 3 for v in set(visitors)))
        self.assertEqual(limits.site_count()["site"], 5)

    def test_parallel_requests_cannot_pass_the_visitor_cap(self):
        c, engine, _ = client(visitor_cap=2)
        engine.release.clear()
        codes, barrier = [], threading.Barrier(6)

        def post():
            barrier.wait()
            codes.append(encode(c, message="slow").status_code)

        threads = [threading.Thread(target=post) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        engine.release.set()
        self.assertEqual(sorted(codes), [202, 202, 429, 429, 429, 429])

    def test_waiting_room_is_bounded(self):
        c, engine, queue = client(max_waiting=2)
        first = encode(c, message="slow").json()["id"]
        wait(c, first, states=("encoding",))
        self.assertEqual(encode(c).status_code, 202)
        self.assertEqual(encode(c).status_code, 202)
        busy = encode(c)
        self.assertEqual((busy.status_code, busy.json()), (503, dict(error="busy")))
        engine.release.set()
        # A refusal before the job starts is not counted against anyone.
        self.assertEqual(queue._reserved, 0)

    def test_refused_upload_is_not_counted(self):
        c, _, _ = client(visitor_cap=1)
        self.assertEqual(encode(c, b"GIF89a not really").json()["issue"], "type")
        self.assertEqual(encode(c).status_code, 202)


class VisitorTests(unittest.TestCase):
    def test_ipv6_visitors_are_their_64(self):
        limits = Limits(None, None)
        self.assertEqual(visitor_address("2001:db8:1:2:aaaa::1"), "2001:db8:1:2::/64")
        self.assertEqual(limits.visitor("2001:db8:1:2::1"), limits.visitor("2001:db8:1:2:ffff:ffff:ffff:ffff"))
        self.assertNotEqual(limits.visitor("2001:db8:1:2::1"), limits.visitor("2001:db8:1:3::1"))
        self.assertEqual(visitor_address("::ffff:192.0.2.7"), "192.0.2.7")
        self.assertEqual(visitor_address("192.0.2.7"), "192.0.2.7")
        self.assertNotEqual(limits.visitor("192.0.2.7"), limits.visitor("192.0.2.8"))


class HostKeyTests(unittest.TestCase):
    """Behind Cloudflare the Durable Object passes per-start keys; without them, local development."""

    def test_internal_route_needs_the_internal_key(self):
        c, _, _ = client(keys=True)
        self.assertEqual(c.get("/api/internal/limits").status_code, 404)
        self.assertEqual(c.get("/api/internal/limits", headers={"x-gf-internal-key": "wrong"}).status_code, 404)
        # The engine key that every forwarded request carries does not open it.
        self.assertEqual(c.get("/api/internal/limits", headers={"x-gf-internal-key": KEYS["GF_ENGINE_KEY"]}).status_code, 404)
        self.assertEqual(c.post("/api/internal/limits", json=dict(day="x", site=99)).status_code, 404)
        self.assertEqual(c.get("/api/internal/limits", headers={"x-gf-internal-key": KEYS["GF_INTERNAL_KEY"]}).status_code, 200)

    def test_internal_route_is_off_without_host_keys(self):
        c, _, _ = client()
        self.assertEqual(c.get("/api/internal/limits").status_code, 404)
        self.assertEqual(c.get("/api/internal/limits", headers={"x-gf-internal-key": ""}).status_code, 404)

    def test_percent_encoded_api_paths_are_refused(self):
        c, _, _ = client(keys=True, site_cap=5)
        internal = {"x-gf-internal-key": KEYS["GF_INTERNAL_KEY"]}
        self.assertEqual(c.get("/api/quota").status_code, 200)
        self.assertEqual(c.get("/api/internal%2Flimits", headers=internal).status_code, 404)
        self.assertEqual(c.get("/api/%71uota").status_code, 404)

    def test_encode_and_decode_need_the_engine_key(self):
        c, _, _ = client(keys=True, visitor_cap=1)
        self.assertEqual(encode(c).json(), dict(error="bot_check"))
        self.assertEqual(decode(c).status_code, 403)
        self.assertEqual(encode(c, headers={"x-gf-engine-key": "wrong"}).status_code, 403)
        self.assertEqual(encode(c, headers={"x-gf-engine-key": KEYS["GF_ENGINE_KEY"]}).status_code, 202)
        self.assertEqual(decode(c, headers={"x-gf-engine-key": KEYS["GF_ENGINE_KEY"]}).status_code, 200)


class BodyLimitTests(unittest.TestCase):
    def test_body_size_and_type_are_checked_before_parsing(self):
        c, _, _ = client()
        self.assertEqual(c.post("/api/encode", content=b"mode=subtle", headers={"content-type": "application/x-www-form-urlencoded"}).status_code, 415)
        self.assertEqual(c.post("/api/decode", json=dict(passphrase="x")).status_code, 415)
        big = c.post("/api/decode", content=b"x", headers={"content-type": "multipart/form-data; boundary=x",
                                                             "content-length": str(app_module.MAX_BODY + 1)})
        self.assertEqual(big.status_code, 413)
        with mock.patch.object(app_module, "MAX_BODY", 4096):  # a streamed body is counted too
            self.assertEqual(encode(c, png(320, 256)).status_code, 413)
        self.assertEqual(c.post("/api/encode", content=b"--x\r\nnot multipart", headers={"content-type": "multipart/form-data; boundary=x"}).status_code, 400)

    def test_uploads_never_spool_to_disk(self):
        from starlette import formparsers

        self.assertGreaterEqual(formparsers.MultiPartParser.spool_max_size, app_module.MAX_BODY)


class DecodeLimitTests(unittest.TestCase):
    def test_daily_decode_caps(self):
        c, _, _ = client(read_site=3, read_visitor=2)
        for _ in range(2):
            self.assertEqual(decode(c).status_code, 200)
        self.assertEqual((decode(c).status_code, decode(c).json()), (429, dict(error="read_visitor_limit")))
        # Refused inputs are not counted; the encode quota is untouched.
        self.assertEqual(c.get("/api/quota").status_code, 404)
        c2, _, _ = client(read_site=1, read_visitor=None)
        self.assertEqual(decode(c2, b"not a png").json()["issue"], "type")
        self.assertEqual(decode(c2).status_code, 200)
        self.assertEqual(decode(c2).json(), dict(error="read_site_limit"))

    def test_decode_waiting_room_is_bounded(self):
        engine = FakeEngine()
        engine.decode_gate = threading.Event()
        with mock.patch.object(app_module, "DECODE_RUNNING", 1), mock.patch.object(app_module, "DECODE_WAITING", 0):
            c, _, _ = client(engine=engine)
            with c:
                first = []
                t = threading.Thread(target=lambda: first.append(decode(c)))
                t.start()
                self.assertTrue(engine.decoding.wait(10))
                busy = decode(c)
                engine.decode_gate.set()
                t.join()
                self.assertEqual((busy.status_code, busy.json()), (503, dict(error="busy")))
                self.assertEqual(json.loads(first[0].text.splitlines()[-1])["found"], True)
                self.assertEqual(decode(c).status_code, 200)  # the slot was given back


class DecodeStreamTests(unittest.TestCase):
    def test_tries_modes_in_order_and_stops_when_found(self):
        c, _, _ = client()
        r = c.post("/api/decode", data=dict(passphrase="right", mode="auto"), files=dict(image=("a.png", png(), "image/png")))
        lines = [json.loads(line) for line in r.text.splitlines()]
        self.assertEqual(lines[:3], [dict(trying="classic"), dict(nothing="classic"), dict(trying="subtle")])
        self.assertEqual(lines[3]["found"], True)
        self.assertEqual((lines[3]["message"], lines[3]["profile"]), ("hello", "bb-mobilenet_v3_small-l2-b16p48"))
        self.assertEqual(len(lines), 4)
        r = c.post("/api/decode", data=dict(passphrase="wrong", mode="long"), files=dict(image=("a.png", png(), "image/png")))
        self.assertEqual([json.loads(line) for line in r.text.splitlines()], [dict(trying="long"), dict(nothing="long"), dict(found=False)])


class RealEngineFixtureTests(unittest.TestCase):
    """The nine demo fixtures through the API with the real models (slow: loads both models)."""

    @classmethod
    def setUpClass(cls):
        from server.engine import Engine

        cls.c, _, _ = client(engine=Engine())

    def decode(self, path, passphrase, mode="auto"):
        r = self.c.post("/api/decode", data=dict(passphrase=passphrase, mode=mode),
                        files=dict(image=(path.name, path.read_bytes(), "image/png")))
        return json.loads(r.text.splitlines()[-1])

    def test_fixtures_decode_exactly_and_controls_find_nothing(self):
        for fixtures in sorted((ROOT / "demo-photos" / "fixtures").glob("*/fixtures.json")):
            for entry in json.loads(fixtures.read_text()):
                mode = entry["encoded"].removesuffix(".png")
                got = self.decode(fixtures.parent / entry["encoded"], "ghostframe public benchmark fixture", mode)
                self.assertEqual((got["found"], got["message"]), (True, entry["recovered_message"]), fixtures.parent.name)
                self.assertEqual(got["profile"], entry["profile"])
        portrait = ROOT / "demo-photos" / "fixtures" / "antonello-portrait-of-a-man"
        self.assertEqual(self.decode(portrait / "classic.png", "ghostframe public benchmark fixture")["message"], "Trust no one.")
        self.assertFalse(self.decode(portrait / "subtle.png", "wrong passphrase")["found"])
        self.assertFalse(self.decode(portrait / "original.png", "ghostframe public benchmark fixture")["found"])


if __name__ == "__main__":
    unittest.main()
