from pathlib import Path
import shutil

ROOT = Path("guest_management")
TARGET = ROOT / "pages" / "dashboard.py"
SOURCE = Path("dashboard_fixed.py")

if not TARGET.exists():
    raise SystemExit(f"ERROR: Dashboard not found: {TARGET}")

if not SOURCE.exists():
    raise SystemExit(
        "ERROR: dashboard_fixed.py must be in the project root "
        "before running this installer."
    )

backup = TARGET.with_suffix(".py.before_email_header_fix")
shutil.copy2(TARGET, backup)
shutil.copy2(SOURCE, TARGET)

print("BACKUP:", backup)
print("UPDATED:", TARGET)
print("Dashboard now uses GuestState/State for event header data.")
print("Dashboard now contains visible individual Send Email / Resend Email action.")
