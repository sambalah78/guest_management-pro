# guest_management/repositories/stall_repository.py
"""Stall repository."""

import logging
from typing import Any, Dict, List, Optional

from .base import BaseRepository

logger = logging.getLogger(__name__)


class StallRepository(BaseRepository):
    """Repository for stall operations."""

    def get_by_event(self, event_id: int) -> List[Dict[str, Any]]:
        """Get all stalls for an event."""
        try:
            response = self.db.table("stalls").select("*").eq("event_id", event_id).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Get stalls for event {event_id} failed: {e}")
            return []

    def get_by_id(self, stall_id: int) -> Optional[Dict[str, Any]]:
        """Get stall by ID."""
        try:
            response = self.db.table("stalls").select("*").eq("id", stall_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Get stall {stall_id} failed: {e}")
            return None

    def get_menu_items(self, stall_id: int) -> List[Dict[str, Any]]:
        """Get menu items for a stall."""
        try:
            response = self.db.table("menu_items").select("*").eq("stall_id", stall_id).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Get menu items for stall {stall_id} failed: {e}")
            return []

    def get_stalls_with_menu(self, event_id: int) -> List[Dict[str, Any]]:
        """Get all stalls with their menu items."""
        try:
            stalls = self.get_by_event(event_id)
            for stall in stalls:
                stall["menu_items"] = self.get_menu_items(stall["id"])
            return stalls
        except Exception as e:
            logger.error(f"Get stalls with menu for event {event_id} failed: {e}")
            return []

    def create(self, stall_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new stall."""
        try:
            response = self.db.table("stalls").insert(stall_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Create stall failed: {e}")
            return None

    def update(self, stall_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a stall."""
        try:
            response = self.db.table("stalls").update(updates).eq("id", stall_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Update stall {stall_id} failed: {e}")
            return None

    def delete(self, stall_id: int) -> bool:
        """Delete a stall."""
        try:
            self.db.table("stalls").delete().eq("id", stall_id).execute()
            return True
        except Exception as e:
            logger.error(f"Delete stall {stall_id} failed: {e}")
            return False

    def delete_by_event(self, event_id: int) -> int:
        """Delete all stalls for an event."""
        try:
            response = self.db.table("stalls").delete().eq("event_id", event_id).execute()
            return len(response.data or [])
        except Exception as e:
            logger.error(f"Delete stalls for event {event_id} failed: {e}")
            return 0

    def create_menu_item(self, menu_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a menu item."""
        try:
            response = self.db.table("menu_items").insert(menu_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Create menu item failed: {e}")
            return None

    def update_menu_item(self, item_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a menu item."""
        try:
            response = self.db.table("menu_items").update(updates).eq("id", item_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Update menu item {item_id} failed: {e}")
            return None

    def delete_menu_item(self, item_id: int) -> bool:
        """Delete a menu item."""
        try:
            self.db.table("menu_items").delete().eq("id", item_id).execute()
            return True
        except Exception as e:
            logger.error(f"Delete menu item {item_id} failed: {e}")
            return False

    def delete_menu_items_by_stall(self, stall_id: int) -> int:
        """Delete all menu items for a stall."""
        try:
            response = self.db.table("menu_items").delete().eq("stall_id", stall_id).execute()
            return len(response.data or [])
        except Exception as e:
            logger.error(f"Delete menu items for stall {stall_id} failed: {e}")
            return 0

    def delete_menu_items_by_event(self, event_id: int) -> int:
        """Delete all menu items for an event."""
        try:
            # Get all stall IDs first
            stalls = self.get_by_event(event_id)
            stall_ids = [s["id"] for s in stalls]
            if stall_ids:
                response = self.db.table("menu_items").delete().in_("stall_id", stall_ids).execute()
                return len(response.data or [])
            return 0
        except Exception as e:
            logger.error(f"Delete menu items for event {event_id} failed: {e}")
            return 0