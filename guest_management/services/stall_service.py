# guest_management/services/stall_service.py
"""Stall service."""

import logging
import base64
from io import BytesIO
from typing import Optional, Dict, Any, List, Tuple

import qrcode

from guest_management.repositories import StallRepository, GuestRepository, TransactionRepository
from guest_management.services.qr_service import QRService
from guest_management.core.exceptions import StallNotFoundError, ValidationError
from guest_management.utils.constants import MAX_UPLOAD_BATCH_SIZE
from guest_management.utils.helpers import safe_float, safe_str

logger = logging.getLogger(__name__)


class StallService:
    """Service for stall operations."""

    def __init__(self):
        self.repo = StallRepository()
        self.guest_repo = GuestRepository()
        self.transaction_repo = TransactionRepository()
        self.qr_service = QRService()

    # --- Stall CRUD ---

    def get_stalls_by_event(self, event_id: int) -> List[Dict[str, Any]]:
        """Get all stalls for an event with menu items."""
        return self.repo.get_stalls_with_menu(event_id)

    def get_stall(self, stall_id: int) -> Dict[str, Any]:
        """Get stall by ID with menu items."""
        stall = self.repo.get_by_id(stall_id)
        if not stall:
            raise StallNotFoundError(f"Stall {stall_id} not found")
        stall["menu_items"] = self.repo.get_menu_items(stall_id)
        return stall

    def create_stall(self, event_id: int, stall_name: str) -> Dict[str, Any]:
        """Create a new stall with QR code."""
        if not stall_name or not stall_name.strip():
            raise ValidationError("Stall name is required")

        # Create stall
        stall_data = {
            "event_id": event_id,
            "stall_name": stall_name.strip(),
            "qr_code": "",  # Placeholder
        }

        stall = self.repo.create(stall_data)
        if not stall:
            raise Exception("Failed to create stall")

        # Generate QR code
        qr_code = self.qr_service.generate_stall_qr(stall["id"], event_id)
        self.repo.update(stall["id"], {"qr_code": qr_code})

        return stall

    def update_stall(self, stall_id: int, stall_name: str, event_id: int) -> Dict[str, Any]:
        """Update stall name."""
        if not stall_name or not stall_name.strip():
            raise ValidationError("Stall name is required")

        # Verify stall exists
        stall = self.repo.get_by_id(stall_id)
        if not stall:
            raise StallNotFoundError(f"Stall {stall_id} not found")

        updated = self.repo.update(stall_id, {"stall_name": stall_name.strip()})
        if not updated:
            raise Exception("Failed to update stall")

        return updated

    def delete_stall(self, stall_id: int, event_id: int) -> bool:
        """Delete a stall and all its menu items."""
        # Verify stall exists
        stall = self.repo.get_by_id(stall_id)
        if not stall:
            raise StallNotFoundError(f"Stall {stall_id} not found")

        # Delete menu items first
        self.repo.delete_menu_items_by_stall(stall_id)

        # Delete stall
        return self.repo.delete(stall_id)

    def delete_all_stalls(self, event_id: int) -> int:
        """Delete all stalls and menu items for an event."""
        # Delete menu items
        self.repo.delete_menu_items_by_event(event_id)

        # Delete stalls
        return self.repo.delete_by_event(event_id)

    # --- Menu Items ---

    def add_menu_item(self, stall_id: int, item_name: str, price: float) -> Dict[str, Any]:
        """Add a menu item to a stall."""
        if not item_name or not item_name.strip():
            raise ValidationError("Item name is required")

        if price <= 0:
            raise ValidationError("Price must be greater than 0")

        # Verify stall exists
        stall = self.repo.get_by_id(stall_id)
        if not stall:
            raise StallNotFoundError(f"Stall {stall_id} not found")

        menu_data = {
            "stall_id": stall_id,
            "item_name": item_name.strip(),
            "price": price,
        }

        item = self.repo.create_menu_item(menu_data)
        if not item:
            raise Exception("Failed to add menu item")

        return item

    def update_menu_item(self, item_id: int, item_name: str, price: float) -> Dict[str, Any]:
        """Update a menu item."""
        if not item_name or not item_name.strip():
            raise ValidationError("Item name is required")

        if price <= 0:
            raise ValidationError("Price must be greater than 0")

        updated = self.repo.update_menu_item(item_id, {
            "item_name": item_name.strip(),
            "price": price,
        })

        if not updated:
            raise Exception("Failed to update menu item")

        return updated

    def delete_menu_item(self, item_id: int) -> bool:
        """Delete a menu item."""
        return self.repo.delete_menu_item(item_id)

    # --- Bulk Operations ---

    def process_stall_excel(self, content: bytes, event_id: int, stall_col: str, item_col: str, price_col: str,
                            data: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Process Excel data and create stalls and menu items."""
        from guest_management.utils.url import get_app_url

        created_items = 0
        skipped_items = 0
        processed_stalls = {}
        current_stall_name = None

        for row in data:
            # Get stall name
            stall_name = row.get(stall_col, "")
            if stall_name and stall_name not in ["nan", "None", ""]:
                current_stall_name = str(stall_name).strip()
            else:
                stall_name = current_stall_name

            item_name = row.get(item_col, "")
            if not item_name or item_name in ["nan", "None", ""]:
                skipped_items += 1
                continue

            # Parse price
            try:
                price_str = str(row.get(price_col, "0")).replace("RM", "").replace("rm", "").replace("$", "").strip()
                price = float(price_str) if price_str else 0
            except (ValueError, TypeError):
                price = 0

            if price <= 0:
                skipped_items += 1
                continue

            # Get or create stall
            if stall_name not in processed_stalls:
                existing = self.repo.repo.db.table("stalls").select("*").eq("event_id", event_id).eq("stall_name",
                                                                                                     stall_name).execute()

                if existing.data:
                    stall = existing.data[0]
                else:
                    # Create stall
                    stall_data = {
                        "event_id": event_id,
                        "stall_name": stall_name,
                        "qr_code": "",  # Placeholder
                    }
                    stall_result = self.repo.repo.db.table("stalls").insert(stall_data).execute()
                    if not stall_result.data:
                        skipped_items += 1
                        continue

                    stall = stall_result.data[0]

                    # Generate QR code
                    app_url = get_app_url()
                    qr_url = f"{app_url}/stall?stall_id={stall['id']}&event_id={event_id}"

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

                    self.repo.update(stall["id"], {"qr_code": qr_code_data})

                processed_stalls[stall_name] = stall
            else:
                stall = processed_stalls[stall_name]

            # Check if item already exists
            existing_item = self.repo.repo.db.table("menu_items").select("*").eq("stall_id", stall["id"]).eq(
                "item_name", item_name).execute()

            if not existing_item.data:
                result = self.repo.repo.db.table("menu_items").insert({
                    "stall_id": stall["id"],
                    "item_name": item_name.strip(),
                    "price": price,
                }).execute()

                if result.data:
                    created_items += 1
                else:
                    skipped_items += 1
            else:
                skipped_items += 1

        return created_items, skipped_items

    # --- Order Processing ---

    def process_order(self, guest_id: str, event_id: int, stall_id: int, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a food order."""
        # Get guest
        guest = self.guest_repo.get_by_guest_id(guest_id, event_id)
        if not guest:
            raise ValidationError("Guest not found")

        if guest.get("status") != "Present":
            raise ValidationError("Guest must be checked in first")

        # Get stall
        stall = self.repo.get_by_id(stall_id)
        if not stall:
            raise StallNotFoundError("Stall not found")

        # Calculate total
        total = sum(item.get("price", 0) for item in items)
        balance = guest.get("amount", 0)

        if balance < total:
            raise ValidationError(f"Insufficient balance! Need RM {total:.2f}, have RM {balance:.2f}")

        new_balance = balance - total

        # Update guest balance
        updated_guest = self.guest_repo.update(guest_id, event_id, {"amount": new_balance})
        if not updated_guest:
            raise Exception("Failed to update guest balance")

        # Record transactions
        transactions = []
        for item in items:
            transactions.append({
                "guest_id": guest_id,
                "event_id": event_id,
                "stall_id": stall_id,
                "item_name": item.get("item_name", ""),
                "amount": item.get("price", 0),
                "balance_after": new_balance,
            })

        self.transaction_repo.create_batch(transactions)

        return {
            "items": items,
            "total": total,
            "balance": new_balance,
            "guest_name": guest.get("name", "Guest"),
        }

    def get_guest_transactions(self, guest_id: str, event_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transaction history for a guest."""
        return self.transaction_repo.get_by_guest(guest_id, event_id, limit)

    def get_guest_balance(self, guest_id: str, event_id: int) -> float:
        """Get remaining balance for a guest."""
        guest = self.guest_repo.get_by_guest_id(guest_id, event_id)
        if not guest:
            return 0.0
        return guest.get("amount", 0.0)