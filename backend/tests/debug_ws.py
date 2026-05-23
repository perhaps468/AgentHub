import sys
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.core import database
from app.main import app

database.configure_database("sqlite+pysqlite:///:memory:", create_schema=True)


def _override_get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[database.get_db] = _override_get_db

with TestClient(app, raise_server_exceptions=True) as client:
    r = client.post("/api/sessions", json={"owner_id": "dev_user", "title": "Test", "mode": "single"})
    session = r.json()
    print("Session created:", session["id"])

    try:
        with client.websocket_connect(f"/ws/{session['id']}") as ws:
            print("WS connected successfully")
            ws.send_json({"type": "ping"})
            print("WS received:", ws.receive_json())
    except WebSocketDisconnect as e:
        print("WS Disconnect - code:", e.code, "reason:", e.reason)
    except Exception as e:
        print("Error:", type(e).__name__, str(e))
