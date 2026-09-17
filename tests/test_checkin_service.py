import pytest

from guest_management.core.exceptions import (
    GuestAlreadyCheckedInError,
    GuestNotFoundError,
    ValidationError,
)
from guest_management.core.security import create_qr_token
from guest_management.services.checkin_service import CheckinService

class FakeScannerAuthService:
    def __init__(self, scanner=None):
        self.scanner = scanner or {
            "device_id": "SCANNER_001",
            "event_id": 18,
            "is_active": True,
        }

    def authenticate(self, event_id, access_token):
        if not access_token:
            return None

        return self.scanner

class FakeRepo:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def check_in(self, event_id, guest_id, scanner_id=""):
        self.calls.append((event_id, guest_id, scanner_id))
        return dict(self.result)


def signed_qr(event_id=18, guest_id="G1"):
    token = create_qr_token(event_id, guest_id)
    return (
        f"https://example.com/checkin/{event_id}"
        f"?guest_id={guest_id}&token={token}"
    )


def test_checkin_service_requires_signed_qr(monkeypatch):
    monkeypatch.setenv("ALLOW_LEGACY_QR", "false")

    with pytest.raises(ValidationError):
        CheckinService(
            FakeRepo({"result": "checked_in", "guest_id": "G1"})
        ).check_in(18, "G1")


def test_checkin_service_accepts_signed_qr(monkeypatch):
    monkeypatch.setenv("ALLOW_LEGACY_QR", "false")

    repo = FakeRepo({"result": "checked_in", "guest_id": "G1"})

    token = create_qr_token(18, "G1")

    scanner_auth = FakeScannerAuthService()

    result = CheckinService(
        repo,
        scanner_auth_service=scanner_auth,
    ).check_in(
        18,
        f"https://example.com/checkin/18?guest_id=G1&token={token}",
        "SCANNER_001",
        scanner_access_token="test-token",
    )

    assert result["receipt_token"] == token
    assert repo.calls == [(18, "G1", "SCANNER_001")]


def test_checkin_service_rejects_invalid_event_id():
    repo = FakeRepo({"result": "checked_in", "guest_id": "G1"})

    with pytest.raises(ValidationError, match="Invalid event ID"):
        CheckinService(repo).check_in(0, signed_qr())

    assert repo.calls == []


def test_checkin_service_rejects_non_numeric_event_id():
    repo = FakeRepo({"result": "checked_in", "guest_id": "G1"})

    with pytest.raises(ValidationError, match="Invalid event ID"):
        CheckinService(repo).check_in("abc", signed_qr())

    assert repo.calls == []


def test_checkin_service_rejects_cross_event_qr(monkeypatch):
    monkeypatch.setenv("ALLOW_LEGACY_QR", "false")

    repo = FakeRepo({"result": "checked_in", "guest_id": "G1"})

    with pytest.raises(
        ValidationError,
        match="QR code belongs to a different event",
    ):
        CheckinService(repo).check_in(18, signed_qr(event_id=19))

    assert repo.calls == []


def test_checkin_service_rejects_tampered_token(monkeypatch):
    monkeypatch.setenv("ALLOW_LEGACY_QR", "false")

    repo = FakeRepo({"result": "checked_in", "guest_id": "G1"})

    raw = (
        "https://example.com/checkin/18"
        "?guest_id=G1&token=tampered-token"
    )

    with pytest.raises(
        ValidationError,
        match="Invalid or tampered QR code",
    ):
        CheckinService(repo).check_in(18, raw)

    assert repo.calls == []


def test_checkin_service_rejects_missing_guest_id(monkeypatch):
    monkeypatch.setenv("ALLOW_LEGACY_QR", "false")

    repo = FakeRepo({"result": "checked_in", "guest_id": "G1"})

    token = create_qr_token(18, "G1")
    raw = f"https://example.com/checkin/18?token={token}"

    with pytest.raises(
        ValidationError,
        match="QR code does not contain a guest ID",
    ):
        CheckinService(repo).check_in(18, raw)

    assert repo.calls == []


def test_checkin_service_rejects_legacy_qr_when_disabled(monkeypatch):
    monkeypatch.setenv("ALLOW_LEGACY_QR", "false")

    repo = FakeRepo({"result": "checked_in", "guest_id": "G1"})

    with pytest.raises(
        ValidationError,
        match="Legacy QR codes are disabled",
    ):
        CheckinService(repo).check_in(18, "G1")

    assert repo.calls == []


def test_checkin_service_accepts_legacy_qr_when_enabled(monkeypatch):
    monkeypatch.setenv("ALLOW_LEGACY_QR", "true")

    repo = FakeRepo(
        {
            "result": "checked_in",
            "guest_id": "G1",
        }
    )

    scanner_auth = FakeScannerAuthService()

    result = CheckinService(
        repo,
        scanner_auth_service=scanner_auth,
    ).check_in(
        18,
        "G1",
        "SCANNER_001",
        scanner_access_token="test-token",
    )

    assert result["result"] == "checked_in"
    assert repo.calls == [(18, "G1", "SCANNER_001")]


def test_checkin_service_maps_already_checked_in():
    repo = FakeRepo(
        {
            "result": "already_checked_in",
            "message": "Guest already checked in",
        }
    )

    with pytest.raises(
        GuestAlreadyCheckedInError,
        match="Guest already checked in",
    ):
        CheckinService(repo).check_in(18, signed_qr())

    assert repo.calls == [(18, "G1", "")]


def test_checkin_service_maps_guest_not_found():
    repo = FakeRepo(
        {
            "result": "not_found",
            "message": "Guest not found",
        }
    )

    with pytest.raises(
        GuestNotFoundError,
        match="Guest not found",
    ):
        CheckinService(repo).check_in(18, signed_qr())

    assert repo.calls == [(18, "G1", "")]


def test_checkin_service_rejects_unexpected_repository_result():
    repo = FakeRepo(
        {
            "result": "database_error",
            "message": "Something went wrong",
        }
    )

    with pytest.raises(
        ValidationError,
        match="Something went wrong",
    ):
        CheckinService(repo).check_in(18, signed_qr())


def test_checkin_service_returns_repository_result_and_receipt_token():
    repo = FakeRepo(
        {
            "result": "checked_in",
            "guest_id": "G1",
            "guest_name": "John",
            "table_number": "T12",
            "present_count": 10,
            "total_guests": 100,
        }
    )

    scanner_auth = FakeScannerAuthService(
        {
            "device_id": "SCANNER_007",
            "event_id": 18,
            "is_active": True,
        }
    )

    result = CheckinService(
        repo,
        scanner_auth_service=scanner_auth,
    ).check_in(
        18,
        signed_qr(),
        "SCANNER_007",
        scanner_access_token="test-token",
    )

    assert result["result"] == "checked_in"
    assert result["guest_id"] == "G1"
    assert result["guest_name"] == "John"
    assert result["table_number"] == "T12"
    assert result["present_count"] == 10
    assert result["total_guests"] == 100

    expected_token = create_qr_token(18, "G1")
    assert result["receipt_token"] == expected_token

    assert repo.calls == [(18, "G1", "SCANNER_007")]