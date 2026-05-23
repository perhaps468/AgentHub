import sys
sys.path.insert(0, '.')
from fastapi.testclient import TestClient
from app.core import database
from app.main import app

database.configure_database('sqlite+pysqlite:///:memory:', create_schema=True)

with TestClient(app) as client:
    resp = client.post('/api/sessions', json={'owner_id': 'test', 'title': 't', 'mode': 'single'})
    sid = resp.json()['id']
    print(f'Session: {sid}')

    import starlette.testclient as tc
    ws = client.websocket_connect(f'/ws/{sid}')
    print(f'WS session type: {type(ws)}')
    print(f'WS has __enter__: {hasattr(ws, "__enter__")}')
    try:
        ws.__enter__()
        print('__enter__ succeeded')
    except Exception as e:
        import traceback
        print(f'__enter__ raised: {type(e).__name__}: {e}')
        traceback.print_exc()

    print(f'WS has portal: {hasattr(ws, "portal")}')
    print(f'WS has _receive_tx: {hasattr(ws, "_receive_tx")}')
    print(f'WS has _send_rx: {hasattr(ws, "_send_rx")}')

    if hasattr(ws, '_receive_tx'):
        rx = ws._receive_tx
        print(f'_receive_tx closed: {rx._closed}')
        print(f'_receive_tx type: {type(rx)}')

    if hasattr(ws, 'portal'):
        print(f'portal: {ws.portal}')
