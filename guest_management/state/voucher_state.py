# guest_management/state/voucher_state.py
"""Voucher and stall management state."""

import reflex as rx
from typing import List, Dict, Any, Optional
from datetime import datetime
import base64
import json
import io
import os
from io import BytesIO

import pandas as pd
import qrcode

from guest_management.database_client import get_db
from guest_management.state.auth_state import AuthState
from guest_management.services.auth_service import AuthService
from guest_management.services.event_service import EventService
import logging

logger = logging.getLogger(__name__)


class VoucherState(rx.State):
    """Voucher and stall management state."""

    # ========================================================================
    # STALLS - All variables are regular class attributes
    # ========================================================================
    stalls_list: List[Dict[str, Any]] = []
    current_stall: Optional[Dict[str, Any]] = None
    current_guest: Optional[dict] = None
    has_amounts: bool = False

    # ========================================================================
    # STALL DIALOGS
    # ========================================================================
    show_stall_dialog: bool = False
    stall_name: str = ""
    show_menu_dialog: bool = False
    selected_stall_id: int = 0
    menu_item_name: str = ""
    menu_item_price: float = 0

    # ========================================================================
    # EDIT DIALOGS
    # ========================================================================
    show_edit_stall_dialog: bool = False
    editing_stall: Optional[dict] = None
    edit_stall_name: str = ""
    show_edit_item_dialog: bool = False
    editing_item: Optional[dict] = None
    edit_item_name: str = ""
    edit_item_price: float = 0

    # ========================================================================
    # DELETE CONFIRMATIONS
    # ========================================================================
    show_delete_stall_confirm: bool = False
    stall_to_delete: Optional[dict] = None
    show_delete_all_stalls_confirm: bool = False

    # ========================================================================
    # ORDERS
    # ========================================================================
    order_items: List[dict] = []
    order_total: float = 0
    order_receipt: dict = {"items": [], "total": 0, "balance": 0}
    show_purchase_receipt: bool = False

    def reset_order(self):
        """Reset the current order and close the purchase receipt."""
        self.order_items = []
        self.order_total = 0.0
        self.order_receipt = {
            "items": [],
            "total": 0.0,
            "balance": 0.0,
        }
        self.show_purchase_receipt = False

    def exit_to_lobby(self):
        """Return to the stall landing page for the current event."""
        self.reset_order()

        # Clear only the currently selected stall.
        self.current_stall = None

        # Keep event and guest authentication context.
        # This allows the guest to move between stalls without
        # entering their ID again.
        self.show_purchase_receipt = False

        if self.url_event_id:
            return rx.redirect(f"/stall?event_id={self.url_event_id}")

        return rx.redirect("/stall")

    # ========================================================================
    # TRANSACTION HISTORY
    # ========================================================================
    show_history_modal: bool = False
    history_guest: Optional[dict] = None
    transactions_list: List[dict] = []

    async def continue_to_menu(self):
        stall_id = self.url_stall_id
        guest_id = self.authenticated_guest.get("guest_id", "") if self.authenticated_guest else ""
        if stall_id and guest_id:
            self.current_guest = self.authenticated_guest
            yield rx.redirect(f"/stall/menu?stall_id={stall_id}&guest_id={guest_id}")
    async def show_guest_history(self, guest: dict):
        """Load and display purchase history for a guest within the current event."""
        try:
            guest_id = (
                guest.get("ID")
                or guest.get("Id")
                or guest.get("id")
                or guest.get("guest_id")
            )

            if not guest_id:
                yield rx.toast.error("Guest ID not found")
                return

            # The dashboard supplies the event context. Prefer the guest's
            # event_id when available, but never allow a cross-event lookup.
            event_id = guest.get("event_id") or self.current_event_id

            if not event_id:
                yield rx.toast.error("Event context not found")
                return

            try:
                event_id_int = int(event_id)
            except (TypeError, ValueError):
                yield rx.toast.error("Invalid event context")
                return

            # This method is an administrative dashboard operation.
            auth = await self.get_state(AuthState)

            if not auth.user_id:
                yield rx.toast.error("Authentication required")
                return

            if not AuthService.can_manage_events(auth.user):
                yield rx.toast.error(
                    "You are not authorized to view purchase history"
                )
                return

            # Confirm the authenticated administrator is authorized for
            # this specific event.
            EventService().get_event(
                event_id_int,
                auth.user_id,
                auth.user,
            )

            self.history_guest = guest
            self.transactions_list = []
            self.show_history_modal = True

            db = get_db()

            response = (
                db.table("transactions")
                .select("*")
                .eq("guest_id", str(guest_id))
                .eq("event_id", event_id_int)
                .order("created_at", desc=True)
                .execute()
            )

            transactions = response.data or []
            formatted_transactions = []

            for transaction in transactions:
                item = dict(transaction)

                amount = item.get("amount", 0) or 0

                try:
                    amount = float(amount)
                except (TypeError, ValueError):
                    amount = 0.0

                created_at = item.get("created_at", "")

                if created_at:
                    try:
                        dt = datetime.fromisoformat(
                            str(created_at).replace("Z", "+00:00")
                        )
                        formatted_date = dt.strftime("%d %b %Y, %I:%M %p")
                    except (TypeError, ValueError):
                        formatted_date = str(created_at)
                else:
                    formatted_date = ""

                item["amount"] = amount
                item["formatted_date"] = formatted_date

                formatted_transactions.append(item)

            self.transactions_list = formatted_transactions

            if not transactions:
                yield rx.toast.info("No purchase history found")

        except Exception:
            logger.exception("Failed to load guest purchase history")
            self.transactions_list = []
            self.show_history_modal = False
            yield rx.toast.error("Unable to load purchase history")

    def close_history_modal(self):
        """Close the purchase history modal."""
        self.show_history_modal = False
        self.history_guest = None
        self.transactions_list = []

    # ========================================================================
    # STALL LANDING / GUEST AUTH - ALL REGULAR VARIABLES (NO PROPERTIES)
    # ========================================================================
    url_stall_id: str = ""
    url_event_id: str = ""
    guest_id_input: str = ""
    guest_authenticated: bool = False
    authenticated_guest: Optional[dict] = None
    params_loaded: bool = False
    stall_load_error: bool = False
    show_qr_dialog: bool = False

    # ========================================================================
    # DELEGATED EVENT PROPERTIES - Use regular attributes instead of @property
    # ========================================================================
    # These are set by parent states or from URL
    current_event_id: str = ""
    current_event: Optional[Dict[str, Any]] = None
    guest_data: List[Dict[str, Any]] = []

    # ========================================================================
    # LOADING
    # ========================================================================
    is_loading: bool = False

    # ========================================================================
    # COMPUTED PROPERTIES (rx.var) - These are fine
    # ========================================================================

    @rx.var
    def is_insufficient_balance(self) -> bool:
        if not self.current_guest:
            return False
        return self.order_total > self.current_guest.get("amount", 0)

    @rx.var
    def used_amount(self) -> float:
        if not self.authenticated_guest:
            return 0.0
        initial = self.authenticated_guest.get("initial_amount", 0)
        current = self.authenticated_guest.get("amount", 0)
        return max(0, initial - current)

    # ========================================================================
    # STALL MANAGEMENT
    # ========================================================================

    async def _authorize_voucher_admin(self) -> tuple[AuthState, int]:
        """Authorize the current user to manage vouchers for the current event."""
        if not self.current_event_id:
            raise PermissionError("Event is not selected")

        try:
            event_id = int(self.current_event_id)
        except (TypeError, ValueError):
            raise PermissionError("Invalid event ID")

        auth = await self.get_state(AuthState)

        if not auth.user_id or not AuthService.can_manage_events(auth.user):
            raise PermissionError("Voucher management requires event admin access")

        EventService().get_event(
            event_id,
            auth.user_id,
            auth.user,
        )

        return auth, event_id

    def _get_current_event_id_for_public_stall(self) -> int | None:
        """Return the event ID represented by the public stall URL."""
        event_id = self.url_event_id or self.current_event_id

        if not event_id:
            return None

        try:
            return int(event_id)
        except (TypeError, ValueError):
            return None

    async def load_stalls(self):
        if not self.current_event_id:
            return

        try:
            db = get_db()
            event_id_int = int(self.current_event_id)

            stalls_res = db.table("stalls").select("*").eq("event_id", event_id_int).execute()
            stalls = stalls_res.data or []

            if not stalls:
                self.stalls_list = []
                return

            stall_ids = [s["id"] for s in stalls]
            menu_res = db.table("menu_items") \
                .select("*") \
                .in_("stall_id", stall_ids) \
                .execute()

            menu_lookup = {}
            for item in (menu_res.data or []):
                stall_id = item["stall_id"]
                if stall_id not in menu_lookup:
                    menu_lookup[stall_id] = []
                menu_lookup[stall_id].append(item)

            for stall in stalls:
                stall["menu_items"] = menu_lookup.get(stall["id"], [])

            self.stalls_list = stalls

        except Exception as e:
            logger.error(f"Error loading stalls: {e}")
            self.stalls_list = []
        finally:
            yield

    def load_stall_by_id(self, stall_id: int) -> bool:
        event_id = self._get_current_event_id_for_public_stall()

        if event_id is None:
            self.current_stall = None
            return False

        for stall in self.stalls_list:
            if (
                stall.get("id") == stall_id
                and stall.get("event_id") == event_id
            ):
                self.current_stall = stall
                return True

        db = get_db()

        res = (
            db.table("stalls")
            .select("*")
            .eq("id", stall_id)
            .eq("event_id", event_id)
            .execute()
        )

        if res.data:
            stall = res.data[0]

            menu_res = (
                db.table("menu_items")
                .select("*")
                .eq("stall_id", stall["id"])
                .execute()
            )

            stall["menu_items"] = menu_res.data or []
            self.current_stall = stall
            self.current_event_id = str(event_id)
            return True

        self.current_stall = None
        return False

    # ========================================================================
    # STALL CRUD
    # ========================================================================

    def open_stall_dialog(self):
        self.show_stall_dialog = True

    def close_stall_dialog(self):
        self.show_stall_dialog = False
        self.stall_name = ""

    def set_stall_name(self, value: str):
        self.stall_name = value

    async def add_stall(self):
        try:
            _, event_id = await self._authorize_voucher_admin()
        except Exception as e:
            logger.warning("Unauthorized voucher stall creation attempt: %s", e)
            yield rx.toast.error("You are not authorized to manage this event")
            return

        if not self.stall_name:
            yield rx.toast.error("Please enter stall name")
            return

        self.is_loading = True
        yield

        try:
            db = get_db()
            base_url = os.getenv("APP_URL", "http://localhost:3000")
            if base_url.startswith("https://http://"):
                base_url = base_url.replace("https://http://", "https://")
            elif base_url.startswith("http://https://"):
                base_url = base_url.replace("http://https://", "https://")
            base_url = base_url.rstrip('/')

            result = db.table("stalls").insert({
                "event_id": event_id,
                "stall_name": self.stall_name,
                "qr_code": ""
            }).execute()

            if result.data:
                new_stall = result.data[0]
                qr_url = f"{base_url}/stall?stall_id={new_stall['id']}&event_id={self.current_event_id}"

                qr = qrcode.QRCode(
                    version=None,
                    error_correction=qrcode.constants.ERROR_CORRECT_H,
                    box_size=10,
                    border=4,
                )
                qr.add_data(qr_url)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                img_str = base64.b64encode(buffer.getvalue()).decode()
                qr_code_data = f"data:image/png;base64,{img_str}"

                db.table("stalls").update({"qr_code": qr_code_data}).eq("id", new_stall["id"]).execute()

                await self.load_stalls()
                stall_name_saved = self.stall_name
                self.stall_name = ""
                self.show_stall_dialog = False
                self.is_loading = False
                yield rx.toast.success(f"Stall '{stall_name_saved}' added with QR code")

        except Exception as e:
            logger.error(f"Error adding stall: {e}")
            self.is_loading = False
            yield rx.toast.error(f"Error: {str(e)}")
        finally:
            self.is_loading = False
            yield

    # ========================================================================
    # MENU ITEMS
    # ========================================================================

    def open_menu_dialog(self, stall_id: int):
        self.selected_stall_id = stall_id
        self.show_menu_dialog = True

    def close_menu_dialog(self):
        self.show_menu_dialog = False
        self.menu_item_name = ""
        self.menu_item_price = 0

    def set_menu_item_name(self, value: str):
        self.menu_item_name = value

    def set_menu_item_price(self, value: str):
        try:
            self.menu_item_price = float(value)
        except:
            self.menu_item_price = 0

    async def add_menu_item(self):
        try:
            _, event_id = await self._authorize_voucher_admin()
        except Exception as e:
            logger.warning("Unauthorized voucher menu creation attempt: %s", e)
            yield rx.toast.error("You are not authorized to manage this event")
            return

        if not self.menu_item_name or self.menu_item_price <= 0:
            yield rx.toast.error("Please fill item name and valid price")
            return

        self.is_loading = True
        yield

        try:
            db = get_db()

            stall_res = (
                db.table("stalls")
                .select("id")
                .eq("id", self.selected_stall_id)
                .eq("event_id", event_id)
                .execute()
            )

            if not stall_res.data:
                yield rx.toast.error("Invalid stall for this event")
                return

            result = db.table("menu_items").insert({
                "stall_id": self.selected_stall_id,
                "item_name": self.menu_item_name,
                "price": self.menu_item_price
            }).execute()

            if result.data:
                self.menu_item_name = ""
                self.menu_item_price = 0
                self.show_menu_dialog = False
                await self.load_stalls()
                self.is_loading = False
                yield rx.toast.success("Menu item added")

        except Exception as e:
            logger.error(f"Error adding menu item: {e}")
            self.is_loading = False
            yield rx.toast.error(f"Error: {str(e)}")
        finally:
            self.is_loading = False
            yield

    # ========================================================================
    # EDIT METHODS
    # ========================================================================

    async def edit_stall(self, stall_id: int, stall_name: str):
        self.editing_stall = {"id": stall_id, "name": stall_name}
        self.edit_stall_name = stall_name
        self.show_edit_stall_dialog = True
        yield

    async def update_stall_name(self):
        try:
            _, event_id = await self._authorize_voucher_admin()
        except Exception as e:
            logger.warning("Unauthorized voucher stall update attempt: %s", e)
            yield rx.toast.error("You are not authorized to manage this event")
            return

        if not self.editing_stall or not self.edit_stall_name.strip():
            yield rx.toast.error("Stall name cannot be empty")
            return

        self.is_loading = True
        yield

        try:
            db = get_db()
            result = db.table("stalls").update({
                "stall_name": self.edit_stall_name.strip()
            }).eq("id", self.editing_stall["id"]).eq("event_id", event_id).execute()

            if result.data:
                await self.load_stalls()
                self.is_loading = False
                self.show_edit_stall_dialog = False
                self.editing_stall = None
                self.edit_stall_name = ""
                yield rx.toast.success(f"Stall renamed to '{self.edit_stall_name}'")

        except Exception as e:
            logger.error(f"Error updating stall: {e}")
            self.is_loading = False
            yield rx.toast.error(f"Error: {str(e)}")
        finally:
            self.is_loading = False
            yield

    def cancel_edit_stall(self):
        self.show_edit_stall_dialog = False
        self.editing_stall = None
        self.edit_stall_name = ""

    def set_edit_stall_name(self, value: str):
        self.edit_stall_name = value

    async def edit_menu_item(self, stall_id: int, item_id: int, current_name: str, current_price: float):
        self.editing_item = {
            "stall_id": stall_id,
            "item_id": item_id,
            "name": current_name,
            "price": current_price
        }
        self.edit_item_name = current_name
        self.edit_item_price = current_price
        self.show_edit_item_dialog = True
        yield

    async def update_menu_item(self):
        try:
            _, event_id = await self._authorize_voucher_admin()
        except Exception as e:
            logger.warning("Unauthorized voucher menu update attempt: %s", e)
            yield rx.toast.error("You are not authorized to manage this event")
            return

        if not self.editing_item:
            return

        if not self.edit_item_name.strip():
            yield rx.toast.error("Item name cannot be empty")
            return

        if self.edit_item_price <= 0:
            yield rx.toast.error("Price must be greater than 0")
            return

        self.is_loading = True
        yield

        try:
            db = get_db()

            stall_res = (
                db.table("stalls")
                .select("id")
                .eq("id", self.editing_item["stall_id"])
                .eq("event_id", event_id)
                .execute()
            )

            if not stall_res.data:
                yield rx.toast.error("Invalid stall for this event")
                return

            result = (
                db.table("menu_items")
                .update({
                    "item_name": self.edit_item_name.strip(),
                    "price": self.edit_item_price,
                })
                .eq("id", self.editing_item["item_id"])
                .eq("stall_id", self.editing_item["stall_id"])
                .execute()
            )

            if result.data:
                await self.load_stalls()
                self.is_loading = False
                self.show_edit_item_dialog = False
                self.editing_item = None
                self.edit_item_name = ""
                self.edit_item_price = 0
                yield rx.toast.success(f"Menu item updated to '{self.edit_item_name}'")

        except Exception as e:
            logger.error(f"Error updating menu item: {e}")
            self.is_loading = False
            yield rx.toast.error(f"Error: {str(e)}")
        finally:
            self.is_loading = False
            yield

    def cancel_edit_item(self):
        self.show_edit_item_dialog = False
        self.editing_item = None
        self.edit_item_name = ""
        self.edit_item_price = 0

    def set_edit_item_name(self, value: str):
        self.edit_item_name = value

    def set_edit_item_price(self, value: str):
        try:
            self.edit_item_price = float(value)
        except:
            self.edit_item_price = 0

    # ========================================================================
    # DELETE METHODS
    # ========================================================================

    async def delete_stall(self, stall_id: int, stall_name: str):
        self.show_delete_stall_confirm = True
        self.stall_to_delete = {"id": stall_id, "name": stall_name}
        yield

    async def confirm_delete_stall(self):
        try:
            _, event_id = await self._authorize_voucher_admin()
        except Exception as e:
            logger.warning("Unauthorized voucher stall deletion attempt: %s", e)
            yield rx.toast.error("You are not authorized to manage this event")
            return

        if not self.stall_to_delete:
            yield rx.toast.error("No stall selected for deletion")
            return

        stall_id = self.stall_to_delete["id"]
        stall_name = self.stall_to_delete["name"]

        self.is_loading = True
        yield

        try:
            db = get_db()

            stall_res = (
                db.table("stalls")
                .select("id")
                .eq("id", stall_id)
                .eq("event_id", event_id)
                .execute()
            )

            if not stall_res.data:
                yield rx.toast.error("Invalid stall for this event")
                return

            db.table("menu_items").delete().eq("stall_id", stall_id).execute()

            result = (
                db.table("stalls")
                .delete()
                .eq("id", stall_id)
                .eq("event_id", event_id)
                .execute()
            )

            if result.data:
                await self.load_stalls()
                self.is_loading = False
                self.show_delete_stall_confirm = False
                self.stall_to_delete = None
                yield rx.toast.success(f"Stall '{stall_name}' deleted successfully!")

        except Exception as e:
            logger.error(f"Error deleting stall: {e}")
            self.is_loading = False
            yield rx.toast.error(f"Error: {str(e)}")
        finally:
            self.is_loading = False
            yield

    def cancel_delete_stall(self):
        self.show_delete_stall_confirm = False
        self.stall_to_delete = None

    async def delete_menu_item(self, stall_id: int, item_id: int, item_name: str):
        try:
            _, event_id = await self._authorize_voucher_admin()
        except Exception as e:
            logger.warning("Unauthorized voucher menu deletion attempt: %s", e)
            yield rx.toast.error("You are not authorized to manage this event")
            return

        self.is_loading = True
        yield

        try:
            db = get_db()

            stall_res = (
                db.table("stalls")
                .select("id")
                .eq("id", stall_id)
                .eq("event_id", event_id)
                .execute()
            )

            if not stall_res.data:
                yield rx.toast.error("Invalid stall for this event")
                return

            result = (
                db.table("menu_items")
                .delete()
                .eq("id", item_id)
                .eq("stall_id", stall_id)
                .execute()
            )

            if result.data:
                await self.load_stalls()
                self.is_loading = False
                yield rx.toast.success(f"Menu item '{item_name}' deleted successfully!")

        except Exception as e:
            logger.error(f"Error deleting menu item: {e}")
            self.is_loading = False
            yield rx.toast.error(f"Error: {str(e)}")
        finally:
            self.is_loading = False
            yield

    async def delete_all_stalls(self):
        self.show_delete_all_stalls_confirm = True
        yield

    async def confirm_delete_all_stalls(self):
        try:
            _, event_id = await self._authorize_voucher_admin()
        except Exception as e:
            logger.warning("Unauthorized bulk voucher deletion attempt: %s", e)
            yield rx.toast.error("You are not authorized to manage this event")
            return

        self.is_loading = True
        yield

        try:
            db = get_db()
            stalls_res = db.table("stalls").select("id").eq("event_id", event_id).execute()
            stall_ids = [s["id"] for s in stalls_res.data] if stalls_res.data else []

            if stall_ids:
                db.table("menu_items").delete().in_("stall_id", stall_ids).execute()

            db.table("stalls").delete().eq("event_id", event_id).execute()
            await self.load_stalls()
            self.is_loading = False
            self.show_delete_all_stalls_confirm = False
            yield rx.toast.success("All stalls and menu items deleted successfully!")

        except Exception as e:
            logger.error(f"Error deleting all stalls: {e}")
            self.is_loading = False
            yield rx.toast.error(f"Error: {str(e)}")
        finally:
            self.is_loading = False
            yield

    def cancel_delete_all_stalls(self):
        self.show_delete_all_stalls_confirm = False

    # ========================================================================
    # ORDERS
    # ========================================================================

    def toggle_order_item(self, item: dict, checked: bool):
        if checked:
            if not any(i.get("id") == item.get("id") for i in self.order_items):
                self.order_items.append(item)
        else:
            self.order_items = [i for i in self.order_items if i.get("id") != item.get("id")]
        self.order_total = sum(i.get("price", 0) for i in self.order_items)

    async def confirm_purchase(self):
        """Complete a voucher purchase atomically in PostgreSQL."""
        if not self.order_items:
            yield rx.toast.error("No items selected")
            return
        if not self.current_guest or not self.current_stall or not self.current_event_id:
            yield rx.toast.error("Guest, stall, or event session is invalid")
            return

        self.is_loading = True
        yield
        try:
            from guest_management.database_client import get_db
            items = [{"id": item.get("id")} for item in self.order_items]
            response = get_db().rpc(
                "process_voucher_purchase",
                {
                    "p_event_id": int(self.current_event_id),
                    "p_guest_id": str(self.current_guest["guest_id"]),
                    "p_stall_id": int(self.current_stall["id"]),
                    "p_items": items,
                },
            ).execute()
            result = (response.data or [{}])[0]
            status = result.get("result")
            if status != "success":
                messages = {
                    "insufficient_balance": "Insufficient balance",
                    "not_checked_in": "Guest must be checked in first",
                    "not_found": "Guest not found",
                    "invalid": "Invalid purchase request",
                }
                yield rx.toast.error(messages.get(status, result.get("message", "Purchase failed")))
                return

            new_balance = float(result.get("balance_after") or 0)
            total = float(result.get("total") or 0)
            items_summary = ", ".join(
                f"{item.get('item_name', 'Item')}" for item in self.order_items
            )
            self.order_receipt = {
                "items": self.order_items,
                "items_summary": items_summary,
                "total": total,
                "balance": new_balance,
            }
            self.order_items = []
            self.order_total = 0
            self.show_purchase_receipt = True
            self.current_guest["amount"] = new_balance
            if self.authenticated_guest:
                self.authenticated_guest["amount"] = new_balance
            yield rx.toast.success(f"Purchase completed: RM {total:.2f}")
        except Exception:
            logger.exception("Atomic voucher purchase failed")
            yield rx.toast.error("Purchase failed. Your balance was not changed.")
        finally:
            self.is_loading = False
            yield

    def load_guest_by_id(self, guest_id: str):
        for g in self.guest_data:
            if g.get("ID") == guest_id or g.get("guest_id") == guest_id:
                self.current_guest = {
                    "name": g.get("Name", ""),
                    "guest_id": g.get("ID", g.get("guest_id", "")),
                    "amount": g.get("amount", 0),
                    "email": g.get("Email", ""),
                    "status": g.get("Status", "")
                }
                return

        db = get_db()
        res = db.table("guests").select("*").eq("guest_id", guest_id).eq("event_id", int(self.current_event_id)).execute()
        if res.data:
            guest = res.data[0]
            self.current_guest = {
                "name": guest.get("name", ""),
                "guest_id": guest.get("guest_id", ""),
                "amount": guest.get("amount", 0),
                "email": guest.get("email", ""),
                "status": guest.get("status", "")
            }

    def setup_stall_menu(self):
        import urllib.parse
        query_str = self.router.url.query
        if query_str:
            if query_str.startswith('?'):
                query_str = query_str[1:]
            params = urllib.parse.parse_qs(query_str)
            stall_id = params.get("stall_id", [""])[0]
            guest_id = params.get("guest_id", [""])[0]
        else:
            stall_id = ""
            guest_id = ""

        if stall_id:
            try:
                self.load_stall_by_id(int(stall_id))
            except ValueError:
                pass
        if guest_id:
            self.load_guest_by_id(guest_id)

    async def load_stall_from_params(self):
        import urllib.parse

        self.params_loaded = False
        self.stall_load_error = False

        query_str = self.router.url.query
        if query_str:
            if query_str.startswith('?'):
                query_str = query_str[1:]
            params = urllib.parse.parse_qs(query_str)
            self.url_stall_id = params.get("stall_id", [""])[0]
            self.url_event_id = params.get("event_id", [""])[0]

        if not self.url_stall_id or not self.url_event_id:
            path = self.router.url.path
            path_parts = path.split('/')
            if len(path_parts) >= 3 and path_parts[1] == "stall" and len(path_parts) >= 4:
                self.url_stall_id = path_parts[2]
                self.url_event_id = path_parts[3]

        if self.url_stall_id and self.url_event_id:
            self.current_event_id = self.url_event_id
            try:
                stall_id_int = int(self.url_stall_id)
                success = self.load_stall_by_id(stall_id_int)
                if not success:
                    self.stall_load_error = True
            except ValueError:
                self.stall_load_error = True
        else:
            self.stall_load_error = True

        self.params_loaded = True
        yield

    async def load_stall_from_url(self):
        if not self.url_stall_id or not self.url_event_id:
            return

        try:
            self.current_event_id = str(int(self.url_event_id))
            stall_id = int(self.url_stall_id)
            self.load_stall_by_id(stall_id)
        except (TypeError, ValueError):
            self.current_stall = None

    async def start_order_from_landing(self):
        """Authenticate a checked-in guest for the public voucher flow."""
        stall_id = self.url_stall_id
        event_id = self.url_event_id
        guest_id = self.guest_id_input.strip()

        if not guest_id:
            yield rx.toast.error("Please enter Guest ID")
            return

        if not stall_id or not event_id:
            yield rx.toast.error("Invalid stall or event information")
            return

        try:
            event_id_int = int(event_id)
            stall_id_int = int(stall_id)
        except (TypeError, ValueError):
            yield rx.toast.error("Invalid stall or event ID format")
            return

        # load_stall_by_id() is already event-scoped by the current
        # event context established from the public URL.
        if (
            not self.current_stall
            or self.current_stall.get("id") != stall_id_int
            or str(self.current_stall.get("event_id")) != str(event_id_int)
        ):
            self.load_stall_by_id(stall_id_int)

            if not self.current_stall:
                yield rx.toast.error("Stall not found")
                return

            if int(self.current_stall.get("event_id", -1)) != event_id_int:
                self.current_stall = None
                yield rx.toast.error("Invalid stall or event information")
                return

        db = get_db()

        res = (
            db.table("guests")
            .select("*")
            .eq("guest_id", guest_id)
            .eq("event_id", event_id_int)
            .execute()
        )

        if not res.data:
            yield rx.toast.error("Guest ID not found")
            return

        guest = res.data[0]

        if guest.get("status") != "Present":
            yield rx.toast.error(
                "You must check in at the event entrance first"
            )
            return

        # Guest IDs may contain quotes, backslashes, or other characters.
        # JSON encoding makes the value safe to embed as a JavaScript string.
        stored_guest_id = json.dumps(str(guest["guest_id"]))

        yield rx.call_script(
            f"""
            localStorage.setItem("last_guest_id", {stored_guest_id});
            """
        )

        # Store initial amount from full_data.
        initial_amount = guest.get("amount", 0)
        full_data = guest.get("full_data")

        if full_data:
            try:
                row = (
                    json.loads(full_data)
                    if isinstance(full_data, str)
                    else full_data
                )
                initial_amount = float(
                    row.get(
                        "Amount",
                        row.get("amount", initial_amount),
                    )
                )
            except Exception:
                pass

        guest["initial_amount"] = initial_amount

        self.authenticated_guest = guest
        self.guest_authenticated = True
        self.guest_id_input = ""

        yield rx.toast.success(
            f"Welcome, {guest.get('name')}!"
        )
        yield

    def reset_stall_session(self):
        self.guest_authenticated = False
        self.authenticated_guest = None
        self.guest_id_input = ""

    def scan_new_stall(self):
        self.reset_stall_session()

    def set_guest_id_input(self, value: str):
        self.guest_id_input = value

    def clear_stored_guest(self):
        yield rx.call_script("localStorage.removeItem('last_guest_id');")
        self.guest_id_input = ""
        yield rx.toast.info("Cleared saved guest ID")

    def set_url_params(self, stall_id: str, event_id: str):
        self.url_stall_id = stall_id
        self.url_event_id = event_id

        if not stall_id or not event_id:
            self.current_stall = None
            return

        try:
            self.current_event_id = str(int(event_id))
            self.load_stall_by_id(int(stall_id))
        except (TypeError, ValueError):
            self.current_stall = None

    # ========================================================================
    # QR
    # ========================================================================

    def show_stall_qr(self, stall: dict):
        stall_id = stall.get("id")
        event_id = self.current_event_id

        base_url = os.getenv("APP_URL", "http://localhost:3000")
        base_url = base_url.rstrip('/')
        if base_url.startswith("https://http://"):
            base_url = base_url.replace("https://http://", "https://")
        elif base_url.startswith("http://https://"):
            base_url = base_url.replace("http://https://", "https://")

        url = f"{base_url}/stall?stall_id={stall_id}&event_id={event_id}"

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        self.current_stall = stall
        self.current_stall["qr_code_data"] = f"data:image/png;base64,{img_str}"
        self.current_stall["qr_url"] = url
        self.show_qr_dialog = True

    def close_qr_dialog(self):
        self.show_qr_dialog = False
        self.current_stall = None

    # ========================================================================
    # EXCEL UPLOAD
    # ========================================================================

    async def handle_stall_excel_upload(self, files: List[rx.UploadFile]):
        try:
            _, event_id = await self._authorize_voucher_admin()
        except Exception as e:
            logger.warning("Unauthorized voucher Excel upload attempt: %s", e)
            yield rx.toast.error("You are not authorized to manage this event")
            return

        if not files or len(files) == 0:
            yield rx.toast.error("No file selected. Please select a file first.")
            return

        self.is_loading = True
        yield

        try:
            file = files[0]
            content = await file.read()

            if len(content) == 0:
                yield rx.toast.error("The selected file is empty.")
                self.is_loading = False
                return

            try:
                df = pd.read_excel(io.BytesIO(content))
            except Exception as e:
                yield rx.toast.error(f"Could not read Excel file: {str(e)}")
                self.is_loading = False
                return

            stall_col = None
            item_col = None
            price_col = None

            for col in df.columns:
                col_lower = col.lower().strip()
                if any(keyword in col_lower for keyword in ["stall", "stall_name", "stall name", "vendor", "booth"]):
                    stall_col = col
                elif any(keyword in col_lower for keyword in ["item", "menu", "product", "item_name", "menu item"]):
                    item_col = col
                elif any(keyword in col_lower for keyword in ["price", "cost", "amount", "rm"]):
                    price_col = col

            if stall_col is None:
                yield rx.toast.error("Could not find 'Stall' column.")
                self.is_loading = False
                return

            if item_col is None:
                yield rx.toast.error("Could not find 'Item' column.")
                self.is_loading = False
                return

            if price_col is None:
                yield rx.toast.error("Could not find 'Price' column.")
                self.is_loading = False
                return

            db = get_db()
            base_url = os.getenv("APP_URL", "http://localhost:3000")
            if base_url.startswith("https://http://"):
                base_url = base_url.replace("https://http://", "https://")
            elif base_url.startswith("http://https://"):
                base_url = base_url.replace("http://https://", "https://")
            base_url = base_url.rstrip('/')

            processed_stalls = {}
            current_stall_name = None
            success_count = 0
            skipped_count = 0

            for idx, row in df.iterrows():
                stall_name = str(row[stall_col]).strip() if pd.notna(row[stall_col]) else None

                if stall_name and stall_name != "nan" and stall_name != "None":
                    current_stall_name = stall_name
                else:
                    stall_name = current_stall_name

                item_name = str(row[item_col]).strip() if pd.notna(row[item_col]) else None

                if not item_name or item_name == "nan" or item_name == "None":
                    skipped_count += 1
                    continue

                price = 0
                if pd.notna(row[price_col]):
                    try:
                        price_str = str(row[price_col]).replace("RM", "").replace("rm", "").replace("$", "").strip()
                        price = float(price_str)
                    except:
                        price = 0

                if not stall_name or stall_name == "nan" or stall_name == "None":
                    skipped_count += 1
                    continue

                if price <= 0:
                    skipped_count += 1
                    continue

                if stall_name not in processed_stalls:
                    existing = db.table("stalls").select("*").eq("event_id", int(self.current_event_id)).eq("stall_name", stall_name).execute()

                    if existing.data:
                        stall = existing.data[0]
                        processed_stalls[stall_name] = stall
                    else:
                        new_stall = db.table("stalls").insert({
                            "event_id": event_id,
                            "stall_name": stall_name,
                            "qr_code": ""
                        }).execute()

                        if not new_stall.data:
                            continue

                        stall = new_stall.data[0]
                        qr_url = f"{base_url}/stall?stall_id={stall['id']}&event_id={self.current_event_id}"

                        qr = qrcode.QRCode(
                            version=None,
                            error_correction=qrcode.constants.ERROR_CORRECT_H,
                            box_size=10,
                            border=4,
                        )
                        qr.add_data(qr_url)
                        qr.make(fit=True)

                        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
                        buffer = BytesIO()
                        img.save(buffer, format="PNG")
                        img_str = base64.b64encode(buffer.getvalue()).decode()
                        qr_code_data = f"data:image/png;base64,{img_str}"

                        db.table("stalls").update({"qr_code": qr_code_data}).eq("id", stall["id"]).execute()
                        processed_stalls[stall_name] = stall
                else:
                    stall = processed_stalls[stall_name]

                existing_item = db.table("menu_items").select("*").eq("stall_id", stall["id"]).eq("item_name", item_name).execute()

                if not existing_item.data:
                    result = db.table("menu_items").insert({
                        "stall_id": stall["id"],
                        "item_name": item_name,
                        "price": price
                    }).execute()

                    if result.data:
                        success_count += 1

            await self.load_stalls()
            self.is_loading = False
            total_stalls = len(processed_stalls)

            if success_count > 0:
                yield rx.toast.success(f"Successfully uploaded {success_count} item(s) to {total_stalls} stall(s)!")
            elif total_stalls > 0:
                yield rx.toast.warning(f"No new items added. {skipped_count} row(s) skipped.")
            else:
                yield rx.toast.error("No stalls or items were uploaded.")

            if skipped_count > 0:
                yield rx.toast.info(f"Skipped {skipped_count} row(s) with missing or invalid data.")

        except Exception as e:
            logger.error(f"Stall upload error: {e}")
            self.is_loading = False
            yield rx.toast.error(f"Error processing file: {str(e)}")
        finally:
            self.is_loading = False
            yield

    # ========================================================================
    # LOAD GUESTS (delegated to GuestState)
    # ========================================================================

    async def load_guests(self):
        """Load guests - should be implemented by parent state."""
        pass