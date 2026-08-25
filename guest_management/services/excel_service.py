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

    def parse_prize_file(self, content: bytes) -> List[Dict[str, Any]]:
        """Parse prize Excel file."""
        try:
            df = pd.read_excel(io.BytesIO(content))
        except Exception:
            raise ValueError("Could not read Excel file")

        df.columns = df.columns.str.strip()
        df.fillna("", inplace=True)

        # Detect columns
        name_col = None
        value_col = None
        image_col = None

        for col in df.columns:
            col_lower = col.lower().strip()
            if any(k in col_lower for k in ["name", "prize", "title"]):
                name_col = col
            elif any(k in col_lower for k in ["value", "price", "amount"]):
                value_col = col
            elif any(k in col_lower for k in ["image", "url", "picture", "photo"]):
                image_col = col

        if not name_col:
            name_col = df.columns[0]

        prizes = []
        for _, row in df.iterrows():
            prize_name = str(row[name_col]) if pd.notna(row[name_col]) else None
            if not prize_name or prize_name in ["nan", "None", ""]:
                continue

            prize = {
                "name": prize_name,
                "value": str(row[value_col]) if value_col and pd.notna(row[value_col]) else "",
                "image_url": str(row[image_col]) if image_col and pd.notna(row[image_col]) else "",
            }
            prizes.append(prize)

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