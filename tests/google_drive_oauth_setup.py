from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/drive",
]

BASE_DIR = Path(__file__).resolve().parents[1]

CLIENT_FILE = Path(
    os.getenv(
        "GOOGLE_DRIVE_OAUTH_CLIENT_FILE",
        "secrets/eventlah-drive-oauth-client.json",
    )
)

TOKEN_FILE = Path(
    os.getenv(
        "GOOGLE_DRIVE_OAUTH_TOKEN_FILE",
        "secrets/eventlah-drive-token.json",
    )
)

if not CLIENT_FILE.is_absolute():
    CLIENT_FILE = BASE_DIR / CLIENT_FILE

if not TOKEN_FILE.is_absolute():
    TOKEN_FILE = BASE_DIR / TOKEN_FILE


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def main() -> None:

    print()
    print("=" * 70)
    print("EventLah Google Drive OAuth Setup")
    print("=" * 70)
    print()

    print("Client file:")
    print(CLIENT_FILE)

    print()
    print("Token file:")
    print(TOKEN_FILE)

    print()

    if not CLIENT_FILE.exists():
        raise FileNotFoundError(
            f"OAuth client file not found:\n{CLIENT_FILE}"
        )

    credentials = None

    # --------------------------------------------------------------
    # Existing token
    # --------------------------------------------------------------

    if TOKEN_FILE.exists():

        print("Existing OAuth token found.")

        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES,
        )

    # --------------------------------------------------------------
    # Refresh existing token
    # --------------------------------------------------------------

    if credentials and credentials.expired:

        if credentials.refresh_token:

            print("Refreshing OAuth token...")

            credentials.refresh(
                Request()
            )

        else:

            print(
                "Existing token has no refresh token."
            )

            credentials = None

    # --------------------------------------------------------------
    # First authorization
    # --------------------------------------------------------------

    if not credentials or not credentials.valid:

        print()
        print(
            "Opening Google authorization..."
        )
        print()

        flow = (
            InstalledAppFlow
            .from_client_secrets_file(
                str(CLIENT_FILE),
                SCOPES,
            )
        )

        credentials = flow.run_local_server(
            port=0,
            access_type="offline",
            prompt="consent",
        )

    # --------------------------------------------------------------
    # Save token
    # --------------------------------------------------------------

    TOKEN_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    TOKEN_FILE.write_text(
        credentials.to_json(),
        encoding="utf-8",
    )

    print()
    print("=" * 70)
    print("Google Drive OAuth SUCCESS")
    print("=" * 70)
    print()
    print(
        f"Token saved to:\n{TOKEN_FILE}"
    )
    print()
    print(
        "Refresh token available:",
        bool(credentials.refresh_token),
    )
    print()


if __name__ == "__main__":
    main()