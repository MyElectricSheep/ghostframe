# The engine API for the demo site (server/app.py), as a Cloudflare Container.
# Built from the repository root: see site/wrangler.jsonc (build_context "..").
# python:3.12-slim, pinned by its multi-platform index digest (resolved 2026-11-12; Dependabot bumps it).
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app TORCH_HOME=/opt/torch \
    GF_HOST=0.0.0.0 GF_PORT=8790 GF_PRELOAD=1 GF_THREADS=4 GF_TRUST_CF_IP=1
WORKDIR /app

# Every dependency from the hashed lock (CPU-only torch from the PyTorch index). --no-deps: nothing
# outside the lock is installed. The project itself is not pip-installed: PYTHONPATH=/app finds it,
# so no unpinned build backend is downloaded either.
COPY server/requirements.lock server/requirements.lock
RUN pip install --no-cache-dir --require-hashes --no-deps -r server/requirements.lock \
        --index-url https://pypi.org/simple --extra-index-url https://download.pytorch.org/whl/cpu

COPY ghostframe.py ./
COPY ghostframe_png ghostframe_png
# Only the legacy modules the Short (legacy-v1) mode imports, directly or indirectly.
COPY experiments/message_cli.py experiments/alignment_search.py experiments/crop_robustness.py \
     experiments/encoder_screen.py experiments/extended.py experiments/frame_keys.py \
     experiments/jpeg_capacity.py experiments/jpeg_carrier.py experiments/jpeg_frame.py \
     experiments/luminance.py experiments/robustness.py experiments/tiled.py experiments/tiled_ecc.py \
     experiments/
COPY server server

# Fetch both checkpoints at build time (each is checked against its pinned SHA-256), and check that
# Short mode's imports resolve, so the container never downloads anything and runs without Internet.
RUN python -c "import experiments.message_cli; from server.engine import Engine; Engine().load()" \
    && chmod -R a+rX /opt/torch

USER nobody
EXPOSE 8790
CMD ["python", "-m", "server.app"]
