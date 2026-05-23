def create_session(client):
    response = client.post(
        "/api/sessions",
        json={"owner_id": "dev_user", "title": "New Session", "mode": "single"},
    )
    assert response.status_code == 201
    return response.json()


def test_websocket_ping_pong(client):
    session = create_session(client)

    with client.websocket_connect(f"/ws/{session['id']}") as websocket:
        websocket.send_json({"type": "ping"})
        assert websocket.receive_json() == {"type": "pong"}


def test_websocket_ping_pong_does_not_persist_messages(client):
    session = create_session(client)

    with client.websocket_connect(f"/ws/{session['id']}") as websocket:
        websocket.send_json({"type": "ping"})
        assert websocket.receive_json() == {"type": "pong"}

        websocket.send_json({"type": "ping"})
        assert websocket.receive_json() == {"type": "pong"}

    history = client.get(f"/api/sessions/{session['id']}/messages")
    assert history.status_code == 200
    assert history.json()["items"] == []


def test_websocket_send_message_persists_human_and_echo_messages(client):
    session = create_session(client)

    with client.websocket_connect(f"/ws/{session['id']}") as websocket:
        websocket.send_json(
            {
                "action": "send_message",
                "session_id": session["id"],
                "content": "hello",
            }
        )
        pushed = websocket.receive_json()

    assert pushed["type"] == "chat_stream"
    assert pushed["session_id"] == session["id"]
    assert pushed["sender_type"] == "agent"
    assert pushed["sender_role"] == "PM"
    assert pushed["content"] == "Echo: hello"
    assert pushed["content_type"] == "text"

    history = client.get(f"/api/sessions/{session['id']}/messages")
    assert history.status_code == 200
    messages = history.json()["items"]
    assert [message["sender_type"] for message in messages] == ["human", "agent"]
    assert [message["content"] for message in messages] == ["hello", "Echo: hello"]


def test_websocket_send_message_moves_session_to_top_of_list(client):
    first = create_session(client)
    second = create_session(client)

    with client.websocket_connect(f"/ws/{first['id']}") as websocket:
        websocket.send_json(
            {
                "action": "send_message",
                "session_id": first["id"],
                "content": "bring me forward",
            }
        )
        websocket.receive_json()

    listing = client.get("/api/sessions", params={"owner_id": "dev_user"})
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()["items"]] == [first["id"], second["id"]]


def test_websocket_returns_error_for_invalid_message(client):
    session = create_session(client)

    with client.websocket_connect(f"/ws/{session['id']}") as websocket:
        websocket.send_json({"action": "send_message", "session_id": session["id"]})
        error = websocket.receive_json()

    assert error == {
        "type": "error",
        "error_code": "invalid_request",
        "error_message": "Invalid request",
    }


def test_websocket_returns_invalid_request_for_malformed_json_and_stays_usable(client):
    session = create_session(client)

    with client.websocket_connect(f"/ws/{session['id']}") as websocket:
        websocket.send_text("not-json")
        error = websocket.receive_json()

        websocket.send_json({"type": "ping"})
        pong = websocket.receive_json()

    assert error == {
        "type": "error",
        "error_code": "invalid_request",
        "error_message": "Invalid request",
    }
    assert pong == {"type": "pong"}


def test_websocket_missing_session_reports_error(client):
    missing_id = "00000000-0000-0000-0000-000000000000"

    with client.websocket_connect(f"/ws/{missing_id}") as websocket:
        error = websocket.receive_json()

    assert error == {
        "type": "error",
        "error_code": "session_not_found",
        "error_message": "Session not found",
    }


def test_websocket_reconnects_to_same_session_and_still_streams_echo(client):
    session = create_session(client)

    with client.websocket_connect(f"/ws/{session['id']}"):
        pass

    with client.websocket_connect(f"/ws/{session['id']}") as websocket:
        websocket.send_json(
            {
                "action": "send_message",
                "session_id": session["id"],
                "content": "hello again",
            }
        )
        pushed = websocket.receive_json()

    assert pushed["type"] == "chat_stream"
    assert pushed["session_id"] == session["id"]
    assert pushed["content"] == "Echo: hello again"
