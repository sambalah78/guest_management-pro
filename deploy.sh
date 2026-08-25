#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${GOOGLE_CLIENT_ID:?GOOGLE_CLIENT_ID is required}"
: "${GOOGLE_CLIENT_SECRET:?GOOGLE_CLIENT_SECRET is required}"
: "${GOOGLE_REDIRECT_URI:?GOOGLE_REDIRECT_URI is required}"
: "${QR_SECRET:?QR_SECRET is required}"
: "${SESSION_SECRET:?SESSION_SECRET is required}"
: "${APP_URL:?APP_URL is required}"

python -m compileall -q guest_management
python -m pytest -q
alembic upgrade head

echo "Application checks passed. Start the web app and email worker as separate processes."
