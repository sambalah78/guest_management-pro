# guest_management/state/ui_state.py
"""UI state management - dialogs, loading, and UI controls."""

import reflex as rx
from typing import Optional, List, Dict, Any


class UIState(rx.State):
    """UI state management for dialogs, loading, and UI controls."""

    # ============ LOADING STATES ============
    is_loading: bool = False

    # ============ DIALOGS ============
    # Upload dialog
    show_upload_dialog: bool = False
    uploaded_filename: str = ""

    # Email dialog
    email_dialog_open: bool = False
    selected_guest_for_email: Optional[dict] = None
    sending_email_guest_id: str = ""
    email_sending: bool = False
    email_progress: int = 0
    email_total: int = 0

    # QR dialogs
    qr_dialog_open: bool = False
    guest_qr_dialog_open: bool = False
    show_qr_dialog: bool = False
    selected_guest_qr: str = ""
    selected_guest_name: str = ""

    # Logo dialog
    logo_dialog_open: bool = False

    # Company logo
    company_logo: str = ""
    company_logo_filename: str = ""

    # Show logo upload
    show_logo_upload: bool = False
    show_invitation_upload: bool = False

    # Clear table confirmation
    show_clear_table_confirm: bool = False

    # ============ SEARCH ============
    search_query: str = ""
    search_name: str = ""
    search_id: str = ""

    # ============ SCREEN ============
    screen_height: int = 0

    # ============ CONTACT FORM ============
    contact_name: str = ""
    contact_email: str = ""
    contact_message: str = ""
    contact_success: bool = False

    # ============ LUCKY DRAW UI ============
    lucky_draw_spinner_open: bool = False
    lucky_draw_show_new_draw_dialog: bool = False
    show_clear_confirm: bool = False
    lucky_draw_window_opened: bool = False
    lucky_draw_setup_complete: bool = False

    # ============ PURCHASE UI ============
    show_purchase_receipt: bool = False
    show_history_modal: bool = False

    # ============ MANUAL CHECK-IN UI ============
    manual_checkin_open: bool = False
    checkin_message: str = ""
    checkin_success: bool = False
    manual_name: str = ""
    manual_guest_id: str = ""

    # ============ KIOSK UI ============
    kiosk_state: str = "idle"  # idle, scanning, success, already_checked, error

    # ============ EVENT LOGO UPLOAD ============
    event_logo: str = ""
    wedding_invitation_card: str = ""

    # ============ TOAST HELPERS ============

    def show_toast(self, message: str, type: str = "info", duration: int = 3000):
        """Show a toast notification."""
        if type == "success":
            return rx.toast.success(message, duration=duration)
        elif type == "error":
            return rx.toast.error(message, duration=duration)
        elif type == "warning":
            return rx.toast.warning(message, duration=duration)
        else:
            return rx.toast.info(message, duration=duration)

    # ============ LOADING CONTROLS ============

    def set_loading(self, loading: bool):
        self.is_loading = loading

    def start_loading(self):
        self.is_loading = True

    def stop_loading(self):
        self.is_loading = False

    # ============ UPLOAD DIALOG ============

    def open_upload_dialog(self):
        self.show_upload_dialog = True

    def close_upload_dialog(self):
        self.show_upload_dialog = False
        self.uploaded_filename = ""

    # ============ EMAIL DIALOG ============

    def open_email_dialog(self, guest: dict):
        self.selected_guest_for_email = guest
        self.email_dialog_open = True

    def close_email_dialog(self):
        self.email_dialog_open = False
        self.selected_guest_for_email = None

    # ============ QR DIALOGS ============

    def open_qr_dialog(self):
        self.qr_dialog_open = True

    def close_qr_dialog(self):
        self.qr_dialog_open = False
        self.show_qr_dialog = False

    def close_guest_qr_dialog(self):
        self.guest_qr_dialog_open = False
        self.selected_guest_qr = ""
        self.selected_guest_name = ""

    # ============ LOGO ============

    def show_logo_dialog(self):
        self.logo_dialog_open = True

    def close_logo_dialog(self):
        self.logo_dialog_open = False

    def clear_logo(self):
        self.company_logo = ""
        self.company_logo_filename = ""
        return rx.toast.success("Logo cleared")

    def clear_event_logo(self):
        self.event_logo = ""
        return rx.toast.success("Logo removed")

    def clear_wedding_invitation(self):
        self.wedding_invitation_card = ""
        return rx.toast.success("Invitation removed")

    # ============ SCREEN ============

    def set_screen_height(self, height: int):
        self.screen_height = height
        available_height = height - 350
        calculated_items = max(15, min(25, available_height // 60))
        self.items_per_page = calculated_items
        self.current_page = 1
        self.calculate_total_pages()

    # ============ SEARCH ============

    def set_search_query(self, value: str):
        self.search_query = value

    def set_search_name(self, value: str):
        self.search_name = value

    def set_search_id(self, value: str):
        self.search_id = value

    # ============ CONTACT FORM ============

    def set_contact_name(self, value: str):
        self.contact_name = value

    def set_contact_email(self, value: str):
        self.contact_email = value

    def set_contact_message(self, value: str):
        self.contact_message = value

    async def submit_contact(self):
        if not self.contact_name or not self.contact_email or not self.contact_message:
            yield rx.toast.error("Please fill all fields")
            return

        self.contact_success = True
        yield rx.toast.success("Thank you! We'll get back to you soon.")

        self.contact_name = ""
        self.contact_email = ""
        self.contact_message = ""

        import asyncio
        await asyncio.sleep(3)
        self.contact_success = False
        yield

    # ============ MANUAL CHECK-IN UI ============

    def open_manual_checkin(self):
        self.manual_checkin_open = True

    def close_manual_checkin(self):
        self.manual_checkin_open = False
        self.manual_name = ""
        self.manual_guest_id = ""
        self.checkin_message = ""
        self.checkin_success = False

    def set_manual_name(self, value: str):
        self.manual_name = value

    def set_manual_guest_id(self, value: str):
        self.manual_guest_id = value

    # ============ KIOSK UI ============

    def set_kiosk_state(self, state: str):
        self.kiosk_state = state

    def reset_kiosk(self):
        self.kiosk_state = "idle"
        self.checkin_guest_name = ""
        self.checkin_table_number = ""

    # ============ LUCKY DRAW UI ============

    def open_lucky_draw_spinner(self):
        self.lucky_draw_spinner_open = True

    def close_lucky_draw_spinner(self):
        self.lucky_draw_spinner_open = False
        self.lucky_draw_spinning = False
        self.lucky_draw_winner = None
        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""

        return rx.call_script("""
            if (window.opener) {
                window.close();
            } else {
                window.location.href = '/lucky-draw';
            }
        """)

    def open_new_draw_dialog(self):
        self.lucky_draw_show_new_draw_dialog = True

    def close_new_draw_dialog(self):
        self.lucky_draw_show_new_draw_dialog = False

    def close_spinner_and_open_new_draw(self):
        self.lucky_draw_spinner_open = False
        self.lucky_draw_spinning = False
        self.lucky_draw_winner = None
        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""
        self.lucky_draw_show_new_draw_dialog = True

    def show_clear_confirm_dialog(self):
        self.show_clear_confirm = True

    def hide_clear_confirm_dialog(self):
        self.show_clear_confirm = False

    # ============ PURCHASE UI ============

    def show_purchase_receipt_dialog(self):
        self.show_purchase_receipt = True

    def hide_purchase_receipt_dialog(self):
        self.show_purchase_receipt = False

    # ============ CLEAR TABLE ============

    def show_clear_table_confirm_dialog(self):
        self.show_clear_table_confirm = True

    def hide_clear_table_confirm_dialog(self):
        self.show_clear_table_confirm = False

    # ============ BULK EMAIL UI ============

    def start_bulk_email(self, total: int):
        self.email_sending = True
        self.email_total = total
        self.email_progress = 0

    def update_bulk_email_progress(self, progress: int):
        self.email_progress = progress

    def stop_bulk_email(self):
        self.email_sending = False
        self.email_progress = 0
        self.email_total = 0
        self.sending_email_guest_id = ""

    def set_sending_email_guest_id(self, guest_id: str):
        self.sending_email_guest_id = guest_id

    def clear_sending_email_guest_id(self):
        self.sending_email_guest_id = ""

    # ============ EVENT LOGO UPLOAD UI ============

    def show_logo_upload_ui(self):
        self.show_logo_upload = True

    def hide_logo_upload_ui(self):
        self.show_logo_upload = False

    def show_invitation_upload_ui(self):
        self.show_invitation_upload = True

    def hide_invitation_upload_ui(self):
        self.show_invitation_upload = False

    # ============ CALCULATE TOTAL PAGES ============

    def calculate_total_pages(self):
        """Calculate total pages for pagination."""
        # This should be implemented by GuestState
        pass

    # ============ ITEMS PER PAGE ============

    @property
    def items_per_page(self) -> int:
        return getattr(self, '_items_per_page', 10)

    @items_per_page.setter
    def items_per_page(self, value: int):
        self._items_per_page = value

    @property
    def current_page(self) -> int:
        return getattr(self, '_current_page', 1)

    @current_page.setter
    def current_page(self, value: int):
        self._current_page = value