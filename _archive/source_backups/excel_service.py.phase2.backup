# guest_management/services/excel_service.py
"""Excel processing service."""

import io
import logging
from typing import Dict, Any, List, Tuple, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ExcelService:
    """Service for Excel file processing."""

    REQUIRED_COLUMNS = ["Name", "Email", "ID", "Table"]

    def parse_guest_file(self, content: bytes) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
        """Parse guest Excel/CSV file and return data with column info."""
        try:
            df = pd.read_excel(io.BytesIO(content))
        except Exception:
            try:
                df = pd.read_csv(io.BytesIO(content))
            except Exception:
                raise ValueError("Could not read file. Please upload Excel or CSV format.")

        df.columns = df.columns.str.strip()
        df.fillna("", inplace=True)

        # Detect columns
        column_map = self._detect_columns(df.columns)

        # Convert to dict list
        data = df.to_dict(orient="records")

        return data, list(df.columns), column_map

    def _detect_columns(self, columns: List[str]) -> Dict[str, str]:
        """Detect column mappings from Excel/CSV."""
        mapping = {}

        for col in columns:
            col_lower = col.lower().strip()

            if col_lower in ["name", "full name", "guest name", "fullname"]:
                mapping["name"] = col
            elif col_lower in ["email", "e-mail", "mail", "email address"]:
                mapping["email"] = col
            elif col_lower in ["id", "guest id", "guest_id", "employee id", "member id", "user id", "userid"]:
                mapping["guest_id"] = col
            elif col_lower in ["table", "table no", "table_no", "table_number", "table number"]:
                mapping["table"] = col
            elif col_lower in ["amount", "voucher", "balance", "credit"]:
                mapping["amount"] = col
            elif col_lower in ["team", "team name", "team_name", "group", "squad"]:
                mapping["team"] = col
            elif col_lower in ["diet", "dietary", "dietary restrictions", "food preference", "restrictions"]:
                mapping["dietary"] = col
            elif col_lower in ["status", "check-in status", "checkin status"]:
                mapping["status"] = col

        return mapping

    def parse_stall_file(self, content: bytes) -> List[Dict[str, Any]]:
        """Parse stall Excel file."""
        try:
            df = pd.read_excel(io.BytesIO(content))
        except Exception:
            raise ValueError("Could not read Excel file")

        df.columns = df.columns.str.strip()
        df.fillna("", inplace=True)

        # Detect columns
        stall_col = None
        item_col = None
        price_col = None

        for col in df.columns:
            col_lower = col.lower().strip()
            if any(k in col_lower for k in ["stall", "vendor", "booth"]):
                stall_col = col
            elif any(k in col_lower for k in ["item", "menu", "product"]):
                item_col = col
            elif any(k in col_lower for k in ["price", "cost", "amount", "rm"]):
                price_col = col

        if not stall_col or not item_col or not price_col:
            raise ValueError("Missing required columns: Stall, Item, Price")

        data = df.to_dict(orient="records")
        return data, stall_col, item_col, price_col

    @staticmethod
    def _parse_prize_value(value: Any) -> float | None:
        """Return a numeric prize value for ranking, when possible."""
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)) and not pd.isna(value):
            return float(value)

        raw = str(value).strip()
        if not raw or raw.lower() in {"nan", "none", "n/a", "na", "-"}:
            return None

        # Supports common client formats: RM 5,000 / $5,000.00 / 5000
        cleaned = (
            raw.replace(",", "")
            .replace("RM", "")
            .replace("rm", "")
            .replace("$", "")
            .strip()
        )
        try:
            return float(cleaned)
        except ValueError:
            return None

    def parse_prize_file(self, content: bytes) -> List[Dict[str, Any]]:
        """Parse a prize Excel file and normalize ranking metadata.

        Supported columns:
          - Rank / Sequence / Order (optional, authoritative when supplied)
          - Prize / Prize Name / Name / Title (required)
          - Value / Price / Amount / Worth (optional)
          - Image / Image URL / Photo / URL (optional)

        Ranking policy:
          1. Explicit client Rank is authoritative.
          2. If Rank is absent/blank, prizes are auto-ranked by numeric value
             descending, so the most expensive prize becomes Rank 1.
          3. Ties retain the client's original Excel order.
        """
        try:
            df = pd.read_excel(io.BytesIO(content))
        except Exception:
            raise ValueError("Could not read Excel file")

        df.columns = df.columns.astype(str).str.strip()
        df.fillna("", inplace=True)

        name_col = value_col = image_col = rank_col = None
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if name_col is None and any(k in col_lower for k in [
                "prize name", "prize", "name", "title", "item"
            ]):
                name_col = col
            elif value_col is None and any(k in col_lower for k in [
                "value", "price", "amount", "worth", "rm"
            ]):
                value_col = col
            elif image_col is None and any(k in col_lower for k in [
                "image url", "image", "url", "picture", "photo", "img", "link"
            ]):
                image_col = col
            elif rank_col is None and any(k in col_lower for k in [
                "rank", "ranking", "sequence", "seq", "order", "priority", "position"
            ]):
                rank_col = col

        if not name_col:
            name_col = df.columns[0] if len(df.columns) else None
        if not name_col:
            raise ValueError("Prize Excel file has no usable prize-name column")

        prizes: List[Dict[str, Any]] = []
        for original_index, row in df.iterrows():
            prize_name = str(row[name_col]).strip()
            if not prize_name or prize_name.lower() in {"nan", "none"}:
                continue

            raw_value = row[value_col] if value_col else ""
            value_text = "" if raw_value in (None, "") else str(raw_value).strip()
            numeric_value = self._parse_prize_value(raw_value)

            raw_rank = row[rank_col] if rank_col else ""
            explicit_rank = None
            try:
                if str(raw_rank).strip():
                    explicit_rank = int(float(str(raw_rank).strip()))
                    if explicit_rank <= 0:
                        explicit_rank = None
            except (TypeError, ValueError):
                explicit_rank = None

            image_url = ""
            if image_col:
                image_url = str(row[image_col]).strip()
                if image_url.lower() in {"nan", "none"}:
                    image_url = ""

            prizes.append({
                "name": prize_name,
                "value": value_text,
                "image_url": image_url,
                "rank": explicit_rank,
                "numeric_value": numeric_value,
                "source_order": int(original_index),
            })

        if not prizes:
            return []

        has_explicit_rank = any(p["rank"] is not None for p in prizes)

        if has_explicit_rank:
            # Explicit rank wins. Unranked rows go after ranked rows, preserving
            # source order. This lets clients deliberately control grand prize
            # ordering without relying on currency parsing.
            prizes.sort(key=lambda p: (
                p["rank"] is None,
                p["rank"] if p["rank"] is not None else 10**9,
                p["source_order"],
            ))
        else:
            # No rank supplied: automatically make the highest-value prize Rank 1.
            # Unknown-value prizes remain after known-value prizes in Excel order.
            prizes.sort(key=lambda p: (
                p["numeric_value"] is None,
                -(p["numeric_value"] or 0),
                p["source_order"],
            ))

        # Normalize final rank to a contiguous 1..N sequence. The original
        # client rank is preserved as source_rank for audit/debugging.
        for position, prize in enumerate(prizes, start=1):
            prize["source_rank"] = prize["rank"]
            prize["rank"] = position
            prize["is_grand_prize"] = position == 1
            prize.pop("numeric_value", None)
            prize.pop("source_order", None)

        return prizes

    def export_guests_to_excel(self, guests: List[Dict[str, Any]], filename: str) -> bytes:
        """Export guests to Excel file."""
        df = pd.DataFrame(guests)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Guests', index=False)

            # Auto-adjust column widths
            worksheet = writer.sheets['Guests']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        output.seek(0)
        return output.read()

    def export_winners_to_excel(self, winners: List[Dict[str, Any]]) -> bytes:
        """Export winners to Excel file."""
        df = pd.DataFrame(winners)

        # Select and rename columns
        columns = ["name", "guest_id", "prize_name", "prize_value", "created_at"]
        available = [c for c in columns if c in df.columns]
        df = df[available]

        rename = {
            "name": "Winner Name",
            "guest_id": "Guest ID",
            "prize_name": "Prize",
            "prize_value": "Prize Value",
            "created_at": "Date & Time",
        }
        df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Winners', index=False)

        output.seek(0)
        return output.read()