from dataclasses import replace

import pytest

from guest_management.core.config import settings
from guest_management.core.exceptions import ConfigurationError


def test_production_rejects_legacy_qr():
    production_settings = replace(
        settings,
        environment="production",
        database_url="postgresql://test",
        qr_secret="q" * 32,
        session_secret="s" * 32,
        scanner_station_secret="x" * 32,
        supabase_url="https://example.supabase.co",
        supabase_anon_key="anon-test-key",
        supabase_secret_key="secret-test-key",
        google_client_id="google-client-id",
        google_client_secret="google-client-secret",
        google_redirect_uri="https://example.com/callback",
        email_provider="test",
        smtp_username="smtp-user",
        smtp_password="smtp-password",
        sender_email="test@example.com",
        allow_legacy_qr=True,
    )

    with pytest.raises(
        ConfigurationError,
        match="ALLOW_LEGACY_QR must be false in production",
    ):
        production_settings.validate()


def test_production_accepts_legacy_qr_disabled():
    production_settings = replace(
        settings,
        environment="production",
        database_url="postgresql://test",
        qr_secret="q" * 32,
        session_secret="s" * 32,
        scanner_station_secret="x" * 32,
        supabase_url="https://example.supabase.co",
        supabase_anon_key="anon-test-key",
        supabase_secret_key="secret-test-key",
        google_client_id="google-client-id",
        google_client_secret="google-client-secret",
        google_redirect_uri="https://example.com/callback",
        email_provider="test",
        smtp_username="smtp-user",
        smtp_password="smtp-password",
        sender_email="test@example.com",
        allow_legacy_qr=False,
    )

    production_settings.validate()