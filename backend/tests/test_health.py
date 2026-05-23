def test_root_returns_backend_health_pointer(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "agenthub-backend",
        "status": "ok",
        "health": "/health",
    }


def test_health_returns_status_and_timestamp(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "agenthub-backend"
    assert body["status"] == "ok"
    assert body["timestamp"].endswith("Z")
