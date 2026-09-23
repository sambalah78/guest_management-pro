from unittest.mock import MagicMock

import pytest

from guest_management.repositories.pre_draw_prize_repository import (
    PreDrawPrizeRepository,
)


def make_repo():
    db = MagicMock()
    repo = PreDrawPrizeRepository(db=db)
    return repo, db


def setup_query_chain(db):
    query = db.table.return_value
    query.select.return_value = query
    query.eq.return_value = query
    query.neq.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.execute.return_value.data = []
    return query


def test_get_by_event_returns_prizes_in_display_order():
    repo, db = make_repo()
    query = setup_query_chain(db)

    rows = [
        {
            "id": 1,
            "event_id": 100,
            "name": "Grand Prize",
            "value": "RM500",
            "winner_count": 1,
            "sort_order": 0,
            "status": "ready",
        },
        {
            "id": 2,
            "event_id": 100,
            "name": "Second Prize",
            "value": "RM200",
            "winner_count": 2,
            "sort_order": 1,
            "status": "ready",
        },
    ]

    query.execute.return_value.data = rows

    result = repo.get_by_event(100)

    assert result == rows
    db.table.assert_called_once_with("pre_draw_prizes")
    query.eq.assert_called_once_with("event_id", 100)
    query.neq.assert_called_once_with("status", "archived")


def test_get_by_event_can_include_archived_prizes():
    repo, db = make_repo()
    query = setup_query_chain(db)

    rows = [
        {
            "id": 1,
            "event_id": 100,
            "name": "Archived Prize",
            "value": "RM100",
            "winner_count": 1,
            "sort_order": 0,
            "status": "archived",
        }
    ]

    query.execute.return_value.data = rows

    result = repo.get_by_event(100, include_archived=True)

    assert result == rows
    query.neq.assert_not_called()


def test_get_by_event_rejects_invalid_event_id():
    repo, _ = make_repo()

    with pytest.raises(
        ValueError,
        match="event_id must be greater than zero",
    ):
        repo.get_by_event(0)


def test_get_by_event_caps_limit():
    repo, db = make_repo()
    query = setup_query_chain(db)

    repo.get_by_event(100, limit=999999)

    query.limit.assert_called_once_with(500)


def test_get_by_id_returns_event_scoped_prize():
    repo, db = make_repo()
    query = setup_query_chain(db)

    row = {
        "id": 5,
        "event_id": 100,
        "name": "Grand Prize",
        "value": "RM500",
        "winner_count": 1,
        "sort_order": 0,
        "status": "ready",
    }

    query.execute.return_value.data = [row]

    result = repo.get_by_id(100, 5)

    assert result == row
    query.eq.assert_any_call("event_id", 100)
    query.eq.assert_any_call("id", 5)


def test_get_by_id_returns_none_when_not_found():
    repo, db = make_repo()
    query = setup_query_chain(db)

    query.execute.return_value.data = []

    assert repo.get_by_id(100, 999) is None


def test_get_by_id_rejects_invalid_prize_id():
    repo, _ = make_repo()

    with pytest.raises(
        ValueError,
        match="prize_id must be greater than zero",
    ):
        repo.get_by_id(100, 0)


def test_create_inserts_normalized_prize_data():
    repo, db = make_repo()
    query = db.table.return_value

    created = {
        "id": 10,
        "event_id": 100,
        "name": "Grand Prize",
        "value": "RM500",
        "image_url": "https://example.com/prize.png",
        "winner_count": 2,
        "sort_order": 1,
        "status": "ready",
    }

    query.insert.return_value.execute.return_value.data = [created]

    result = repo.create(
        event_id=100,
        name="  Grand Prize  ",
        value=" RM500 ",
        image_url=" https://example.com/prize.png ",
        winner_count=2,
        sort_order=1,
        status="READY",
    )

    assert result == created

    payload = query.insert.call_args.args[0]

    assert payload["event_id"] == 100
    assert payload["name"] == "Grand Prize"
    assert payload["value"] == "RM500"
    assert payload["image_url"] == "https://example.com/prize.png"
    assert payload["winner_count"] == 2
    assert payload["sort_order"] == 1
    assert payload["status"] == "ready"
    assert "created_at" in payload
    assert "updated_at" in payload


def test_create_rejects_empty_name():
    repo, _ = make_repo()

    with pytest.raises(
        ValueError,
        match="Pre-draw prize name is required",
    ):
        repo.create(
            event_id=100,
            name="",
        )


def test_create_rejects_invalid_winner_count():
    repo, _ = make_repo()

    with pytest.raises(
        ValueError,
        match="winner_count must be greater than zero",
    ):
        repo.create(
            event_id=100,
            name="Prize",
            winner_count=0,
        )


def test_create_rejects_invalid_status():
    repo, _ = make_repo()

    with pytest.raises(
        ValueError,
        match="Invalid pre-draw prize status",
    ):
        repo.create(
            event_id=100,
            name="Prize",
            status="invalid",
        )


def test_update_only_sends_allowed_fields():
    repo, db = make_repo()
    query = db.table.return_value

    updated = {
        "id": 10,
        "event_id": 100,
        "name": "Updated Prize",
        "value": "RM800",
        "winner_count": 3,
        "sort_order": 2,
        "status": "ready",
    }

    query.update.return_value = query
    query.eq.return_value = query
    query.execute.return_value.data = [updated]

    result = repo.update(
        event_id=100,
        prize_id=10,
        updates={
            "name": " Updated Prize ",
            "value": " RM800 ",
            "winner_count": 3,
            "sort_order": 2,
            "status": "READY",
            "event_id": 999,
            "id": 999,
            "unknown_field": "should be ignored",
        },
    )

    assert result == updated

    payload = query.update.call_args.args[0]

    assert payload["name"] == "Updated Prize"
    assert payload["value"] == "RM800"
    assert payload["winner_count"] == 3
    assert payload["sort_order"] == 2
    assert payload["status"] == "ready"

    assert "event_id" not in payload
    assert "id" not in payload
    assert "unknown_field" not in payload
    assert "updated_at" in payload


def test_update_returns_existing_prize_when_no_mutable_fields_are_supplied():
    repo, _ = make_repo()

    existing = {
        "id": 10,
        "event_id": 100,
        "name": "Prize",
    }

    repo.get_by_id = MagicMock(return_value=existing)

    result = repo.update(
        event_id=100,
        prize_id=10,
        updates={"unknown_field": "ignored"},
    )

    assert result == existing
    repo.get_by_id.assert_called_once_with(100, 10)


def test_update_returns_none_when_prize_does_not_exist():
    repo, db = make_repo()
    query = db.table.return_value

    query.update.return_value = query
    query.eq.return_value = query
    query.execute.return_value.data = []

    result = repo.update(
        event_id=100,
        prize_id=10,
        updates={"name": "Updated Prize"},
    )

    assert result is None


def test_archive_sets_status_to_archived():
    repo, _ = make_repo()

    expected = {
        "id": 10,
        "event_id": 100,
        "status": "archived",
    }

    repo.update = MagicMock(return_value=expected)

    result = repo.archive(100, 10)

    assert result == expected
    repo.update.assert_called_once_with(
        100,
        10,
        {"status": "archived"},
    )


def test_reset_generated_for_event_requires_existing_event():
    repo, db = make_repo()

    connection = MagicMock()
    db.engine.begin.return_value.__enter__.return_value = connection

    event_result = MagicMock()
    event_result.first.return_value = None
    connection.execute.return_value = event_result

    with pytest.raises(
        ValueError,
        match="Event 100 does not exist",
    ):
        repo.reset_generated_for_event(100)


def test_reset_generated_for_event_resets_generated_prizes():
    repo, db = make_repo()

    connection = MagicMock()
    db.engine.begin.return_value.__enter__.return_value = connection

    event_result = MagicMock()
    event_result.first.return_value = (100,)

    update_result = MagicMock()
    update_result.rowcount = 3

    connection.execute.side_effect = [
        event_result,
        update_result,
    ]

    result = repo.reset_generated_for_event(100)

    assert result == 3
    assert connection.execute.call_count == 2


def test_delete_returns_false_when_prize_does_not_exist():
    repo, _ = make_repo()

    repo.get_by_id = MagicMock(return_value=None)

    assert repo.delete(100, 10) is False

    repo.get_by_id.assert_called_once_with(100, 10)


def test_delete_removes_existing_event_scoped_prize():
    repo, db = make_repo()

    repo.get_by_id = MagicMock(
        return_value={
            "id": 10,
            "event_id": 100,
            "name": "Prize",
        }
    )

    query = db.table.return_value
    query.delete.return_value = query
    query.eq.return_value = query

    result = repo.delete(100, 10)

    assert result is True

    db.table.assert_called_with("pre_draw_prizes")
    query.eq.assert_any_call("event_id", 100)
    query.eq.assert_any_call("id", 10)
