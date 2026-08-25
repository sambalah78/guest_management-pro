"""Central application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

from .exceptions import ConfigurationError


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _email_list(name: str) -> tuple[str, ...]:
    """Read a comma-separated email allowlist."""
    raw = _env(name)

    if not raw:
        return ()

    return tuple(
        email.strip().lower()
        for email in raw.split(",")
        if email.strip()
    )


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str
    app_url: str
    database_url: str

    qr_secret: str

    sendgrid_api_key: str
    sender_email: str

    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str

    google_drive_root_folder_id: str

    # Event creator allowlist
    event_creator_emails: tuple[str, ...]

    session_secret: str
    session_ttl_seconds: int

    email_worker_batch_size: int
    email_worker_interval_seconds: float
    email_max_attempts: int

    allow_legacy_qr: bool

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {
            "production",
            "prod",
        }

    def is_event_creator(self, email: str | None) -> bool:
        """Return True when the email is allowed to create events."""
        if not email:
            return False

        return email.strip().lower() in self.event_creator_emails

    def validate(self) -> None:
        required = {
            "DATABASE_URL": self.database_url,
            "QR_SECRET": self.qr_secret,
            "SESSION_SECRET": self.session_secret,
        }

        if self.is_production:
            required.update(
                {
                    "GOOGLE_CLIENT_ID": self.google_client_id,
                    "GOOGLE_CLIENT_SECRET": self.google_client_secret,
                    "GOOGLE_REDIRECT_URI": self.google_redirect_uri,
                    "SENDGRID_API_KEY": self.sendgrid_api_key,
                    "SENDER_EMAIL": self.sender_email,
                }
            )

        missing = [
            key
            for key, value in required.items()
            if not value
        ]

        if missing:
            raise ConfigurationError(
                "Missing required environment variables: "
                + ", ".join(missing)
            )

        if len(self.qr_secret) < 32:
            raise ConfigurationError(
                "QR_SECRET must contain at least 32 characters"
            )

        if len(self.session_secret) < 32:
            raise ConfigurationError(
                "SESSION_SECRET must contain at least 32 characters"
            )


def load_settings() -> Settings:

    def integer(name: str, default: int) -> int:
        try:
            return int(
                _env(name, str(default))
            )
        except ValueError as exc:
            raise ConfigurationError(
                f"{name} must be an integer"
            ) from exc

    def number(name: str, default: float) -> float:
        try:
            return float(
                _env(name, str(default))
            )
        except ValueError as exc:
            raise ConfigurationError(
                f"{name} must be a number"
            ) from exc

    return Settings(
        environment=_env(
            "ENVIRONMENT",
            "development",
        ),

        app_url=_env(
            "APP_URL",
            "http://localhost:3000",
        ).rstrip("/"),

        database_url=_env(
            "DATABASE_URL",
            "sqlite:///./guest_management.db",
        ),

        qr_secret=_env(
            "QR_SECRET",
            "dev-qr-secret-change-me-please-32-characters",
        ),

        sendgrid_api_key=_env(
            "SENDGRID_API_KEY"
        ),

        sender_email=_env(
            "SENDER_EMAIL"
        ),

        google_client_id=_env(
            "GOOGLE_CLIENT_ID"
        ),

        google_client_secret=_env(
            "GOOGLE_CLIENT_SECRET"
        ),

        google_redirect_uri=_env(
            "GOOGLE_REDIRECT_URI",
            "http://localhost:8000/api/auth/google/callback",
        ),

        google_drive_root_folder_id=_env(
            "GOOGLE_DRIVE_ROOT_FOLDER_ID"
        ),

        event_creator_emails=_email_list(
            "EVENT_CREATOR_EMAILS"
        ),

        session_secret=_env(
            "SESSION_SECRET",
            "dev-session-secret-change-me-please-32-characters",
        ),

        session_ttl_seconds=max(
            300,
            integer(
                "SESSION_TTL_SECONDS",
                28800,
            ),
        ),

        email_worker_batch_size=max(
            1,
            min(
                integer(
                    "EMAIL_WORKER_BATCH_SIZE",
                    50,
                ),
                500,
            ),
        ),

        email_worker_interval_seconds=max(
            1.0,
            number(
                "EMAIL_WORKER_INTERVAL_SECONDS",
                2.0,
            ),
        ),

        email_max_attempts=max(
            1,
            min(
                integer(
                    "EMAIL_MAX_ATTEMPTS",
                    5,
                ),
                20,
            ),
        ),

        allow_legacy_qr=_env(
            "ALLOW_LEGACY_QR",
            "false",
        ).lower()
        in {
            "1",
            "true",
            "yes",
        },
    )


settings = load_settings()