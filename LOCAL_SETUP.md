# EventLah Guest Management – Windows Local Setup

This version has **no Supabase dependency**.

Local architecture:

- Reflex web app: `http://localhost:3000`
- Reflex backend/API: `http://localhost:8000`
- SQLite database: `guest_management.db`
- Google OAuth: Google Cloud OAuth client
- Google Drive: authenticated user's Drive (`drive.file` scope)
- Gmail SMTP: optional for local testing, required when email delivery is enabled

## 1. Install Python

Use Python 3.11 or 3.12. On Windows, verify the Python launcher:

```powershell
py --version
```

If `py` is not available, install Python from the official Python Windows installer and enable **Add python.exe to PATH**.

## 2. Extract the project

Extract `guest_management_production_v2.zip`, then open PowerShell in the project root:

```powershell
cd "C:\path\to\guest_management"
```

You should see `requirements.txt`, `rxconfig.py`, and the `guest_management` folder.

## 3. Create the virtual environment

```powershell
py -3.11 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the script:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again.

Verify:

```powershell
python --version
python -m pip --version
```

## 4. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
pip check
```

Expected final line from `pip check`:

```text
No broken requirements found.
```

## 5. Create local environment file

```powershell
Copy-Item .env.example .env
```

Generate two secrets:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Run it twice and use different values for `QR_SECRET` and `SESSION_SECRET`.

For local development, keep:

```text
ENVIRONMENT=development
APP_URL=http://localhost:3000
DATABASE_URL=sqlite:///./guest_management.db
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
ALLOW_LEGACY_QR=false
```

## 6. Configure Google OAuth

Open Google Cloud Console and select/create the project used by EventLah.

Enable:

- Google Identity / OAuth consent configuration
- Google Drive API

Create an OAuth client:

```text
APIs & Services
→ Credentials
→ Create Credentials
→ OAuth client ID
→ Web application
```

Add this exact local redirect URI:

```text
http://localhost:8000/api/auth/google/callback
```

Put the generated values in `.env`:

```text
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

The application requests these scopes:

```text
openid
email
profile
https://www.googleapis.com/auth/drive.file
```

For a Google account used during development, complete the OAuth consent/test-user setup in Google Cloud if the OAuth app is still in testing.

## 7. Initialize the local database

Run:

```powershell
python -m guest_management.database_init
```

You should see:

```text
Database schema initialized.
```

This creates `guest_management.db` in the project root.

## 8. Run automated tests

```powershell
pytest -q
```

Do this before starting the application.

## 9. Start EventLah

```powershell
reflex run
```

Open:

```text
http://localhost:3000
```

The Reflex backend should be available at:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:3000/health
```

## 10. Test Google login

Open:

```text
http://localhost:3000/login
```

Click:

```text
Continue with Google
```

Google redirects to:

```text
http://localhost:8000/api/auth/google/callback
```

After successful authentication you should return to:

```text
http://localhost:3000/events
```

The application creates a local `users` row and an encrypted Google Drive refresh-token record.

## 11. Test Google Drive

After signing in, the application has permission to create/read files created by EventLah using the `drive.file` scope.

When file-upload features call `GoogleDriveService`, EventLah creates an `EventLah` folder in the signed-in user's Google Drive if one does not already exist.

## 12. Test guest/check-in flow

Create a test event, import a small guest list, then verify:

1. Guest appears in the database.
2. A signed QR is generated.
3. Scanner accepts the signed QR.
4. Guest becomes `Present`.
5. A `checkins` record is created.
6. A second scan returns `already_checked_in`.

Do not enable legacy/plain guest-ID QR codes.

## 13. Test email locally (optional)

Set these in `.env`:

```text
EMAIL_PROVIDER=gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-gmail-address@example.com
SMTP_PASSWORD=your-gmail-app-password
SENDER_EMAIL=your-gmail-address@example.com
```

Then run the worker separately:

```powershell
python -m guest_management.workers.email_worker
```

The web application queues email jobs; the worker sends them asynchronously.

## 14. Two-terminal workflow

Terminal 1 – web app:

```powershell
.\.venv\Scripts\Activate.ps1
reflex run
```

Terminal 2 – email worker:

```powershell
.\.venv\Scripts\Activate.ps1
python -m guest_management.workers.email_worker
```

The worker is not required if you are not testing email.

## 15. Local database inspection

The SQLite file is:

```text
guest_management.db
```

It is ignored by Git.

For production, replace `DATABASE_URL` with PostgreSQL, for example:

```text
DATABASE_URL=postgresql+psycopg://user:password@host:5432/eventlah
```

Do not use SQLite for a multi-instance production deployment.

## 16. Before production

Do not deploy until all of these pass:

- Google login works
- Role/authorization tests pass
- 3,000 guest import test passes
- concurrent duplicate check-in test passes
- voucher transaction concurrency test passes
- email queue test passes
- Gmail SMTP delivery test passes
- PostgreSQL backup/restore has been tested
- HTTPS is enabled
- production `SESSION_SECRET` and `QR_SECRET` are long random values
- `.env` is not committed
