#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${APP_URL:?APP_URL is required}"
: "${QR_SECRET:?QR_SECRET is required}"
: "${SESSION_SECRET:?SESSION_SECRET is required}"
: "${SESSION_ENCRYPTION_KEY:?SESSION_ENCRYPTION_KEY is required}"
: "${SCANNER_STATION_SECRET:?SCANNER_STATION_SECRET is required}"
: "${SUPABASE_URL:?SUPABASE_URL is required}"
: "${SUPABASE_ANON_KEY:?SUPABASE_ANON_KEY is required}"
: "${SUPABASE_SECRET_KEY:?SUPABASE_SECRET_KEY is required}"
: "${EMAIL_PROVIDER:?EMAIL_PROVIDER is required}"
: "${SMTP_HOST:?SMTP_HOST is required}"
: "${SMTP_PORT:?SMTP_PORT is required}"
: "${SMTP_USERNAME:?SMTP_USERNAME is required}"
: "${SMTP_PASSWORD:?SMTP_PASSWORD is required}"
: "${SENDER_EMAIL:?SENDER_EMAIL is required}"

python -m compileall -q guest_management
python -m pytest -q
python -m alembic upgrade head

echo "Application checks passed. Start the web app and email worker as separate processes."
