# The engine API for the demo site (server/app.py), as a Cloudflare Container.
# Built from the repository root: see site/wrangler.jsonc (build_context "..").
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app TORCH_HOME=/opt/torch \
    GF_HOST=0.0.0.0 GF_PORT=8790 GF_PRELOAD=1 GF_THREADS=4 GF_TRUST_CF_IP=1
WORKDIR /app

# CPU-only torch first, so the pinned torch==2.7.1 in pyproject is already satisfied.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.7.1 torchvision==0.22.1

COPY pyproject.toml README.md ghostframe.py ./
COPY ghostframe_png ghostframe_png
RUN pip install --no-cache-dir '.[tiled,server]'

COPY experiments experiments
COPY server server

# Fetch both checkpoints at build time (each is checked against its pinned SHA-256),
# so the container never downloads anything and can run without Internet access.
RUN python -c "from server.engine import Engine; Engine().load()" && chmod -R a+rX /opt/torch

USER nobody
EXPOSE 8790
CMD ["python", "-m", "server.app"]
