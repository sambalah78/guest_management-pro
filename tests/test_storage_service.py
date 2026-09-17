from unittest.mock import Mock

import pytest

from guest_management.services.storage_service import StorageService


@pytest.fixture
def storage_service():
    client = Mock()
    return StorageService(client=client), client


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------


def test_build_path_returns_event_scoped_path():
    service = StorageService()

    path = service._build_path(123, "logo", "company-logo.png")

    assert path == "events/123/logo/company-logo.png"


def test_build_path_normalizes_asset_type_and_filename():
    service = StorageService()

    path = service._build_path(
        "123",
        " LOGO ",
        r"C:\fakepath\company-logo.png",
    )

    assert path == "events/123/logo/company-logo.png"


@pytest.mark.parametrize(
    "event_id",
    [None, "", "abc", 0, -1, -100],
)
def test_build_path_rejects_invalid_event_id(event_id):
    service = StorageService()

    with pytest.raises(ValueError):
        service._build_path(event_id, "logo", "logo.png")


@pytest.mark.parametrize(
    "filename",
    [None, "", "   ", ".", ".."],
)
def test_build_path_rejects_invalid_filename(filename):
    service = StorageService()

    with pytest.raises(ValueError):
        service._build_path(123, "logo", filename)


def test_build_path_strips_directory_from_filename():
    service = StorageService()

    path = service._build_path(
        123,
        "logo",
        "../../logo.png",
    )

    assert path == "events/123/logo/logo.png"


def test_build_path_rejects_unsupported_asset_type():
    service = StorageService()

    with pytest.raises(ValueError, match="Unsupported asset type"):
        service._build_path(123, "document", "file.pdf")


# ---------------------------------------------------------------------------
# Upload validation
# ---------------------------------------------------------------------------


def test_upload_rejects_empty_content():
    service = StorageService()

    with pytest.raises(ValueError, match="empty file"):
        service.upload(
            event_id=123,
            asset_type="logo",
            filename="logo.png",
            content=b"",
            mime_type="image/png",
        )


def test_upload_rejects_missing_mime_type():
    service = StorageService()

    with pytest.raises(ValueError, match="MIME type"):
        service.upload(
            event_id=123,
            asset_type="logo",
            filename="logo.png",
            content=b"image-data",
            mime_type="",
        )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


def test_upload_calls_supabase_storage(storage_service):
    service, client = storage_service

    service.upload(
        event_id=123,
        asset_type="logo",
        filename="logo.png",
        content=b"image-data",
        mime_type="image/png",
    )

    client.storage.from_.assert_called_once_with("event-assets")

    bucket = client.storage.from_.return_value

    bucket.upload.assert_called_once_with(
        "events/123/logo/logo.png",
        b"image-data",
        {
            "content-type": "image/png",
            "upsert": "true",
        },
    )


def test_upload_returns_storage_asset(storage_service):
    service, client = storage_service

    asset = service.upload(
        event_id=123,
        asset_type="logo",
        filename="logo.png",
        content=b"image-data",
        mime_type="image/png",
    )

    assert asset.path == "events/123/logo/logo.png"
    assert asset.filename == "logo.png"
    assert asset.mime_type == "image/png"
    assert asset.size == len(b"image-data")
    assert asset.is_valid is True


def test_upload_supports_upsert(storage_service):
    service, client = storage_service

    service.upload(
        event_id=123,
        asset_type="logo",
        filename="logo.png",
        content=b"image-data",
        mime_type="image/png",
        upsert=True,
    )

    bucket = client.storage.from_.return_value

    bucket.upload.assert_called_once_with(
        "events/123/logo/logo.png",
        b"image-data",
        {
            "content-type": "image/png",
            "upsert": "true",
        },
    )


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def test_download_returns_bytes(storage_service):
    service, client = storage_service

    bucket = client.storage.from_.return_value
    bucket.download.return_value = b"file-content"

    result = service.download("events/123/logo/logo.png")

    assert result == b"file-content"

    bucket.download.assert_called_once_with(
        "events/123/logo/logo.png"
    )


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def test_delete_returns_true_on_success(storage_service):
    service, client = storage_service

    result = service.delete("events/123/logo/logo.png")

    assert result is True

    bucket = client.storage.from_.return_value

    bucket.remove.assert_called_once_with(
        ["events/123/logo/logo.png"]
    )


def test_delete_returns_false_on_failure(storage_service):
    service, client = storage_service

    bucket = client.storage.from_.return_value
    bucket.remove.side_effect = RuntimeError("Storage error")

    result = service.delete("events/123/logo/logo.png")

    assert result is False


# ---------------------------------------------------------------------------
# Exists
# ---------------------------------------------------------------------------


def test_exists_returns_true_when_file_is_present(storage_service):
    service, client = storage_service

    bucket = client.storage.from_.return_value
    bucket.list.return_value = [
        {"name": "logo.png"},
        {"name": "other.png"},
    ]

    result = service.exists("events/123/logo/logo.png")

    assert result is True

    bucket.list.assert_called_once_with(
        "events/123/logo"
    )


def test_exists_returns_false_when_file_is_missing(storage_service):
    service, client = storage_service

    bucket = client.storage.from_.return_value
    bucket.list.return_value = [
        {"name": "other.png"},
    ]

    result = service.exists("events/123/logo/logo.png")

    assert result is False


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_health_check_returns_true_when_storage_is_available(storage_service):
    service, client = storage_service

    bucket = client.storage.from_.return_value
    bucket.list.return_value = []

    result = service.health_check()

    assert result is True

    bucket.list.assert_called_once_with("")


def test_health_check_returns_false_when_storage_fails(storage_service):
    service, client = storage_service

    bucket = client.storage.from_.return_value
    bucket.list.side_effect = RuntimeError("Storage unavailable")

    result = service.health_check()

    assert result is False