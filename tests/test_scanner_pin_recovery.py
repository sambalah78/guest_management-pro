from pathlib import Path

REPO = Path('guest_management/repositories/scanner_repository.py')
SERVICE = Path('guest_management/services/scanner_station_auth_service.py')
STATE = Path('guest_management/state/scanner_state.py')
DASHBOARD = Path('guest_management/pages/dashboard.py')


def test_repository_supports_encrypted_pin_recovery():
    s = REPO.read_text(encoding='utf-8')
    assert 'def encrypt_pin' in s
    assert 'def decrypt_pin' in s
    assert 'pin_ciphertext' in s


def test_provisioning_persists_encrypted_pin():
    s = SERVICE.read_text(encoding='utf-8')
    assert 'pin_ciphertext = self.repo.encrypt_pin(scanner_pin)' in s
    assert 'pin_ciphertext=pin_ciphertext' in s


def test_admin_recovery_is_authorized():
    s = STATE.read_text(encoding='utf-8')
    assert 'async def reveal_scanner_pin' in s
    assert 'auth.is_event_admin' in s
    assert 'decrypt_pin' in s



def test_scanner_state_has_pin_recovery_handlers():
    state = Path("guest_management/state/scanner_state.py").read_text(
        encoding="utf-8"
    )
    assert "def reveal_scanner_pin(" in state
    assert "def hide_scanner_pin(" in state
    assert "def toggle_scanner_pin(" in state

def test_dashboard_has_view_pin():
    s = DASHBOARD.read_text(encoding='utf-8')
    assert 'View PIN' in s
    assert 'ScannerState.toggle_scanner_pin' in s
