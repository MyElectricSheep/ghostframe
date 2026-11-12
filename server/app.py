"""HTTP API for the Ghostframe demo site.

    .venv/bin/python -m server.app            # http://127.0.0.1:8790 (the site's dev proxy target)

Configuration (environment):
  GF_SITE_DAILY_CAP, GF_VISITOR_DAILY_CAP   encode caps per UTC day ("none" = no cap)
  GF_ENCODE_TIMEOUT_S                       hard stop per encode (default 300)
  GF_TURNSTILE_SECRET                       when set, every encode and decode needs a Turnstile token
  GF_TRUST_CF_IP=1                          take the visitor address from CF-Connecting-IP
  GF_STATIC_DIR                             optionally also serve the built site (site/dist)
  GF_THREADS, GF_PRELOAD=1                  torch threads; load both models at start-up
Nothing is written to disk except short-lived temporary files inside a job.
"""
import base64
import json
import logging
import os
import threading

import anyio
import httpx
from starlette import formparsers
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Mount, Route

from server import inputs
from server.engine import MODES, ORDER, Engine
from server.jobs import Limits, Queue, env_cap

log = logging.getLogger("ghostframe.server")
# Keep uploads in memory: Starlette would otherwise spool files over 1 MB to a temporary file.
formparsers.MultiPartParser.max_file_size = 41 * 1024 * 1024
NO_STORE = {"Cache-Control": "no-store, no-transform", "X-Content-Type-Options": "nosniff"}
DECODE_SLOTS = threading.BoundedSemaphore(2)


def error(status, code, **extra):
    return JSONResponse(dict(error=code, **extra), status_code=status, headers=NO_STORE)


def client_address(request):
    if os.environ.get("GF_TRUST_CF_IP") == "1" and request.headers.get("cf-connecting-ip"):
        return request.headers["cf-connecting-ip"]
    return request.client.host if request.client else "unknown"


async def bot_check(request, form):
    secret = os.environ.get("GF_TURNSTILE_SECRET")
    if not secret:
        return True
    token = form.get("cf-turnstile-response") or ""
    if not token:
        return False
    async with httpx.AsyncClient(timeout=10) as client:
        reply = await client.post("https://challenges.cloudflare.com/turnstile/v0/siteverify",
                                  data=dict(secret=secret, response=token, remoteip=client_address(request)))
    return bool(reply.json().get("success"))


async def read_upload(form, name):
    upload = form.get(name)
    if upload is None or isinstance(upload, str):
        return None
    data = await upload.read(inputs.MAX_UPLOAD + 1)
    return data


def build_app(engine=None, queue=None):
    engine = engine or Engine(threads=int(os.environ.get("GF_THREADS", "4")))
    limits = queue.limits if queue else Limits(env_cap("GF_SITE_DAILY_CAP", 50), env_cap("GF_VISITOR_DAILY_CAP", 3))
    queue = queue or Queue(engine, limits, timeout=float(os.environ.get("GF_ENCODE_TIMEOUT_S", "300")))

    async def internal_limits(request: Request):
        # For the Cloudflare host only (the Worker never forwards /api/internal/*): read today's
        # site-wide count to persist it, or restore it after the container restarts.
        if request.method == "POST":
            body = await request.json()
            return JSONResponse(limits.restore_site_count(str(body.get("day")), body.get("site", 0)), headers=NO_STORE)
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
        form = await request.form(max_files=1, max_fields=8)
        mode = form.get("mode")
        if mode not in MODES:
            return error(400, "bad_mode")
        if not await bot_check(request, form):
            return error(403, "bot_check")
        visitor = limits.visitor(client_address(request))
        limit = limits.check(visitor)
        if limit:
            return error(429, limit)
        message = (form.get("message") or "").encode("utf-8")
        passphrase = (form.get("passphrase") or "").encode("utf-8")
        if not message:
            return error(400, "empty_message")
        if len(message) > MODES[mode]["capacity"]:
            return error(400, "message_too_long", limit=MODES[mode]["capacity"], bytes=len(message))
        if not passphrase:
            return error(400, "empty_passphrase")
        data = await read_upload(form, "image")
        await form.close()
        if data is None:
            return error(400, "issue", issue="type")
        try:
            cover, conversion = await anyio.to_thread.run_sync(inputs.cover, data)
        except inputs.Issue as issue:
            return error(400, "issue", issue=issue.code, **issue.details)
        job = queue.submit(mode, visitor, cover, message, passphrase, conversion)
        return JSONResponse(queue.poll(job.id), status_code=202, headers=NO_STORE)

    async def job_status(request: Request):
        view = queue.poll(request.path_params["job_id"])
        return JSONResponse(view, headers=NO_STORE) if view else error(404, "unknown_job")

    async def job_cancel(request: Request):
        view = queue.cancel(request.path_params["job_id"])
        return JSONResponse(view, headers=NO_STORE) if view else error(404, "unknown_job")

    async def job_result(request: Request):
        kind = "difference" if request.path_params["kind"] == "difference" else "marked"
        data = queue.take_result(request.path_params["job_id"], kind)
        if data is None:
            return error(404, "no_result")
        headers = dict(NO_STORE)
        if kind == "marked":
            headers["Content-Disposition"] = 'attachment; filename="ghostframe-message.png"'
        return Response(data, media_type="image/png", headers=headers)

    async def decode(request: Request):
        form = await request.form(max_files=1, max_fields=8)
        mode = form.get("mode") or "auto"
        if mode != "auto" and mode not in MODES:
            return error(400, "bad_mode")
        if not await bot_check(request, form):
            return error(403, "bot_check")
        passphrase = (form.get("passphrase") or "").encode("utf-8")
        if not passphrase:
            return error(400, "empty_passphrase")
        data = await read_upload(form, "image")
        await form.close()
        if data is None:
            return error(400, "issue", issue="type")
        try:
            png = await anyio.to_thread.run_sync(inputs.marked_png, data)
        except inputs.Issue as issue:
            return error(400, "issue", issue=issue.code, **issue.details)
        modes = ORDER if mode == "auto" else (mode,)

        async def lines():
            await anyio.to_thread.run_sync(DECODE_SLOTS.acquire)
            try:
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
            finally:
                DECODE_SLOTS.release()

        return StreamingResponse(lines(), media_type="application/x-ndjson", headers=NO_STORE)

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
    app = Starlette(routes=routes)
    app.state.engine, app.state.queue = engine, queue
    if os.environ.get("GF_PRELOAD") == "1":
        threading.Thread(target=engine.load, daemon=True).start()
    return app


def main():
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(build_app(), host=os.environ.get("GF_HOST", "127.0.0.1"), port=int(os.environ.get("GF_PORT", "8790")),
                proxy_headers=False, access_log=False)


if __name__ == "__main__":
    main()
