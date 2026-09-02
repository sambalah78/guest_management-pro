# guest_management/utils/constants.py
"""Application constants."""

# Colors
GOLD = "#D4AF37"
BLACK = "#000000"
DARK_GRAY = "#696969"
LIGHT_GRAY = "#D3D3D3"
WHITE = "#FFFFFF"

# Event Types
EVENT_TYPES = {
    "company_dinner": {
        "name": "Company Dinner",
        "icon": "🏢",
        "features": {
            "qr_checkin": True,
            "email_invitations": True,
            "table_assignment": True,
            "food_vouchers": False,
            "multiple_stalls": False,
            "lucky_draw": True,
            "team_management": False,
            "score_tracking": False,
            "parent_guardian_info": False,
            "dietary_restrictions": True,
            "plus_one_management": False,
        },
        "fields": ["name", "email", "id", "table", "dietary_restrictions", "employee_id"]
    },
    "wedding_dinner": {
        "name": "Wedding Dinner",
        "icon": "💒",
        "features": {
            "qr_checkin": True,
            "email_invitations": True,
            "table_assignment": True,
            "food_vouchers": False,
            "multiple_stalls": False,
            "lucky_draw": False,
            "team_management": False,
            "score_tracking": False,
            "parent_guardian_info": True,
            "dietary_restrictions": True,
            "plus_one_management": True,
        },
        "fields": ["name", "email", "id", "table", "dietary_restrictions", "parent_name", "parent_phone",
                   "plus_one_name"]
    },
    "sports_day": {
        "name": "Sports Day",
        "icon": "⚽",
        "features": {
            "qr_checkin": True,
            "email_invitations": True,
            "table_assignment": True,
            "food_vouchers": True,
            "multiple_stalls": True,
            "lucky_draw": True,
            "team_management": True,
            "score_tracking": False,
            "parent_guardian_info": True,
            "dietary_restrictions": False,
            "plus_one_management": False,
        },
        "fields": ["name", "email", "id", "table", "amount", "team_name", "parent_name", "parent_phone", "jersey_size"]
    },
    "lucky_draw": {
        "name": "Lucky Draw",
        "icon": "🎁",
        "features": {
            "qr_checkin": False,
            "email_invitations": False,
            "table_assignment": False,
            "food_vouchers": False,
            "multiple_stalls": False,
            "lucky_draw": True,
            "team_management": False,
            "score_tracking": False,
            "parent_guardian_info": False,
            "dietary_restrictions": False,
            "plus_one_management": False,
        },
        "fields": [
            "name",
            "email",
            "id",
        ],
    },
}

# Public routes (no auth required)
PUBLIC_ROUTES = [
    "/", "/home", "/login", "/checkin", "/success",
    "/already-checked", "/stall", "/stall/menu",
    "/scanner", "/scanner-guest", "/scanner_guest"
]

# Scanner settings
MAX_SCANNERS = 8
SCANNER_THROTTLE_MS = 300
SCANNER_QUEUE_DELAY_MS = 100

# Email settings
BULK_EMAIL_BATCH_SIZE = 5
BULK_EMAIL_BATCH_DELAY_SECONDS = 2
EMAIL_THROTTLE_SECONDS = 0.5

# Pagination
DEFAULT_PAGE_SIZE = 10
PAGE_SIZES = [10, 25, 50, 100]

# Upload
MAX_UPLOAD_BATCH_SIZE = 500
ALLOWED_UPLOAD_EXTENSIONS = [".xlsx", ".xls", ".csv"]
