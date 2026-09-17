from unittest.mock import MagicMock

import pytest

from guest_management.repositories.scanner_repository import ScannerRepository


def test_generate_access_token_has_eventlah_prefix():
    token = ScannerRepository.generate_access_token()

    assert token.startswith("ELST_")
    assert len(token) > 80


def test_generate_access_token_is_unique():
    token_a = ScannerRepository.generate_access_token()
    token_b = ScannerRepository.generate_access_token()

    assert token_a != token_b


def test_hash_access_token_is_deterministic():
    token = "ELST_test-token"
    pepper = "a" * 32

    first = ScannerRepository.hash_access_token(token, pepper)
    second = ScannerRepository.hash_access_token(token, pepper)

    assert first == second
    assert len(first) == 64


def test_hash_access_token_changes_with_token():
    pepper = "a" * 32

    first = ScannerRepository.hash_access_token(
        "ELST_token-one",
        pepper,
    )
    second = ScannerRepository.hash_access_token(
        "ELST_token-two",
        pepper,
    )

    assert first != second


def test_hash_access_token_changes_with_pepper():
    token = "ELST_test-token"

    first = ScannerRepository.hash_access_token(
        token,
        "a" * 32,
    )
    second = ScannerRepository.hash_access_token(
        token,
        "b" * 32,
    )

    assert first != second


def test_hash_access_token_rejects_empty_token():
    with pytest.raises(ValueError, match="access token"):
        ScannerRepository.hash_access_token(
            "",
            "a" * 32,
        )


def test_hash_access_token_rejects_short_pepper():
    with pytest.raises(ValueError, match="pepper"):
        ScannerRepository.hash_access_token(
            "ELST_test-token",
            "short",
        )

def test_get_by_access_token_hash_returns_scanner():
    db = MagicMock()
    repo = ScannerRepository(db=db)

    row = {
        "id": 1,
        "event_id": 10,
        "device_id": "EL-ABC",
        "device_name": "Registration Desk 1",
        "is_active": True,
    }

    query = db.table.return_value
    query.select.return_value = query
    query.eq.return_value = query
    query.limit.return_value = query
    query.execute.return_value.data = [row]

    result = repo.get_by_access_token_hash("abc123")

    assert result == row
    query.eq.assert_called_once_with(
        "access_token_hash",
        "abc123",
    )