# EventLah / Guest Management – Production Guide

## Architecture

- Reflex frontend/backend application
- PostgreSQL as the source-of-truth database
- Google OAuth for administrator authentication
- Google Drive (`drive.file`) for files, imports, logos and exports
- SendGrid for email delivery
- SQLAlchemy repositories/services; no Supabase dependency
- Durable email queue and independent email worker

## Required production environment

```text
ENVIRONMENT=production
APP_URL=https://your-domain.example
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://your-domain.example/api/auth/google/callback
QR_SECRET=...
SESSION_SECRET=...
SENDGRID_API_KEY=...
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
- Keep `SESSION_SECRET` and `QR_SECRET` stable after deployment.
- Use HTTPS in production.
- Use a managed PostgreSQL service or a hardened PostgreSQL server with automated backups.
- Use a separate worker process for email jobs.
