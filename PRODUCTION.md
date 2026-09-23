# EventLah / Guest Management – Production Guide

## Architecture

- Reflex frontend/backend application
- PostgreSQL as the source-of-truth database
- Google OAuth for administrator authentication
- Google Drive (`drive.file`) for files, imports, logos and exports
- Gmail SMTP for email delivery
- SQLAlchemy repositories/services for application data access
- Durable email queue and independent email worker

## Required production environment

```text
ENVIRONMENT=production
APP_URL=https://your-domain.example
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SECRET_KEY=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://your-domain.example/api/auth/google/callback
GOOGLE_DRIVE_ROOT_FOLDER_ID=...
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
```

## Database

Run the SQLAlchemy/Alembic migration before accepting traffic. For a first deployment, the application can initialize the schema with `python -m guest_management.database_init`, but a real production rollout should use Alembic and a database backup/restore plan.

## Google OAuth

Create a Google Cloud Web Application OAuth client. Add the exact callback URL shown in `GOOGLE_REDIRECT_URI`. The application requests `openid email profile` plus `drive.file`. The authenticated user's Drive refresh token is encrypted at rest using a key derived from `SESSION_SECRET`.

## Security

- Never commit `.env` or production secrets.
- Rotate any credentials previously exposed in older archives.
- Keep `SESSION_SECRET`, `QR_SECRET`, `SESSION_ENCRYPTION_KEY`, and `SCANNER_STATION_SECRET` stable after deployment unless intentionally rotating them through the appropriate recovery procedure.
- `SESSION_ENCRYPTION_KEY` must be URL-safe Base64 and decode to exactly 32 bytes.
- Production configuration rejects the development default secrets.
- `APP_URL` and `GOOGLE_REDIRECT_URI` must use HTTPS and must not point to localhost in production.
- Keep `ALLOW_LEGACY_QR=false` in production.
- Use HTTPS in production.
- Use a managed PostgreSQL service or a hardened PostgreSQL server with automated backups.
- Use a separate worker process for email jobs.
- Never expose `SUPABASE_SECRET_KEY` or `SUPABASE_SERVICE_ROLE_KEY` to browser/client-side code.
- `SUPABASE_SERVICE_ROLE_KEY` is used only by the read-only production authentication smoke test.
