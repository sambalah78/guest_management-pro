import pytest

from guest_management.services.pre_draw_service import PreDrawService


class FakeEventRepository:
    def __init__(self, event_type="lucky_draw"):
        self.event = {
            "id": 100,
            "name": "Test Event",
            "event_type": event_type,
            "user_id": "test-user",
        }

    def get_by_id(self, event_id, user_id):
        if int(event_id) != 100:
            return None

        return (
            self.event
            if str(user_id) == str(self.event.get("user_id"))
            else None
        )

    def get_by_id_any(self, event_id):
        return self.event if int(event_id) == 100 else None


class FakeGuestRepository:
    def __init__(self, guests):
        self.guests = list(guests)

    def get_by_event(self, event_id, limit=200, offset=0):
        rows = self.guests[offset : offset + limit]
        return rows, len(self.guests)


class FakePrizeRepository:
    def __init__(self, prizes):
        self.prizes = list(prizes)

    def get_by_event(
        self,
        event_id,
        *,
        include_archived=False,
        limit=100,
    ):
        rows = [
            dict(prize)
            for prize in self.prizes
            if include_archived
            or str(prize.get("status", "draft")).lower()
            != "archived"
        ]
        return rows[:limit]


class FakeWinnerRepository:
    def __init__(self):
        self.calls = []

    def finalize_random_generation(
        self,
        event_id,
        winners,
        prize_ids,
    ):
        self.calls.append(
            {
                "event_id": event_id,
                "winners": winners,
                "prize_ids": prize_ids,
            }
        )
        return winners


class FirstSampleRng:
    def sample(self, population, count):
        return list(population[:count])


def build_service(
    *,
    event_type="lucky_draw",
    guests=None,
    prizes=None,
):
    return PreDrawService(
        event_repository=FakeEventRepository(
            event_type=event_type
        ),
        guest_repository=FakeGuestRepository(
            guests or []
        ),
        prize_repository=FakePrizeRepository(
            prizes or []
        ),
        winner_repository=FakeWinnerRepository(),
        rng=FirstSampleRng(),
    )


def test_random_pre_draw_generates_unique_winners_across_prizes():
    guests = [
        {"guest_id": "G001", "name": "Alice", "status": "Absent"},
        {"guest_id": "G002", "name": "Bob", "status": "Absent"},
        {"guest_id": "G003", "name": "Carol", "status": "Present"},
        {"guest_id": "G004", "name": "David", "status": "Absent"},
    ]

    prizes = [
        {
            "id": 1,
            "name": "Grand Prize",
            "value": "RM 500",
            "image_url": "",
            "winner_count": 2,
            "sort_order": 0,
            "status": "ready",
        },
        {
            "id": 2,
            "name": "Second Prize",
            "value": "RM 200",
            "image_url": "",
            "winner_count": 1,
            "sort_order": 1,
            "status": "ready",
        },
    ]

    service = build_service(
        guests=guests,
        prizes=prizes,
    )

    winners = service.generate_random_winners(100, "test-user")

    assert len(winners) == 3

    assert len(
        {
            winner["guest_id"].lower()
            for winner in winners
        }
    ) == 3

    assert [
        winner["guest_id"]
        for winner in winners
    ] == ["G001", "G002", "G003"]

    assert [
        winner["prize_id"]
        for winner in winners
    ] == [1, 1, 2]

    assert service.winner_repository.calls[0]["prize_ids"] == [1, 2]


def test_standalone_pre_draw_ignores_checkin_status():
    guests = [
        {
            "guest_id": "G001",
            "name": "Absent Guest",
            "status": "Absent",
        },
        {
            "guest_id": "G002",
            "name": "Present Guest",
            "status": "Present",
        },
    ]

    prizes = [
        {
            "id": 1,
            "name": "Prize",
            "value": "RM 100",
            "image_url": "",
            "winner_count": 1,
            "sort_order": 0,
            "status": "draft",
        }
    ]

    service = build_service(
        guests=guests,
        prizes=prizes,
    )

    winners = service.generate_random_winners(100, "test-user")

    assert winners[0]["guest_id"] == "G001"


def test_random_pre_draw_rejects_insufficient_participants():
    guests = [
        {"guest_id": "G001", "name": "Alice", "status": "Absent"},
        {"guest_id": "G002", "name": "Bob", "status": "Absent"},
    ]

    prizes = [
        {
            "id": 1,
            "name": "Prize",
            "value": "RM 100",
            "image_url": "",
            "winner_count": 3,
            "sort_order": 0,
            "status": "ready",
        }
    ]

    service = build_service(
        guests=guests,
        prizes=prizes,
    )

    with pytest.raises(
        ValueError,
        match="exceeds the available participant count",
    ):
        service.generate_random_winners(100, "test-user")


def test_random_pre_draw_rejects_duplicate_guest_ids():
    guests = [
        {"guest_id": "G001", "name": "Alice", "status": "Absent"},
        {
            "guest_id": "g001",
            "name": "Alice Duplicate",
            "status": "Absent",
        },
    ]

    prizes = [
        {
            "id": 1,
            "name": "Prize",
            "value": "RM 100",
            "image_url": "",
            "winner_count": 1,
            "sort_order": 0,
            "status": "ready",
        }
    ]

    service = build_service(
        guests=guests,
        prizes=prizes,
    )

    with pytest.raises(
        ValueError,
        match="Duplicate Guest IDs",
    ):
        service.generate_random_winners(100, "test-user")


def test_random_pre_draw_rejects_generated_prize_configuration():
    guests = [
        {"guest_id": "G001", "name": "Alice", "status": "Absent"},
    ]

    prizes = [
        {
            "id": 1,
            "name": "Prize",
            "value": "RM 100",
            "image_url": "",
            "winner_count": 1,
            "sort_order": 0,
            "status": "generated",
        }
    ]

    service = build_service(
        guests=guests,
        prizes=prizes,
    )

    with pytest.raises(
        ValueError,
        match="already been generated",
    ):
        service.generate_random_winners(100, "test-user")


def test_random_pre_draw_is_disabled_for_wedding_events():
    guests = [
        {"guest_id": "G001", "name": "Alice", "status": "Absent"},
    ]

    prizes = [
        {
            "id": 1,
            "name": "Prize",
            "value": "RM 100",
            "image_url": "",
            "winner_count": 1,
            "sort_order": 0,
            "status": "ready",
        }
    ]

    service = build_service(
        event_type="wedding_dinner",
        guests=guests,
        prizes=prizes,
    )

    with pytest.raises(
        ValueError,
        match="Pre-Draw is not enabled",
    ):
        service.generate_random_winners(100, "test-user")

def test_manager_can_generate_pre_draw_for_event_owned_by_another_user():
    """OWNER/ADMIN access must use EventService manager authorization."""
    service = build_service(
        guests=[
            {"guest_id": "G001", "name": "Alice", "status": "Absent"},
            {"guest_id": "G002", "name": "Bob", "status": "Absent"},
            {"guest_id": "G003", "name": "Carol", "status": "Absent"},
        ],
        prizes=[
            {
                "id": 1,
                "name": "Prize 1",
                "value": "100",
                "winner_count": 1,
                "sort_order": 1,
                "status": "ready",
            },
            {
                "id": 2,
                "name": "Prize 2",
                "value": "200",
                "winner_count": 1,
                "sort_order": 2,
                "status": "ready",
            },
            {
                "id": 3,
                "name": "Prize 3",
                "value": "300",
                "winner_count": 1,
                "sort_order": 3,
                "status": "ready",
            },
        ],
    )

    user = {
        "id": "admin-user",
        "role": "ADMIN",
        "is_active": True,
    }

    winners = service.generate_random_winners(
        100,
        "admin-user",
        user,
    )

    assert len(winners) == 3
    assert len({winner["guest_id"] for winner in winners}) == 3
