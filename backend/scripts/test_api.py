import httpx

# Test health
r = httpx.get("http://127.0.0.1:8088/health", timeout=10)
print("=== /health ===")
print(r.status_code, r.text)

# Test agents
r = httpx.get("http://127.0.0.1:8088/api/agents/default", timeout=10)
print("\n=== /api/agents/default ===")
print(r.status_code, r.text)

# Test sessions
r = httpx.post(
    "http://127.0.0.1:8088/api/sessions",
    json={"owner_id": "test_user", "mode": "single"},
    timeout=10
)
print("\n=== POST /api/sessions ===")
print(r.status_code, r.text)
session_id = r.json()["id"]

# Test message history
r = httpx.get(f"http://127.0.0.1:8088/api/sessions/{session_id}/messages", timeout=10)
print("\n=== GET messages ===")
print(r.status_code, r.text)
