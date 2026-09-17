"""
Durable email job repository.

SQLAlchemy / SQLite implementation.

Responsibilities:
    - Create durable email jobs
    - Prevent duplicate invitation jobs
    - Claim queued jobs for the worker
    - Mark jobs sent
    - Mark jobs failed
    - Retry failed/cancelled jobs
    - Explicitly resend sent jobs
    - Provide dashboard delivery statistics

Safety rules:
    - All operations are event-scoped where applicable.
    - SENT jobs are never automatically retried.
    - RETRY is allowed only for FAILED/CANCELLED jobs.
    - RESEND is explicitly allowed only for SENT jobs.
    - All DateTime columns receive real Python datetime objects.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from guest_management.database import engine
from guest_management.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class EmailJobRepository:
    """Repository for durable email delivery jobs."""

    STATUSES = (
        "queued",
        "processing",
        "sent",
        "failed",
        "cancelled",
    )

    # ==================================================================
    # DATETIME HELPERS
    # ==================================================================

    @staticmethod
    def _now() -> datetime:
        """
        Return a real Python datetime object.

        IMPORTANT:
        Do NOT use .isoformat() here.

        SQLAlchemy SQLite DateTime columns require datetime/date
        objects rather than ISO strings.
        """
        return datetime.now(timezone.utc)

    @staticmethod
    def _normalize_datetime(value: Any) -> Optional[datetime]:
        """
        Normalize a value to a Python datetime.

        This is mainly useful when a caller passes a datetime-like
        value into repository methods.
        """

        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            value = value.strip()

            if not value:
                return None

            try:
                parsed = datetime.fromisoformat(
                    value.replace("Z", "+00:00")
                )

                if parsed.tzinfo is None:
                    parsed = parsed.replace(
                        tzinfo=timezone.utc
                    )

                return parsed

            except ValueError:
                logger.warning(
                    "Unable to parse datetime value: %r",
                    value,
                )
                return None

        return None

    # ==================================================================
    # RESULT HELPERS
    # ==================================================================

    @staticmethod
    def _row_to_dict(row: Any) -> Dict[str, Any]:
        """Convert a SQLAlchemy Row into a normal dictionary."""

        if row is None:
            return {}

        try:
            return dict(row._mapping)
        except AttributeError:
            return dict(row)

    @classmethod
    def _rows_to_dicts(
        cls,
        rows: Any,
    ) -> List[Dict[str, Any]]:
        return [
            cls._row_to_dict(row)
            for row in rows
        ]

    @staticmethod
    def _raise_db(
        operation: str,
        exc: Exception,
    ) -> None:
        logger.exception(
            "Email repository database error: %s",
            operation,
        )

        raise DatabaseError(
            f"Email repository operation failed: {operation}"
        ) from exc

    # ==================================================================
    # ENQUEUE SINGLE JOB
    # ==================================================================

    def enqueue(
        self,
        job: Dict[str, Any],
        force: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Create an email job.

        Normal mode:
            Idempotent.
            Existing event/guest/email_type job is returned.

        force=True:
            Explicitly reset an existing job and queue it again.

        This is used for RESEND.
        """

        try:
            event_id = int(job["event_id"])
            guest_id = str(job["guest_id"])
            email_type = str(
                job.get("email_type")
                or "invitation"
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "event_id and guest_id are required"
            ) from exc

        now = self._now()

        # --------------------------------------------------------------
        # Check for existing job
        # --------------------------------------------------------------

        find_stmt = text(
            """
            SELECT *
            FROM email_jobs
            WHERE event_id = :event_id
              AND guest_id = :guest_id
              AND email_type = :email_type
            LIMIT 1
            """
        )

        try:
            with engine.begin() as conn:

                existing = conn.execute(
                    find_stmt,
                    {
                        "event_id": event_id,
                        "guest_id": guest_id,
                        "email_type": email_type,
                    },
                ).mappings().first()

                # ------------------------------------------------------
                # FORCE / RESEND EXISTING JOB
                # ------------------------------------------------------

                if existing is not None:

                    if not force:
                        return dict(existing)

                    update_stmt = text(
                        """
                        UPDATE email_jobs
                        SET
                            event_id = :event_id,
                            guest_id = :guest_id,
                            email_type = :email_type,
                            recipient = :recipient,
                            subject = :subject,
                            html_content = :html_content,
                            plain_text = :plain_text,
                            status = 'queued',
                            attempts = 0,
                            available_at = :available_at,
                            locked_at = NULL,
                            sent_at = NULL,
                            last_error = NULL,
                            provider_message_id = NULL,
                            updated_at = :updated_at
                        WHERE id = :id
                          AND event_id = :event_id
                        """
                    )

                    conn.execute(
                        update_stmt,
                        {
                            "id": int(existing["id"]),
                            "event_id": event_id,
                            "guest_id": guest_id,
                            "email_type": email_type,
                            "recipient": str(
                                job.get("recipient")
                                or ""
                            ),
                            "subject": str(
                                job.get("subject")
                                or ""
                            ),
                            "html_content": str(
                                job.get("html_content")
                                or ""
                            ),
                            "plain_text": str(
                                job.get("plain_text")
                                or ""
                            ),
                            "available_at": now,
                            "updated_at": now,
                        },
                    )

                    refreshed = conn.execute(
                        text(
                            """
                            SELECT *
                            FROM email_jobs
                            WHERE id = :id
                              AND event_id = :event_id
                            LIMIT 1
                            """
                        ),
                        {
                            "id": int(existing["id"]),
                            "event_id": event_id,
                        },
                    ).mappings().first()

                    return (
                        dict(refreshed)
                        if refreshed
                        else None
                    )

                # ------------------------------------------------------
                # NEW JOB
                # ------------------------------------------------------

                insert_stmt = text(
                    """
                    INSERT INTO email_jobs (
                        event_id,
                        guest_id,
                        email_type,
                        recipient,
                        subject,
                        html_content,
                        plain_text,
                        status,
                        attempts,
                        available_at,
                        locked_at,
                        sent_at,
                        last_error,
                        provider_message_id,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        :event_id,
                        :guest_id,
                        :email_type,
                        :recipient,
                        :subject,
                        :html_content,
                        :plain_text,
                        'queued',
                        0,
                        :available_at,
                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        :created_at,
                        :updated_at
                    )
                    """
                )

                try:
                    result = conn.execute(
                        insert_stmt,
                        {
                            "event_id": event_id,
                            "guest_id": guest_id,
                            "email_type": email_type,
                            "recipient": str(
                                job.get("recipient")
                                or ""
                            ),
                            "subject": str(
                                job.get("subject")
                                or ""
                            ),
                            "html_content": str(
                                job.get("html_content")
                                or ""
                            ),
                            "plain_text": str(
                                job.get("plain_text")
                                or ""
                            ),
                            "available_at": now,
                            "created_at": now,
                            "updated_at": now,
                        },
                    )

                except IntegrityError:

                    # Another process may have inserted the same
                    # event/guest/email_type between SELECT and INSERT.
                    #
                    # The transaction is rolled back automatically
                    # when this connection context exits.
                    #
                    # We perform a second lookup outside this block.
                    raise

                job_id = result.lastrowid

            # ----------------------------------------------------------
            # Re-read inserted job
            # ----------------------------------------------------------

            if job_id is None:
                return None

            with engine.connect() as conn:
                row = conn.execute(
                    text(
                        """
                        SELECT *
                        FROM email_jobs
                        WHERE id = :id
                        LIMIT 1
                        """
                    ),
                    {"id": int(job_id)},
                ).mappings().first()

                if row:
                    result = dict(row)
                    result["_newly_created"] = True
                    return result

                return None

        except IntegrityError:

            # Duplicate race condition.
            # Return the existing job rather than failing.
            try:
                with engine.connect() as conn:
                    row = conn.execute(
                        find_stmt,
                        {
                            "event_id": event_id,
                            "guest_id": guest_id,
                            "email_type": email_type,
                        },
                    ).mappings().first()

                    return (
                        dict(row)
                        if row
                        else None
                    )

            except Exception as exc:
                self._raise_db(
                    "lookup duplicate email job",
                    exc,
                )

        except DatabaseError:
            raise

        except SQLAlchemyError as exc:
            self._raise_db(
                "enqueue email job",
                exc,
            )

        except Exception as exc:
            self._raise_db(
                "enqueue email job",
                exc,
            )

        return None

    # ==================================================================
    # BULK ENQUEUE
    # ==================================================================

    def enqueue_many(
        self,
        jobs: List[Dict[str, Any]],
        batch_size: int = 500,
    ) -> int:
        """
        Idempotently enqueue many jobs.

        Existing event/guest/email_type combinations are skipped.
        """

        if not jobs:
            return 0

        batch_size = max(
            1,
            min(int(batch_size), 500),
        )

        created = 0

        for start in range(
            0,
            len(jobs),
            batch_size,
        ):
            batch = jobs[
                start : start + batch_size
            ]

            for job in batch:
                try:
                    result = self.enqueue(
                        job,
                        force=False,
                    )

                    if result:
                        # Determine whether this was actually new.
                        #
                        # Existing rows are intentionally returned by
                        # enqueue(), so check status/created_at is not
                        # sufficient. For the application's current
                        # bulk flow, counting successful queue lookups
                        # would incorrectly report duplicates as created.
                        #
                        # Therefore explicitly check whether this job
                        # existed before inserting via helper below.
                        if self._was_created_recently(
                            result,
                            job,
                        ):
                            created += 1

                except Exception:
                    logger.exception(
                        "Unable to enqueue guest email "
                        "event=%s guest=%s",
                        job.get("event_id"),
                        job.get("guest_id"),
                    )

        return created

    def _was_created_recently(
        self,
        result: Dict[str, Any],
        job: Dict[str, Any],
    ) -> bool:
        """
        Determine whether enqueue() created the job.

        This helper is intentionally conservative.

        For the application's current use, enqueue_many() is called
        primarily with unsent guests, so an existing job means the
        invitation was already queued/sent.
        """

        if not result:
            return False

        # If the job was just created it will normally have attempts=0
        # and queued status. However a worker could process it immediately.
        #
        # We therefore perform a direct existence check and use the
        # job's creation timestamp compared with the current operation.
        #
        # The bulk caller only needs the number newly inserted. To avoid
        # misleading counts, use a direct marker when available.

        return bool(
            result.get("_newly_created", False)
        )

    # ==================================================================
    # RECOVER STALE PROCESSING JOBS
    # ==================================================================

    def recover_stale_processing_jobs(
        self,
        max_age_minutes: int = 15,
    ) -> int:
        """
        Requeue processing jobs whose worker lease has expired.

        A stale processing job is one that has remained PROCESSING
        longer than max_age_minutes.

        Attempts are intentionally preserved. A recovered job will
        receive its next attempt number when claim_batch() claims it.

        Returns the number of recovered jobs.
        """

        max_age_minutes = max(
            1,
            int(max_age_minutes),
        )

        now = self._now()
        cutoff = now - timedelta(
            minutes=max_age_minutes,
        )

        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text(
                        """
                        UPDATE email_jobs
                        SET
                            status = 'queued',
                            available_at = :available_at,
                            locked_at = NULL,
                            updated_at = :updated_at
                        WHERE status = 'processing'
                          AND locked_at IS NOT NULL
                          AND locked_at < :cutoff
                        """
                    ),
                    {
                        "available_at": now,
                        "updated_at": now,
                        "cutoff": cutoff,
                    },
                )

                recovered = int(
                    result.rowcount or 0
                )

                if recovered:
                    logger.warning(
                        "Recovered %s stale processing email job(s)",
                        recovered,
                    )

                return recovered

        except SQLAlchemyError as exc:
            self._raise_db(
                "recover stale email jobs",
                exc,
            )

        except Exception as exc:
            self._raise_db(
                "recover stale email jobs",
                exc,
            )

        return 0

    # ==================================================================
    # CLAIM JOBS
    # ==================================================================

    def claim_batch(
        self,
        batch_size: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Claim queued jobs for the email worker.

        SQLite implementation.

        A transaction is used so that the SELECT and UPDATE happen
        together.

        The worker receives jobs marked as PROCESSING.
        """

        batch_size = max(
            1,
            min(int(batch_size), 100),
        )

        now = self._now()

        try:
            with engine.begin() as conn:

                # ------------------------------------------------------
                # Recover stale processing jobs
                # ------------------------------------------------------

                stale_cutoff = now - timedelta(
                    minutes=15,
                )

                recovered = conn.execute(
                    text(
                        """
                        UPDATE email_jobs
                        SET
                            status = 'queued',
                            available_at = :available_at,
                            locked_at = NULL,
                            updated_at = :updated_at
                        WHERE status = 'processing'
                          AND locked_at IS NOT NULL
                          AND locked_at < :cutoff
                        """
                    ),
                    {
                        "available_at": now,
                        "updated_at": now,
                        "cutoff": stale_cutoff,
                    },
                )

                recovered_count = int(
                    recovered.rowcount or 0
                )

                if recovered_count:
                    logger.warning(
                        "Recovered %s stale processing "
                        "email job(s)",
                        recovered_count,
                    )

                rows = conn.execute(
                    text(
                        """
                        SELECT *
                        FROM email_jobs
                        WHERE status = 'queued'
                          AND (
                              available_at IS NULL
                              OR available_at <= :now
                          )
                        ORDER BY id ASC
                        LIMIT :limit
                        """
                    ),
                    {
                        "now": now,
                        "limit": batch_size,
                    },
                ).mappings().all()

                if not rows:
                    return []

                ids = [
                    int(row["id"])
                    for row in rows
                ]

                for job_id in ids:

                    conn.execute(
                        text(
                            """
                            UPDATE email_jobs
                            SET
                                status = 'processing',
                                attempts = COALESCE(attempts, 0) + 1,
                                locked_at = :locked_at,
                                updated_at = :updated_at
                            WHERE id = :id
                              AND status = 'queued'
                            """
                        ),
                        {
                            "id": job_id,
                            "locked_at": now,
                            "updated_at": now,
                        },
                    )



                # SQLite/text() IN expanding syntax is easier to avoid
                # here by querying individually in the same transaction.

                result: List[Dict[str, Any]] = []

                for job_id in ids:
                    row = conn.execute(
                        text(
                            """
                            SELECT *
                            FROM email_jobs
                            WHERE id = :id
                            """
                        ),
                        {"id": job_id},
                    ).mappings().first()

                    if row:
                        result.append(
                            dict(row)
                        )

                return result

        except SQLAlchemyError as exc:
            self._raise_db(
                "claim email jobs",
                exc,
            )

        except Exception as exc:
            self._raise_db(
                "claim email jobs",
                exc,
            )

        return []

    # ==================================================================
    # GET EVENT JOBS
    # ==================================================================

    def get_event_jobs(
        self,
        event_id: int,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return recent email jobs for an event."""

        limit = max(
            1,
            min(int(limit), 500),
        )

        try:
            with engine.connect() as conn:

                rows = conn.execute(
                    text(
                        """
                        SELECT
                            id,
                            event_id,
                            guest_id,
                            email_type,
                            recipient,
                            subject,
                            status,
                            attempts,
                            available_at,
                            locked_at,
                            sent_at,
                            last_error,
                            provider_message_id,
                            provider_status,
                            delivered_at,
                            bounced_at,
                            opened_at,
                            clicked_at,
                            created_at,
                            updated_at
                        FROM email_jobs
                        WHERE event_id = :event_id
                        ORDER BY id DESC
                        LIMIT :limit
                        """
                    ),
                    {
                        "event_id": int(event_id),
                        "limit": limit,
                    },
                ).mappings().all()

                return self._rows_to_dicts(rows)

        except SQLAlchemyError as exc:
            self._raise_db(
                "get event email jobs",
                exc,
            )

        except Exception as exc:
            self._raise_db(
                "get event email jobs",
                exc,
            )

        return []

    # ==================================================================
    # GET COMPLETE DELIVERY DETAILS
    # ==================================================================

    def get_delivery_details(
        self,
        job_id: int,
        event_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return the complete delivery record for one event-scoped job."""
        try:
            with engine.connect() as conn:
                row = conn.execute(
                    text(
                        """
                        SELECT
                            id, event_id, guest_id, email_type, recipient,
                            subject, status, attempts, available_at, locked_at,
                            sent_at, last_error, provider_message_id,
                            provider_status, delivered_at, bounced_at,
                            opened_at, clicked_at, created_at, updated_at
                        FROM email_jobs
                        WHERE id = :id AND event_id = :event_id
                        LIMIT 1
                        """
                    ),
                    {"id": int(job_id), "event_id": int(event_id)},
                ).mappings().first()
                return dict(row) if row else None
        except SQLAlchemyError as exc:
            self._raise_db("get email delivery details", exc)
        except Exception as exc:
            self._raise_db("get email delivery details", exc)
        return None

    # ==================================================================
    # GET SINGLE JOB
    # ==================================================================

    def get_job(
        self,
        job_id: int,
        event_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Get one email job.

        Always event-scoped.
        """

        try:
            with engine.connect() as conn:

                row = conn.execute(
                    text(
                        """
                        SELECT *
                        FROM email_jobs
                        WHERE id = :id
                          AND event_id = :event_id
                        LIMIT 1
                        """
                    ),
                    {
                        "id": int(job_id),
                        "event_id": int(event_id),
                    },
                ).mappings().first()

                return (
                    dict(row)
                    if row
                    else None
                )

        except SQLAlchemyError as exc:
            self._raise_db(
                "get email job",
                exc,
            )

        except Exception as exc:
            self._raise_db(
                "get email job",
                exc,
            )

        return None

    # ==================================================================
    # MARK SENT
    # ==================================================================

    def mark_sent(
        self,
        job_id: int,
        event_id: int,
        guest_id: str,
        provider_message_id: str = "",
    ) -> None:
        """
        Mark an email job as successfully accepted by SendGrid.

        Also updates guests.email_sent=True.
        """

        now = self._now()

        try:
            with engine.begin() as conn:

                result = conn.execute(
                    text(
                        """
                        UPDATE email_jobs
                        SET
                            status = 'sent',
                            sent_at = :sent_at,
                            provider_message_id = :provider_message_id,
                            last_error = NULL,
                            locked_at = NULL,
                            updated_at = :updated_at
                        WHERE id = :id
                          AND event_id = :event_id
                        """
                    ),
                    {
                        "id": int(job_id),
                        "event_id": int(event_id),
                        "sent_at": now,
                        "provider_message_id": (
                            provider_message_id
                            or None
                        ),
                        "updated_at": now,
                    },
                )

                if result.rowcount == 0:
                    raise ValueError(
                        f"Email job {job_id} "
                        f"not found for event {event_id}"
                    )

                conn.execute(
                    text(
                        """
                        UPDATE guests
                        SET
                            email_sent = TRUE,
                            updated_at = :updated_at
                        WHERE event_id = :event_id
                          AND guest_id = :guest_id
                        """
                    ),
                    {
                        "event_id": int(event_id),
                        "guest_id": str(guest_id),
                        "updated_at": now,
                    },
                )

        except SQLAlchemyError as exc:
            self._raise_db(
                "mark email job sent",
                exc,
            )

        except Exception as exc:
            self._raise_db(
                "mark email job sent",
                exc,
            )

    # ==================================================================
    # MARK FAILED
    # ==================================================================

    def mark_failed(
        self,
        job_id: int,
        error: str,
        retry: bool,
    ) -> None:
        """
        Mark a worker failure.

        retry=True:
            queue the job for another automatic attempt.

        retry=False:
            permanently mark failed.
        """

        now = self._now()

        delay = timedelta(
            seconds=32
        )

        available_at = (
            now + delay
        )

        status = (
            "queued"
            if retry
            else "failed"
        )

        try:
            with engine.begin() as conn:

                result = conn.execute(
                    text(
                        """
                        UPDATE email_jobs
                        SET
                            status = :status,
                            last_error = :last_error,
                            available_at = :available_at,
                            locked_at = NULL,
                            updated_at = :updated_at
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": int(job_id),
                        "status": status,
                        "last_error": str(error)[
                            :4000
                        ],
                        "available_at": available_at,
                        "updated_at": now,
                    },
                )

                if result.rowcount == 0:
                    raise ValueError(
                        f"Email job {job_id} "
                        "not found"
                    )

        except SQLAlchemyError as exc:
            self._raise_db(
                "mark email job failed",
                exc,
            )

        except Exception as exc:
            self._raise_db(
                "mark email job failed",
                exc,
            )

    # ==================================================================
    # SAFE MANUAL RETRY
    # ==================================================================

    def retry_failed_job(
        self,
        job_id: int,
        event_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Manually retry a FAILED or CANCELLED job.

        SENT jobs are rejected.
        """

        try:
            with engine.begin() as conn:

                row = conn.execute(
                    text(
                        """
                        SELECT *
                        FROM email_jobs
                        WHERE id = :id
                          AND event_id = :event_id
                        LIMIT 1
                        """
                    ),
                    {
                        "id": int(job_id),
                        "event_id": int(event_id),
                    },
                ).mappings().first()

                if not row:
                    return None

                status = str(
                    row["status"]
                    or ""
                ).lower()

                if status not in {
                    "failed",
                    "cancelled",
                }:
                    raise ValueError(
                        f"Job {job_id} cannot be "
                        f"retried because its status "
                        f"is '{status}'."
                    )

                now = self._now()

                conn.execute(
                    text(
                        """
                        UPDATE email_jobs
                        SET
                            status = 'queued',
                            attempts = 0,
                            last_error = NULL,
                            available_at = :available_at,
                            locked_at = NULL,
                            updated_at = :updated_at
                        WHERE id = :id
                          AND event_id = :event_id
                        """
                    ),
                    {
                        "id": int(job_id),
                        "event_id": int(event_id),
                        "available_at": now,
                        "updated_at": now,
                    },
                )

                refreshed = conn.execute(
                    text(
                        """
                        SELECT *
                        FROM email_jobs
                        WHERE id = :id
                          AND event_id = :event_id
                        LIMIT 1
                        """
                    ),
                    {
                        "id": int(job_id),
                        "event_id": int(event_id),
                    },
                ).mappings().first()

                return (
                    dict(refreshed)
                    if refreshed
                    else None
                )

        except SQLAlchemyError as exc:
            self._raise_db(
                "retry failed email job",
                exc,
            )

        except Exception as exc:
            self._raise_db(
                "retry failed email job",
                exc,
            )

        return None

    # ==================================================================
    # SAFE RESEND SENT JOB
    # ==================================================================

    def resend_sent_job(
        self,
        job_id: int,
        event_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Explicitly resend an already-sent email.

        This is different from retry_failed_job().

        Only SENT jobs are accepted here.
        """

        try:
            with engine.begin() as conn:

                row = conn.execute(
                    text(
                        """
                        SELECT *
                        FROM email_jobs
                        WHERE id = :id
                          AND event_id = :event_id
                        LIMIT 1
                        """
                    ),
                    {
                        "id": int(job_id),
                        "event_id": int(event_id),
                    },
                ).mappings().first()

                if not row:
                    return None

                status = str(
                    row["status"]
                    or ""
                ).lower()

                if status != "sent":
                    raise ValueError(
                        f"Job {job_id} cannot be "
                        f"resent because its status "
                        f"is '{status}'."
                    )

                now = self._now()

                conn.execute(
                    text(
                        """
                        UPDATE email_jobs
                        SET
                            status = 'queued',
                            attempts = 0,
                            last_error = NULL,
                            sent_at = NULL,
                            provider_message_id = NULL,
                            locked_at = NULL,
                            available_at = :available_at,
                            updated_at = :updated_at
                        WHERE id = :id
                          AND event_id = :event_id
                          AND status = 'sent'
                        """
                    ),
                    {
                        "id": int(job_id),
                        "event_id": int(event_id),
                        "available_at": now,
                        "updated_at": now,
                    },
                )

                refreshed = conn.execute(
                    text(
                        """
                        SELECT *
                        FROM email_jobs
                        WHERE id = :id
                          AND event_id = :event_id
                        LIMIT 1
                        """
                    ),
                    {
                        "id": int(job_id),
                        "event_id": int(event_id),
                    },
                ).mappings().first()

                return (
                    dict(refreshed)
                    if refreshed
                    else None
                )

        except SQLAlchemyError as exc:
            self._raise_db(
                "resend sent email job",
                exc,
            )

        except Exception as exc:
            self._raise_db(
                "resend sent email job",
                exc,
            )

        return None

    # ==================================================================
    # RETRY ALL FAILED / CANCELLED
    # ==================================================================

    def retry_failed_jobs(
        self,
        event_id: int,
    ) -> int:
        """
        Queue all FAILED/CANCELLED jobs for an event.
        """

        now = self._now()

        try:
            with engine.begin() as conn:

                result = conn.execute(
                    text(
                        """
                        UPDATE email_jobs
                        SET
                            status = 'queued',
                            attempts = 0,
                            last_error = NULL,
                            locked_at = NULL,
                            available_at = :available_at,
                            updated_at = :updated_at
                        WHERE event_id = :event_id
                          AND status IN (
                              'failed',
                              'cancelled'
                          )
                        """
                    ),
                    {
                        "event_id": int(event_id),
                        "available_at": now,
                        "updated_at": now,
                    },
                )

                return int(
                    result.rowcount or 0
                )

        except SQLAlchemyError as exc:
            self._raise_db(
                "retry failed email jobs",
                exc,
            )

        except Exception as exc:
            self._raise_db(
                "retry failed email jobs",
                exc,
            )

        return 0

    # ==================================================================
    # SUMMARY
    # ==================================================================

    def get_event_summary(
        self,
        event_id: int,
    ) -> Dict[str, int]:
        """
        Return email delivery counts for an event.
        """

        result = {
            "queued": 0,
            "processing": 0,
            "sent": 0,
            "failed": 0,
            "cancelled": 0,
        }

        try:
            with engine.connect() as conn:

                rows = conn.execute(
                    text(
                        """
                        SELECT
                            status,
                            COUNT(*) AS count
                        FROM email_jobs
                        WHERE event_id = :event_id
                        GROUP BY status
                        """
                    ),
                    {
                        "event_id": int(event_id),
                    },
                ).mappings().all()

                for row in rows:

                    status = str(
                        row["status"]
                        or ""
                    ).lower()

                    if status in result:
                        result[status] = int(
                            row["count"] or 0
                        )

                return result

        except SQLAlchemyError as exc:
            self._raise_db(
                "get email event summary",
                exc,
            )

        except Exception as exc:
            self._raise_db(
                "get email event summary",
                exc,
            )

        return result