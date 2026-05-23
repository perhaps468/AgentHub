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

    import starlette.testclient as tc
    ws = client.websocket_connect("/ws/" + sid)

    # Manually enter to see what happens
    import starlette.websockets as ws_lib

    # Patch receive to see all messages before raise
    orig_raise = ws._raise_on_close
    received_messages = []
    def patch_raise(msg):
        received_messages.append(msg)
        print("Message before raise:", msg)
        orig_raise(msg)
    ws._raise_on_close = patch_raise

    try:
        ws.__enter__()
        print("__enter__ OK")
    except ws_lib.WebSocketDisconnect as e:
        print("Disconnected:", e.code, e.reason)
    except Exception as e:
        import traceback
        print("Other error:", type(e).__name__)
        traceback.print_exc()

    print("All messages:", received_messages)
