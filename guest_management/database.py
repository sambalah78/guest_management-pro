"""Provider-independent SQL database layer.

PostgreSQL is the production database. SQLite is supported for local development.
The application uses PostgreSQL/SQLite directly.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, Integer, MetaData, String, Text, UniqueConstraint,
    create_engine, delete, func, insert, select, text, update, Column,Integer,String,Table,

)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

from guest_management.core.config import settings
from guest_management.core.exceptions import DatabaseError

metadata = MetaData()


def _table(name: str, *columns, **kwargs):
    from sqlalchemy import Table
    return Table(name, metadata, *columns, **kwargs)

users = _table(
    "users",
    __import__("sqlalchemy").Column("id", String(128), primary_key=True),
    __import__("sqlalchemy").Column("google_subject", String(255), unique=True, nullable=False),
    __import__("sqlalchemy").Column("email", String(320), unique=True, nullable=False),
    __import__("sqlalchemy").Column("name", String(255), nullable=False, default=""),
    __import__("sqlalchemy").Column("picture", Text, default=""),
    __import__("sqlalchemy").Column("google_refresh_token_enc", Text),
    __import__("sqlalchemy").Column("role", String(50), nullable=False, default="OWNER"),
    __import__("sqlalchemy").Column("is_active", Boolean, nullable=False, default=True),
    __import__("sqlalchemy").Column("created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    __import__("sqlalchemy").Column("updated_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
)

sessions = _table(
    "sessions",
    __import__("sqlalchemy").Column("id", String(128), primary_key=True),
    __import__("sqlalchemy").Column("user_id", String(128), nullable=False),
    __import__("sqlalchemy").Column("token_hash", String(128), unique=True, nullable=False),
    __import__("sqlalchemy").Column("expires_at", DateTime(timezone=True), nullable=False),
    __import__("sqlalchemy").Column("created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
)

events = _table(
    "events",
    Column("id", Integer, primary_key=True),
    Column("name", String(255), nullable=False),
    Column("event_type", String(64), nullable=False),
    Column("company_name", String(255)),
    Column("date", String(64)),
    Column("time", String(64)),
    Column("venue", String(500)),
    Column("theme", String(255)),

    Column("guest_count", Integer, nullable=False, default=0),
    Column("present_count", Integer, nullable=False, default=0),

    Column("user_id", String(128), nullable=False),

    # --------------------------------------------------------------
    # Legacy assets
    # --------------------------------------------------------------
    Column("logo", Text),
    Column("wedding_invitation", Text),

    # --------------------------------------------------------------
    # Google Drive logo
    # --------------------------------------------------------------
    Column("logo_drive_file_id", String(255), nullable=False, default=""),
    Column("logo_filename", String(255), nullable=False, default=""),
    Column("logo_mime_type", String(100), nullable=False, default=""),

    # --------------------------------------------------------------
    # Google Drive invitation
    # --------------------------------------------------------------
    Column(
        "invitation_drive_file_id",
        String(255),
        nullable=False,
        default="",
    ),
    Column(
        "invitation_filename",
        String(255),
        nullable=False,
        default="",
    ),
    Column(
        "invitation_mime_type",
        String(100),
        nullable=False,
        default="",
    ),

    # --------------------------------------------------------------
    # Google Drive guest list
    # --------------------------------------------------------------
    Column(
        "guest_list_drive_file_id",
        String(255),
        nullable=False,
        default="",
    ),
    Column(
        "guest_list_filename",
        String(255),
        nullable=False,
        default="",
    ),
    Column(
        "guest_list_mime_type",
        String(100),
        nullable=False,
        default="",
    ),
    Column(
        "guest_list_uploaded_at",
        DateTime,
        nullable=True,
    ),

    # --------------------------------------------------------------
    # Google Drive event folder
    # --------------------------------------------------------------
    Column(
        "event_drive_folder_id",
        String(255),
        nullable=False,
        default="",
    ),

    # --------------------------------------------------------------
    # Timestamps
    # --------------------------------------------------------------
    Column(
        "created_at",
        DateTime,
        nullable=False,
    ),
    Column(
        "updated_at",
        DateTime,
        nullable=False,
    ),
)

guests = _table(
    "guests",
    __import__("sqlalchemy").Column("id", Integer, primary_key=True, autoincrement=True),
    __import__("sqlalchemy").Column("event_id", Integer, nullable=False),
    __import__("sqlalchemy").Column("guest_id", String(255), nullable=False),
    __import__("sqlalchemy").Column("name", String(255), nullable=False),
    __import__("sqlalchemy").Column("email", String(320)),
    __import__("sqlalchemy").Column("phone", String(64)),
    __import__("sqlalchemy").Column("status", String(32), nullable=False, default="Absent"),
    __import__("sqlalchemy").Column("table_number", String(64), default="TBD"),
    __import__("sqlalchemy").Column("amount", Float, nullable=False, default=0),
    __import__("sqlalchemy").Column("team_name", String(255)),
    __import__("sqlalchemy").Column("qr_code", Text),
    __import__("sqlalchemy").Column("qr_url", Text),
    __import__("sqlalchemy").Column("email_sent", Boolean, nullable=False, default=False),
    __import__("sqlalchemy").Column("full_data", JSON, nullable=False, default=dict),
    __import__("sqlalchemy").Column("created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    __import__("sqlalchemy").Column("updated_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    UniqueConstraint("event_id", "guest_id", name="uq_guests_event_guest_id"),
    __import__("sqlalchemy").Index("idx_guests_event_status", "event_id", "status"),
    __import__("sqlalchemy").Index("idx_guests_event_updated", "event_id", "updated_at"),
    __import__("sqlalchemy").Index("idx_guests_event_name", "event_id", "name"),
)

scanner_devices = _table(
    "scanner_devices",
    __import__("sqlalchemy").Column("id", Integer, primary_key=True, autoincrement=True),
    __import__("sqlalchemy").Column("event_id", Integer, nullable=False),
    __import__("sqlalchemy").Column("device_id", String(255), nullable=False),
    __import__("sqlalchemy").Column("device_name", String(255)),
    __import__("sqlalchemy").Column("total_scans", Integer, nullable=False, default=0),
    __import__("sqlalchemy").Column("last_used", DateTime(timezone=True)),
    __import__("sqlalchemy").Column("created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    __import__("sqlalchemy").Column("updated_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    UniqueConstraint("event_id", "device_id", name="uq_scanner_devices_event_device"),
)

stalls = _table(
    "stalls",
    __import__("sqlalchemy").Column("id", Integer, primary_key=True, autoincrement=True),
    __import__("sqlalchemy").Column("event_id", Integer, nullable=False),
    __import__("sqlalchemy").Column("stall_name", String(255), nullable=False),
    __import__("sqlalchemy").Column("description", Text),
    __import__("sqlalchemy").Column("qr_code", Text),
    __import__("sqlalchemy").Column("created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    __import__("sqlalchemy").Column("updated_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
)

menu_items = _table(
    "menu_items",
    __import__("sqlalchemy").Column("id", Integer, primary_key=True, autoincrement=True),
    __import__("sqlalchemy").Column("stall_id", Integer, nullable=False),
    __import__("sqlalchemy").Column("item_name", String(255), nullable=False),
    __import__("sqlalchemy").Column("description", Text),
    __import__("sqlalchemy").Column("price", Float, nullable=False, default=0),
    __import__("sqlalchemy").Column("image_url", Text),
    __import__("sqlalchemy").Column("created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    __import__("sqlalchemy").Column("updated_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
)

transactions = _table(
    "transactions",
    __import__("sqlalchemy").Column("id", Integer, primary_key=True, autoincrement=True),
    __import__("sqlalchemy").Column("event_id", Integer, nullable=False),
    __import__("sqlalchemy").Column("guest_id", String(255), nullable=False),
    __import__("sqlalchemy").Column("stall_id", Integer),
    __import__("sqlalchemy").Column("menu_item_id", Integer),
    __import__("sqlalchemy").Column("item_name", String(255)),
    __import__("sqlalchemy").Column("quantity", Integer, nullable=False, default=1),
    __import__("sqlalchemy").Column("amount", Float, nullable=False, default=0),
    __import__("sqlalchemy").Column("created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
)

checkins = _table(
    "checkins",
    __import__("sqlalchemy").Column("id", Integer, primary_key=True, autoincrement=True),
    __import__("sqlalchemy").Column("event_id", Integer, nullable=False),
    __import__("sqlalchemy").Column("guest_id", String(255), nullable=False),
    __import__("sqlalchemy").Column("scanner_id", String(255)),
    __import__("sqlalchemy").Column("result", String(32), nullable=False),
    __import__("sqlalchemy").Column("checked_in_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    __import__("sqlalchemy").Column("created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
)

email_jobs = _table(
    "email_jobs",
    __import__("sqlalchemy").Column("id", Integer, primary_key=True, autoincrement=True),
    __import__("sqlalchemy").Column("event_id", Integer),
    __import__("sqlalchemy").Column("guest_id", String(255), nullable=False),
    __import__("sqlalchemy").Column("email_type", String(64), nullable=False, default="invitation"),
    __import__("sqlalchemy").Column("recipient", String(320), nullable=False),
    __import__("sqlalchemy").Column("subject", String(500), nullable=False),
    __import__("sqlalchemy").Column("html_content", Text, nullable=False),
    __import__("sqlalchemy").Column("plain_text", Text, nullable=False, default=""),
    __import__("sqlalchemy").Column("status", String(32), nullable=False, default="queued"),
    __import__("sqlalchemy").Column("attempts", Integer, nullable=False, default=0),
    __import__("sqlalchemy").Column("available_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    __import__("sqlalchemy").Column("locked_at", DateTime(timezone=True)),
    __import__("sqlalchemy").Column("sent_at", DateTime(timezone=True)),
    __import__("sqlalchemy").Column("last_error", Text),
    __import__("sqlalchemy").Column("provider_message_id", String(255)),
    __import__("sqlalchemy").Column("created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    __import__("sqlalchemy").Column("updated_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    UniqueConstraint("event_id", "guest_id", "email_type", name="uq_email_jobs_event_guest_type"),
)

winners = _table(
    "winners",
    __import__("sqlalchemy").Column("id", Integer, primary_key=True, autoincrement=True),
    __import__("sqlalchemy").Column("event_id", Integer, nullable=False),
    __import__("sqlalchemy").Column("guest_id", String(255)),
    __import__("sqlalchemy").Column("name", String(255)),
    __import__("sqlalchemy").Column("prize", String(255)),
    __import__("sqlalchemy").Column("prize_name", String(255)),
    __import__("sqlalchemy").Column("prize_value", String(255)),
    __import__("sqlalchemy").Column("prize_image", Text),
    __import__("sqlalchemy").Column("created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
)

from sqlalchemy import Index
Index("idx_events_user_created", events.c.user_id, events.c.created_at)
Index("idx_checkins_event_time", checkins.c.event_id, checkins.c.checked_in_at)
Index("idx_checkins_event_guest", checkins.c.event_id, checkins.c.guest_id)
Index("idx_transactions_event_guest_time", transactions.c.event_id, transactions.c.guest_id, transactions.c.created_at)
Index("idx_menu_items_stall", menu_items.c.stall_id)
Index("idx_email_jobs_queue", email_jobs.c.status, email_jobs.c.available_at, email_jobs.c.id)
Index("idx_winners_event_time", winners.c.event_id, winners.c.created_at)

TABLES = {t.name: t for t in metadata.sorted_tables}


def _default_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./guest_management.db")


def make_engine() -> Engine:
    url = _default_database_url()
    kwargs: dict[str, Any] = {"future": True, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
    return create_engine(url, **kwargs)


engine = make_engine()
_initialized = False

def init_db() -> None:
    global _initialized
    if _initialized:
        return
    metadata.create_all(engine)
    with engine.begin() as conn:
        # SQLite does not enforce foreign keys by default.
        if conn.dialect.name == "sqlite":
            conn.execute(text("PRAGMA foreign_keys=ON"))
    _initialized = True

def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class Result:
    def __init__(self, data=None, count=None):
        self.data = data or []
        self.count = count


class Query:
    """Small compatibility query builder used by repositories during the provider-independent database migration.

    It deliberately exposes only operations used by this application.
    """
    def __init__(self, db: "Database", table_name: str):
        self.db = db
        self.table = TABLES[table_name]
        self._filters = []
        self._order = []
        self._limit = None
        self._offset = None
        self._columns = None
        self._count = None
        self._head = False
        self._operation = "select"
        self._payload = None
        self._upsert_conflict = None
        self._ignore_duplicates = False

    def select(self, columns="*", count=None, head=False):
        self._operation, self._columns, self._count, self._head = "select", columns, count, head
        return self

    def eq(self, column, value): self._filters.append(self.table.c[column] == value); return self
    def neq(self, column, value): self._filters.append(self.table.c[column] != value); return self
    def gt(self, column, value): self._filters.append(self.table.c[column] > value); return self
    def gte(self, column, value): self._filters.append(self.table.c[column] >= value); return self
    def lt(self, column, value): self._filters.append(self.table.c[column] < value); return self
    def lte(self, column, value): self._filters.append(self.table.c[column] <= value); return self
    def in_(self, column, values): self._filters.append(self.table.c[column].in_(list(values))); return self
    def ilike(self, column, value): self._filters.append(self.table.c[column].ilike(value)); return self
    def is_(self, column, value):
        self._filters.append(self.table.c[column].is_(value)); return self
    def or_(self, expression):
        # Field filter syntax: field.ilike.*term*,field.ilike.*term*
        from sqlalchemy import or_
        clauses = []
        for item in expression.split(","):
            field, op, raw = item.partition(".")
            if op != "ilike" or field not in self.table.c:
                continue
            if raw.startswith("*") and raw.endswith("*"):
                raw = f"%{raw[1:-1]}%"
            clauses.append(self.table.c[field].ilike(raw))
        if clauses:
            self._filters.append(or_(*clauses))
        return self
    def order(self, column, desc=False): self._order.append((column, desc)); return self
    def limit(self, value): self._limit = int(value); return self
    def range(self, start, end): self._offset, self._limit = int(start), int(end) - int(start) + 1; return self
    def insert(self, payload): self._operation, self._payload = "insert", payload; return self
    def update(self, payload): self._operation, self._payload = "update", payload; return self
    def delete(self): self._operation = "delete"; return self
    def upsert(self, payload, on_conflict=None, ignore_duplicates=False):
        self._operation, self._payload = "upsert", payload
        self._upsert_conflict, self._ignore_duplicates = on_conflict, ignore_duplicates
        return self

    def execute(self) -> Result:
        try:
            with self.db.engine.begin() as conn:
                if self._operation == "select":
                    columns = self._select_columns()
                    stmt = select(*columns)
                    if self._filters: stmt = stmt.where(*self._filters)
                    for col, desc in self._order:
                        stmt = stmt.order_by(self.table.c[col].desc() if desc else self.table.c[col].asc())
                    count = None
                    if self._count == "exact":
                        count_stmt = select(func.count()).select_from(self.table)
                        if self._filters: count_stmt = count_stmt.where(*self._filters)
                        count = int(conn.execute(count_stmt).scalar_one())
                    if self._head:
                        return Result([], count)
                    if self._limit is not None: stmt = stmt.limit(self._limit)
                    if self._offset is not None: stmt = stmt.offset(self._offset)
                    rows = [_row_dict(dict(r._mapping)) for r in conn.execute(stmt).fetchall()]
                    return Result(rows, count)
                if self._operation == "insert":
                    payload = self._payload if isinstance(self._payload, list) else [self._payload]
                    rows = []
                    for item in payload:
                        values = _clean_values(item)
                        result = conn.execute(insert(self.table).values(**values))
                        if result.inserted_primary_key and "id" in self.table.c:
                            row = conn.execute(select(self.table).where(self.table.c.id == result.inserted_primary_key[0])).mappings().first()
                            if row: rows.append(_row_dict(dict(row)))
                    return Result(rows)
                if self._operation == "update":
                    values = _clean_values(self._payload)
                    values.setdefault("updated_at", datetime.now(timezone.utc)) if "updated_at" in self.table.c else None
                    stmt = update(self.table).values(**values)
                    if self._filters: stmt = stmt.where(*self._filters)
                    conn.execute(stmt)
                    stmt2 = select(self.table)
                    if self._filters: stmt2 = stmt2.where(*self._filters)
                    return Result([_row_dict(dict(r._mapping)) for r in conn.execute(stmt2).fetchall()])
                if self._operation == "delete":
                    stmt = delete(self.table)
                    if self._filters: stmt = stmt.where(*self._filters)
                    conn.execute(stmt)
                    return Result([])
                if self._operation == "upsert":
                    payload = self._payload if isinstance(self._payload, list) else [self._payload]
                    rows = []
                    conflict_cols = [x.strip() for x in (self._upsert_conflict or "").split(",") if x.strip()]
                    for item in payload:
                        values = _clean_values(item)
                        existing = None
                        if conflict_cols:
                            cond = [self.table.c[c] == values.get(c) for c in conflict_cols]
                            existing = conn.execute(select(self.table).where(*cond).limit(1)).mappings().first()
                        if existing:
                            if self._ignore_duplicates:
                                continue
                            conn.execute(update(self.table).where(self.table.c.id == existing["id"]).values(**values))
                            row = conn.execute(select(self.table).where(self.table.c.id == existing["id"])).mappings().first()
                        else:
                            result = conn.execute(insert(self.table).values(**values))
                            row = conn.execute(select(self.table).where(self.table.c.id == result.inserted_primary_key[0])).mappings().first() if "id" in self.table.c else None
                        if row: rows.append(_row_dict(dict(row)))
                    return Result(rows)
        except IntegrityError as exc:
            raise DatabaseError("Database constraint violation") from exc
        except Exception as exc:
            raise DatabaseError("Database query failed") from exc

    def _select_columns(self):
        if self._columns in (None, "*"): return list(self.table.c)
        names = [x.strip() for x in str(self._columns).split(",")]
        return [self.table.c[n] for n in names if n in self.table.c]


class Database:
    def __init__(self, db_engine: Engine = engine): self.engine = db_engine
    def table(self, name: str) -> Query: return Query(self, name)
    def rpc(self, name: str, params: dict[str, Any]) -> Query:
        return RPCQuery(self, name, params)


class RPCQuery:
    def __init__(self, db: Database, name: str, params: dict[str, Any]): self.db, self.name, self.params = db, name, params
    def execute(self) -> Result:
        if self.name == "check_in_guest": return self.db.check_in_guest(self.params)
        if self.name == "get_event_stats": return self.db.event_stats(self.params)
        if self.name == "claim_email_jobs": return self.db.claim_email_jobs(self.params)
        if self.name == "requeue_stale_email_jobs": return self.db.requeue_stale_email_jobs(self.params)
        if self.name == "process_voucher_purchase": return self.db.process_voucher_purchase(self.params)
        if self.name == "increment_scanner_scans": return self.db.increment_scanner_scans(self.params)
        raise DatabaseError(f"Unsupported database operation: {self.name}")


def _clean_values(values: dict[str, Any]) -> dict[str, Any]:
    out = dict(values)
    for key, value in list(out.items()):
        if key not in TABLES.get("guests", guests).c and False:
            pass
        if isinstance(value, datetime): continue
        if isinstance(value, dict) and key == "full_data": continue
        if isinstance(value, (list, tuple)) and key not in {"full_data"}: out[key] = json.dumps(value)
    return out


def _row_dict(row) -> dict[str, Any]:
    result = dict(row)
    for key, value in list(result.items()):
        if isinstance(value, datetime): result[key] = value.isoformat()
    return result


def _init_method(self):
    return None


def _db_check_in_guest(self: Database, p):
    event_id, guest_id, scanner_id = int(p["p_event_id"]), str(p["p_guest_id"]).strip(), p.get("p_scanner_id")
    now = datetime.now(timezone.utc)
    with self.engine.begin() as conn:
        stmt = select(guests).where(guests.c.event_id == event_id, guests.c.guest_id == guest_id).with_for_update()
        row = conn.execute(stmt).mappings().first()
        if not row:
            conn.execute(insert(checkins).values(event_id=event_id, guest_id=guest_id, scanner_id=scanner_id, result="not_found", checked_in_at=now, created_at=now))
            return Result([{"result":"not_found","message":"Guest not found","event_id":event_id,"guest_id":guest_id,"present_count":0,"total_guests":0,"checked_in_at":now.isoformat()}])
        if row.get("status") == "Present":
            conn.execute(insert(checkins).values(event_id=event_id, guest_id=guest_id, scanner_id=scanner_id, result="already_checked_in", checked_in_at=now, created_at=now))
            stats = conn.execute(select(func.count()).select_from(guests).where(guests.c.event_id == event_id)).scalar_one()
            present = conn.execute(select(func.count()).select_from(guests).where(guests.c.event_id == event_id, guests.c.status == "Present")).scalar_one()
            return Result([{"result":"already_checked_in","message":"Guest already checked in","event_id":event_id,"guest_id":guest_id,"guest_name":row.get("name"),"table_number":row.get("table_number"),"team_name":row.get("team_name") or "","present_count":present,"total_guests":stats,"checked_in_at": _row_dict({"v": row.get("updated_at") or now})["v"]}])
        conn.execute(update(guests).where(guests.c.id == row["id"]).values(status="Present", updated_at=now))
        conn.execute(insert(checkins).values(event_id=event_id, guest_id=guest_id, scanner_id=scanner_id, result="checked_in", checked_in_at=now, created_at=now))
        present = conn.execute(select(func.count()).select_from(guests).where(guests.c.event_id == event_id, guests.c.status == "Present")).scalar_one()
        total = conn.execute(select(func.count()).select_from(guests).where(guests.c.event_id == event_id)).scalar_one()
        conn.execute(update(events).where(events.c.id == event_id).values(present_count=present, guest_count=total, updated_at=now))
        return Result([{"result":"checked_in","message":"Check-in successful","event_id":event_id,"guest_id":guest_id,"guest_name":row.get("name"),"table_number":row.get("table_number"),"team_name":row.get("team_name") or "","present_count":present,"total_guests":total,"checked_in_at": now.isoformat()}])


def _db_event_stats(self: Database, p):
    event_id = int(p["p_event_id"])
    with self.engine.connect() as conn:
        total = conn.execute(select(func.count()).select_from(guests).where(guests.c.event_id == event_id)).scalar_one()
        present = conn.execute(select(func.count()).select_from(guests).where(guests.c.event_id == event_id, guests.c.status == "Present")).scalar_one()
    return Result([{"total_guests": total, "present_count": present, "absent_count": total-present}])


def _db_claim_email_jobs(self: Database, p):
    size = max(1, min(int(p.get("p_batch_size", 50)), 500)); now = datetime.now(timezone.utc)
    with self.engine.begin() as conn:
        rows = conn.execute(select(email_jobs).where(email_jobs.c.status == "queued", email_jobs.c.available_at <= now).order_by(email_jobs.c.id).with_for_update(skip_locked=True).limit(size)).mappings().all()
        ids = [r["id"] for r in rows]
        if ids:
            conn.execute(update(email_jobs).where(email_jobs.c.id.in_(ids)).values(status="processing", locked_at=now, attempts=email_jobs.c.attempts + 1, updated_at=now))
            rows = conn.execute(select(email_jobs).where(email_jobs.c.id.in_(ids))).mappings().all()
    return Result([_row_dict(r) for r in rows])


def _db_requeue_stale_email_jobs(self: Database, p):
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max(1, int(p.get("p_age_minutes", 10))))
    with self.engine.begin() as conn:
        result = conn.execute(update(email_jobs).where(email_jobs.c.status == "processing", email_jobs.c.locked_at < cutoff).values(status="queued", locked_at=None, available_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)))
        return Result([{"count": result.rowcount or 0}])


def _db_increment_scanner_scans(self: Database, p):
    with self.engine.begin() as conn:
        conn.execute(update(scanner_devices).where(scanner_devices.c.device_id == p.get("p_device_id")).values(total_scans=scanner_devices.c.total_scans + 1, last_used=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)))
    return Result([])


Database.check_in_guest = _db_check_in_guest
Database.event_stats = _db_event_stats
Database.claim_email_jobs = _db_claim_email_jobs
Database.requeue_stale_email_jobs = _db_requeue_stale_email_jobs
Database.increment_scanner_scans = _db_increment_scanner_scans


def _db_process_voucher_purchase(self: Database, p):
    event_id = int(p["p_event_id"]); guest_id = str(p["p_guest_id"]).strip(); stall_id = int(p["p_stall_id"]); items = p.get("p_items") or []
    if not items: return Result([{"result":"invalid","message":"No items selected"}])
    now = datetime.now(timezone.utc)
    with self.engine.begin() as conn:
        guest = conn.execute(select(guests).where(guests.c.event_id == event_id, guests.c.guest_id == guest_id).with_for_update()).mappings().first()
        if not guest: return Result([{"result":"not_found","message":"Guest not found"}])
        if guest.get("status") != "Present": return Result([{"result":"not_checked_in","message":"Guest must be checked in first"}])
        ids = [int(i.get("id")) for i in items if i.get("id") is not None]
        if not ids: return Result([{"result":"invalid","message":"Invalid items"}])
        menu_rows = conn.execute(select(menu_items).where(menu_items.c.stall_id == stall_id, menu_items.c.id.in_(ids))).mappings().all()
        by_id = {r["id"]: r for r in menu_rows}
        if len(by_id) != len(set(ids)): return Result([{"result":"invalid","message":"One or more menu items are invalid"}])
        total = 0.0
        for item in items:
            row = by_id.get(int(item["id"]))
            qty = max(1, int(item.get("quantity", 1)))
            total += float(row.get("price") or 0) * qty
        balance = float(guest.get("amount") or 0)
        if balance < total: return Result([{"result":"insufficient_balance","message":"Insufficient balance","balance_after":balance,"total":total}])
        new_balance = balance - total
        conn.execute(update(guests).where(guests.c.id == guest["id"]).values(amount=new_balance, updated_at=now))
        for item in items:
            row = by_id[int(item["id"])]
            qty = max(1, int(item.get("quantity", 1)))
            conn.execute(insert(transactions).values(event_id=event_id, guest_id=guest_id, stall_id=stall_id, menu_item_id=row["id"], item_name=row.get("item_name"), quantity=qty, amount=float(row.get("price") or 0) * qty, created_at=now))
        return Result([{"result":"success","message":"Purchase completed","balance_after":new_balance,"total":total}])

Database.process_voucher_purchase = _db_process_voucher_purchase


def get_db() -> Database:
    init_db()
    return Database()
