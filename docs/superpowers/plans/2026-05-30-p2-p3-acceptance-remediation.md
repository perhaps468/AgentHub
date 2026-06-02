# P2 P3 Acceptance Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining P2/P3 acceptance gaps defined in `openspec/docs/migration/06-p2-p3-acceptance-closure.md` so Runtime, workspace, diff/command flow, preview, and self-repair all run on the formal production path.

**Architecture:** Keep the current Runtime-centric design and finish the missing formal links instead of rebuilding subsystems. The work is sequenced as Task A replay closure, Task C event closure, Task D runtime closure, and final spec/progress writeback, while preserving Task B's existing workspace model and tightening its validation where needed.

**Tech Stack:** FastAPI, SQLAlchemy, Python runtime tools, Vue 3, TypeScript, pytest, Vitest.

---

## File Structure

- Modify: `backend/app/api/ws.py`
  Runtime WebSocket protocol bridge. Must become the single formal event transport for runtime, apply, command, preview, and repair events.
- Modify: `backend/app/runtime/runtime_agent_service.py`
  Runtime orchestration entrypoint. Must emit structured runtime events and stop depending on legacy fallback for normal operation.
- Modify: `backend/app/runtime/event_bridge.py`
  Runtime event definitions and bridge routing. Must route all formal event types end-to-end, not just type declarations.
- Modify: `backend/app/api/pending_changes.py`
  Confirm/apply entrypoint. Must emit `apply_result` into the same observable runtime path.
- Modify: `backend/app/runtime/tools/run_command_tool.py`
  Command execution tool. Must return structured data usable for `command_result` events instead of only formatted text.
- Create: `backend/app/runtime/command_result.py`
  Small parser/formatter module to convert command execution output into a typed payload used by runtime and WS.
- Modify: `backend/app/runtime/repair_state.py`
  Existing state machine definitions. Must be consumed by the runtime loop and surface event payloads.
- Modify: `frontend/src/utils/useChatStreamState.ts`
  Frontend runtime stream state. Must preserve replay nodes on persisted messages and consume apply/command/preview/repair events.
- Modify: `frontend/src/components/zhu.vue`
  Main session UI event consumer. Must wire all new WS events into store state and PreviewPanel.
- Modify: `frontend/src/components/zhu/PreviewPanel.vue`
  Preview UI. Must become data-driven from `preview_result` instead of placeholder-only rendering.
- Modify: `frontend/src/types/agenthub.ts`
  Shared frontend event and message metadata types for runtime replay, preview, apply result, command result, and repair state.
- Modify: `backend/tests/runtime/test_runtime_agent_service.py`
  Runtime service coverage for replay persistence and formal runtime path behavior.
- Modify: `backend/tests/runtime/test_diff_preview_self_repair.py`
  Backend acceptance tests for apply/command/preview/repair events.
- Modify: `backend/tests/api/test_ws.py`
  WS forwarding coverage for new event types.
- Modify: `frontend/src/components/zhu.spec.ts`
  Frontend session-level event handling coverage.
- Modify: `frontend/src/components/Chat-input-area.spec.ts`
  Existing chat flow regression coverage if message event handling changes affect send lifecycle.
- Modify: `frontend/src/utils/useChatStreamState.spec.ts`
  Replay persistence and event consumption coverage.
- Modify: `openspec/docs/migration/05-roadmap-and-progress.md`
  Progress writeback after implementation.
- Modify: `openspec/docs/migration/06-p2-p3-acceptance-closure.md`
  Write back final closure status and key decisions after verification.

## Execution Order

1. Task 1 closes Task A replay and removes the remaining P2 ambiguity.
2. Task 2 closes Task C formal event flow for apply and command execution.
3. Task 3 closes Task D preview and self-repair runtime wiring.
4. Task 4 performs acceptance verification and writes status back into spec/progress docs.

## Task 1: Close P2 Runtime Replay And Formal Runtime Path

**Files:**
- Modify: `backend/app/api/ws.py`
- Modify: `backend/app/runtime/runtime_agent_service.py`
- Modify: `frontend/src/utils/useChatStreamState.ts`
- Modify: `frontend/src/components/zhu.vue`
- Modify: `frontend/src/types/agenthub.ts`
- Modify: `backend/tests/runtime/test_runtime_agent_service.py`
- Modify: `backend/tests/api/test_ws.py`
- Modify: `frontend/src/utils/useChatStreamState.spec.ts`

- [ ] **Step 1: Write the failing backend test for formal runtime-only behavior**

```python
def test_ws_runtime_path_emits_runtime_events_when_runtime_enabled(client, monkeypatch, auth_token):
    monkeypatch.setenv("RUNTIME_USE_RUNTIME_AGENT", "1")

    with client.websocket_connect(f"/ws/session-1?x-token={auth_token}") as ws:
        ws.send_json({"action": "send_message", "session_id": "session-1", "content": "inspect file"})
        event_types = [ws.receive_json()["type"] for _ in range(5)]

    assert "message_start" in event_types
    assert "runtime_state" in event_types
    assert "message_end" in event_types
```

- [ ] **Step 2: Run backend WS test to verify current gap**

Run: `C:\Users\lx\AppData\Local\Programs\Python\Python313\python.exe -m pytest backend/tests/api/test_ws.py -k runtime_path -v`
Expected: FAIL because replay/runtime-only assertions are incomplete or the test does not exist yet.

- [ ] **Step 3: Write the failing frontend replay persistence test**

```ts
it('persists runtime replay nodes onto the final assistant message', () => {
  const state = useChatStreamState()

  state.handleMessageStart({
    type: 'message_start',
    stream_id: 'stream-1',
    agent_role: 'PM',
    message: { id: 'msg-1', session_id: 's-1', sender_type: 'agent', sender_role: 'PM', type: 'text', content: '', payload: {}, metadata: {}, status: 'streaming', created_at: '2026-05-30T00:00:00Z' },
  }, 's-1')

  state.handleRuntimeState({ type: 'runtime_state', stream_id: 'stream-1', message_id: 'msg-1', state: 'thinking', timestamp: '2026-05-30T00:00:01Z' }, 's-1')
  const finished = state.handleMessageEnd({ type: 'message_end', stream_id: 'stream-1', message_id: 'msg-1', status: 'completed', final_content: 'done' }, 's-1')

  expect(finished?.runtime_nodes).toHaveLength(1)
  expect(finished?.runtime_nodes[0]?.node_type).toBe('runtime_state')
})
```

- [ ] **Step 4: Run frontend replay test to verify it fails**

Run: `powershell -Command "& '.\node_modules\.bin\vitest.CMD' run frontend\src\utils\useChatStreamState.spec.ts"`
Expected: FAIL because `handleMessageEnd()` currently finalizes the stream without preserving replay metadata on the persisted result.

- [ ] **Step 5: Implement runtime replay persistence and single formal runtime path**

```python
# backend/app/runtime/runtime_agent_service.py
def _finalize_agent_message(self, status: str, final_content: str | None = None) -> None:
    if self._agent_message is None:
        return

    final_text = final_content if final_content is not None else self._accumulated_content
    runtime_nodes = getattr(self._bridge, "replay_nodes", [])

    metadata = dict(self._agent_message.msg_metadata or {})
    metadata["runtime_replay"] = runtime_nodes
    metadata["runtime_path"] = "runtime_agent_service"

    self._agent_message.content = final_text
    self._agent_message.payload = {"text": final_text}
    self._agent_message.msg_metadata = metadata
    self._agent_message.status = status
    self.db.add(self._agent_message)
    self.db.commit()
```

```python
# backend/app/runtime/event_bridge.py
self._replay_nodes: list[dict[str, Any]] = []

def _push_replay_node(self, node: dict[str, Any]) -> None:
    self._replay_nodes.append(node)

@property
def replay_nodes(self) -> list[dict[str, Any]]:
    return list(self._replay_nodes)
```

```ts
// frontend/src/utils/useChatStreamState.ts
return {
  stream_id: stream.stream_id,
  message_id: stream.message_id,
  session_id: stream.session_id,
  sender_role: stream.sender_role,
  accumulated_content: stream.accumulated_content,
  type: stream.type,
  payload: stream.payload,
  metadata: {
    ...(stream.metadata || {}),
    runtime_replay: [...stream.runtime_nodes],
    runtime_state: stream.runtime_state,
  },
  runtime_nodes: [...stream.runtime_nodes],
  created_at: stream.created_at,
}
```

- [ ] **Step 6: Tighten WS handling so runtime is the default production path**

```python
# backend/app/api/ws.py
def runtime_use_runtime_agent() -> bool:
    load_env_file()
    return os.getenv("RUNTIME_USE_RUNTIME_AGENT", "1") in ("1", "true", "True")
```

```python
# backend/app/api/ws.py
if not runtime_use_runtime_agent():
    await _send_error(
        websocket,
        "legacy_runtime_disabled",
        "Legacy responder path is disabled for acceptance closure verification",
        stream_id=stream_id,
        agent_role=agent.role,
    )
    continue
```

- [ ] **Step 7: Run focused backend tests**

Run: `C:\Users\lx\AppData\Local\Programs\Python\Python313\python.exe -m pytest backend/tests/runtime/test_runtime_agent_service.py backend/tests/api/test_ws.py -v`
Expected: PASS

- [ ] **Step 8: Run focused frontend tests**

Run: `powershell -Command "& '.\node_modules\.bin\vitest.CMD' run frontend\src\utils\useChatStreamState.spec.ts frontend\src\components\zhu.spec.ts"`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/api/ws.py backend/app/runtime/runtime_agent_service.py backend/app/runtime/event_bridge.py frontend/src/utils/useChatStreamState.ts frontend/src/components/zhu.vue frontend/src/types/agenthub.ts backend/tests/runtime/test_runtime_agent_service.py backend/tests/api/test_ws.py frontend/src/utils/useChatStreamState.spec.ts frontend/src/components/zhu.spec.ts
git commit -m "feat: persist runtime replay and enforce runtime path"
```

## Task 2: Close Diff Apply And Command Result Formal Event Flow

**Files:**
- Modify: `backend/app/api/pending_changes.py`
- Modify: `backend/app/api/ws.py`
- Modify: `backend/app/runtime/event_bridge.py`
- Modify: `backend/app/runtime/tools/run_command_tool.py`
- Create: `backend/app/runtime/command_result.py`
- Modify: `backend/app/runtime/runtime_agent_service.py`
- Modify: `frontend/src/utils/useChatStreamState.ts`
- Modify: `frontend/src/components/zhu.vue`
- Modify: `frontend/src/types/agenthub.ts`
- Modify: `backend/tests/runtime/test_diff_preview_self_repair.py`
- Modify: `backend/tests/api/test_ws.py`

- [ ] **Step 1: Write failing backend test for apply confirmation event**

```python
def test_apply_pending_change_returns_apply_result_event_payload(client, auth_headers, seeded_pending_change):
    response = client.post(
        "/api/pending-changes/apply",
        headers=auth_headers,
        json={"change_id": seeded_pending_change.change_id, "session_id": "session-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "applied"
    assert body["event"]["type"] == "apply_result"
    assert body["event"]["change_id"] == seeded_pending_change.change_id
```

- [ ] **Step 2: Run pending change backend test to verify it fails**

Run: `C:\Users\lx\AppData\Local\Programs\Python\Python313\python.exe -m pytest backend/tests/runtime/test_diff_preview_self_repair.py -k apply_result -v`
Expected: FAIL because the API currently returns plain REST JSON without a formal event payload.

- [ ] **Step 3: Write failing backend test for command result parsing**

```python
def test_run_command_tool_returns_structured_command_result():
    tool = RunCommandTool(workspace_root="D:/code/ZiJieAI/AgentHub")
    result = tool.execute(command="python --version", cwd=".", timeout_seconds=30)

    assert isinstance(result, dict)
    assert result["type"] == "command_result"
    assert "stdout" in result
    assert "exit_code" in result
```

- [ ] **Step 4: Run command result backend test to verify it fails**

Run: `C:\Users\lx\AppData\Local\Programs\Python\Python313\python.exe -m pytest backend/tests/runtime/test_diff_preview_self_repair.py -k command_result -v`
Expected: FAIL because `RunCommandTool.execute()` currently returns formatted text.

- [ ] **Step 5: Implement shared command result payload**

```python
# backend/app/runtime/command_result.py
from dataclasses import dataclass

@dataclass
class CommandResultPayload:
    type: str
    command: str
    cwd: str
    stdout: str
    stderr: str
    exit_code: int
    success: bool
    timed_out: bool

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "command": self.command,
            "cwd": self.cwd,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "success": self.success,
            "timed_out": self.timed_out,
        }
```

- [ ] **Step 6: Convert `RunCommandTool` to return structured payload first, text second**

```python
# backend/app/runtime/tools/run_command_tool.py
from app.runtime.command_result import CommandResultPayload

def _build_payload(...):
    return CommandResultPayload(
        type="command_result",
        command=command,
        cwd=cwd,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        success=success,
        timed_out=timed_out,
    )

def execute(...):
    payload = self._build_payload(...)
    return payload.to_dict()
```

- [ ] **Step 7: Emit `apply_result` and `command_result` through the formal WS path**

```python
# backend/app/api/pending_changes.py
event = {
    "type": "apply_result",
    "change_id": change_id,
    "success": success,
    "status": "applied" if success else "rejected",
    "message": message,
}

return ApplyChangeResponse(
    success=success,
    change_id=change_id,
    message=message,
    status=event["status"],
    event=event,
)
```

```python
# backend/app/runtime/event_bridge.py
elif event_type == "command_result":
    self._emit_command_result(data)
```

```python
# backend/app/api/ws.py
elif event.type == "command_result":
    await websocket.send_json(event.to_dict())
elif event.type == "apply_result":
    await websocket.send_json(event.to_dict())
```

- [ ] **Step 8: Update frontend consumers for apply and command results**

```ts
// frontend/src/types/agenthub.ts
export interface CommandResultEvent {
  type: 'command_result'
  command: string
  cwd: string
  stdout: string
  stderr: string
  exit_code: number
  success: boolean
  timed_out: boolean
  stream_id?: string
  message_id?: string
  timestamp?: string
}
```

```ts
// frontend/src/utils/useChatStreamState.ts
function handleCommandResult(event: CommandResultEvent) {
  return {
    command: event.command,
    cwd: event.cwd,
    exit_code: event.exit_code,
    success: event.success,
    stdout: event.stdout,
    stderr: event.stderr,
  }
}
```

- [ ] **Step 9: Run backend acceptance tests**

Run: `C:\Users\lx\AppData\Local\Programs\Python\Python313\python.exe -m pytest backend/tests/runtime/test_diff_preview_self_repair.py backend/tests/api/test_ws.py -v`
Expected: PASS

- [ ] **Step 10: Run frontend event handling tests**

Run: `powershell -Command "& '.\node_modules\.bin\vitest.CMD' run frontend\src\utils\useChatStreamState.spec.ts frontend\src\components\zhu.spec.ts"`
Expected: PASS

- [ ] **Step 11: Commit**

```bash
git add backend/app/api/pending_changes.py backend/app/api/ws.py backend/app/runtime/event_bridge.py backend/app/runtime/tools/run_command_tool.py backend/app/runtime/command_result.py backend/app/runtime/runtime_agent_service.py frontend/src/utils/useChatStreamState.ts frontend/src/components/zhu.vue frontend/src/types/agenthub.ts backend/tests/runtime/test_diff_preview_self_repair.py backend/tests/api/test_ws.py
git commit -m "feat: formalize apply and command runtime events"
```

## Task 3: Close Preview And Self-Repair Runtime Flow

**Files:**
- Modify: `backend/app/runtime/event_bridge.py`
- Modify: `backend/app/runtime/runtime_agent_service.py`
- Modify: `backend/app/runtime/repair_state.py`
- Modify: `backend/app/api/ws.py`
- Modify: `frontend/src/components/zhu/PreviewPanel.vue`
- Modify: `frontend/src/components/zhu.vue`
- Modify: `frontend/src/utils/useChatStreamState.ts`
- Modify: `frontend/src/types/agenthub.ts`
- Modify: `backend/tests/runtime/test_diff_preview_self_repair.py`
- Modify: `frontend/src/components/zhu.spec.ts`

- [ ] **Step 1: Write failing preview WS test**

```python
def test_preview_result_is_forwarded_to_ws_client(client, auth_token):
    with client.websocket_connect(f"/ws/session-1?x-token={auth_token}") as ws:
        preview_event = {
            "type": "preview_result",
            "preview_id": "preview-1",
            "workspace_id": "ws-1",
            "preview_url": "http://localhost:4173/preview/preview-1",
            "status": "ready",
            "message_id": "msg-1",
            "stream_id": "stream-1",
            "timestamp": "2026-05-30T00:00:00Z",
        }
        ws.app.state.preview_test_event = preview_event
        event = ws.receive_json()

    assert event["type"] == "preview_result"
```

- [ ] **Step 2: Run preview WS test to verify it fails**

Run: `C:\Users\lx\AppData\Local\Programs\Python\Python313\python.exe -m pytest backend/tests/api/test_ws.py -k preview_result -v`
Expected: FAIL because `ws.py` does not yet forward `preview_result`.

- [ ] **Step 3: Write failing frontend PreviewPanel test**

```ts
it('renders preview iframe when preview_result arrives', async () => {
  const wrapper = mount(PreviewPanel, {
    props: {
      previewState: {
        type: 'web',
        title: 'Preview',
        url: 'http://localhost:4173/preview/preview-1',
      },
    },
  })

  expect(wrapper.find('iframe').attributes('src')).toBe('http://localhost:4173/preview/preview-1')
})
```

- [ ] **Step 4: Run PreviewPanel test to verify current mismatch**

Run: `powershell -Command "& '.\node_modules\.bin\vitest.CMD' run frontend\src\components\zhu.spec.ts"`
Expected: FAIL or missing coverage because preview event data is not wired into `previewState`.

- [ ] **Step 5: Wire preview result into WS and frontend**

```python
# backend/app/api/ws.py
elif event.type == "preview_result":
    await websocket.send_json(event.to_dict())
```

```ts
// frontend/src/components/zhu.vue
} else if (msg.type === 'preview_result') {
  previewState.value = {
    type: 'web',
    title: 'Runtime Preview',
    url: msg.preview_url || '',
    description: msg.status || 'ready',
  }
```

- [ ] **Step 6: Integrate self-repair state machine with runtime event emission**

```python
# backend/app/runtime/runtime_agent_service.py
from app.runtime.repair_state import RepairState, RepairStateMachine

self._repair_state = RepairStateMachine()

def _emit_repair_state(self, state: RepairState, message: str) -> None:
    self._repair_state.transition(state)
    event = self._repair_state.get_event(message=message)
    self._event_queue.put_nowait(("repair_state", event.to_dict()))
```

```python
# backend/app/runtime/event_bridge.py
elif event_type == "repair_state":
    self._emit_repair_state(data)
```

- [ ] **Step 7: Forward `repair_state` in WS and consume it in frontend**

```python
# backend/app/api/ws.py
elif event.type == "repair_state":
    await websocket.send_json(event)
```

```ts
// frontend/src/utils/useChatStreamState.ts
function handleRepairState(event: RepairStateEventData) {
  repairState.value = {
    state: event.state,
    attempt: event.attempt,
    maxAttempts: event.max_attempts,
    message: event.message,
  }
}
```

- [ ] **Step 8: Run backend repair/preview tests**

Run: `C:\Users\lx\AppData\Local\Programs\Python\Python313\python.exe -m pytest backend/tests/runtime/test_diff_preview_self_repair.py backend/tests/api/test_ws.py -v`
Expected: PASS

- [ ] **Step 9: Run frontend preview/repair tests**

Run: `powershell -Command "& '.\node_modules\.bin\vitest.CMD' run frontend\src\components\zhu.spec.ts frontend\src\utils\useChatStreamState.spec.ts"`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/runtime/event_bridge.py backend/app/runtime/runtime_agent_service.py backend/app/runtime/repair_state.py backend/app/api/ws.py frontend/src/components/zhu/PreviewPanel.vue frontend/src/components/zhu.vue frontend/src/utils/useChatStreamState.ts frontend/src/types/agenthub.ts backend/tests/runtime/test_diff_preview_self_repair.py frontend/src/components/zhu.spec.ts
git commit -m "feat: wire preview and repair runtime flows"
```

## Task 4: Acceptance Verification And Spec Writeback

**Files:**
- Modify: `openspec/docs/migration/05-roadmap-and-progress.md`
- Modify: `openspec/docs/migration/06-p2-p3-acceptance-closure.md`

- [ ] **Step 1: Run backend regression suite for touched runtime areas**

Run: `C:\Users\lx\AppData\Local\Programs\Python\Python313\python.exe -m pytest backend/tests/runtime/test_runtime_agent_service.py backend/tests/runtime/test_diff_preview_self_repair.py backend/tests/api/test_ws.py -v`
Expected: PASS

- [ ] **Step 2: Run frontend regression suite for touched stream/UI areas**

Run: `powershell -Command "& '.\node_modules\.bin\vitest.CMD' run frontend\src\utils\useChatStreamState.spec.ts frontend\src\components\zhu.spec.ts frontend\src\components\Login.spec.ts frontend\src\veiws\Chat-input-area.spec.ts"`
Expected: PASS

- [ ] **Step 3: Update roadmap/progress doc with closure status**

```md
## P2 / P3 Acceptance Closure

- P2 Runtime events now run on the formal runtime path and persist replay metadata on final assistant messages.
- P3 apply confirmation, command execution, preview, and repair state all emit structured runtime/WS events.
- Legacy responder fallback remains feature-gated for rollback only and is no longer the default business path.
```

- [ ] **Step 4: Update acceptance closure doc with final status**

```md
## Closure Status

- Task A: completed
- Task B: completed
- Task C: completed
- Task D: completed

## Verification Evidence

- Backend runtime/WS acceptance tests passed on 2026-05-30.
- Frontend stream/preview/repair tests passed on 2026-05-30.
- No remaining temporary bypass path is required for normal P2/P3 execution.
```

- [ ] **Step 5: Run doc sanity check**

Run: `powershell -Command "Get-Content openspec/docs/migration/05-roadmap-and-progress.md; Get-Content openspec/docs/migration/06-p2-p3-acceptance-closure.md"`
Expected: updated status sections are present and reference the final implemented behavior.

- [ ] **Step 6: Commit**

```bash
git add openspec/docs/migration/05-roadmap-and-progress.md openspec/docs/migration/06-p2-p3-acceptance-closure.md
git commit -m "docs: record p2 p3 acceptance closure"
```

## Acceptance Checklist

- [ ] `ws.py` forwards `message_*`, `runtime_state`, `tool_event`, `change_preview`, `apply_result`, `command_result`, `preview_result`, and `repair_state`.
- [ ] Final persisted assistant messages contain runtime replay metadata.
- [ ] New sessions require formal `workspace_id` binding and runtime resolves workspace from session binding first.
- [ ] Apply flow cannot bypass structured preview and emits a formal result event.
- [ ] Command execution results are structured and observable by runtime and frontend.
- [ ] PreviewPanel renders runtime-driven preview data instead of placeholder-only content.
- [ ] Self-repair exposes bounded retry state through the runtime event stream.
- [ ] `05-roadmap-and-progress.md` and `06-p2-p3-acceptance-closure.md` are updated after verification.

## Open Risks To Watch During Implementation

- Preserving rollback capability while making runtime the default path can accidentally break local developer flows if tests still assume `FixedAgentResponder`.
- Persisting replay metadata on messages must avoid inflating payload size uncontrollably; store only minimal nodes.
- `RunCommandTool` return-shape changes can break existing agent prompt assumptions if callers still expect plain text.
- Preview wiring must stop short of introducing a P4 artifact platform abstraction; keep it minimal and session-scoped.
