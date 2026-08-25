import pytest
from guest_management.core.exceptions import ValidationError
from guest_management.services.email_service import EmailService

def test_email_validation():
    assert EmailService.validate_email(" Test@Example.com ") == "test@example.com"
    with pytest.raises(ValidationError): EmailService.validate_email("not-an-email")
