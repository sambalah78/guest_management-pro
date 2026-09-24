"""Security and concurrency tests for the scanner check-in service.

These tests exercise the current production service boundary:
- signed QR validation
- cross-event QR rejection
- scanner credential enforcement
- scanner/event binding
- scanner identity binding
- inactive/invalid station rejection
- concurrent service calls for the same guest

The final persistence/concurrency guarantee remains covered by the
PostgreSQL database concurrency suite.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest

from guest_management.core.exceptions import (
    GuestAlreadyCheckedInError,
    ValidationError,
)
from guest_management.core.security import create_qr_token
from guest_management.services import checkin_service
from guest_management.services.checkin_service import CheckinService


EVENT_ID = 18
GUEST_ID = "G1"
SCANNER_ID = "EL-SCANNER-001"
SCANNER_TOKEN = "ELST_test-scanner-token"


def signed_qr(
    event_id: int = EVENT_ID,
    guest_id: str = GUEST_ID,
) -> str:
    token = create_qr_token(event_id, guest_id)
    return (
        f"https://example.com/checkin/"
        f"{event_id}?guest_id={guest_id}&token={token}"
    )


def make_service(
    repository_result=None,
    scanner_record=None,
):
    repo = MagicMock()
    repo.check_in.return_value = repository_result or {
        "result": "checked_in",
        "guest_id": GUEST_ID,
        "guest_name": "John",
        "table_number": "T12",
        "present_count": 10,
        "total_guests": 100,
    }

    scanner_auth = MagicMock()
    scanner_auth.authenticate.return_value = scanner_record or {
        "id": 1,
        "event_id": EVENT_ID,
        "device_id": SCANNER_ID,
        "device_name": "Registration Desk 1",
        "is_active": True,
    }

    service = CheckinService(
        repository=repo,
        scanner_auth_service=scanner_auth,
    )
    return service, repo, scanner_auth


def test_valid_signed_qr_with_valid_scanner_is_accepted():
    service, repo, scanner_auth = make_service()

    result = service.check_in(
        EVENT_ID,
        signed_qr(),
        SCANNER_ID,
        scanner_access_token=SCANNER_TOKEN,
    )

    assert result["result"] == "checked_in"
    repo.check_in.assert_called_once_with(
        event_id=EVENT_ID,
        guest_id=GUEST_ID,
        scanner_id=SCANNER_ID,
    )
    scanner_auth.authenticate.assert_called_once_with(
        event_id=EVENT_ID,
        access_token=SCANNER_TOKEN,
    )


def test_missing_scanner_identity_is_rejected_before_repository_write():
    service, repo, scanner_auth = make_service()

    with pytest.raises(
        ValidationError,
        match="Scanner station identity required",
    ):
        service.check_in(
            EVENT_ID,
            signed_qr(),
            "",
            scanner_access_token=SCANNER_TOKEN,
        )

    repo.check_in.assert_not_called()
    scanner_auth.authenticate.assert_not_called()


def test_missing_scanner_token_is_rejected_before_repository_write():
    service, repo, scanner_auth = make_service()

    with pytest.raises(
        ValidationError,
        match="Scanner station authentication required",
    ):
        service.check_in(
            EVENT_ID,
            signed_qr(),
            SCANNER_ID,
        )

    repo.check_in.assert_not_called()
    scanner_auth.authenticate.assert_not_called()


def test_invalid_scanner_token_is_rejected_before_repository_write():
    service, repo, scanner_auth = make_service()
    scanner_auth.authenticate.return_value = None

    with pytest.raises(
        ValidationError,
        match="Invalid, inactive, or incorrectly assigned scanner station",
    ):
        service.check_in(
            EVENT_ID,
            signed_qr(),
            SCANNER_ID,
            scanner_access_token="ELST_invalid",
        )

    repo.check_in.assert_not_called()


def test_inactive_scanner_is_rejected():
    service, repo, scanner_auth = make_service(
        scanner_record={
            "id": 1,
            "event_id": EVENT_ID,
            "device_id": SCANNER_ID,
            "device_name": "Registration Desk 1",
            "is_active": False,
        }
    )

    # ScannerStationAuthService is responsible for rejecting inactive
    # scanners. The CheckinService boundary must stop the check-in when
    # authentication fails.
    scanner_auth.authenticate.return_value = None

    with pytest.raises(
        ValidationError,
        match="Invalid, inactive, or incorrectly assigned scanner station",
    ):
        service.check_in(
            EVENT_ID,
            signed_qr(),
            SCANNER_ID,
            scanner_access_token=SCANNER_TOKEN,
        )

    repo.check_in.assert_not_called()

def test_scanner_from_different_event_is_rejected():
    service, repo, scanner_auth = make_service(
        scanner_record={
            "id": 1,
            "event_id": EVENT_ID + 1,
            "device_id": SCANNER_ID,
            "device_name": "Registration Desk 1",
            "is_active": True,
        }
    )

    # The service receives whatever the auth service returns, but the
    # production auth service itself must enforce event binding. This
    # test verifies the service does not proceed if auth returns None.
    scanner_auth.authenticate.return_value = None

    with pytest.raises(
        ValidationError,
        match="Invalid, inactive, or incorrectly assigned scanner station",
    ):
        service.check_in(
            EVENT_ID,
            signed_qr(),
            SCANNER_ID,
            scanner_access_token=SCANNER_TOKEN,
        )

    repo.check_in.assert_not_called()


def test_scanner_identity_mismatch_is_rejected():
    service, repo, scanner_auth = make_service(
        scanner_record={
            "id": 1,
            "event_id": EVENT_ID,
            "device_id": "EL-DIFFERENT-SCANNER",
            "device_name": "Registration Desk X",
            "is_active": True,
        }
    )

    with pytest.raises(
        ValidationError,
        match="Scanner station identity mismatch",
    ):
        service.check_in(
            EVENT_ID,
            signed_qr(),
            SCANNER_ID,
            scanner_access_token=SCANNER_TOKEN,
        )

    repo.check_in.assert_not_called()


def test_cross_event_qr_is_rejected():
    service, repo, scanner_auth = make_service()

    with pytest.raises(
        ValidationError,
        match="QR code belongs to a different event",
    ):
        service.check_in(
            EVENT_ID,
            signed_qr(event_id=EVENT_ID + 1),
            SCANNER_ID,
            scanner_access_token=SCANNER_TOKEN,
        )

    scanner_auth.authenticate.assert_not_called()
    repo.check_in.assert_not_called()


def test_tampered_qr_is_rejected():
    service, repo, scanner_auth = make_service()

    qr = signed_qr()
    tampered = qr.replace("guest_id=G1", "guest_id=G999")

    with pytest.raises(
        ValidationError,
        match="Invalid or tampered QR code",
    ):
        service.check_in(
            EVENT_ID,
            tampered,
            SCANNER_ID,
            scanner_access_token=SCANNER_TOKEN,
        )

    scanner_auth.authenticate.assert_not_called()
    repo.check_in.assert_not_called()


def test_legacy_qr_is_rejected_when_disabled():
    service, repo, scanner_auth = make_service()

    test_settings = replace(
        checkin_service.settings,
        allow_legacy_qr=False,
    )

    with patch.object(
        checkin_service,
        "settings",
        test_settings,
    ):
        with pytest.raises(
            ValidationError,
            match="Legacy QR codes are disabled",
        ):
            service.check_in(
                EVENT_ID,
                GUEST_ID,
                SCANNER_ID,
                scanner_access_token=SCANNER_TOKEN,
            )

    scanner_auth.authenticate.assert_not_called()
    repo.check_in.assert_not_called()


def test_legacy_qr_can_be_enabled_explicitly():
    service, repo, scanner_auth = make_service()

    test_settings = replace(
        checkin_service.settings,
        allow_legacy_qr=True,
    )

    with patch.object(
        checkin_service,
        "settings",
        test_settings,
    ):
        result = service.check_in(
            EVENT_ID,
            GUEST_ID,
            SCANNER_ID,
            scanner_access_token=SCANNER_TOKEN,
        )

    assert result["result"] == "checked_in"

def test_manual_checkin_does_not_require_scanner_token():
    service, repo, scanner_auth = make_service()

    result = service.check_in(
        EVENT_ID,
        GUEST_ID,
        manual=True,
    )

    assert result["result"] == "checked_in"
    scanner_auth.authenticate.assert_not_called()
    repo.check_in.assert_called_once_with(
        event_id=EVENT_ID,
        guest_id=GUEST_ID,
        scanner_id="",
    )


def test_repository_already_checked_in_is_normalized():
    service, repo, _ = make_service(
        repository_result={
            "result": "already_checked_in",
            "guest_id": GUEST_ID,
            "message": "Guest already checked in",
        }
    )

    with pytest.raises(GuestAlreadyCheckedInError):
        service.check_in(
            EVENT_ID,
            signed_qr(),
            SCANNER_ID,
            scanner_access_token=SCANNER_TOKEN,
        )


def test_concurrent_service_calls_preserve_security_boundary():
    """Every concurrent scanner request must independently authenticate.

    This deliberately uses an isolated fake repository/auth service.
    Database-level atomicity is tested separately against PostgreSQL.
    """

    repo = MagicMock()
    scanner_auth = MagicMock()

    scanner_auth.authenticate.return_value = {
        "id": 1,
        "event_id": EVENT_ID,
        "device_id": SCANNER_ID,
        "device_name": "Registration Desk 1",
        "is_active": True,
    }

    # Simulate one successful write followed by duplicate responses.
    call_count = 0

    def check_in_side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "result": "checked_in",
                "guest_id": GUEST_ID,
                "guest_name": "John",
                "table_number": "T12",
                "present_count": 1,
                "total_guests": 100,
            }
        return {
            "result": "already_checked_in",
            "guest_id": GUEST_ID,
            "message": "Guest already checked in",
        }

    repo.check_in.side_effect = check_in_side_effect

    service = CheckinService(
        repository=repo,
        scanner_auth_service=scanner_auth,
    )

    def worker():
        try:
            result = service.check_in(
                EVENT_ID,
                signed_qr(),
                SCANNER_ID,
                scanner_access_token=SCANNER_TOKEN,
            )
            return "checked_in"
        except GuestAlreadyCheckedInError:
            return "already_checked_in"

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda _: worker(), range(10)))

    assert results.count("checked_in") == 1
    assert results.count("already_checked_in") == 9
    assert scanner_auth.authenticate.call_count == 10
    assert repo.check_in.call_count == 10
