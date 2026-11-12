"""One encode at a time, a visible queue, daily caps, a hard stop, and nothing kept.

Job states, as the site shows them:
  queued -> starting (models loading) -> encoding (progress) -> done | refused | timed_out | cancelled
Inputs live only in memory and are dropped when a job ends. A result is kept until it has been
downloaded or RESULT_TTL has passed, whichever comes first. A queued job whose page stops
polling for ABANDON_AFTER seconds loses its place (the copy: "kept while this tab stays open").
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import hmac
import ipaddress
import logging
import os
import secrets
import threading
import time
import uuid
from dataclasses import dataclass, field

from server.engine import Refused, difference_png

RESULT_TTL = 15 * 60
MAX_WAITING = 10  # queued jobs plus reservations not yet submitted; beyond this, 'busy'
ABANDON_AFTER = 60
SLOW_AFTER = 120


class Stopped(Exception):
    def __init__(self, why):
        super().__init__(why)
        self.why = why


@dataclass
class Job:
    id: str
    mode: str
    visitor: str
    cover: object = None
    message: bytes = b""
    passphrase: bytes = b""
    colour_conversion: str | None = None
    state: str = "queued"
    progress: float = 0.0
    created: float = field(default_factory=time.monotonic)
    started: float | None = None
    finished: float | None = None
    last_poll: float = field(default_factory=time.monotonic)
    cancel: bool = False
    reservation: Reservation | None = None
    result: bytes | None = None
    difference: bytes | None = None
    sha256: str | None = None

    def forget_inputs(self):
        self.cover, self.message, self.passphrase = None, b"", b""


def visitor_address(address):
    """The address that identifies a visitor: IPv4 as is, IPv6 cut to its /64 (one household or
    host usually holds a whole /64, so counting single IPv6 addresses would be trivial to dodge)."""
    try:
        ip = ipaddress.ip_address(address.strip())
    except ValueError:
        return address
    if ip.version == 6:
        if ip.ipv4_mapped is not None:
            return str(ip.ipv4_mapped)
        return str(ipaddress.ip_network(f"{ip}/64", strict=False).network_address) + "/64"
    return str(ip)


@dataclass
class Reservation:
    """One counted encode or decode, taken before the upload is read. Released (given back) if
    the request is refused before any work starts."""
    kind: str
    visitor: str
    day: dt.date


class Limits:
    """Daily caps per UTC day, a site-wide number and a few per visitor, for encodes and decodes.

    Visitors are told apart by a keyed hash of their IP address (IPv6: its /64); the key and the
    counts are replaced every UTC day and never written anywhere.
    """

    def __init__(self, site_cap, visitor_cap, decode_site_cap=None, decode_visitor_cap=None):
        self.site_cap, self.visitor_cap = site_cap, visitor_cap
        self.caps = dict(encode=(site_cap, visitor_cap), decode=(decode_site_cap, decode_visitor_cap))
        self._day, self._key = None, b""
        self._site = dict(encode=0, decode=0)
        self._visitors = dict(encode=collections.Counter(), decode=collections.Counter())
        self._lock = threading.Lock()

    def _roll(self):
        today = dt.datetime.now(dt.timezone.utc).date()
        if today != self._day:
            self._day, self._key = today, secrets.token_bytes(32)
            self._site = dict(encode=0, decode=0)
            self._visitors = dict(encode=collections.Counter(), decode=collections.Counter())

    def visitor(self, address):
        with self._lock:
            self._roll()
            return hmac.new(self._key, visitor_address(address).encode(), hashlib.sha256).hexdigest()[:24]

    def _refusal(self, kind, visitor):
        site_cap, visitor_cap = self.caps[kind]
        prefix = "" if kind == "encode" else "read_"
        if site_cap is not None and self._site[kind] >= site_cap:
            return prefix + "site_limit"
        if visitor_cap is not None and self._visitors[kind][visitor] >= visitor_cap:
            return prefix + "visitor_limit"
        return None

    def check(self, visitor, kind="encode"):
        """None if an encode (or decode) may start, else the refusal code: 'site_limit' or
        'visitor_limit' for encodes, 'read_site_limit' or 'read_visitor_limit' for decodes."""
        with self._lock:
            self._roll()
            return self._refusal(kind, visitor)

    def reserve(self, visitor, kind="encode"):
        """Check and count in one step: a Reservation, or the refusal code. Callers hold no lock."""
        with self._lock:
            self._roll()
            refusal = self._refusal(kind, visitor)
            if refusal:
                return refusal
            self._site[kind] += 1
            self._visitors[kind][visitor] += 1
            return Reservation(kind, visitor, self._day)

    def give_back(self, reservation):
        """Undo one count, only on the UTC day it was taken (yesterday's counts are gone)."""
        with self._lock:
            self._roll()
            if reservation.day != self._day:
                return
            kind = reservation.kind
            self._site[kind] = max(0, self._site[kind] - 1)
            self._visitors[kind][reservation.visitor] = max(0, self._visitors[kind][reservation.visitor] - 1)

    def site_open(self):
        with self._lock:
            self._roll()
            return self.site_cap is None or self._site["encode"] < self.site_cap

    def site_count(self):
        """Today's site-wide counts, for the host to persist (the per-visitor counts are not exported)."""
        with self._lock:
            self._roll()
            return dict(day=self._day.isoformat(), site=self._site["encode"], read=self._site["decode"])

    def restore_site_count(self, day, site, read=0):
        """Restore persisted site-wide counts after a restart. Ignored unless they are today's;
        never lowers a live count."""
        with self._lock:
            self._roll()
            if day == self._day.isoformat():
                self._site["encode"] = max(self._site["encode"], int(site))
                self._site["decode"] = max(self._site["decode"], int(read))
            return dict(day=self._day.isoformat(), site=self._site["encode"], read=self._site["decode"])

    def quota(self):
        """The site-wide daily encode count, read from the same counter `reserve` uses: encodes
        left today, the cap, and when it resets (the next midnight UTC). None when there is no cap."""
        with self._lock:
            self._roll()
            if self.site_cap is None:
                return None
            tomorrow = dt.datetime.combine(self._day + dt.timedelta(days=1), dt.time(), dt.timezone.utc)
            return dict(left=max(0, self.site_cap - self._site["encode"]), limit=self.site_cap,
                        resets_at=tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ"))


class Queue:
    def __init__(self, engine, limits, timeout=300, clock=time.monotonic, max_waiting=MAX_WAITING):
        self.engine, self.limits, self.timeout, self.clock = engine, limits, timeout, clock
        self.max_waiting, self._reserved = max_waiting, 0
        self.jobs: dict[str, Job] = {}
        self.waiting: collections.deque[str] = collections.deque()
        self._cv = threading.Condition()
        self._worker = threading.Thread(target=self._run, name="encode-worker", daemon=True)
        self._worker.start()

    # ---- API used by the routes
    def reserve(self, visitor):
        """Atomically check the daily caps and the waiting room, and count one encode.

        Returns a Reservation to pass to submit() (or release() if the request is refused before
        it starts), or a refusal code: 'site_limit', 'visitor_limit' or 'busy'."""
        with self._cv:
            if len(self.waiting) + self._reserved >= self.max_waiting:
                return "busy"
            reservation = self.limits.reserve(visitor)
            if isinstance(reservation, Reservation):
                self._reserved += 1
            return reservation

    def release(self, reservation):
        with self._cv:
            self._reserved -= 1
            self.limits.give_back(reservation)

    def submit(self, reservation, mode, cover, message, passphrase, colour_conversion):
        job = Job(id=uuid.uuid4().hex, mode=mode, visitor=reservation.visitor, cover=cover, message=message,
                  passphrase=passphrase, colour_conversion=colour_conversion, reservation=reservation)
        with self._cv:
            self._reserved -= 1
            self.jobs[job.id] = job
            self.waiting.append(job.id)
            self._cv.notify()
        return job

    def poll(self, job_id):
        with self._cv:
            self._sweep()
            job = self.jobs.get(job_id)
            if job is None:
                return None
            job.last_poll = self.clock()
            return self._view(job)

    def cancel(self, job_id):
        with self._cv:
            job = self.jobs.get(job_id)
            if job is None:
                return None
            if job.state == "queued":  # never started: the encode is given back
                self.waiting.remove(job.id)
                self.limits.give_back(job.reservation)
                self._finish(job, "cancelled")
            # A started encode stays counted when cancelled: the CPU was spent, and refunding it
            # would let cancel-and-resubmit run the encoder without limit.
            elif job.state in ("starting", "encoding"):
                job.cancel = True
            return self._view(job)

    def take_result(self, job_id, kind):
        """The exact result bytes. Each image is released (deleted) once it has been fetched."""
        with self._cv:
            job = self.jobs.get(job_id)
            if job is None or job.state != "done":
                return None
            if kind == "difference":
                data, job.difference = job.difference, None
            else:
                data, job.result = job.result, None
            return data

    # ---- internals
    def _position(self, job):
        try:
            ahead = list(self.waiting).index(job.id)
        except ValueError:
            return 0
        running = any(j.state in ("starting", "encoding") for j in self.jobs.values())
        return ahead + (1 if running else 0)

    def _view(self, job):
        now = self.clock()
        end = job.finished or now
        view = dict(id=job.id, mode=job.mode, state=job.state, position=self._position(job) if job.state == "queued" else 0,
                    progress=round(job.progress, 4), elapsed_s=round(end - job.created, 1),
                    slow=job.state == "encoding" and job.started is not None and now - job.started >= SLOW_AFTER,
                    colour_conversion=job.colour_conversion)
        if job.state == "done":
            view.update(sha256=job.sha256, result_available=job.result is not None)
        return view

    def _finish(self, job, state):
        job.state, job.finished = state, self.clock()
        job.forget_inputs()

    def _sweep(self):
        now = self.clock()
        for job in list(self.jobs.values()):
            if job.state == "queued" and now - job.last_poll > ABANDON_AFTER:
                self.waiting.remove(job.id)
                self.limits.give_back(job.reservation)
                self._finish(job, "cancelled")
            if job.finished is not None and now - job.finished > RESULT_TTL:
                del self.jobs[job.id]

    def _run(self):
        while True:
            with self._cv:
                while not self.waiting:
                    self._cv.wait(timeout=5)
                    self._sweep()
                job = self.jobs[self.waiting.popleft()]
                job.state = "encoding" if self.engine.ready.is_set() else "starting"
                job.started = self.clock()
            self._encode(job)

    def _encode(self, job):
        deadline = job.started + self.timeout

        def progress(fraction):
            if job.cancel:
                raise Stopped("cancelled")
            if self.clock() > deadline:
                raise Stopped("timed_out")
            job.progress = fraction

        try:
            self.engine.load()
            with self._cv:
                if job.state == "starting":
                    job.state, job.started = "encoding", self.clock()
                    deadline = job.started + self.timeout
            if job.cancel:
                raise Stopped("cancelled")
            data = self.engine.encode(job.cover, job.message, job.passphrase, job.mode, progress=progress)
            difference = difference_png(job.cover, data, job.mode)
            with self._cv:
                job.result, job.difference = data, difference
                job.sha256 = hashlib.sha256(data).hexdigest()
                job.progress = 1.0
                self._finish(job, "done")
        except Stopped as stop:
            with self._cv:
                self._finish(job, stop.why)
        except Refused:
            with self._cv:
                self._finish(job, "refused")
        except Exception:  # keep the worker alive; the page shows a generic failure
            logging.getLogger("ghostframe.server").exception("encode failed")
            with self._cv:
                self._finish(job, "failed")


def env_cap(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return None if value.strip().lower() in ("", "none", "off") else int(value)
