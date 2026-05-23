"""P1-1-4: GET /api/agents/default 接口测试。"""

import pytest


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.core import database
    from app.main import app

    database.configure_database("sqlite+pysqlite:///:memory:", create_schema=True)
    with TestClient(app) as test_client:
        yield test_client
    database.Base.metadata.drop_all(bind=database.engine)


class TestDefaultAgentEndpoint:
    def test_returns_pm_agent_id(self, client):
        response = client.get("/api/agents/default")
        assert response.status_code == 200
        assert response.json()["id"] == "pm_agent"

    def test_returns_pm_agent_name(self, client):
        response = client.get("/api/agents/default")
        assert response.json()["name"] == "PM Agent"

    def test_returns_pm_role(self, client):
        response = client.get("/api/agents/default")
        assert response.json()["role"] == "PM"

    def test_returns_avatar_url(self, client):
        response = client.get("/api/agents/default")
        data = response.json()
        assert "avatar_url" in data
        assert data["avatar_url"] is None

    def test_response_has_exactly_four_fields(self, client):
        response = client.get("/api/agents/default")
        data = response.json()
        assert set(data.keys()) == {"id", "name", "role", "avatar_url"}

    def test_response_excludes_model(self, client):
        response = client.get("/api/agents/default")
        data = response.json()
        assert "model" not in data

    def test_response_excludes_system_prompt(self, client):
        response = client.get("/api/agents/default")
        data = response.json()
        assert "system_prompt" not in data

    def test_response_excludes_provider(self, client):
        response = client.get("/api/agents/default")
        data = response.json()
        assert "provider" not in data

    def test_no_auth_required(self, client):
        """P1 阶段无 Auth。"""
        response = client.get("/api/agents/default")
        assert response.status_code == 200
