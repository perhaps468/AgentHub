import re

with open('D:/code/ZiJieAI/AgentHub/backend/tests/api/test_ws_runtime_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace test methods - use regex to find and replace
old_pattern = r'    def test_runtime_path_emits_message_start\(self\):.*?(?=\n\n    def test_runtime_path_emits_message_delta|class _MockWebSocketForWS|\n# ---)'

# Build replacement with explicit string concatenation to avoid f-string issues
def make_new_tests():
    lines = []
    lines.append('    def test_runtime_path_emits_message_start(self, _e2e_env):')
    lines.append('        session_id, db, token = _e2e_env')
    lines.append('        try:')
    lines.append('            msgs = self._run_ws_runtime_flow(session_id, token, db, "hello runtime")')
    lines.append('            assert len(msgs) > 0, "No WS messages sent. Got: " + str(msgs)')
    lines.append('            assert msgs[0]["type"] == "message_start", "Expected message_start, got " + msgs[0]["type"]')
    lines.append('        finally:')
    lines.append('            db.close()')
    lines.append('')
    lines.append('    def test_runtime_path_emits_message_delta(self, _e2e_env):')
    lines.append('        session_id, db, token = _e2e_env')
    lines.append('        try:')
    lines.append('            msgs = self._run_ws_runtime_flow(session_id, token, db, "hello runtime")')
    lines.append('            delta_msgs = [m for m in msgs if m["type"] == "message_delta"]')
    lines.append('            assert len(delta_msgs) > 0, "Expected >=1 message_delta, got " + str([m["type"] for m in msgs])')
    lines.append('        finally:')
    lines.append('            db.close()')
    lines.append('')
    lines.append('    def test_runtime_path_emits_message_end(self, _e2e_env):')
    lines.append('        session_id, db, token = _e2e_env')
    lines.append('        try:')
    lines.append('            msgs = self._run_ws_runtime_flow(session_id, token, db, "hello runtime")')
    lines.append('            assert msgs[-1]["type"] == "message_end", "Expected message_end, got " + msgs[-1]["type"]')
    lines.append('        finally:')
    lines.append('            db.close()')
    lines.append('')
    lines.append('    def test_runtime_path_event_sequence(self, _e2e_env):')
    lines.append('        session_id, db, token = _e2e_env')
    lines.append('        try:')
    lines.append('            msgs = self._run_ws_runtime_flow(session_id, token, db, "hello runtime")')
    lines.append('            event_types = [m["type"] for m in msgs]')
    lines.append('            assert event_types[0] == "message_start", "First must be start, got " + str(event_types)')
    lines.append('            assert event_types[-1] == "message_end", "Last must be end, got " + str(event_types)')
    lines.append('            assert event_types.count("message_start") == 1')
    lines.append('            assert event_types.count("message_end") == 1')
    lines.append('        finally:')
    lines.append('            db.close()')
    lines.append('')
    lines.append('    def test_runtime_path_error_code_not_fixed_responder_failed(self, _e2e_env):')
    lines.append('        session_id, db, token = _e2e_env')
    lines.append('')
    lines.append('        class _FailingAdapter:')
    lines.append('            async def async_generate_with_history(self, messages_history, model, **kwargs):')
    lines.append('                raise RuntimeError("LLM unavailable in test")')
    lines.append('')
    lines.append('        try:')
    lines.append('            msgs = self._run_ws_runtime_flow(session_id, token, db, "hello", fake_adapter=_FailingAdapter())')
    lines.append('            error_msgs = [m for m in msgs if m["type"] == "message_error"]')
    lines.append('            assert len(error_msgs) >= 1, "Expected >=1 message_error, got " + str([m["type"] for m in msgs])')
    lines.append('            error_codes = [m.get("error_code") for m in error_msgs]')
    lines.append('            assert not any(c == "fixed_responder_failed" for c in error_codes), "Error code should NOT be fixed_responder_failed. Got: " + str(error_codes)')
    lines.append('        finally:')
    lines.append('            db.close()')
    return '\n'.join(lines)

# Find and replace
# Pattern: find test_runtime_path_emits_message_start through the last test method
start_marker = '\n    def test_runtime_path_emits_message_start(self):'
end_marker = '\n\n# --------------'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx >= 0 and end_idx >= 0:
    new_content = content[:start_idx] + '\n' + make_new_tests() + content[end_idx:]
    with open('D:/code/ZiJieAI/AgentHub/backend/tests/api/test_ws_runtime_agent.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('SUCCESS')
else:
    print('ERROR: start_idx=%d end_idx=%d' % (start_idx, end_idx))
    if start_idx >= 0:
        print('Content around start:', repr(content[start_idx:start_idx+200]))
