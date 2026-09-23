from guest_management.core.security import (
    create_qr_token,
    create_session_id,
    decrypt_session_token,
    encrypt_session_token,
    extract_scan_payload,
    hash_session_id,
    verify_qr_token,
    create_voucher_access_code,
    verify_voucher_access_code,
)


def test_qr_token_round_trip():
    token = create_qr_token(18, "GUEST-100")
    assert verify_qr_token(18, "GUEST-100", token)
    assert not verify_qr_token(19, "GUEST-100", token)
    assert not verify_qr_token(18, "GUEST-101", token)


def test_extract_qr_url():
    token = create_qr_token(18, "GUEST-100")
    raw = f"https://example.com/checkin/18?guest_id=GUEST-100&token={token}"
    guest_id, extracted_token, event_id = extract_scan_payload(raw)
    assert guest_id == "GUEST-100"
    assert extracted_token == token
    assert event_id == "18"


def test_session_id_is_random():
    first = create_session_id()
    second = create_session_id()

    assert first
    assert second
    assert first != second
    assert len(first) >= 32
    assert len(second) >= 32


def test_session_id_hash_is_deterministic():
    session_id = create_session_id()

    first_hash = hash_session_id(session_id)
    second_hash = hash_session_id(session_id)

    assert first_hash == second_hash
    assert len(first_hash) == 64


def test_session_id_hash_does_not_equal_plaintext():
    session_id = create_session_id()

    assert hash_session_id(session_id) != session_id


def test_session_id_hash_changes_when_session_id_changes():
    first = create_session_id()
    second = create_session_id()

    assert hash_session_id(first) != hash_session_id(second)


def test_session_id_hash_rejects_empty_value():
    import pytest

    with pytest.raises(ValueError, match="session_id must not be empty"):
        hash_session_id("")


def test_encrypt_decrypt_session_token_round_trip():
    token = "supabase-access-token-example"

    encrypted = encrypt_session_token(token)

    assert encrypted
    assert encrypted != token
    assert decrypt_session_token(encrypted) == token


def test_encrypt_session_token_produces_different_ciphertext_each_time():
    token = "supabase-access-token-example"

    first = encrypt_session_token(token)
    second = encrypt_session_token(token)

    assert first != second
    assert decrypt_session_token(first) == token
    assert decrypt_session_token(second) == token


def test_encrypt_decrypt_supports_unicode():
    token = "supabase-token-你好-🔐"

    encrypted = encrypt_session_token(token)

    assert decrypt_session_token(encrypted) == token


def test_encrypt_session_token_rejects_empty_value():
    import pytest

    with pytest.raises(ValueError, match="token must not be empty"):
        encrypt_session_token("")


def test_decrypt_session_token_rejects_empty_value():
    import pytest

    with pytest.raises(ValueError, match="ciphertext must not be empty"):
        decrypt_session_token("")


def test_decrypt_session_token_rejects_invalid_base64():
    import pytest

    with pytest.raises(ValueError, match="Invalid encrypted session token"):
        decrypt_session_token("not-valid-base64!!!")


def test_decrypt_session_token_rejects_tampered_ciphertext():
    import base64
    import pytest

    encrypted = encrypt_session_token("supabase-access-token-example")
    payload = bytearray(base64.urlsafe_b64decode(encrypted.encode("ascii")))

    payload[-1] ^= 1

    tampered = base64.urlsafe_b64encode(payload).decode("ascii")

    with pytest.raises(ValueError, match="Invalid encrypted session token"):
        decrypt_session_token(tampered)


def test_decrypt_session_token_rejects_truncated_ciphertext():
    import base64
    import pytest

    encrypted = encrypt_session_token("supabase-access-token-example")
    payload = base64.urlsafe_b64decode(encrypted.encode("ascii"))
    truncated = base64.urlsafe_b64encode(payload[:12]).decode("ascii")

    with pytest.raises(ValueError, match="Invalid encrypted session token"):
        decrypt_session_token(truncated)


def test_decrypt_session_token_rejects_wrong_key(monkeypatch):
    import base64
    import secrets
    import pytest

    encrypted = encrypt_session_token("supabase-access-token-example")

    wrong_key = base64.urlsafe_b64encode(
        secrets.token_bytes(32)
    ).decode("ascii")

    monkeypatch.setattr(
        "guest_management.core.security.settings",
        type(
            "SettingsStub",
            (),
            {"session_encryption_key": wrong_key},
        )(),
    )

    with pytest.raises(ValueError, match="Invalid encrypted session token"):
        decrypt_session_token(encrypted)


def test_voucher_access_code_is_bound_to_event_and_guest():
    code = create_voucher_access_code(18, "GUEST-100")

    assert len(code) == 16
    assert code == code.upper()
    assert verify_voucher_access_code(18, "GUEST-100", code)
    assert verify_voucher_access_code(18, "GUEST-100", code.lower())
    assert not verify_voucher_access_code(19, "GUEST-100", code)
    assert not verify_voucher_access_code(18, "GUEST-101", code)
    assert not verify_voucher_access_code(18, "GUEST-100", code[:-1])
