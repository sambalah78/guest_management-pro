import pytest
from guest_management.core.exceptions import GuestAlreadyCheckedInError, ValidationError
from guest_management.core.security import create_qr_token
from guest_management.services.checkin_service import CheckinService

class FakeRepo:
    def __init__(self, result): self.result, self.calls = result, []
    def check_in(self, event_id, guest_id, scanner_id=""):
        self.calls.append((event_id, guest_id, scanner_id)); return dict(self.result)

def test_checkin_service_requires_signed_qr(monkeypatch):
    monkeypatch.setenv("ALLOW_LEGACY_QR", "false")
    with pytest.raises(ValidationError): CheckinService(FakeRepo({"result":"checked_in","guest_id":"G1"})).check_in(18, "G1")

def test_checkin_service_accepts_signed_qr(monkeypatch):
    monkeypatch.setenv("ALLOW_LEGACY_QR", "false")
    repo = FakeRepo({"result":"checked_in","guest_id":"G1"})
    token = create_qr_token(18, "G1")
    result = CheckinService(repo).check_in(18, f"https://example.com/checkin/18?guest_id=G1&token={token}", "SCANNER_001")
    assert result["receipt_token"] == token
    assert repo.calls == [(18, "G1", "SCANNER_001")]
