"""One encode at a time, a visible queue, daily caps, a hard stop, and nothing kept.

Job states, as the site shows them:
  queued -> starting (models loading) -> encoding (progress) -> done | refused | timed_out | cancelled
Inputs live only in memory and are dropped when a job ends. A result is kept until it has been
downloaded or RESULT_TTL has passed, whichever comes first. A queued job whose page stops
polling for ABANDON_AFTER seconds loses its place (the copy: "kept while this tab stays open").
"""
import collections
import datetime as dt
import hashlib
import hmac
import logging
import os
import secrets
import threading
import time
import uuid
from dataclasses import dataclass, field

from server.engine import Refused, difference_png

RESULT_TTL = 15 * 60
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
    result: bytes | None = None
    difference: bytes | None = None
    sha256: str | None = None

    def forget_inputs(self):
        self.cover, self.message, self.passphrase = None, b"", b""


class Limits:
    """Daily encode caps per UTC day: a site-wide number and a few per visitor.

    Visitors are told apart by a keyed hash of their IP address; the key and the counts are
    replaced every UTC day and never written anywhere.
    """

    def __init__(self, site_cap, visitor_cap):
        self.site_cap, self.visitor_cap = site_cap, visitor_cap
        self._day, self._key, self._site, self._visitors = None, b"", 0, collections.Counter()
        self._lock = threading.Lock()

    def _roll(self):
        today = dt.datetime.now(dt.timezone.utc).date()
        if today != self._day:
            self._day, self._key, self._site, self._visitors = today, secrets.token_bytes(32), 0, collections.Counter()

    def visitor(self, address):
        with self._lock:
            self._roll()
            return hmac.new(self._key, address.encode(), hashlib.sha256).hexdigest()[:24]

    def check(self, visitor):
        """None if an encode may start, else 'site_limit' or 'visitor_limit'."""
        with self._lock:
            self._roll()
            if self.site_cap is not None and self._site >= self.site_cap:
                return "site_limit"
            if self.visitor_cap is not None and self._visitors[visitor] >= self.visitor_cap:
                return "visitor_limit"
            return None

    def take(self, visitor):
        with self._lock:
            self._roll()
            self._site += 1
            self._visitors[visitor] += 1

    def give_back(self, visitor):
        with self._lock:
            self._site = max(0, self._site - 1)
            self._visitors[visitor] = max(0, self._visitors[visitor] - 1)

    def site_open(self):
        with self._lock:
            self._roll()
            return self.site_cap is None or self._site < self.site_cap

    def quota(self):
        """The site-wide daily count, read from the same counter `check` and `take` use: encodes
        left today, the cap, and when it resets (the next midnight UTC). None when there is no cap."""
        with self._lock:
            self._roll()
            if self.site_cap is None:
                return None
            tomorrow = dt.datetime.combine(self._day + dt.timedelta(days=1), dt.time(), dt.timezone.utc)
            return dict(left=max(0, self.site_cap - self._site), limit=self.site_cap,
                        resets_at=tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ"))


class Queue:
    def __init__(self, engine, limits, timeout=300, clock=time.monotonic):
        self.engine, self.limits, self.timeout, self.clock = engine, limits, timeout, clock
        self.jobs: dict[str, Job] = {}
        self.waiting: collections.deque[str] = collections.deque()
        self._cv = threading.Condition()
        self._worker = threading.Thread(target=self._run, name="encode-worker", daemon=True)
        self._worker.start()

    # ---- API used by the routes
    def submit(self, mode, visitor, cover, message, passphrase, colour_conversion):
        job = Job(id=uuid.uuid4().hex, mode=mode, visitor=visitor, cover=cover, message=message,
                  passphrase=passphrase, colour_conversion=colour_conversion)
        with self._cv:
            self.limits.take(visitor)
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
            if job.state == "queued":
                self.waiting.remove(job.id)
                self.limits.give_back(job.visitor)
                self._finish(job, "cancelled")
            elif job.state in ("starting", "encoding"):
                job.cancel = True
            return self._view(job)

    def take_result(self, job_id, kind):
        """The exact result bytes. The marked PNG is released (deleted) once it has been fetched."""
        with self._cv:
            job = self.jobs.get(job_id)
            if job is None or job.state != "done":
                return None
            if kind == "difference":
                return job.difference
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
                self.limits.give_back(job.visitor)
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
                if stop.why == "cancelled":
                    self.limits.give_back(job.visitor)
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
