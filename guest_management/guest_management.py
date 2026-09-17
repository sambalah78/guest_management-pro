from guest_management.core.config import settings
from guest_management.database import init_db

# guest_management.py
import reflex as rx
from guest_management.auth_api import api as auth_api

from guest_management.pages import (
    home_page, sign_in, events, create_event,
    dashboard, check_in, success, already_checked, scanner, lucky_draw,
    voucher_manager, stall_landing, stall_menu, scanner_guest, about,
    products, contact, print_qr, select_event_type, lucky_draw_display, pre_draw_display, splash, health, lucky_draw_external_display

)
if settings.is_production:
    settings.validate()
else:
    init_db()

from guest_management.state import (
    GuestState, EventState, ScannerState, SuccessState, LuckyDrawState,
    AuthState, EmailState, VoucherState, UIState
)


def index():
    return splash.splash_screen()
# App configuration
app = rx.App(
    api_transformer=auth_api,
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
    ],
    style={
        # ... your existing styles ...
    },
    head_components=[
        rx.script(
            "const link = document.createElement('link');"
            "link.rel = 'icon';"
            "link.href = '/logo1.png';"
            "link.type = 'image/png';"
            "document.head.appendChild(link);"
        ),
        rx.script(src="/js/usb_scanner.js"),
    ]
)

# Routes
app.add_page(index, route="/")
app.add_page(health.health_page, route="/health", title="Health")
app.add_page(home_page.home, route="/home")
app.add_page(sign_in.login_page, route="/login")
app.add_page(events.events_page, route="/events", on_load=[AuthState.check_auth, EventState.load_events])
app.add_page(create_event.create_event_page, route="/create-event", on_load=AuthState.check_auth)
app.add_page(
    dashboard.dashboard,
    route="/dashboard/[event_id]",
    on_load=[
        AuthState.check_auth,
        EventState.load_event_from_url,
        GuestState.load_guests,
    ],
)
app.add_page(
    check_in.checkin_page,
    route="/checkin/[event_id]",
    on_load=[
        AuthState.check_auth,
        GuestState.set_current_event_from_url,
    ],
    title="Manual Check-In",
)

# Scanner routes - Use ScannerState
app.add_page(
    scanner.scanner_page,
    route="/scanner/[event_id]",
    on_load=ScannerState.set_current_event_from_url
)
app.add_page(
    scanner_guest.scanner_guest_page,
    route="/scanner_guest/[event_id]",
    on_load=ScannerState.set_current_event_from_url
)
app.add_page(
    scanner_guest.scanner_guest_page,
    route="/scanner-guest/[event_id]",
    on_load=ScannerState.set_current_event_from_url
)

# Success route
app.add_page(
    success.success_page,
    route="/success/[event_id]",
    on_load=SuccessState.fetch_checked_in_guest_details
)

# Already checked routes - Use ScannerState
app.add_page(
    already_checked.already_checked_page,
    route="/already-checked/[event_id]",
    on_load=ScannerState.set_current_event_from_url
)
app.add_page(
    already_checked.already_checked_page,
    route="/already_checked/[event_id]",
    on_load=ScannerState.set_current_event_from_url
)

# Voucher manager
app.add_page(
    voucher_manager.voucher_manager_page,
    route="/voucher-manager",
    on_load=[AuthState.check_auth, VoucherState.load_stalls],
    title="Voucher Manager"
)

# Stall routes
app.add_page(stall_landing.stall_landing, route="/stall", on_load=VoucherState.load_stall_from_params, title="Stall Ordering")
app.add_page(stall_menu.stall_menu, route="/stall/menu", on_load=[VoucherState.setup_stall_menu, VoucherState.load_stall_from_url])

# Lucky draw
app.add_page(
    lucky_draw.lucky_draw_page,
    route="/lucky-draw",
    on_load=[AuthState.check_auth, GuestState.load_guests, GuestState.load_lucky_draw_eligible_guests, GuestState.load_winners],
    title="Lucky Draw"
)
app.add_page(
    lucky_draw.lucky_draw_page,
    route="/lucky-draw/[event_id]",
    on_load=[AuthState.check_auth, LuckyDrawState.initialize_lucky_draw_event],
    title="Lucky Draw"
)

app.add_page(rx.fragment(), route="/checkin-handler", on_load=ScannerState.handle_scan)
app.add_page(
    print_qr.print_qr_page,
    route="/print-qr",
    on_load=[AuthState.check_auth, VoucherState.load_stalls],
    title="Print QR Codes"
)
app.add_page(select_event_type.select_event_type_page, route="/select-event-type", title="Select Event Type")
app.add_page(
    pre_draw_display.pre_draw_display_page,
    route="/lucky-draw/pre-draw-display",
    title="Pre-Draw Display",
    on_load=LuckyDrawState.initialize_pre_draw_display,
)
app.add_page(
    lucky_draw_display.lucky_draw_display_page,
    route="/lucky-draw-display",
    title="Lucky Draw Display",
    on_load=LuckyDrawState.load_lucky_draw_display_data,
)
app.add_page(
    lucky_draw_external_display.lucky_draw_external_display_page,
    route="/lucky-draw/external-display/[event_id]",
    title="Lucky Draw External Display",
)
app.add_page(about.about_page, route="/about", title="About - EventLah")
app.add_page(products.products_page, route="/products", title="Products - EventLah")
app.add_page(contact.contact_page, route="/contact", title="Contact - EventLah")
# app.add_page(multi_scanner.multi_scanner_page, route="/scanners")