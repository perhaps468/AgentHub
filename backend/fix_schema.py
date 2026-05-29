import socket
import time

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5)
try:
    sock.connect(('127.0.0.1', 8088))
    request = b'GET /api/sessions/4eca00cd-0921-49db-9b82-bd46af76836e/messages?page=1&page_size=5 HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n'
    print("Sending...")
    sock.sendall(request)
    print("Receiving...")
    data = b''
    start = time.time()
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        except socket.timeout:
            break
    print(f"Got {len(data)} bytes in {time.time() - start:.2f}s")
    print(data.decode(errors='replace')[:500])
finally:
    sock.close()
