def create_session(client, **overrides):
    payload = {"owner_id": "dev_user", "title": "New Session", "mode": "single"}
    payload.update(overrides)
    response = client.post("/api/sessions", json=payload)
    assert response.status_code == 201
    return response.json()


def test_create_session_can_be_read_from_detail_and_list(client):
    created = create_session(client)

    detail = client.get(f"/api/sessions/{created['id']}")
    assert detail.status_code == 200
    assert detail.json() == created

    listing = client.get("/api/sessions", params={"owner_id": "dev_user"})
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["has_more"] is False
    assert body["items"] == [created]


def test_create_session_validates_required_owner_and_mode(client):
    missing_owner = client.post("/api/sessions", json={"title": "x", "mode": "single"})
    invalid_mode = client.post(
        "/api/sessions",
        json={"owner_id": "dev_user", "title": "x", "mode": "invalid"},
    )

    assert missing_owner.status_code == 400
    assert invalid_mode.status_code == 400


def test_patch_updates_session_fields_and_archived_filter(client):
    created = create_session(client)

    patched = client.patch(
        f"/api/sessions/{created['id']}",
        json={"title": "Updated", "is_pinned": True, "is_archived": True},
    )
    assert patched.status_code == 200
    patched_body = patched.json()
    assert patched_body["title"] == "Updated"
    assert patched_body["is_pinned"] is True
    assert patched_body["is_archived"] is True

    default_listing = client.get("/api/sessions", params={"owner_id": "dev_user"})
    assert default_listing.json()["items"] == []

    archived_listing = client.get(
        "/api/sessions",
        params={"owner_id": "dev_user", "include_archived": "true"},
    )
    assert archived_listing.json()["items"] == [patched_body]

    restored = client.patch(
        f"/api/sessions/{created['id']}",
        json={"is_archived": False},
    )
    assert restored.status_code == 200
    active_listing = client.get("/api/sessions", params={"owner_id": "dev_user"})
    assert active_listing.json()["items"] == [restored.json()]


def test_patch_rejects_empty_body_and_missing_session(client):
    created = create_session(client)

    empty_patch = client.patch(f"/api/sessions/{created['id']}", json={})
    missing_patch = client.patch(
        "/api/sessions/00000000-0000-0000-0000-000000000000",
        json={"title": "Nope"},
    )

    assert empty_patch.status_code == 400
    assert missing_patch.status_code == 404


def test_delete_archives_session_without_removing_history(client):
    created = create_session(client)

    deleted = client.delete(f"/api/sessions/{created['id']}")

    assert deleted.status_code == 200
    assert deleted.json() == {
        "archived": True,
        "mode": "archive_alias",
        "session_id": created["id"],
    }
    detail = client.get(f"/api/sessions/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["is_archived"] is True


def test_message_history_requires_existing_session_and_paginates(client):
    created = create_session(client)

    missing = client.get(
        "/api/sessions/00000000-0000-0000-0000-000000000000/messages"
    )
    invalid_page = client.get(
        f"/api/sessions/{created['id']}/messages",
        params={"page": 0},
    )
    empty_history = client.get(f"/api/sessions/{created['id']}/messages")

    assert missing.status_code == 404
    assert invalid_page.status_code == 400
    assert empty_history.status_code == 200
    assert empty_history.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
        "has_more": False,
    }
