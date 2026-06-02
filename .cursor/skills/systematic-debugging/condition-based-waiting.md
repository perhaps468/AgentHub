# Condition-Based Waiting

Replace arbitrary timeouts with condition polling.

## The Problem with Arbitrary Waits

```python
# BAD: Random timeout
time.sleep(5)  # Why 5? What if 2 is enough? What if 10 is needed?
```

Problems:
- Too short → flaky tests, race conditions
- Too long → slow execution, wasted time
- Non-deterministic → hard to debug
- No signal → you don't know what you're waiting for

## The Solution: Poll Until Condition

```python
# GOOD: Wait for condition
def wait_until(predicate, timeout=30, interval=0.5):
    """Poll until predicate returns truthy, or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(interval)
    raise TimeoutError(f"Condition not met within {timeout}s")
```

## Usage Patterns

### Pattern 1: Async Resource Ready

```python
# BAD
time.sleep(10)
response = http.get(url)

# GOOD
def is_ready():
    try:
        http.get(url)
        return True
    except ConnectionRefusedError:
        return False

wait_until(is_ready, timeout=30)
response = http.get(url)
```

### Pattern 2: Database State

```python
# BAD
time.sleep(2)
rows = db.query("SELECT * FROM orders WHERE status = 'processed'")

# GOOD
def has_processed_orders():
    count = db.query("SELECT COUNT(*) FROM orders WHERE status = 'processed'")[0]
    return count > 0 if count else False

wait_until(has_processed_orders, timeout=30)
rows = db.query("SELECT * FROM orders WHERE status = 'processed'")
```

### Pattern 3: File System State

```python
# BAD
time.sleep(1)
with open("output.json") as f:
    data = json.load(f)

# GOOD
import os

def file_exists_with_content():
    if not os.path.exists("output.json"):
        return False
    return os.path.getsize("output.json") > 0

wait_until(file_exists_with_content, timeout=10)
with open("output.json") as f:
    data = json.load(f)
```

### Pattern 4: External Process

```python
# BAD
subprocess.run(["build"])
time.sleep(5)

# GOOD
def build_complete():
    return os.path.exists("dist/bundle.js")

proc = subprocess.Popen(["build"])
wait_until(build_complete, timeout=120)
```

## Timeout Selection

| Context | Typical Timeout | Rationale |
|---------|-----------------|-----------|
| Local operation | 5-10s | Should complete quickly |
| Network call | 30s | Accounts for latency |
| Background job | 60-120s | May involve queueing |
| Heavy computation | 300s+ | Machine learning, builds |

## Error Messages

Always include what condition failed:

```python
raise TimeoutError(
    f"Condition not met within {timeout}s. "
    f"Expected: {expected_description}, "
    f"Last check returned: {last_result}"
)
```

## Anti-Pattern: Nested Waits

```python
# BAD: Waiting for something that waits internally
time.sleep(10)
response = service.fetch()
if response.needs_processing:
    time.sleep(5)  # Already waiting inside!
    service.process()
```

**Fix:** Remove nested waits. Each operation should either poll its own condition or return immediately with status.
