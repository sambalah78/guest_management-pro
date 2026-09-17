import pytest

from guest_management.models.pre_draw_prize import PreDrawPrize


def test_pre_draw_prize_accepts_valid_configuration():
    prize = PreDrawPrize(
        id=None,
        event_id=1,
        name="RM100 Voucher",
        value="RM100",
        winner_count=10,
        sort_order=1,
    )

    assert prize.name == "RM100 Voucher"
    assert prize.value == "RM100"
    assert prize.winner_count == 10
    assert prize.status == "draft"


def test_pre_draw_prize_rejects_invalid_event_id():
    with pytest.raises(ValueError):
        PreDrawPrize(
            id=None,
            event_id=0,
            name="RM100 Voucher",
        )


def test_pre_draw_prize_rejects_empty_name():
    with pytest.raises(ValueError):
        PreDrawPrize(
            id=None,
            event_id=1,
            name="",
        )


def test_pre_draw_prize_rejects_zero_winner_count():
    with pytest.raises(ValueError):
        PreDrawPrize(
            id=None,
            event_id=1,
            name="RM100 Voucher",
            winner_count=0,
        )


def test_pre_draw_prize_rejects_negative_winner_count():
    with pytest.raises(ValueError):
        PreDrawPrize(
            id=None,
            event_id=1,
            name="RM100 Voucher",
            winner_count=-1,
        )


def test_pre_draw_prize_rejects_negative_sort_order():
    with pytest.raises(ValueError):
        PreDrawPrize(
            id=None,
            event_id=1,
            name="RM100 Voucher",
            sort_order=-1,
        )


def test_pre_draw_prize_rejects_invalid_status():
    with pytest.raises(ValueError):
        PreDrawPrize(
            id=None,
            event_id=1,
            name="RM100 Voucher",
            status="invalid",
        )


def test_pre_draw_prize_normalizes_values():
    prize = PreDrawPrize(
        id=None,
        event_id=1,
        name="  RM100 Voucher  ",
        value=" RM100 ",
        winner_count=10,
        status="READY",
    )

    assert prize.name == "RM100 Voucher"
    assert prize.value == "RM100"
    assert prize.status == "ready"


def test_pre_draw_prize_from_dict():
    prize = PreDrawPrize.from_dict(
        {
            "id": 5,
            "event_id": 10,
            "name": "RM300 Voucher",
            "value": "RM300",
            "winner_count": 5,
            "sort_order": 2,
            "status": "READY",
        }
    )

    assert prize.id == 5
    assert prize.event_id == 10
    assert prize.name == "RM300 Voucher"
    assert prize.value == "RM300"
    assert prize.winner_count == 5
    assert prize.sort_order == 2
    assert prize.status == "ready"


def test_pre_draw_prize_to_dict():
    prize = PreDrawPrize(
        id=5,
        event_id=10,
        name="RM500 Voucher",
        value="RM500",
        winner_count=3,
        sort_order=4,
        status="generated",
    )

    data = prize.to_dict()

    assert data["id"] == 5
    assert data["event_id"] == 10
    assert data["name"] == "RM500 Voucher"
    assert data["value"] == "RM500"
    assert data["winner_count"] == 3
    assert data["sort_order"] == 4
    assert data["status"] == "generated"