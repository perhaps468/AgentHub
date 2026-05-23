import sys
sys.path.insert(0, ".")
from fastapi.testclient import TestClient
from app.core import database
from app.main import app

database.configure_database("sqlite+pysqlite:///:memory:", create_schema=True)

with TestClient(app) as client:
    resp = client.post("/api/sessions", json={"owner_id": "test", "title": "t", "mode": "single"})
    sid = resp.json()["id"]
    print("Session:", sid)

    ws = client.websocket_connect("/ws/" + sid)
    print("WS type:", type(ws).__name__)

    try:
        ws.__enter__()
        print("__enter__ OK")
    except Exception as e:
        import traceback
        print("__enter__ failed:", type(e).__name__, str(e)[:200])
        traceback.print_exc()

    print("has portal:", hasattr(ws, "portal"))
    print("has _receive_tx:", hasattr(ws, "_receive_tx"))

    if hasattr(ws, "_receive_tx"):
        rx = ws._receive_tx
        print("_receive_tx closed:", rx._closed)
        print("_receive_tx type:", type(rx).__name__)
