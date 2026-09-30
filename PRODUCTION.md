# EventLah – Production Guide

## Architecture

- Reflex frontend/backend application
- PostgreSQL via Supabase as the source-of-truth database
- Supabase Authentication with server-side application sessions
- Supabase Storage for application file storage
- SMTP email delivery
- Durable email queue and independent email worker
- SQLAlchemy repositories/services for application data access
- Signed QR codes for guest check-in
- Scanner station authentication for event-day scanning
- Reflex Cloud for production hosting

## Required production environment

```text
ENVIRONMENT=production
APP_URL=https://eventlah.reflex.dev
API_URL=https://eventlah.reflex.dev

DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SECRET_KEY=...

QR_SECRET=...
SESSION_SECRET=...
SESSION_ENCRYPTION_KEY=...
SCANNER_STATION_SECRET=...

EMAIL_PROVIDER=gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=...
SMTP_PASSWORD=...
SENDER_EMAIL=...

ALLOW_LEGACY_QR=false