#!/usr/bin/env sh

. ./.venv/bin/activate
./.venv/bin/gunicorn -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --access-logfile - sl_statistics_backend:app