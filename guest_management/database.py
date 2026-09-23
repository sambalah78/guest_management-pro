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
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    func,
    insert,
    select,
    text,
    update,
    Identity,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

from guest_management.core.config import settings
from guest_management.core.exceptions import DatabaseError

metadata = MetaData()


def _pg_uuid():
    return PG_UUID(as_uuid=False).with_variant(String(128), "sqlite")


def _pg_bigint():
    # PostgreSQL BIGINT; SQLite INTEGER preserves autoincrement semantics.
    return BigInteger().with_variant(Integer(), "sqlite")


def _pg_numeric(precision=12, scale=2):
    # Preserve exact monetary precision in PostgreSQL while retaining the
    # existing SQLite test behaviour.
    return Numeric(precision, scale).with_variant(Numeric(precision, scale), "sqlite")


def _pg_jsonb():
    return JSONB().with_variant(JSON(), "sqlite")


# Shared metadata type for JSONB in PostgreSQL and JSON in SQLite tests.
JSON_TYPE = _pg_jsonb()


def _role_type():
    from sqlalchemy import Enum
    return Enum(
        "OWNER",
        "ADMIN",
        name="eventlah_user_role",
        native_enum=True,
    ).with_variant(String(50), "sqlite")


def _table(name: str, *columns, **kwargs):
    return Table(name, metadata, *columns, **kwargs)


users = _table(
    "users",
    Column("id", _pg_uuid(), primary_key=True),
    Column("email", Text, nullable=False, unique=True),
    Column("name", Text, nullable=False, server_default=text("''")),
    Column("picture_url", Text, nullable=False, server_default=text("''")),
    Column(
        "role",
        _role_type(),
        nullable=False,
        server_default=text("'ADMIN'"),
    ),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)


auth_sessions = _table(
    "auth_sessions",
    Column("id", _pg_bigint(), Identity(start=1, increment=1), primary_key=True),
    Column("session_id_hash", Text, nullable=False, unique=True),
    Column("user_id", _pg_uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("access_token_ciphertext", Text, nullable=False),
    Column("refresh_token_ciphertext", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("last_used_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("revoked_at", DateTime(timezone=True)),
)

events = _table(
    "events",
    Column("id", _pg_bigint(), Identity(start=1, increment=1), primary_key=True),
    Column("name", Text, nullable=False),
    Column("event_type", Text, nullable=False, server_default=text("'company_dinner'")),
    Column("company_name", Text, nullable=False, server_default=text("''")),
    Column("date", Text, nullable=False, server_default=text("''")),
    Column("time", Text, nullable=False, server_default=text("''")),
    Column("venue", Text, nullable=False, server_default=text("''")),
    Column("theme", Text, nullable=False, server_default=text("''")),
    Column("guest_count", Integer, nullable=False, server_default=text("0")),
    Column("present_count", Integer, nullable=False, server_default=text("0")),
    Column("user_id", _pg_uuid(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("logo", Text, nullable=False, server_default=text("''")),
    Column("wedding_invitation", Text, nullable=False, server_default=text("''")),
    Column("logo_storage_path", Text, nullable=False, server_default=text("''")),
    Column("logo_filename", Text, nullable=False, server_default=text("''")),
    Column("logo_mime_type", Text, nullable=False, server_default=text("''")),
    Column("invitation_storage_path", Text, nullable=False, server_default=text("''")),
    Column("invitation_filename", Text, nullable=False, server_default=text("''")),
    Column("invitation_mime_type", Text, nullable=False, server_default=text("''")),
    Column("guest_list_storage_path", Text, nullable=False, server_default=text("''")),
    Column("guest_list_filename", Text, nullable=False, server_default=text("''")),
    Column("guest_list_mime_type", Text, nullable=False, server_default=text("''")),
    Column("guest_list_uploaded_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    CheckConstraint("event_type IN ('company_dinner', 'wedding_dinner', 'sports_day')", name="events_event_type_check"),
    CheckConstraint("guest_count >= 0", name="events_guest_count_check"),
    CheckConstraint("present_count >= 0 AND present_count <= guest_count", name="events_present_count_check"),
)

guests = _table(
    "guests",
    Column("id", _pg_bigint(), Identity(start=1, increment=1), primary_key=True),
    Column("event_id", _pg_bigint(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
    Column("guest_id", Text, nullable=False),
    Column("name", Text, nullable=False, server_default=text("''")),
    Column("email", Text, nullable=False, server_default=text("''")),
    Column("phone", Text, nullable=False, server_default=text("''")),
    Column("status", Text, nullable=False, server_default=text("'Absent'")),
    Column("table_number", Text, nullable=False, server_default=text("'TBD'")),
    Column("amount", _pg_numeric(), nullable=False, server_default=text("0")),
    Column("team_name", Text),
    Column("qr_code", Text),
    Column("qr_url", Text),
    Column("email_sent", Boolean, nullable=False, server_default=text("false")),
    Column(
        "full_data",
        JSON_TYPE,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    ),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("event_id", "guest_id", name="guests_event_guest_unique"),
)

scanner_devices = _table(
    "scanner_devices",
    Column("id", _pg_bigint(), Identity(start=1, increment=1), primary_key=True),
    Column(
        "event_id",
        _pg_bigint(),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("device_id", Text, nullable=False),
    Column("device_name", Text, nullable=False, server_default=text("''")),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("total_scans", Integer, nullable=False, server_default=text("0")),
    Column("last_used", DateTime(timezone=True)),
    Column(
        "assigned_by",
        _pg_uuid(),
        ForeignKey("users.id", ondelete="SET NULL"),
    ),
    Column("assigned_at", DateTime(timezone=True)),
    Column("access_token_hash", Text),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    ),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    ),
    UniqueConstraint(
        "event_id",
        "device_id",
        name="scanner_event_device_unique",
    ),
    CheckConstraint(
        "total_scans >= 0",
        name="scanner_total_scans_check",
    ),
)

stalls = _table(
    "stalls",
    Column("id", _pg_bigint(), Identity(start=1, increment=1), primary_key=True),
    Column("event_id", _pg_bigint(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
    Column("stall_name", Text, nullable=False),
    Column("description", Text),
    Column("qr_code", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)

menu_items = _table(
    "menu_items",
    Column("id", _pg_bigint(), Identity(start=1, increment=1), primary_key=True),
    Column("stall_id", _pg_bigint(), ForeignKey("stalls.id", ondelete="CASCADE"), nullable=False),
    Column("item_name", Text, nullable=False),
    Column("description", Text),
    Column("price", _pg_numeric(), nullable=False, server_default=text("0")),
    Column("image_url", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)

transactions = _table(
    "transactions",
    Column("id", _pg_bigint(), Identity(start=1, increment=1), primary_key=True),
    Column("event_id", _pg_bigint(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
    Column("guest_id", Text, nullable=False),
    Column("stall_id", _pg_bigint(), ForeignKey("stalls.id", ondelete="SET NULL")),
    Column("menu_item_id", _pg_bigint(), ForeignKey("menu_items.id", ondelete="SET NULL")),
    Column("item_name", Text),
    Column("quantity", Integer, nullable=False, server_default=text("1")),
    Column("amount", _pg_numeric(), nullable=False, server_default=text("0")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    CheckConstraint("quantity > 0", name="transactions_quantity_check"),
)

checkins = _table(
    "checkins",
    Column("id", _pg_bigint(), Identity(start=1, increment=1), primary_key=True),
    Column("event_id", _pg_bigint(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
    Column("guest_id", Text, nullable=False),
    Column("scanner_id", Text),
    Column("result", Text, nullable=False),
    Column("checked_in_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)

checkin_history = _table(
    "checkin_history",
    Column("id", _pg_bigint(), Identity(start=1, increment=1), primary_key=True),
    Column("event_id", _pg_bigint(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
    Column("guest_id", Text, nullable=False),
    Column("scanner_id", Text, nullable=False),
    Column("result", Text, nullable=False),
    Column("checked_in_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)

email_jobs = _table(
    "email_jobs",
    Column("id", _pg_bigint(), Identity(start=1, increment=1), primary_key=True),
    Column("event_id", _pg_bigint(), ForeignKey("events.id", ondelete="CASCADE")),
    Column("guest_id", Text, nullable=False),
    Column("email_type", Text, nullable=False, server_default=text("'invitation'")),
    Column("recipient", Text, nullable=False),
    Column("subject", Text, nullable=False),
    Column("html_content", Text, nullable=False),
    Column("plain_text", Text, nullable=False, server_default=text("''")),
    Column("status", Text, nullable=False, server_default=text("'queued'")),
    Column("attempts", Integer, nullable=False, server_default=text("0")),
    Column("available_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("locked_at", DateTime(timezone=True)),
    Column("sent_at", DateTime(timezone=True)),
    Column("last_error", Text),
    Column("provider_message_id", Text),
    Column("provider_status", Text),
    Column("delivered_at", DateTime(timezone=True)),
    Column("bounced_at", DateTime(timezone=True)),
    Column("opened_at", DateTime(timezone=True)),
    Column("clicked_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("event_id", "guest_id", "email_type", name="email_jobs_event_guest_type_unique"),
    CheckConstraint("attempts >= 0", name="email_jobs_attempts_check"),
    CheckConstraint("status IN ('queued', 'processing', 'sent', 'failed', 'cancelled')",
                    name="email_jobs_status_check"),
)

winners = _table(
    "winners",
    Column("id", _pg_bigint(), Identity(start=1, increment=1), primary_key=True),
    Column("event_id", _pg_bigint(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
    Column("guest_id", Text, nullable=False),
    Column("name", Text),
    Column("prize", Text),
    Column("prize_name", Text),
    Column("prize_value", Text),
    Column("prize_image", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("event_id", "guest_id", name="winners_event_guest_unique"),
)

pre_draw_winners = _table(
    "pre_draw_winners",
    Column("id", _pg_bigint(), Identity(start=1, increment=1), primary_key=True),
    Column("event_id", _pg_bigint(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
    Column("guest_id", Text, nullable=False),
    Column("name", Text, nullable=False),
    Column("prize_name", Text, nullable=False, server_default=text("''")),
    Column("prize_value", Text, nullable=False, server_default=text("''")),
    Column("image_url", Text, nullable=False, server_default=text("''")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("event_id", "guest_id", name="pre_draw_winners_event_guest_unique"),
)

pre_draw_prizes = _table(
    "pre_draw_prizes",
    Column("id", _pg_bigint(), Identity(start=1, increment=1), primary_key=True),
    Column("event_id", _pg_bigint(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
    Column("name", Text, nullable=False),
    Column("value", Text, nullable=False, server_default=text("''")),
    Column("image_url", Text, nullable=False, server_default=text("''")),
    Column("winner_count", Integer, nullable=False, server_default=text("1")),
    Column("sort_order", Integer, nullable=False, server_default=text("0")),
    Column("status", Text, nullable=False, server_default=text("'draft'")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    CheckConstraint("winner_count > 0", name="pre_draw_prizes_winner_count_positive"),
    CheckConstraint("sort_order >= 0", name="pre_draw_prizes_sort_order_nonnegative"),
    CheckConstraint("status IN ('draft', 'ready', 'generated', 'archived')", name="pre_draw_prizes_status_check"),
)

event_assets = _table(
    "event_assets",
    Column("id", _pg_bigint(), Identity(start=1, increment=1), primary_key=True),
    Column("event_id", _pg_bigint(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
    Column("asset_type", Text, nullable=False),
    Column("storage_bucket", Text, nullable=False, server_default=text("'event-assets'")),
    Column("storage_path", Text, nullable=False),
    Column("filename", Text, nullable=False, server_default=text("''")),
    Column("mime_type", Text, nullable=False, server_default=text("''")),
    Column("size_bytes", BigInteger),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    CheckConstraint("asset_type IN ('logo', 'invitation', 'guest_list')", name="event_assets_type_check"),
    UniqueConstraint("event_id", "asset_type", name="event_assets_event_type_unique"),
)

# Match the live Supabase indexes exactly. Descending expressions are important
# for the intended newest-first queries.
Index("idx_users_active", users.c.is_active)
Index("idx_users_role", users.c.role)
Index("idx_auth_sessions_user", auth_sessions.c.user_id)
Index("idx_auth_sessions_expires", auth_sessions.c.expires_at)
Index(
    "idx_auth_sessions_active",
    auth_sessions.c.expires_at,
    postgresql_where=auth_sessions.c.revoked_at.is_(None),
)
Index("idx_events_date", events.c.date)
Index("idx_events_user_created", events.c.user_id, events.c.created_at.desc())
Index("idx_guests_event_status", guests.c.event_id, guests.c.status)
Index("idx_guests_event_updated", guests.c.event_id, guests.c.updated_at)
Index("idx_guests_event_name", guests.c.event_id, guests.c.name)
Index("idx_guests_email", guests.c.email)
Index("idx_scanners_event_active", scanner_devices.c.event_id, scanner_devices.c.is_active)
Index(
    "idx_scanner_devices_access_token_hash",
    scanner_devices.c.access_token_hash,
    unique=True,
    postgresql_where=scanner_devices.c.access_token_hash.is_not(None),
)
Index("idx_stalls_event", stalls.c.event_id)
Index("idx_menu_items_stall", menu_items.c.stall_id)
Index("idx_transactions_event", transactions.c.event_id)
Index("idx_transactions_event_guest_time", transactions.c.event_id, transactions.c.guest_id, transactions.c.created_at)
Index("idx_checkins_event_guest", checkins.c.event_id, checkins.c.guest_id)
Index("idx_checkins_event_time", checkins.c.event_id, checkins.c.checked_in_at)
Index("idx_checkin_history_event", checkin_history.c.event_id, checkin_history.c.created_at.desc())
Index("idx_email_jobs_claim", email_jobs.c.status, email_jobs.c.available_at, email_jobs.c.id)
Index("idx_email_jobs_event", email_jobs.c.event_id)
Index("idx_winners_event", winners.c.event_id)
Index("idx_pre_draw_winners_event", pre_draw_winners.c.event_id)
Index("idx_pre_draw_prizes_event_order", pre_draw_prizes.c.event_id, pre_draw_prizes.c.sort_order)
Index("idx_event_assets_event", event_assets.c.event_id)

TABLES = {t.name: t for t in metadata.sorted_tables}


def _default_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()

    if not url:
        raise RuntimeError(
            "DATABASE_URL is required. "
            "Production must use Supabase PostgreSQL."
        )

    return url


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

    def eq(self, column, value):
        self._filters.append(self.table.c[column] == value);
        return self

    def neq(self, column, value):
        self._filters.append(self.table.c[column] != value);
        return self

    def gt(self, column, value):
        self._filters.append(self.table.c[column] > value);
        return self

    def gte(self, column, value):
        self._filters.append(self.table.c[column] >= value);
        return self

    def lt(self, column, value):
        self._filters.append(self.table.c[column] < value);
        return self

    def lte(self, column, value):
        self._filters.append(self.table.c[column] <= value);
        return self

    def in_(self, column, values):
        self._filters.append(self.table.c[column].in_(list(values)));
        return self

    def ilike(self, column, value):
        self._filters.append(self.table.c[column].ilike(value));
        return self

    def is_(self, column, value):
        self._filters.append(self.table.c[column].is_(value));
        return self

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

    def order(self, column, desc=False):
        self._order.append((column, desc));
        return self

    def limit(self, value):
        self._limit = int(value);
        return self

    def range(self, start, end):
        self._offset, self._limit = int(start), int(end) - int(start) + 1;
        return self

    def insert(self, payload):
        self._operation, self._payload = "insert", payload;
        return self

    def update(self, payload):
        self._operation, self._payload = "update", payload;
        return self

    def delete(self):
        self._operation = "delete";
        return self

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
                            row = conn.execute(select(self.table).where(
                                self.table.c.id == result.inserted_primary_key[0])).mappings().first()
                            if row: rows.append(_row_dict(dict(row)))
                    return Result(rows)
                if self._operation == "update":
                    values = _clean_values(self._payload)
                    values.setdefault("updated_at",
                                      datetime.now(timezone.utc)) if "updated_at" in self.table.c else None
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
                            row = conn.execute(
                                select(self.table).where(self.table.c.id == existing["id"])).mappings().first()
                        else:
                            result = conn.execute(insert(self.table).values(**values))
                            row = conn.execute(select(self.table).where(self.table.c.id == result.inserted_primary_key[
                                0])).mappings().first() if "id" in self.table.c else None
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
    def __init__(self, db: Database, name: str, params: dict[str, Any]):
        self.db, self.name, self.params = db, name, params

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
            conn.execute(
                insert(checkins).values(event_id=event_id, guest_id=guest_id, scanner_id=scanner_id, result="not_found",
                                        checked_in_at=now, created_at=now))
            return Result(
                [{"result": "not_found", "message": "Guest not found", "event_id": event_id, "guest_id": guest_id,
                  "present_count": 0, "total_guests": 0, "checked_in_at": now.isoformat()}])
        if row.get("status") == "Present":
            conn.execute(insert(checkins).values(event_id=event_id, guest_id=guest_id, scanner_id=scanner_id,
                                                 result="already_checked_in", checked_in_at=now, created_at=now))
            stats = conn.execute(
                select(func.count()).select_from(guests).where(guests.c.event_id == event_id)).scalar_one()
            present = conn.execute(select(func.count()).select_from(guests).where(guests.c.event_id == event_id,
                                                                                  guests.c.status == "Present")).scalar_one()
            return Result([{"result": "already_checked_in", "message": "Guest already checked in", "event_id": event_id,
                            "guest_id": guest_id, "guest_name": row.get("name"),
                            "table_number": row.get("table_number"), "team_name": row.get("team_name") or "",
                            "present_count": present, "total_guests": stats,
                            "checked_in_at": _row_dict({"v": row.get("updated_at") or now})["v"]}])
        conn.execute(update(guests).where(guests.c.id == row["id"]).values(status="Present", updated_at=now))
        conn.execute(
            insert(checkins).values(event_id=event_id, guest_id=guest_id, scanner_id=scanner_id, result="checked_in",
                                    checked_in_at=now, created_at=now))
        # Increment the event counter atomically.
        #
        # Do NOT calculate present_count with COUNT() and then write the
        # result back. Under concurrent check-ins, multiple transactions
        # can observe the same count and overwrite each other's updates.
        conn.execute(
            update(events)
            .where(events.c.id == event_id)
            .values(
                present_count=events.c.present_count + 1,
                updated_at=now,
            )
        )

        # Read the counter after the atomic increment so the response
        # reflects the current committed event counter for this transaction.
        event_row = conn.execute(
            select(events.c.present_count, events.c.guest_count)
            .where(events.c.id == event_id)
        ).mappings().first()

        present = int(event_row["present_count"]) if event_row else 0
        total = int(event_row["guest_count"]) if event_row else 0

        return Result(
            [{"result": "checked_in", "message": "Check-in successful", "event_id": event_id, "guest_id": guest_id,
              "guest_name": row.get("name"), "table_number": row.get("table_number"),
              "team_name": row.get("team_name") or "", "present_count": present, "total_guests": total,
              "checked_in_at": now.isoformat()}])


def _db_event_stats(self: Database, p):
    event_id = int(p["p_event_id"])
    with self.engine.connect() as conn:
        total = conn.execute(select(func.count()).select_from(guests).where(guests.c.event_id == event_id)).scalar_one()
        present = conn.execute(select(func.count()).select_from(guests).where(guests.c.event_id == event_id,
                                                                              guests.c.status == "Present")).scalar_one()
    return Result([{"total_guests": total, "present_count": present, "absent_count": total - present}])


def _db_claim_email_jobs(self: Database, p):
    size = max(1, min(int(p.get("p_batch_size", 50)), 500));
    now = datetime.now(timezone.utc)
    with self.engine.begin() as conn:
        rows = conn.execute(
            select(email_jobs).where(email_jobs.c.status == "queued", email_jobs.c.available_at <= now).order_by(
                email_jobs.c.id).with_for_update(skip_locked=True).limit(size)).mappings().all()
        ids = [r["id"] for r in rows]
        if ids:
            conn.execute(update(email_jobs).where(email_jobs.c.id.in_(ids)).values(status="processing", locked_at=now,
                                                                                   attempts=email_jobs.c.attempts + 1,
                                                                                   updated_at=now))
            rows = conn.execute(select(email_jobs).where(email_jobs.c.id.in_(ids))).mappings().all()
    return Result([_row_dict(r) for r in rows])


def _db_requeue_stale_email_jobs(self: Database, p):
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max(1, int(p.get("p_age_minutes", 10))))
    with self.engine.begin() as conn:
        result = conn.execute(
            update(email_jobs).where(email_jobs.c.status == "processing", email_jobs.c.locked_at < cutoff).values(
                status="queued", locked_at=None, available_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)))
        return Result([{"count": result.rowcount or 0}])


def _db_increment_scanner_scans(self: Database, p):
    event_id = int(p["p_event_id"])
    device_id = str(p["p_device_id"]).strip()
    now = datetime.now(timezone.utc)

    with self.engine.begin() as conn:
        result = conn.execute(
            update(scanner_devices)
            .where(
                scanner_devices.c.event_id == event_id,
                scanner_devices.c.device_id == device_id,
                scanner_devices.c.is_active.is_(True),
            )
            .values(
                total_scans=scanner_devices.c.total_scans + 1,
                last_used=now,
                updated_at=now,
            )
        )

        if result.rowcount != 1:
            raise ValueError(
                "Scanner station is invalid or inactive."
            )

    return Result([])


Database.check_in_guest = _db_check_in_guest
Database.event_stats = _db_event_stats
Database.claim_email_jobs = _db_claim_email_jobs
Database.requeue_stale_email_jobs = _db_requeue_stale_email_jobs
Database.increment_scanner_scans = _db_increment_scanner_scans


def _db_process_voucher_purchase(self: Database, p):
    event_id = int(p["p_event_id"]);
    guest_id = str(p["p_guest_id"]).strip();
    stall_id = int(p["p_stall_id"]);
    items = p.get("p_items") or []
    if not items: return Result([{"result": "invalid", "message": "No items selected"}])
    now = datetime.now(timezone.utc)
    with self.engine.begin() as conn:
        guest = conn.execute(select(guests).where(guests.c.event_id == event_id,
                                                  guests.c.guest_id == guest_id).with_for_update()).mappings().first()
        if not guest: return Result([{"result": "not_found", "message": "Guest not found"}])
        if guest.get("status") != "Present": return Result(
            [{"result": "not_checked_in", "message": "Guest must be checked in first"}])
        ids = [int(i.get("id")) for i in items if i.get("id") is not None]
        if not ids: return Result([{"result": "invalid", "message": "Invalid items"}])
        stall = conn.execute(
            select(stalls).where(
                stalls.c.id == stall_id,
                stalls.c.event_id == event_id,
            )
        ).mappings().first()
        if not stall:
            return Result([{"result": "invalid", "message": "Invalid stall"}])

        menu_rows = conn.execute(
            select(menu_items).where(
                menu_items.c.stall_id == stall_id,
                menu_items.c.id.in_(ids),
            )
        ).mappings().all()
        by_id = {r["id"]: r for r in menu_rows}
        if len(by_id) != len(set(ids)): return Result(
            [{"result": "invalid", "message": "One or more menu items are invalid"}])
        total = 0.0
        for item in items:
            row = by_id.get(int(item["id"]))
            qty = max(1, int(item.get("quantity", 1)))
            total += float(row.get("price") or 0) * qty
        balance = float(guest.get("amount") or 0)
        if balance < total: return Result(
            [{"result": "insufficient_balance", "message": "Insufficient balance", "balance_after": balance,
              "total": total}])
        new_balance = balance - total
        conn.execute(update(guests).where(guests.c.id == guest["id"]).values(amount=new_balance, updated_at=now))
        for item in items:
            row = by_id[int(item["id"])]
            qty = max(1, int(item.get("quantity", 1)))
            conn.execute(insert(transactions).values(event_id=event_id, guest_id=guest_id, stall_id=stall_id,
                                                     menu_item_id=row["id"], item_name=row.get("item_name"),
                                                     quantity=qty, amount=float(row.get("price") or 0) * qty,
                                                     created_at=now))
        return Result(
            [{"result": "success", "message": "Purchase completed", "balance_after": new_balance, "total": total}])


Database.process_voucher_purchase = _db_process_voucher_purchase


def get_db() -> Database:
    return Database()
