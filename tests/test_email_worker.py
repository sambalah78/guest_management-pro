from unittest.mock import MagicMock, patch

import pytest

from guest_management.workers.email_worker import EmailWorker


def _make_worker(jobs):
    worker = object.__new__(EmailWorker)

    worker.batch_size = len(jobs) or 1
    worker.repo = MagicMock()
    worker.repo.claim_batch.return_value = jobs
    worker.storage_service = MagicMock()
    worker.event_repo = MagicMock()
    worker.guest_repo = MagicMock()

    return worker


def _job(job_id):
    return {
        "id": job_id,
        "event_id": 1,
        "guest_id": f"guest-{job_id}",
        "recipient": f"guest{job_id}@example.com",
        "attempts": 1,
        "subject": "Test",
        "html_content": "<p>Test</p>",
        "plain_text": "Test",
    }


def test_run_once_reuses_one_smtp_connection_for_batch():
    jobs = [
        _job(1),
        _job(2),
        _job(3),
    ]

    worker = _make_worker(jobs)

    smtp = MagicMock()

    with patch.object(
        worker,
        "_connect_smtp",
        return_value=smtp,
    ) as connect_mock, patch.object(
        worker,
        "build_message",
        return_value=MagicMock(),
    ):

        processed = worker.run_once()

    assert processed == 3
    connect_mock.assert_called_once()

    assert smtp.send_message.call_count == 3
    smtp.quit.assert_called_once()

    assert worker.repo.mark_sent.call_count == 3
    worker.repo.mark_failed.assert_not_called()


def test_run_once_no_jobs_does_not_connect_smtp():
    worker = _make_worker([])

    with patch.object(
        worker,
        "_connect_smtp",
    ) as connect_mock:

        processed = worker.run_once()

    assert processed == 0
    connect_mock.assert_not_called()


def test_connect_smtp_performs_tls_and_login():
    worker = object.__new__(EmailWorker)

    smtp = MagicMock()

    with patch(
        "guest_management.workers.email_worker.smtplib.SMTP",
        return_value=smtp,
    ) as smtp_class:

        result = worker._connect_smtp()

    assert result is smtp

    smtp_class.assert_called_once()

    smtp.ehlo.assert_any_call()
    assert smtp.ehlo.call_count == 2

    smtp.starttls.assert_called_once_with()

    smtp.login.assert_called_once()


def test_send_one_reuses_supplied_smtp_connection():
    worker = object.__new__(EmailWorker)

    smtp = MagicMock()

    job = _job(1)

    with patch.object(
        worker,
        "build_message",
        return_value=MagicMock(),
    ), patch.object(
        worker,
        "_connect_smtp",
    ) as connect_mock:

        result = worker.send_one(
            job,
            smtp=smtp,
        )

    assert result == ""
    smtp.send_message.assert_called_once()
    smtp.quit.assert_not_called()
    smtp.close.assert_not_called()
    connect_mock.assert_not_called()


def test_send_one_closes_smtp_when_it_owns_connection():
    worker = object.__new__(EmailWorker)

    smtp = MagicMock()

    job = _job(1)

    with patch.object(
        worker,
        "build_message",
        return_value=MagicMock(),
    ), patch.object(
        worker,
        "_connect_smtp",
        return_value=smtp,
    ) as connect_mock:

        worker.send_one(job)

    connect_mock.assert_called_once()
    smtp.send_message.assert_called_once()
    smtp.quit.assert_called_once()


def test_smtp_failure_discards_connection_and_next_job_reconnects():
    jobs = [
        _job(1),
        _job(2),
    ]

    worker = _make_worker(jobs)

    first_smtp = MagicMock()
    second_smtp = MagicMock()

    first_smtp.send_message.side_effect = OSError(
        "SMTP connection lost"
    )

    with patch.object(
        worker,
        "_connect_smtp",
        side_effect=[
            first_smtp,
            second_smtp,
        ],
    ) as connect_mock, patch.object(
        worker,
        "build_message",
        return_value=MagicMock(),
    ):

        processed = worker.run_once()

    assert processed == 1

    assert connect_mock.call_count == 2

    first_smtp.quit.assert_called_once()
    second_smtp.quit.assert_called_once()

    assert first_smtp.send_message.call_count == 1
    assert second_smtp.send_message.call_count == 1

    assert worker.repo.mark_failed.call_count == 1
    worker.repo.mark_failed.assert_called_once_with(
        job_id=1,
        error="SMTP connection lost",
        retry=True,
    )

    assert worker.repo.mark_sent.call_count == 1
    worker.repo.mark_sent.assert_called_once()


def test_connection_failure_is_retried_for_each_claimed_job():
    jobs = [
        _job(1),
        _job(2),
    ]

    worker = _make_worker(jobs)

    with patch.object(
        worker,
        "_connect_smtp",
        side_effect=OSError("SMTP unavailable"),
    ) as connect_mock:

        processed = worker.run_once()

    assert processed == 0
    assert connect_mock.call_count == 2

    assert worker.repo.mark_sent.call_count == 0
    assert worker.repo.mark_failed.call_count == 2


def test_send_one_failure_with_supplied_smtp_does_not_close_connection():
    worker = object.__new__(EmailWorker)

    smtp = MagicMock()
    smtp.send_message.side_effect = OSError(
        "SMTP connection lost"
    )

    job = _job(1)

    with patch.object(
        worker,
        "build_message",
        return_value=MagicMock(),
    ):

        with pytest.raises(OSError, match="SMTP connection lost"):
            worker.send_one(
                job,
                smtp=smtp,
            )

    smtp.quit.assert_not_called()
    smtp.close.assert_not_called()
