import pytest

from guest_management.core.exceptions import DatabaseError, GuestAlreadyCheckedInError
from guest_management.repositories.checkin_repository import CheckinRepository


class FakeResponse:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class FakeRPC:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def execute(self):
        if self.error:
            raise self.error
        return self.response


class FakeDB:
    def __init__(self, rpc_response=None, rpc_error=None):
        self.rpc_response = rpc_response
        self.rpc_error = rpc_error
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        return FakeRPC(self.rpc_response, self.rpc_error)


def make_repo(result=None, error=None):
    return CheckinRepository(FakeDB(rpc_response=result, rpc_error=error))


def test_check_in_requires_event_id():
    repo = make_repo()

    with pytest.raises(ValueError, match="event_id is required"):
        repo.check_in(0, "G1")

    assert repo.db.calls == []


def test_check_in_requires_guest_id():
    repo = make_repo()

    with pytest.raises(ValueError, match="guest_id is required"):
        repo.check_in(18, "")

    assert repo.db.calls == []


def test_check_in_strips_guest_and_scanner_ids():
    repo = make_repo(
        FakeResponse(
            data=[
                {
                    "result": "checked_in",
                    "guest_id": "G1",
                }
            ]
        )
    )

    result = repo.check_in(
        18,
        "  G1  ",
        "  SCANNER_001  ",
    )

    assert result["result"] == "checked_in"
    assert repo.db.calls == [
        (
            "check_in_guest",
            {
                "p_event_id": 18,
                "p_guest_id": "G1",
                "p_scanner_id": "SCANNER_001",
            },
        )
    ]


def test_check_in_converts_empty_scanner_id_to_none():
    repo = make_repo(
        FakeResponse(
            data=[
                {
                    "result": "checked_in",
                    "guest_id": "G1",
                }
            ]
        )
    )

    repo.check_in(18, "G1", "")

    assert repo.db.calls[0][1]["p_scanner_id"] is None


def test_check_in_returns_successful_result():
    expected = {
        "result": "checked_in",
        "guest_id": "G1",
        "guest_name": "John",
        "table_number": "T12",
        "present_count": 50,
        "total_guests": 100,
    }

    repo = make_repo(FakeResponse(data=[expected]))

    result = repo.check_in(18, "G1")

    assert result == expected


def test_check_in_maps_already_checked_in():
    repo = make_repo(
        FakeResponse(
            data=[
                {
                    "result": "already_checked_in",
                    "message": "Guest already checked in",
                }
            ]
        )
    )

    with pytest.raises(
        GuestAlreadyCheckedInError,
        match="Guest already checked in",
    ):
        repo.check_in(18, "G1")


def test_check_in_returns_not_found_result():
    expected = {
        "result": "not_found",
        "message": "Guest not found",
        "event_id": 18,
        "guest_id": "G1",
    }

    repo = make_repo(FakeResponse(data=[expected]))

    result = repo.check_in(18, "G1")

    assert result == expected


def test_check_in_rejects_empty_rpc_result():
    repo = make_repo(FakeResponse(data=[]))

    with pytest.raises(
        DatabaseError,
        match="Check-in RPC returned no result",
    ):
        repo.check_in(18, "G1")


def test_check_in_rejects_invalid_rpc_result():
    repo = make_repo(FakeResponse(data=["invalid"]))

    with pytest.raises(
        DatabaseError,
        match="Check-in RPC returned an invalid result",
    ):
        repo.check_in(18, "G1")


def test_check_in_rejects_unexpected_result_type():
    repo = make_repo(
        FakeResponse(
            data=[
                {
                    "result": "unexpected",
                    "message": "Unexpected result",
                }
            ]
        )
    )

    with pytest.raises(
        DatabaseError,
        match="Unexpected result",
    ):
        repo.check_in(18, "G1")


def test_check_in_converts_database_failure_to_database_error():
    repo = make_repo(error=RuntimeError("connection lost"))

    with pytest.raises(
        DatabaseError,
        match="atomic guest check-in",
    ):
        repo.check_in(18, "G1")