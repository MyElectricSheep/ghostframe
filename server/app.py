"""HTTP API for the Ghostframe demo site.

    .venv/bin/python -m server.app            # http://127.0.0.1:8790 (the site's dev proxy target)

Configuration (environment):
  GF_SITE_DAILY_CAP, GF_VISITOR_DAILY_CAP   encode caps per UTC day ("none" = no cap)
  GF_DECODE_SITE_DAILY_CAP,                 decode caps per UTC day (default 1000 and 20)
  GF_DECODE_VISITOR_DAILY_CAP
  GF_ENCODE_TIMEOUT_S                       hard stop per encode (default 300)
  GF_ENGINE_KEY                             set by the Cloudflare host (a fresh random value per container
                                            start). When set, encode and decode are refused unless the
                                            request carries it (the Worker has checked Turnstile), and
                                            /api/internal/limits needs GF_INTERNAL_KEY. When unset (local
                                            development), there is no bot check and no internal route.
  GF_INTERNAL_KEY                           the host's key for /api/internal/limits (only with GF_ENGINE_KEY)
  GF_TRUST_CF_IP=1                          take the visitor address from CF-Connecting-IP
  GF_STATIC_DIR                             optionally also serve the built site (site/dist)
  GF_THREADS, GF_PRELOAD=1                  torch threads; load both models at start-up
Nothing is written to disk: uploads, inputs and results stay in memory.
"""
import base64
import hmac
import json
import logging
import os
import threading

import anyio
from starlette import formparsers
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Mount, Route

from server import inputs
from server.engine import MODES, ORDER, Engine
from server.jobs import Limits, Queue, Reservation, env_cap

log = logging.getLogger("ghostframe.server")
# Largest accepted request body: the largest upload plus room for the multipart framing and the
# small text fields. The Worker enforces the same number before forwarding.
MAX_BODY = inputs.MAX_UPLOAD + 1024 * 1024
MAX_FIELD = 16 * 1024  # message, passphrase and mode are far smaller
# Uploads stay in memory: a body is at most MAX_BODY, so no file part ever reaches the spool size.
formparsers.MultiPartParser.spool_max_size = MAX_BODY
NO_STORE = {"Cache-Control": "no-store, no-transform", "X-Content-Type-Options": "nosniff"}
ENGINE_KEY_HEADER = "x-gf-engine-key"
INTERNAL_KEY_HEADER = "x-gf-internal-key"
DECODE_RUNNING = 2   # decodes that run at once
DECODE_WAITING = 6   # decodes allowed to wait for a slot; more get 'busy'


def error(status, code, **extra):
    return JSONResponse(dict(error=code, **extra), status_code=status, headers=NO_STORE)


def client_address(request):
    if os.environ.get("GF_TRUST_CF_IP") == "1" and request.headers.get("cf-connecting-ip"):
        return request.headers["cf-connecting-ip"]
    return request.client.host if request.client else "unknown"


def key_matches(request, header, expected):
    given = request.headers.get(header, "")
    return bool(expected) and hmac.compare_digest(given.encode(), expected.encode())


class TooLarge(Exception):
    pass


async def read_form(request):
    """Parse a multipart body of at most MAX_BODY bytes, entirely in memory.

    Returns (form, None) or (None, error response). The caller closes the form."""
    content_type = request.headers.get("content-type", "")
    if content_type.split(";", 1)[0].strip().lower() != "multipart/form-data":
        return None, error(415, "bad_request")
    length = request.headers.get("content-length")
    if length is not None:
        if not length.isdigit():
            return None, error(400, "bad_request")
        if int(length) > MAX_BODY:
            return None, error(413, "too_large")
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_BODY:
            return None, error(413, "too_large")
    sent = False

    async def replay():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": bytes(body), "more_body": False}

    buffered = Request(request.scope, replay)
    try:
        form = await buffered.form(max_files=1, max_fields=8, max_part_size=MAX_FIELD)
    except (HTTPException, formparsers.MultiPartException):
        return None, error(400, "bad_request")
    return form, None


async def read_upload(form, name):
    upload = form.get(name)
    if upload is None or isinstance(upload, str):
        return None
    return await upload.read(inputs.MAX_UPLOAD + 1)


class GuardedStream(StreamingResponse):
    """A streamed decode that always gives its place back, even if the client goes away before
    the stream starts. The slot is awaited in async code: waiting takes no worker thread."""

    def __init__(self, content, slots, on_close, **kw):
        super().__init__(content, **kw)
        self.slots, self.on_close = slots, on_close

    async def __call__(self, scope, receive, send):
        try:
            async with self.slots:
                await super().__call__(scope, receive, send)
        finally:
            self.on_close()


def build_app(engine=None, queue=None):
    engine = engine or Engine(threads=int(os.environ.get("GF_THREADS", "4")))
    limits = queue.limits if queue else Limits(
        env_cap("GF_SITE_DAILY_CAP", 50), env_cap("GF_VISITOR_DAILY_CAP", 3),
        env_cap("GF_DECODE_SITE_DAILY_CAP", 1000), env_cap("GF_DECODE_VISITOR_DAILY_CAP", 20))
    queue = queue or Queue(engine, limits, timeout=float(os.environ.get("GF_ENCODE_TIMEOUT_S", "300")))
    engine_key = os.environ.get("GF_ENGINE_KEY") or None
    internal_key = os.environ.get("GF_INTERNAL_KEY") if engine_key else None
    if engine_key:
        log.info("encode and decode need the host's engine key (the Worker checks Turnstile)")
    else:
        log.warning("GF_ENGINE_KEY is not set: no bot check and no /api/internal route (local development)")
    decode_slots = anyio.Semaphore(DECODE_RUNNING)
    decodes = dict(in_flight=0)  # decodes validating, waiting or running; one event loop, no lock

    def verified(request):
        return engine_key is None or key_matches(request, ENGINE_KEY_HEADER, engine_key)

    async def internal_limits(request: Request):
        # Only for the Durable Object's own calls (it sends GF_INTERNAL_KEY; forwarded visitor
        # requests never carry it): read today's site-wide counts to persist them, or restore them.
        if not internal_key or not key_matches(request, INTERNAL_KEY_HEADER, internal_key):
            return error(404, "not_found")
        if request.method == "POST":
            body = await request.json()
            return JSONResponse(limits.restore_site_count(str(body.get("day")), body.get("site", 0), body.get("read", 0)),
                                headers=NO_STORE)
        return JSONResponse(limits.site_count(), headers=NO_STORE)

    async def quota(request: Request):
        # Read-only: the site-wide encodes left today. Reading messages never changes it.
        q = limits.quota()
        if q is None:
            return error(404, "no_limit")
        return JSONResponse(q, headers=NO_STORE)

    async def status(request: Request):
        visitor = limits.visitor(client_address(request))
        return JSONResponse(dict(engine_ready=engine.ready.is_set(), site_open=limits.site_open(),
                                 visitor_open=limits.check(visitor) is None), headers=NO_STORE)

    async def encode(request: Request):
        if not verified(request):
            return error(403, "bot_check")
        form, refused = await read_form(request)
        if refused:
            return refused
        reservation = None
        try:
            mode = form.get("mode")
            if mode not in MODES:
                return error(400, "bad_mode")
            message = (form.get("message") or "").encode("utf-8")
            passphrase = (form.get("passphrase") or "").encode("utf-8")
            if not message:
                return error(400, "empty_message")
            if len(message) > MODES[mode]["capacity"]:
                return error(400, "message_too_long", limit=MODES[mode]["capacity"], bytes=len(message))
            if not passphrase:
                return error(400, "empty_passphrase")
            # Check the caps and the waiting room and count the encode in one step, before the
            # photo is read, so parallel requests can't slip past either.
            reservation = queue.reserve(limits.visitor(client_address(request)))
            if not isinstance(reservation, Reservation):
                code, reservation = reservation, None
                return error(503, code) if code == "busy" else error(429, code)
            data = await read_upload(form, "image")
            if data is None:
                return error(400, "issue", issue="type")
            try:
                cover, conversion = await anyio.to_thread.run_sync(inputs.cover, data)
            except inputs.Issue as issue:
                return error(400, "issue", issue=issue.code, **issue.details)
            job, reservation = queue.submit(reservation, mode, cover, message, passphrase, conversion), None
            return JSONResponse(queue.poll(job.id), status_code=202, headers=NO_STORE)
        finally:
            if reservation is not None:  # refused before it started: not counted
                queue.release(reservation)
            await form.close()

    async def job_status(request: Request):
        view = queue.poll(request.path_params["job_id"])
        return JSONResponse(view, headers=NO_STORE) if view else error(404, "unknown_job")

    async def job_cancel(request: Request):
        view = queue.cancel(request.path_params["job_id"])
        return JSONResponse(view, headers=NO_STORE) if view else error(404, "unknown_job")

    async def job_result(request: Request):
        kind = request.path_params["kind"]
        if kind not in ("marked", "difference"):
            return error(404, "no_result")
        data = queue.take_result(request.path_params["job_id"], kind)
        if data is None:
            return error(404, "no_result")
        headers = dict(NO_STORE)
        if kind == "marked":
            headers["Content-Disposition"] = 'attachment; filename="ghostframe-message.png"'
        return Response(data, media_type="image/png", headers=headers)

    async def decode(request: Request):
        if not verified(request):
            return error(403, "bot_check")
        form, refused = await read_form(request)
        if refused:
            return refused
        reservation, handed_over = None, False
        try:
            mode = form.get("mode") or "auto"
            if mode != "auto" and mode not in MODES:
                return error(400, "bad_mode")
            passphrase = (form.get("passphrase") or "").encode("utf-8")
            if not passphrase:
                return error(400, "empty_passphrase")
            if decodes["in_flight"] >= DECODE_RUNNING + DECODE_WAITING:
                return error(503, "busy")
            reservation = limits.reserve(limits.visitor(client_address(request)), kind="decode")
            if not isinstance(reservation, Reservation):
                code, reservation = reservation, None
                return error(429, code)
            decodes["in_flight"] += 1
            data = await read_upload(form, "image")
            if data is None:
                return error(400, "issue", issue="type")
            try:
                png = await anyio.to_thread.run_sync(inputs.marked_png, data)
            except inputs.Issue as issue:
                return error(400, "issue", issue=issue.code, **issue.details)
            modes = ORDER if mode == "auto" else (mode,)

            async def lines():
                for m in modes:
                    yield json.dumps(dict(trying=m)) + "\n"
                    message = await anyio.to_thread.run_sync(engine.decode, png, passphrase, m)
                    if message is not None:
                        try:
                            text = message.decode("utf-8")
                        except UnicodeDecodeError:
                            text = None
                        yield json.dumps(dict(found=True, mode=m, profile=MODES[m]["profile"], bytes=len(message),
                                              message=text, message_b64=base64.b64encode(message).decode())) + "\n"
                        return
                    yield json.dumps(dict(nothing=m)) + "\n"
                yield json.dumps(dict(found=False)) + "\n"

            def done():
                decodes["in_flight"] -= 1

            handed_over = True
            return GuardedStream(lines(), decode_slots, done, media_type="application/x-ndjson", headers=NO_STORE)
        finally:
            if not handed_over and reservation is not None:
                limits.give_back(reservation)  # refused before it ran: not counted
                decodes["in_flight"] -= 1
            await form.close()

    routes = [
        Route("/api/status", status),
        Route("/api/quota", quota),
        Route("/api/internal/limits", internal_limits, methods=["GET", "POST"]),
        Route("/api/encode", encode, methods=["POST"]),
        Route("/api/jobs/{job_id}", job_status),
        Route("/api/jobs/{job_id}/cancel", job_cancel, methods=["POST"]),
        Route("/api/jobs/{job_id}/{kind:str}.png", job_result),
        Route("/api/decode", decode, methods=["POST"]),
    ]
    static = os.environ.get("GF_STATIC_DIR")
    if static:
        from starlette.staticfiles import StaticFiles

        routes.append(Mount("/", app=StaticFiles(directory=static, html=True)))
    starlette_app = Starlette(routes=routes)
    starlette_app.state.engine, starlette_app.state.queue = engine, queue
    if os.environ.get("GF_PRELOAD") == "1":
        threading.Thread(target=engine.load, daemon=True).start()

    async def app(scope, receive, send):
        # API paths are plain ASCII: a percent-encoded one (such as /api/internal%2Flimits, which
        # the server would decode before routing) is refused before it reaches a route.
        if scope["type"] == "http" and scope["path"].startswith("/api") and b"%" in scope.get("raw_path", b""):
            await error(404, "not_found")(scope, receive, send)
            return
        await starlette_app(scope, receive, send)

    app.state = starlette_app.state
    return app


def main():
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(build_app(), host=os.environ.get("GF_HOST", "127.0.0.1"), port=int(os.environ.get("GF_PORT", "8790")),
                proxy_headers=False, access_log=False, limit_concurrency=16, timeout_keep_alive=10)


if __name__ == "__main__":
    main()
