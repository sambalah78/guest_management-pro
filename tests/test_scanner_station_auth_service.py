from unittest.mock import MagicMock, patch

import pytest

from guest_management.services.scanner_station_auth_service import (
    ScannerStationAuthService,
)


def make_scanner(
    event_id=10,
    device_id="EL-ABC",
    device_name="Registration Desk 1",
    is_active=True,
):
    return {
        "id": 1,
        "event_id": event_id,
        "device_id": device_id,
        "device_name": device_name,
        "is_active": is_active,
    }


def make_service(repo=None):
    return ScannerStationAuthService(
        repo=repo or MagicMock()
    )


def test_authenticate_rejects_empty_pin():
    repo = MagicMock()
    service = make_service(repo)

    assert service.authenticate(10, "") is None
    repo.get_by_access_token_hash.assert_not_called()


def test_authenticate_rejects_invalid_pin_format():
    repo = MagicMock()
    service = make_service(repo)

    assert service.authenticate(10, "123") is None
    assert service.authenticate(10, "12345") is None
    assert service.authenticate(10, "abcd") is None

    repo.get_by_access_token_hash.assert_not_called()


def test_authenticate_rejects_unknown_pin():
    repo = MagicMock()
    repo.get_by_access_token_hash.return_value = None

    service = make_service(repo)

    with patch(
        "guest_management.services.scanner_station_auth_service.settings"
    ) as mocked_settings:
        mocked_settings.scanner_station_secret = "x" * 32

        assert service.authenticate(10, "4827") is None


def test_authenticate_rejects_inactive_scanner():
    repo = MagicMock()

    repo.get_by_access_token_hash.return_value = make_scanner(
        event_id=10,
        is_active=False,
    )

    service = make_service(repo)

    with patch(
        "guest_management.services.scanner_station_auth_service.settings"
    ) as mocked_settings:
        mocked_settings.scanner_station_secret = "x" * 32

        assert service.authenticate(10, "4827") is None


def test_authenticate_rejects_scanner_from_different_event():
    repo = MagicMock()

    repo.get_by_access_token_hash.return_value = make_scanner(
        event_id=20,
    )

    service = make_service(repo)

    with patch(
        "guest_management.services.scanner_station_auth_service.settings"
    ) as mocked_settings:
        mocked_settings.scanner_station_secret = "x" * 32

        assert service.authenticate(10, "4827") is None


def test_service_does_not_require_event_service():
    repo = MagicMock()

    service = ScannerStationAuthService(repo=repo)

    assert service is not None


def test_issue_session_uses_elss_prefix():
    scanner = make_scanner()

    with patch(
        "guest_management.services.scanner_station_auth_service.settings"
    ) as mocked_settings:
        mocked_settings.scanner_station_secret = "x" * 32

        session = ScannerStationAuthService.issue_session(scanner)

    assert session.startswith("ELSS_")
    assert len(session) > len("ELSS_")


def test_issue_session_contains_no_plaintext_pin():
    scanner = make_scanner()

    with patch(
        "guest_management.services.scanner_station_auth_service.settings"
    ) as mocked_settings:
        mocked_settings.scanner_station_secret = "x" * 32

        session = ScannerStationAuthService.issue_session(scanner)

    assert "4827" not in session


def test_provision_station_requires_four_digit_pin():
    repo = MagicMock()
    service = make_service(repo)

    with pytest.raises(ValueError, match="exactly 4 digits"):
        service.provision_station(
            event_id=10,
            device_name="Registration Desk 1",
            pin="123",
        )

    repo.create.assert_not_called()


def test_provision_station_rejects_five_digit_pin():
    repo = MagicMock()
    service = make_service(repo)

    with pytest.raises(ValueError, match="exactly 4 digits"):
        service.provision_station(
            event_id=10,
            device_name="Registration Desk 1",
            pin="12345",
        )

    repo.create.assert_not_called()


def test_provision_station_rejects_non_numeric_pin():
    repo = MagicMock()
    service = make_service(repo)

    with pytest.raises(ValueError, match="exactly 4 digits"):
        service.provision_station(
            event_id=10,
            device_name="Registration Desk 1",
            pin="12AB",
        )

    repo.create.assert_not_called()


def test_provision_station_returns_pin_and_stores_hash():
    repo = MagicMock()

    repo.create.return_value = {
        "event_id": 10,
        "device_id": "EL-test-device",
        "device_name": "Registration Desk 1",
        "is_active": True,
    }

    service = make_service(repo)

    with patch(
        "guest_management.services.scanner_station_auth_service.settings"
    ) as mocked_settings:
        mocked_settings.scanner_station_secret = "x" * 32

        result = service.provision_station(
            event_id=10,
            device_name="Registration Desk 1",
            pin="4827",
        )

    assert result is not None

    create_kwargs = repo.create.call_args.kwargs

    assert create_kwargs["event_id"] == 10
    assert create_kwargs["device_name"] == "Registration Desk 1"

    assert create_kwargs["access_token_hash"]
    assert create_kwargs["access_token_hash"] != "4827"

    if "pin_ciphertext" in create_kwargs:
        assert create_kwargs["pin_ciphertext"]
        assert create_kwargs["pin_ciphertext"] != "4827"


def test_provision_station_does_not_store_plaintext_pin_as_access_hash():
    repo = MagicMock()

    repo.create.return_value = {
        "event_id": 10,
        "device_id": "EL-test-device",
        "device_name": "Registration Desk 1",
        "is_active": True,
    }

    service = make_service(repo)

    with patch(
        "guest_management.services.scanner_station_auth_service.settings"
    ) as mocked_settings:
        mocked_settings.scanner_station_secret = "x" * 32

        service.provision_station(
            event_id=10,
            device_name="Registration Desk 1",
            pin="4827",
        )

    create_kwargs = repo.create.call_args.kwargs

    assert create_kwargs["access_token_hash"] != "4827"


def test_pin_hash_is_deterministic():
    first = ScannerStationAuthService._hash_pin("4827")
    second = ScannerStationAuthService._hash_pin("4827")

    assert first == second
    assert first != "4827"


def test_different_pins_have_different_hashes():
    first = ScannerStationAuthService._hash_pin("4827")
    second = ScannerStationAuthService._hash_pin("9153")

    assert first != second
