#!/usr/bin/env bash
# Entrypoint for self-hosted platforms (Render / Railway / VPS).
# They inject the public port via $PORT.
set -e
exec uvicorn server:app --host 0.0.0.0 --port "${PORT:-8001}"
