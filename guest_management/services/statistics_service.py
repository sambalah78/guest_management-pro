# guest_management/services/statistics_service.py
"""Statistics service."""

import logging
from typing import Dict, Any, List

from guest_management.repositories import GuestRepository, TransactionRepository

logger = logging.getLogger(__name__)


class StatisticsService:
    """Service for statistics calculations."""

    def __init__(self):
        self.guest_repo = GuestRepository()
        self.transaction_repo = TransactionRepository()

    def get_event_stats(self, event_id: int) -> Dict[str, Any]:
        """Get comprehensive statistics for an event."""
        response = self.guest_repo.db.rpc("get_event_stats", {"p_event_id": int(event_id)}).execute()
        row = (response.data or [{}])[0]
        total_guests = int(row.get("total_guests", 0))
        present = int(row.get("present_count", 0))
        absent = int(row.get("absent_count", total_guests - present))
        return {
            "total_guests": total_guests,
            "present_count": present,
            "absent_count": absent,
            "present_percentage": round(present / total_guests * 100, 1) if total_guests else 0,
            "absent_percentage": round(absent / total_guests * 100, 1) if total_guests else 0,
        }

    def get_guest_statistics(self, guests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics from guest list."""
        total = len(guests)
        present = sum(1 for g in guests if g.get("status") in ["Present", "present"])
        absent = total - present

        return {
            "total": total,
            "present": present,
            "absent": absent,
            "present_percentage": round((present / total * 100) if total > 0 else 0),
            "absent_percentage": round((absent / total * 100) if total > 0 else 0),
        }

    def get_email_statistics(self, guests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate email statistics from guest list."""
        total = len(guests)
        sent = sum(1 for g in guests if g.get("email_sent", False))

        return {
            "total": total,
            "sent": sent,
            "unsent": total - sent,
            "sent_percentage": round((sent / total * 100) if total > 0 else 0),
        }

    def get_voucher_statistics(self, guests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate voucher statistics from guest list."""
        total = len(guests)
        has_voucher = sum(1 for g in guests if g.get("amount", 0) > 0)
        total_amount = sum(g.get("amount", 0) for g in guests)

        return {
            "total_guests": total,
            "guests_with_vouchers": has_voucher,
            "total_voucher_amount": total_amount,
            "average_voucher": round(total_amount / has_voucher, 2) if has_voucher > 0 else 0,
        }