# Version history:
# 1.1.0 (2026-09-04) - Render deploy of 37cc54a1 failed at startup: arena_provider.install()
#   creates its default runtime/arena_intelligence_deliveries.sqlite parent dir on first run
#   (db_path.parent.mkdir), but USER 65532 had no write access to /app - COPY leaves /app
#   root-owned. Fixed by pre-creating runtime/ and chown'ing it to 65532 while still root,
#   before dropping privileges. Non-root execution preserved (USER 65532 unchanged).
#   Note: without a persistent disk mounted over /app/runtime (see deploy/render.yaml's
#   ARENA_DELIVERIES_PATH), this directory's contents (delivery idempotency state) are lost
#   on every restart/redeploy - that's a Render config decision, not fixed here.
# 1.0.0 (2026-09-04) - provider-neutral OCI image.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
RUN mkdir -p /app/runtime && chown -R 65532:65532 /app/runtime
USER 65532
EXPOSE 8080
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8080"]
