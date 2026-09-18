"""Central application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

from .exceptions import ConfigurationError


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str
    app_url: str
    database_url: str

    # Supabase infrastructure
    # Kept for existing application integrations.
    supabase_url: str
    supabase_anon_key: str
    supabase_secret_key: str

    # QR configuration
    qr_secret: str

    # Email configuration
    email_provider: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    sender_email: str

    # Google OAuth / Drive
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    google_drive_root_folder_id: str

    # Session configuration
    session_secret: str
    session_ttl_seconds: int

    # Scanner configuration
    scanner_station_secret: str

    # Email worker configuration
    email_worker_batch_size: int
    email_worker_interval_seconds: float
    email_max_attempts: int

    # QR compatibility
    allow_legacy_qr: bool

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {
            "production",
            "prod",
        }

    def validate(self) -> None:
        required = {
            "DATABASE_URL": self.database_url,
            "QR_SECRET": self.qr_secret,
            "SESSION_SECRET": self.session_secret,
            "SCANNER_STATION_SECRET": self.scanner_station_secret,
        }

        if self.is_production:
            required.update(
                {
                    # Existing Supabase configuration
                    "SUPABASE_URL": self.supabase_url,
                    "SUPABASE_ANON_KEY": self.supabase_anon_key,
                    "SUPABASE_SECRET_KEY": self.supabase_secret_key,

                    # Google
                    "GOOGLE_CLIENT_ID": self.google_client_id,
                    "GOOGLE_CLIENT_SECRET": self.google_client_secret,
                    "GOOGLE_REDIRECT_URI": self.google_redirect_uri,

                    # Email
                    "EMAIL_PROVIDER": self.email_provider,
                    "SMTP_USERNAME": self.smtp_username,
                    "SMTP_PASSWORD": self.smtp_password,
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

        if len(self.scanner_station_secret) < 32:
            raise ConfigurationError(
                "SCANNER_STATION_SECRET must contain at least 32 characters"
            )
        if self.is_production and self.allow_legacy_qr:
            raise ConfigurationError(
                "ALLOW_LEGACY_QR must be false in production"
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
            "",
        ),

        # Supabase
        supabase_url=_env(
            "SUPABASE_URL",
        ),

        supabase_anon_key=_env(
            "SUPABASE_ANON_KEY",
        ),

        supabase_secret_key=_env(
            "SUPABASE_SECRET_KEY",
        ),

        # QR
        qr_secret=_env(
            "QR_SECRET",
            "dev-qr-secret-change-me-please-32-characters",
        ),

        # Gmail SMTP
        email_provider=_env(
            "EMAIL_PROVIDER",
            "gmail",
        ).lower(),

        smtp_host=_env(
            "SMTP_HOST",
            "smtp.gmail.com",
        ),

        smtp_port=max(
            1,
            integer(
                "SMTP_PORT",
                587,
            ),
        ),

        smtp_username=_env(
            "SMTP_USERNAME",
        ),

        smtp_password=_env(
            "SMTP_PASSWORD",
        ),

        sender_email=_env(
            "SENDER_EMAIL",
        ),

        # Google OAuth / Drive
        google_client_id=_env(
            "GOOGLE_CLIENT_ID",
        ),

        google_client_secret=_env(
            "GOOGLE_CLIENT_SECRET",
        ),

        google_redirect_uri=_env(
            "GOOGLE_REDIRECT_URI",
            "http://localhost:8000/api/auth/google/callback",
        ),

        google_drive_root_folder_id=_env(
            "GOOGLE_DRIVE_ROOT_FOLDER_ID",
        ),

        # Session
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

        # Scanner
        scanner_station_secret=_env(
            "SCANNER_STATION_SECRET",
            "",
        ),

        # Email worker
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

        # QR compatibility
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