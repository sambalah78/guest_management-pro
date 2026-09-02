from guest_management.services.google_drive_connection_service import (
    GoogleDriveConnectionService,
)


USER_ID = "6TYF0Tib9nqXr2SQ0h2EMcf_wqpqF5v1"


class FakeRepository:
    def __init__(self):
        self.rows = []

    def list_by_user(self, user_id, active_only=False):
        rows = [
            r for r in self.rows
            if r["user_id"] == user_id
        ]

        if active_only:
            rows = [
                r for r in rows
                if r["is_active"]
            ]

        return rows

    def get_by_id(self, connection_id):
        return next(
            (
                r for r in self.rows
                if r["id"] == connection_id
            ),
            None,
        )

    def get_by_user_and_email(
        self,
        user_id,
        google_email,
    ):
        email = google_email.lower()

        return next(
            (
                r
                for r in self.rows
                if r["user_id"] == user_id
                and r["google_email"] == email
            ),
            None,
        )

    def get_primary(self, user_id):
        return next(
            (
                r
                for r in self.rows
                if r["user_id"] == user_id
                and r["is_primary"]
                and r["is_active"]
            ),
            None,
        )

    def get_backup_connections(self, user_id):
        return [
            r
            for r in self.rows
            if r["user_id"] == user_id
            and r["connection_role"] == "BACKUP"
            and r["is_active"]
        ]

    def create(self, **kwargs):
        import uuid

        row = {
            "id": kwargs.pop("id", str(uuid.uuid4())),
            **kwargs,
            "created_at": None,
            "updated_at": None,
        }

        self.rows.append(row)
        return row

    def update(self, connection_id, updates):
        row = self.get_by_id(connection_id)

        if not row:
            return None

        row.update(updates)
        return row

    def set_primary(self, connection_id):
        row = self.get_by_id(connection_id)

        if not row:
            return None

        row["connection_role"] = "PRIMARY"
        row["is_primary"] = True
        return row

    def set_backup(self, connection_id):
        row = self.get_by_id(connection_id)

        if not row:
            return None

        row["connection_role"] = "BACKUP"
        row["is_primary"] = False
        return row

    def deactivate(self, connection_id):
        row = self.get_by_id(connection_id)

        if not row:
            return None

        row["is_active"] = False
        row["is_primary"] = False
        return row

    def activate(self, connection_id):
        row = self.get_by_id(connection_id)

        if not row:
            return None

        row["is_active"] = True
        return row

    def mark_verified(self, connection_id):
        row = self.get_by_id(connection_id)

        if row:
            row["last_verified_at"] = "verified"

        return row

    def mark_error(self, connection_id, error):
        row = self.get_by_id(connection_id)

        if row:
            row["last_error"] = error

        return row


def make_service():
    repo = FakeRepository()
    service = GoogleDriveConnectionService(repo)
    return service, repo


def test_register_primary():
    service, repo = make_service()

    connection = service.register_connection(
        user_id=USER_ID,
        google_email="eventlahsolutions@gmail.com",
        refresh_token="refresh-primary",
        root_folder_id="ROOT_PRIMARY",
        connection_role="PRIMARY",
    )

    assert connection["google_email"] == (
        "eventlahsolutions@gmail.com"
    )
    assert connection["connection_role"] == "PRIMARY"
    assert connection["is_primary"] is True
    assert connection["is_active"] is True

    assert (
        "encrypted_refresh_token"
        not in connection
    )


def test_register_backup():
    service, repo = make_service()

    connection = service.register_connection(
        user_id=USER_ID,
        google_email="samabalah.kenny@gmail.com",
        refresh_token="refresh-backup",
        root_folder_id="ROOT_BACKUP",
        connection_role="BACKUP",
    )

    assert connection["google_email"] == (
        "samabalah.kenny@gmail.com"
    )
    assert connection["connection_role"] == "BACKUP"
    assert connection["is_primary"] is False


def test_second_primary_demotes_first():
    service, repo = make_service()

    first = service.register_connection(
        user_id=USER_ID,
        google_email="eventlahsolutions@gmail.com",
        refresh_token="refresh-1",
        connection_role="PRIMARY",
    )

    second = service.register_connection(
        user_id=USER_ID,
        google_email="samabalah.kenny@gmail.com",
        refresh_token="refresh-2",
        connection_role="PRIMARY",
    )

    first_row = repo.get_by_id(first["id"])
    second_row = repo.get_by_id(second["id"])

    assert first_row["is_primary"] is False
    assert first_row["connection_role"] == "BACKUP"

    assert second_row["is_primary"] is True
    assert second_row["connection_role"] == "PRIMARY"


def test_make_primary_demotes_existing_primary():
    service, repo = make_service()

    first = service.register_connection(
        user_id=USER_ID,
        google_email="eventlahsolutions@gmail.com",
        refresh_token="refresh-1",
        connection_role="PRIMARY",
    )

    second = service.register_connection(
        user_id=USER_ID,
        google_email="samabalah.kenny@gmail.com",
        refresh_token="refresh-2",
        connection_role="BACKUP",
    )

    promoted = service.make_primary(
        USER_ID,
        second["id"],
    )

    assert promoted["is_primary"] is True
    assert promoted["connection_role"] == "PRIMARY"

    first_row = repo.get_by_id(first["id"])

    assert first_row["is_primary"] is False
    assert first_row["connection_role"] == "BACKUP"


def test_make_backup():
    service, repo = make_service()

    connection = service.register_connection(
        user_id=USER_ID,
        google_email="eventlahsolutions@gmail.com",
        refresh_token="refresh",
        connection_role="PRIMARY",
    )

    result = service.make_backup(
        USER_ID,
        connection["id"],
    )

    assert result["is_primary"] is False
    assert result["connection_role"] == "BACKUP"


def test_deactivate_connection():
    service, repo = make_service()

    connection = service.register_connection(
        user_id=USER_ID,
        google_email="eventlahsolutions@gmail.com",
        refresh_token="refresh",
        connection_role="PRIMARY",
    )

    result = service.deactivate(
        USER_ID,
        connection["id"],
    )

    assert result["is_active"] is False
    assert result["is_primary"] is False


def test_activate_connection():
    service, repo = make_service()

    connection = service.register_connection(
        user_id=USER_ID,
        google_email="eventlahsolutions@gmail.com",
        refresh_token="refresh",
        connection_role="PRIMARY",
    )

    service.deactivate(
        USER_ID,
        connection["id"],
    )

    result = service.activate(
        USER_ID,
        connection["id"],
    )

    assert result["is_active"] is True


def test_connection_cannot_be_accessed_by_other_user():
    service, repo = make_service()

    connection = service.register_connection(
        user_id=USER_ID,
        google_email="eventlahsolutions@gmail.com",
        refresh_token="refresh",
        connection_role="PRIMARY",
    )

    other_user = "another-user"

    try:
        service.make_primary(
            other_user,
            connection["id"],
        )
        assert False, "Expected PermissionError"
    except PermissionError:
        pass


def test_list_connections_hides_encrypted_token():
    service, repo = make_service()

    service.register_connection(
        user_id=USER_ID,
        google_email="eventlahsolutions@gmail.com",
        refresh_token="refresh",
        connection_role="PRIMARY",
    )

    service.register_connection(
        user_id=USER_ID,
        google_email="samabalah.kenny@gmail.com",
        refresh_token="backup",
        connection_role="BACKUP",
    )

    connections = service.list_connections(USER_ID)

    assert len(connections) == 2

    for connection in connections:
        assert (
            "encrypted_refresh_token"
            not in connection
        )
        assert "refresh_token" not in connection


def test_only_one_primary_exists():
    service, repo = make_service()

    first = service.register_connection(
        user_id=USER_ID,
        google_email="eventlahsolutions@gmail.com",
        refresh_token="refresh-1",
        connection_role="PRIMARY",
    )

    second = service.register_connection(
        user_id=USER_ID,
        google_email="samabalah.kenny@gmail.com",
        refresh_token="refresh-2",
        connection_role="PRIMARY",
    )

    primaries = [
        row
        for row in repo.list_by_user(USER_ID)
        if row["is_primary"]
    ]

    assert len(primaries) == 1
    assert primaries[0]["id"] == second["id"]