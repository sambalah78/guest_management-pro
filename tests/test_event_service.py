from unittest.mock import Mock

import pytest

from guest_management.core.exceptions import AuthorizationError
from guest_management.services.event_service import EventService


def make_event_repository():
    repo = Mock()

    repo.get_by_id_any.return_value = {
        "id": 100,
        "name": "Other User Event",
        "user_id": "other-user",
        "logo_storage_path": "",
        "invitation_storage_path": "",
        "guest_list_storage_path": "",
    }

    repo.get_by_id.return_value = None

    repo.delete.return_value = True

    return repo


def make_storage_service():
    storage = Mock()
    storage.delete.return_value = None
    return storage


def test_owner_can_delete_event_owned_by_another_user():
    repo = make_event_repository()
    storage = make_storage_service()

    service = EventService(
        repository=repo,
        storage_service=storage,
    )

    user = {
        "id": "owner-user",
        "email": "owner@example.com",
        "role": "OWNER",
        "is_active": True,
    }

    result = service.delete_event(
        event_id=100,
        user_id="owner-user",
        user=user,
    )

    assert result is True

    repo.get_by_id_any.assert_called_once_with(100)
    repo.get_by_id.assert_not_called()
    repo.delete.assert_called_once_with(100)


def test_admin_can_delete_event_owned_by_another_user():
    repo = make_event_repository()
    storage = make_storage_service()

    service = EventService(
        repository=repo,
        storage_service=storage,
    )

    user = {
        "id": "admin-user",
        "email": "admin@example.com",
        "role": "ADMIN",
        "is_active": True,
    }

    result = service.delete_event(
        event_id=100,
        user_id="admin-user",
        user=user,
    )

    assert result is True

    repo.get_by_id_any.assert_called_once_with(100)
    repo.get_by_id.assert_not_called()
    repo.delete.assert_called_once_with(100)


def test_non_admin_can_only_delete_owned_event():
    repo = make_event_repository()
    storage = make_storage_service()

    service = EventService(
        repository=repo,
        storage_service=storage,
    )

    user = {
        "id": "regular-user",
        "email": "user@example.com",
        "role": "USER",
        "is_active": True,
    }

    with pytest.raises(
        AuthorizationError,
        match="Event not found or access denied",
    ):
        service.delete_event(
            event_id=100,
            user_id="regular-user",
            user=user,
        )

    repo.get_by_id.assert_called_once_with(
        100,
        "regular-user",
    )
    repo.get_by_id_any.assert_not_called()
    repo.delete.assert_not_called()

def test_owner_can_create_event():
    repo = Mock()
    repo.create.return_value = {
        "id": 101,
        "name": "Owner Event",
        "user_id": "owner-user",
        "event_type": "company_dinner",
    }
    repo.get_by_id.return_value = repo.create.return_value

    storage = make_storage_service()

    service = EventService(
        repository=repo,
        storage_service=storage,
    )

    user = {
        "id": "owner-user",
        "email": "owner@example.com",
        "role": "OWNER",
        "is_active": True,
    }

    result = service.create_event(
        event_data={
            "name": "Owner Event",
            "event_type": "company_dinner",
        },
        user_id="owner-user",
        user=user,
    )

    assert result["id"] == 101
    repo.create.assert_called_once()
    repo.get_by_id.assert_called_once_with(
        101,
        "owner-user",
    )


def test_admin_can_create_event():
    repo = Mock()
    repo.create.return_value = {
        "id": 102,
        "name": "Admin Event",
        "user_id": "admin-user",
        "event_type": "company_dinner",
    }
    repo.get_by_id.return_value = repo.create.return_value

    storage = make_storage_service()

    service = EventService(
        repository=repo,
        storage_service=storage,
    )

    user = {
        "id": "admin-user",
        "email": "admin@example.com",
        "role": "ADMIN",
        "is_active": True,
    }

    result = service.create_event(
        event_data={
            "name": "Admin Event",
            "event_type": "company_dinner",
        },
        user_id="admin-user",
        user=user,
    )

    assert result["id"] == 102
    repo.create.assert_called_once()
    repo.get_by_id.assert_called_once_with(
        102,
        "admin-user",
    )


def test_non_admin_cannot_create_event():
    repo = Mock()
    storage = make_storage_service()

    service = EventService(
        repository=repo,
        storage_service=storage,
    )

    user = {
        "id": "regular-user",
        "email": "user@example.com",
        "role": "USER",
        "is_active": True,
    }

    with pytest.raises(
        AuthorizationError,
        match="User is not authorized to create events",
    ):
        service.create_event(
            event_data={
                "name": "Unauthorized Event",
                "event_type": "company_dinner",
            },
            user_id="regular-user",
            user=user,
        )

    repo.create.assert_not_called()