from unittest.mock import MagicMock

import pytest

from guest_management.core.exceptions import AuthorizationError
from guest_management.services.scanner_service import ScannerService


def make_user(role="ADMIN", active=True):
    return {
        "id": "admin-user-id",
        "email": "admin@example.com",
        "role": role,
        "is_active": active,
    }


def make_service():
    repo = MagicMock()
    event_service = MagicMock()

    event_service.get_event.return_value = {
        "id": 10,
        "name": "Test Event",
    }

    service = ScannerService(
        repo=repo,
        event_service=event_service,
    )

    return service, repo, event_service


def test_get_scanners_requires_authenticated_user():
    service, repo, event_service = make_service()

    with pytest.raises(
        AuthorizationError,
        match="Authenticated user required",
    ):
        service.get_scanners(
            event_id=10,
            user_id="",
            user=make_user(),
        )

    repo.get_by_event.assert_not_called()
    event_service.get_event.assert_not_called()


def test_get_scanners_rejects_non_admin():
    service, repo, event_service = make_service()

    with pytest.raises(
        AuthorizationError,
        match="not authorized",
    ):
        service.get_scanners(
            event_id=10,
            user_id="user-1",
            user=make_user(role="USER"),
        )

    repo.get_by_event.assert_not_called()
    event_service.get_event.assert_not_called()


def test_get_scanners_rejects_inactive_admin():
    service, repo, event_service = make_service()

    with pytest.raises(
        AuthorizationError,
        match="not authorized",
    ):
        service.get_scanners(
            event_id=10,
            user_id="admin-user-id",
            user=make_user(active=False),
        )

    repo.get_by_event.assert_not_called()
    event_service.get_event.assert_not_called()


def test_get_scanners_allows_active_admin():
    service, repo, event_service = make_service()

    repo.get_by_event.return_value = [
        {
            "event_id": 10,
            "device_id": "EL-001",
            "is_active": True,
        }
    ]

    result = service.get_scanners(
        event_id=10,
        user_id="admin-user-id",
        user=make_user(),
    )

    assert result[0]["device_id"] == "EL-001"
    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        make_user(),
    )
    repo.get_by_event.assert_called_once_with(10)


def test_activate_scanner_requires_authorization():
    service, repo, event_service = make_service()

    with pytest.raises(AuthorizationError):
        service.activate_scanner(
            event_id=10,
            device_id="EL-001",
            user_id="user-1",
            user=make_user(role="USER"),
        )

    repo.set_active.assert_not_called()


def test_deactivate_scanner_requires_authorization():
    service, repo, event_service = make_service()

    with pytest.raises(AuthorizationError):
        service.deactivate_scanner(
            event_id=10,
            device_id="EL-001",
            user_id="user-1",
            user=make_user(role="USER"),
        )

    repo.set_active.assert_not_called()


def test_delete_scanner_requires_authorization():
    service, repo, event_service = make_service()

    with pytest.raises(AuthorizationError):
        service.delete_scanner(
            event_id=10,
            device_id="EL-001",
            user_id="user-1",
            user=make_user(role="USER"),
        )

    repo.delete.assert_not_called()
