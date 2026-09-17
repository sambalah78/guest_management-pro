from unittest.mock import MagicMock, patch

from guest_management.services.scanner_station_auth_service import (
    ScannerStationAuthService,
)
from guest_management.repositories.scanner_repository import ScannerRepository


def test_authenticate_returns_active_scanner():
    repo = MagicMock()

    scanner = {
        "id": 1,
        "event_id": 10,
        "device_id": "EL-ABC",
        "device_name": "Registration Desk 1",
        "is_active": True,
    }

    repo.get_by_access_token_hash.return_value = scanner

    service = ScannerStationAuthService(repo=repo)

    with patch(
            "guest_management.services.scanner_station_auth_service.settings"
    ) as mocked_settings:
        mocked_settings.scanner_station_secret = "x" * 32

        result = service.authenticate(10, "ELST_test-token")

    assert result == scanner
    repo.get_by_access_token_hash.assert_called_once()


def test_authenticate_rejects_empty_token():
    repo = MagicMock()
    service = ScannerStationAuthService(repo=repo)

    assert service.authenticate(10, "") is None
    repo.get_by_access_token_hash.assert_not_called()


def test_authenticate_rejects_unknown_token():
    repo = MagicMock()
    repo.get_by_access_token_hash.return_value = None

    service = ScannerStationAuthService(repo=repo)

    with patch(
            "guest_management.services.scanner_station_auth_service.settings"
    ) as mocked_settings:
        mocked_settings.scanner_station_secret = "x" * 32

        result = service.authenticate(10, "ELST_test-token")

    assert result is None


def test_authenticate_rejects_inactive_scanner():
    repo = MagicMock()

    repo.get_by_access_token_hash.return_value = {
        "id": 1,
        "event_id": 10,
        "device_id": "EL-ABC",
        "device_name": "Registration Desk 1",
        "is_active": False,
    }

    service = ScannerStationAuthService(repo=repo)

    with patch(
            "guest_management.services.scanner_station_auth_service.settings"
    ) as mocked_settings:
        mocked_settings.scanner_station_secret = "x" * 32

        result = service.authenticate(10, "ELST_test-token")

    assert result is None

def test_authenticate_rejects_scanner_from_different_event():
    repo = MagicMock()

    repo.get_by_access_token_hash.return_value = {
        "id": 1,
        "event_id": 20,
        "device_id": "EL-ABC",
        "device_name": "Registration Desk 1",
        "is_active": True,
    }

    service = ScannerStationAuthService(repo=repo)

    with patch(
        "guest_management.services.scanner_station_auth_service.settings"
    ) as mocked_settings:
        mocked_settings.scanner_station_secret = "x" * 32

        result = service.authenticate(
            10,
            "ELST_valid-token",
        )

    assert result is None

def test_provision_station_returns_plaintext_token_and_stores_hash():
    repo = MagicMock()

    scanner = {
        "id": 1,
        "event_id": 10,
        "device_id": "EL-ABC",
        "device_name": "Registration Desk 1",
        "is_active": True,
    }

    repo.create.return_value = scanner

    service = ScannerStationAuthService(repo=repo)

    with patch(
        "guest_management.services.scanner_station_auth_service.settings"
    ) as mocked_settings:
        mocked_settings.scanner_station_secret = "x" * 32

        result_scanner, access_token = service.provision_station(
            10,
            "Registration Desk 1",
            "admin-user-id",
        )

    assert result_scanner == scanner
    assert access_token.startswith("ELST_")
    assert len(access_token) > 80

    repo.create.assert_called_once()

    call_kwargs = repo.create.call_args.kwargs

    assert call_kwargs["event_id"] == 10
    assert call_kwargs["device_name"] == "Registration Desk 1"
    assert call_kwargs["assigned_by"] == "admin-user-id"

    assert call_kwargs["access_token_hash"] == (
        ScannerRepository.hash_access_token(
            access_token,
            "x" * 32,
        )
    )

def test_provision_station_does_not_store_plaintext_token():
    repo = MagicMock()

    repo.create.return_value = {
        "id": 1,
        "event_id": 10,
        "device_id": "EL-ABC",
        "device_name": "Registration Desk 1",
        "is_active": True,
    }

    service = ScannerStationAuthService(repo=repo)

    with patch(
        "guest_management.services.scanner_station_auth_service.settings"
    ) as mocked_settings:
        mocked_settings.scanner_station_secret = "x" * 32

        _, access_token = service.provision_station(
            10,
            "Registration Desk 1",
        )

    call_kwargs = repo.create.call_args.kwargs

    assert access_token not in call_kwargs.values()