import pytest
from unittest.mock import MagicMock, patch

from guest_management.core.exceptions import AuthorizationError
from guest_management.repositories.scanner_repository import ScannerRepository
from guest_management.services.scanner_station_auth_service import (
    ScannerStationAuthService,
)


def make_admin_user():
    return {
        "id": "admin-user-id",
        "role": "ADMIN",
        "is_active": True,
    }


def make_event_service():
    event_service = MagicMock()
    event_service.get_event.return_value = {
        "id": 10,
        "name": "Test Event",
    }
    return event_service


# ============================================================================
# AUTHENTICATION
# ============================================================================


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

    event_service = make_event_service()

    service = ScannerStationAuthService(
        repo=repo,
        event_service=event_service,
    )

    with patch(
        "guest_management.services.scanner_station_auth_service.settings"
    ) as mocked_settings:
        mocked_settings.scanner_station_secret = "x" * 32

        result = service.authenticate(
            10,
            "ELST_test-token",
        )

    assert result == scanner

    repo.get_by_access_token_hash.assert_called_once()


def test_authenticate_rejects_empty_token():
    repo = MagicMock()

    service = ScannerStationAuthService(repo=repo)

    with pytest.raises(
        AuthorizationError,
        match="Scanner access token required",
    ):
        service.authenticate(
            10,
            "",
        )

    repo.get_by_access_token_hash.assert_not_called()


def test_authenticate_rejects_unknown_token():
    repo = MagicMock()

    repo.get_by_access_token_hash.return_value = None

    service = ScannerStationAuthService(repo=repo)

    with patch(
        "guest_management.services.scanner_station_auth_service.settings"
    ) as mocked_settings:
        mocked_settings.scanner_station_secret = "x" * 32

        with pytest.raises(
            AuthorizationError,
            match="Invalid scanner access token",
        ):
            service.authenticate(
                10,
                "ELST_test-token",
            )

    repo.get_by_access_token_hash.assert_called_once()


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

        with pytest.raises(
            AuthorizationError,
            match="Scanner station is inactive",
        ):
            service.authenticate(
                10,
                "ELST_test-token",
            )

    repo.get_by_access_token_hash.assert_called_once()


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

        with pytest.raises(
            AuthorizationError,
            match="Scanner station is not assigned to this event",
        ):
            service.authenticate(
                10,
                "ELST_valid-token",
            )

    repo.get_by_access_token_hash.assert_called_once()


# ============================================================================
# PROVISIONING
# ============================================================================


def test_provision_station_returns_plaintext_token_and_stores_hash():
    repo = MagicMock()

    repo.create.return_value = {
        "event_id": 10,
        "device_id": "EL-test-device",
        "device_name": "Registration Desk 1",
        "is_active": True,
    }

    event_service = make_event_service()
    admin_user = make_admin_user()

    service = ScannerStationAuthService(
        repo=repo,
        event_service=event_service,
    )

    scanner, token = service.provision_station(
        event_id=10,
        device_name="Registration Desk 1",
        actor_user_id="admin-user-id",
        actor_user=admin_user,
    )

    assert scanner["event_id"] == 10
    assert token
    assert isinstance(token, str)

    repo.create.assert_called_once()

    create_kwargs = repo.create.call_args.kwargs

    assert create_kwargs["event_id"] == 10
    assert create_kwargs["device_name"] == "Registration Desk 1"
    assert create_kwargs["assigned_by"] == "admin-user-id"

    assert create_kwargs["access_token_hash"]
    assert create_kwargs["access_token_hash"] != token

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        admin_user,
    )


def test_provision_station_rejects_missing_actor():
    repo = MagicMock()
    event_service = make_event_service()

    service = ScannerStationAuthService(
        repo=repo,
        event_service=event_service,
    )

    with pytest.raises(
        AuthorizationError,
        match="Authenticated user required",
    ):
        service.provision_station(
            event_id=10,
            device_name="Registration Desk 1",
        )

    repo.create.assert_not_called()
    event_service.get_event.assert_not_called()


def test_provision_station_rejects_non_admin():
    repo = MagicMock()
    event_service = make_event_service()

    user = {
        "id": "normal-user-id",
        "role": "USER",
        "is_active": True,
    }

    service = ScannerStationAuthService(
        repo=repo,
        event_service=event_service,
    )

    with pytest.raises(
        AuthorizationError,
        match="not authorized",
    ):
        service.provision_station(
            event_id=10,
            device_name="Registration Desk 1",
            actor_user_id="normal-user-id",
            actor_user=user,
        )

    repo.create.assert_not_called()
    event_service.get_event.assert_not_called()


def test_provision_station_rejects_inactive_admin():
    repo = MagicMock()
    event_service = make_event_service()

    user = {
        "id": "admin-user-id",
        "role": "ADMIN",
        "is_active": False,
    }

    service = ScannerStationAuthService(
        repo=repo,
        event_service=event_service,
    )

    with pytest.raises(
        AuthorizationError,
        match="not authorized",
    ):
        service.provision_station(
            event_id=10,
            device_name="Registration Desk 1",
            actor_user_id="admin-user-id",
            actor_user=user,
        )

    repo.create.assert_not_called()
    event_service.get_event.assert_not_called()


def test_provision_station_does_not_store_plaintext_token():
    repo = MagicMock()

    repo.create.return_value = {
        "event_id": 10,
        "device_id": "EL-test-device",
        "device_name": "Registration Desk 1",
        "is_active": True,
    }

    event_service = make_event_service()
    admin_user = make_admin_user()

    service = ScannerStationAuthService(
        repo=repo,
        event_service=event_service,
    )

    scanner, plaintext_token = service.provision_station(
        event_id=10,
        device_name="Registration Desk 1",
        actor_user_id="admin-user-id",
        actor_user=admin_user,
    )

    assert scanner
    assert plaintext_token

    stored_hash = repo.create.call_args.kwargs["access_token_hash"]
    assert stored_hash
    assert stored_hash != plaintext_token

    # The plaintext token must never be supplied to the repository.
    for call_arg in repo.create.call_args.args:
        assert call_arg != plaintext_token


    for call_value in repo.create.call_args.kwargs.values():
        assert call_value != plaintext_token
