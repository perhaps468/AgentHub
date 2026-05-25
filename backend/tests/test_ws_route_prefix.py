def test_websocket_is_served_under_ws_prefix(client):
    with client.websocket_connect("/ws/00000000-0000-0000-0000-000000000000") as websocket:
        payload = websocket.receive_json()
        assert payload["type"] == "error"
        assert payload["error_code"] == "session_not_found"
