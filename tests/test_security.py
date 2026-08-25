from guest_management.core.security import create_qr_token, extract_scan_payload, verify_qr_token


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
