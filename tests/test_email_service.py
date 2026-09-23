from unittest.mock import MagicMock
import pytest
from guest_management.core.exceptions import ValidationError
from guest_management.services.email_service import EmailService

def test_email_validation():
    assert EmailService.validate_email(" Test@Example.com ") == "test@example.com"
    with pytest.raises(ValidationError): EmailService.validate_email("not-an-email")


def test_guest_invitation_contains_voucher_credentials():
    from guest_management.core.security import create_voucher_access_code

    service = EmailService(repository=MagicMock())
    event = {
        "id": 18,
        "name": "Test Event",
        "company_name": "Test Company",
        "date": "2026-09-19",
        "time": "18:00",
        "venue": "Test Venue",
    }
    guest = {
        "guest_id": "GUEST-100",
        "name": "Test Guest",
        "email": "guest@example.com",
        "table_number": "10",
    }

    job = service.build_guest_invitation_job(event, guest)
    code = create_voucher_access_code(18, "GUEST-100")

    assert "Guest ID: GUEST-100" in job["plain_text"]
    assert f"Voucher Access Code: {code}" in job["plain_text"]
    assert code in job["html_content"]
    assert "Voucher Access Code" in job["html_content"]
