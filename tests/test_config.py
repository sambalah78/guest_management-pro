from dataclasses import replace

import pytest

from guest_management.core.config import settings
from guest_management.core.exceptions import ConfigurationError


def _production_settings(**overrides):
    values = {
        "environment": "production",
        "database_url": "postgresql://test",
        "qr_secret": "q" * 32,
        "session_secret": "s" * 32,
        "session_encryption_key": (
            "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
        ),
        "scanner_station_secret": "x" * 32,
        "supabase_url": "https://example.supabase.co",
        "supabase_anon_key": "anon-test-key",
        "supabase_secret_key": "secret-test-key",
        "google_client_id": "google-client-id",
        "google_client_secret": "google-client-secret",
        "google_redirect_uri": "https://example.com/callback",
        "email_provider": "test",
        "smtp_username": "smtp-user",
        "smtp_password": "smtp-password",
        "sender_email": "test@example.com",
        "allow_legacy_qr": False,
        "app_url": "https://app.example.com",
    }
    values.update(overrides)
    return replace(settings, **values)


def test_production_rejects_legacy_qr():
    production_settings = _production_settings(
        allow_legacy_qr=True,
    )

    with pytest.raises(
        ConfigurationError,
        match="ALLOW_LEGACY_QR must be false in production",
    ):
        production_settings.validate()


def test_production_accepts_legacy_qr_disabled():
    production_settings = _production_settings()

    production_settings.validate()


def test_production_rejects_development_qr_secret():
    production_settings = _production_settings(
        qr_secret="dev-qr-secret-change-me-please-32-characters",
    )

    with pytest.raises(
        ConfigurationError,
        match="development default secrets",
    ):
        production_settings.validate()


def test_production_rejects_development_session_secret():
    production_settings = _production_settings(
        session_secret="dev-session-secret-change-me-please-32-characters",
    )

    with pytest.raises(
        ConfigurationError,
        match="development default secrets",
    ):
        production_settings.validate()


def test_production_rejects_development_session_encryption_key():
    production_settings = _production_settings(
        session_encryption_key=(
            "dev-session-encryption-key-change-me-please-32-characters"
        ),
    )

    with pytest.raises(
        ConfigurationError,
        match="development default secrets",
    ):
        production_settings.validate()


def test_production_rejects_invalid_session_encryption_key():
    production_settings = _production_settings(
        session_encryption_key="not-a-valid-base64-key-" + "x" * 20,
    )

    with pytest.raises(
        ConfigurationError,
        match="URL-safe base64",
    ):
        production_settings.validate()


def test_production_rejects_wrong_length_session_encryption_key():
    production_settings = _production_settings(
        session_encryption_key="c2hvcnQ=",
    )

    with pytest.raises(
        ConfigurationError,
        match="exactly 32 bytes",
    ):
        production_settings.validate()


def test_production_rejects_localhost_app_url():
    production_settings = _production_settings(
        app_url="http://localhost:3000",
    )

    with pytest.raises(
        ConfigurationError,
        match="APP_URL must use HTTPS",
    ):
        production_settings.validate()


def test_production_rejects_non_https_app_url():
    production_settings = _production_settings(
        app_url="http://eventlah.example.com",
    )

    with pytest.raises(
        ConfigurationError,
        match="APP_URL must use HTTPS",
    ):
        production_settings.validate()


def test_production_rejects_localhost_google_redirect_uri():
    production_settings = _production_settings(
        google_redirect_uri=(
            "http://localhost:8000/api/auth/google/callback"
        ),
    )

    with pytest.raises(
        ConfigurationError,
        match="GOOGLE_REDIRECT_URI must use HTTPS",
    ):
        production_settings.validate()


def test_production_rejects_non_https_google_redirect_uri():
    production_settings = _production_settings(
        google_redirect_uri=(
            "http://app.example.com/api/auth/google/callback"
        ),
    )

    with pytest.raises(
        ConfigurationError,
        match="GOOGLE_REDIRECT_URI must use HTTPS",
    ):
        production_settings.validate()
