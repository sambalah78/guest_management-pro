from guest_management.repositories.google_drive_connection_repository import (
    GoogleDriveConnectionRepository,
)


def test_repository_imports():
    repository = GoogleDriveConnectionRepository()
    assert repository is not None


def test_table_name():
    assert (
        GoogleDriveConnectionRepository.TABLE
        == "google_drive_connections"
    )


def test_empty_user_returns_no_connections():
    repository = GoogleDriveConnectionRepository()

    assert repository.list_by_user("") == []
    assert repository.get_primary("") is None
    assert repository.get_backup_connections("") == []


def test_invalid_create_requires_connection_id():
    repository = GoogleDriveConnectionRepository()

    try:
        repository.create(
            connection_id="",
            user_id="user-1",
            google_email="test@example.com",
        )
    except ValueError as exc:
        assert "connection_id" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_invalid_create_requires_user_id():
    repository = GoogleDriveConnectionRepository()

    try:
        repository.create(
            connection_id="connection-1",
            user_id="",
            google_email="test@example.com",
        )
    except ValueError as exc:
        assert "user_id" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_invalid_create_requires_email():
    repository = GoogleDriveConnectionRepository()

    try:
        repository.create(
            connection_id="connection-1",
            user_id="user-1",
            google_email="",
        )
    except ValueError as exc:
        assert "google_email" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_invalid_connection_role():
    repository = GoogleDriveConnectionRepository()

    try:
        repository.create(
            connection_id="connection-1",
            user_id="user-1",
            google_email="test@example.com",
            connection_role="INVALID",
        )
    except ValueError as exc:
        assert "PRIMARY or BACKUP" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError"
        )