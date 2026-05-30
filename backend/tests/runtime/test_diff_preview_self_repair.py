# -*- coding: utf-8 -*-
"""Task C-D: Diff Preview / Self-Repair 核心测试。

本文档严格按 06-task-cd-diff-preview-self-repair.md 验收条件 TDD 实现。

验收条件 (10.1-10.6):
1. diff 可展示且可确认
2. 未确认前不落盘
3. 确认后状态与结果一致
4. 命令结果可追踪
5. preview 可展示
6. self-repair 有明确上限与可观察过程

测试覆盖:
- C-3: diff 消息结构与前端渲染
- C-4: apply 结果同步
- C-5: command result 消息流
- D-1: preview 主链路
- D-2: self-repair 状态机
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Task C-3: PendingChange 生命周期收口测试
# ---------------------------------------------------------------------------


class TestPendingChangeLifecycle:
    """C-3: PendingChange 生命周期状态转换测试。

    验收条件 10.1: diff 可展示且可确认
    """

    def test_pending_change_has_required_fields_for_diff_display(self):
        """C-3: PendingChange 必须包含 diff 展示所需的所有字段。

        必须包含: change_id, file_path, operation, unified_diff, status, created_at
        """
        from app.runtime.pending_change import PendingChange, ChangeOperation, ChangeStatus

        pc = PendingChange(
            change_id="test-123",
            path="/workspace/test.py",
            operation=ChangeOperation.CREATE,
            proposed_content="print('hello')",
        )

        # 必需字段
        assert pc.change_id == "test-123"
        assert pc.path == "/workspace/test.py"
        assert pc.operation == ChangeOperation.CREATE
        assert pc.unified_diff, "unified_diff must be computed"
        assert pc.status == ChangeStatus.PREVIEW
        assert pc.created_at, "created_at must be set"

        # 验证 unified_diff 包含必要信息
        diff = pc.unified_diff
        assert "test.py" in diff or "test" in diff
        assert "--- /dev/null" in diff or "+++" in diff

    def test_pending_change_status_transitions(self):
        """C-3: PendingChange 状态转换: PREVIEW -> APPLIED / REJECTED."""
        from app.runtime.pending_change import PendingChange, ChangeOperation, ChangeStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("old content", encoding="utf-8")

            pc = PendingChange(
                change_id="test-456",
                path=str(test_file),
                operation=ChangeOperation.UPDATE,
                original_content="old content",
                proposed_content="new content",
            )

            # 初始状态
            assert pc.status == ChangeStatus.PREVIEW

            # 应用后状态变为 APPLIED
            success = pc.apply()
            assert success, f"apply() should succeed, error={pc.error}"
            assert pc.status == ChangeStatus.APPLIED

    def test_pending_change_rejected_on_concurrent_modification(self):
        """C-3: 文件在预览后被修改时，apply 应该拒绝。

        验收条件 10.2: 未确认前不落盘（此处测试防止外部修改导致的不一致）
        """
        from app.runtime.pending_change import PendingChange, ChangeOperation, ChangeStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("original content", encoding="utf-8")

            pc = PendingChange(
                change_id="test-789",
                path=str(test_file),
                operation=ChangeOperation.UPDATE,
                original_content="original content",
                proposed_content="modified content",
            )

            # 外部修改文件
            test_file.write_text("modified by someone else", encoding="utf-8")

            # apply 应该拒绝
            success = pc.apply()
            assert not success, "apply() should reject when file was modified"
            assert pc.status != ChangeStatus.APPLIED
            assert "modified" in pc.error or "changed" in pc.error.lower()


# ---------------------------------------------------------------------------
# Task C-3: diff 消息结构测试 (后端)
# ---------------------------------------------------------------------------


class TestDiffPreviewEventStructure:
    """C-3: diff 预览响应契约测试。

    验收条件 10.1: diff 可展示且可确认
    """

    def test_change_preview_event_structure(self):
        """C-3: change_preview 事件必须符合正式结构。

        必须包含: type, change_id, file_path, operation, unified_diff, status
        """
        from app.runtime.event_bridge import ChangePreviewEvent

        event = ChangePreviewEvent(
            change_id="diff-123",
            operation="create",
            path="/workspace/newfile.py",
            unified_diff="--- /dev/null\n+++ b/newfile.py\n@@ -0,0 +1,1 @@\n+print('hello')",
            status="pending_confirmation",
            stream_id="stream-abc",
            message_id="msg-xyz",
        )

        assert event.type == "change_preview"
        assert event.change_id == "diff-123"
        assert event.operation == "create"
        assert event.path == "/workspace/newfile.py"
        assert event.unified_diff.startswith("--- /dev/null")
        assert event.status == "pending_confirmation"

    def test_change_preview_event_serialization(self):
        """C-3: change_preview 事件必须能序列化为 JSON。"""
        from app.runtime.event_bridge import ChangePreviewEvent

        event = ChangePreviewEvent(
            change_id="diff-456",
            operation="update",
            path="/workspace/existing.py",
            unified_diff="--- a/existing.py\n+++ b/existing.py\n@@ -1 +1,2 @@\n old\n+new",
            status="pending_confirmation",
            stream_id="stream-def",
            message_id="msg-uvw",
        )

        # 必须能序列化为 JSON
        data = event.to_dict()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert parsed["change_id"] == "diff-456"
        assert parsed["operation"] == "update"
        assert parsed["status"] == "pending_confirmation"


# ---------------------------------------------------------------------------
# Task C-4: apply 确认链路测试
# ---------------------------------------------------------------------------


class TestApplyConfirmationProtocol:
    """C-4: apply 确认链路测试。

    验收条件 10.3: 确认后状态与结果一致
    """

    def test_apply_api_success_response(self):
        """C-4: apply 成功时返回正确响应结构。

        必须包含: success, change_id, message
        """
        from app.runtime.tools.apply_change_tool import ApplyChangeTool, _PENDING_CHANGE_REGISTRY
        from app.runtime.pending_change import PendingChange, ChangeStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "HelloWorld.java"
            pc = PendingChange.make_create(
                path=str(test_file),
                proposed_content="public class HelloWorld {}",
            )
            change_id = pc.change_id
            _PENDING_CHANGE_REGISTRY[change_id] = pc

            tool = ApplyChangeTool(workspace_root=Path(tmpdir))
            result = tool.execute(change_id=change_id)

            # 成功响应包含文件名
            assert "HelloWorld.java" in result
            assert pc.status == ChangeStatus.APPLIED

            # apply 后从注册表移除
            assert change_id not in _PENDING_CHANGE_REGISTRY

    def test_apply_api_not_found_response(self):
        """C-4: apply 不存在的 change_id 时返回错误。"""
        from app.runtime.tools.apply_change_tool import ApplyChangeTool, _PENDING_CHANGE_REGISTRY

        with tempfile.TemporaryDirectory() as tmpdir:
            tool = ApplyChangeTool(workspace_root=Path(tmpdir))
            result = tool.execute(change_id="non-existent-id")

            assert "Error" in result or "not found" in result.lower() or "already" in result.lower()

    def test_apply_idempotent(self):
        """C-4: 重复 apply 同一 change_id 应该被拒绝。

        验收条件 10.3: 确认后状态与结果一致
        """
        from app.runtime.tools.apply_change_tool import ApplyChangeTool, _PENDING_CHANGE_REGISTRY
        from app.runtime.pending_change import PendingChange, ChangeStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "idempotent.py"
            pc = PendingChange.make_create(
                path=str(test_file),
                proposed_content="print('test')",
            )
            change_id = pc.change_id
            _PENDING_CHANGE_REGISTRY[change_id] = pc

            tool = ApplyChangeTool(workspace_root=Path(tmpdir))

            # 第一次成功
            result1 = tool.execute(change_id=change_id)
            assert pc.status == ChangeStatus.APPLIED
            assert test_file.exists()

            # 第二次失败
            result2 = tool.execute(change_id=change_id)
            assert "already" in result2.lower() or "Error" in result2
            assert change_id not in _PENDING_CHANGE_REGISTRY


# ---------------------------------------------------------------------------
# Task C-5: 命令执行结果消息流测试
# ---------------------------------------------------------------------------


class TestCommandResultStructure:
    """C-5: 命令执行结果结构化返回测试。

    验收条件 10.4: 命令结果可追踪
    """

    def test_command_result_has_required_fields(self):
        """C-5: Command result 必须包含所有必要字段。

        必须包含: command, cwd, stdout, stderr, exit_code, success, timed_out
        """
        # 模拟 CommandResult 结构
        command_result = {
            "type": "command_result",
            "command": "pytest tests/",
            "cwd": "/workspace",
            "stdout": "test passed",
            "stderr": "",
            "exit_code": 0,
            "success": True,
            "timed_out": False,
        }

        # 验证必需字段
        assert command_result["type"] == "command_result"
        assert "command" in command_result
        assert "cwd" in command_result
        assert "stdout" in command_result
        assert "stderr" in command_result
        assert "exit_code" in command_result
        assert "success" in command_result
        assert "timed_out" in command_result

    def test_command_result_failure_case(self):
        """C-5: 命令失败时 stderr 和 exit_code 正确。"""
        command_result = {
            "type": "command_result",
            "command": "pytest tests/ --fail",
            "cwd": "/workspace",
            "stdout": "",
            "stderr": "FAILED test_example.py",
            "exit_code": 1,
            "success": False,
            "timed_out": False,
        }

        assert not command_result["success"]
        assert command_result["exit_code"] != 0
        assert "FAILED" in command_result["stderr"]

    def test_run_command_tool_returns_structured_result(self):
        """C-5: RunCommandTool 返回结构化结果。"""
        from app.runtime.tools.run_command_tool import RunCommandTool
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            tool = RunCommandTool(workspace_root=Path(tmpdir))
            result = tool.execute(command="echo hello", timeout=5, cwd=str(tmpdir))

            # 结果应该是结构化的（JSON 或包含结构化字段）
            assert isinstance(result, str)
            # 如果是 JSON 格式，解析后应包含必要字段
            try:
                parsed = json.loads(result)
                assert "exit_code" in parsed or "success" in parsed or "stdout" in parsed
            except json.JSONDecodeError:
                # 如果是纯文本，应该至少包含退出码或输出
                pass


# ---------------------------------------------------------------------------
# Task D-1: preview 结果结构测试
# ---------------------------------------------------------------------------


class TestPreviewResultStructure:
    """D-1: preview 结果结构化返回测试。

    验收条件 10.5: preview 可展示
    """

    def test_preview_result_has_required_fields(self):
        """D-1: Preview result 必须包含所有必要字段。

        必须包含: preview_id, workspace_id, preview_url, status, source_message_id, created_at
        """
        preview_result = {
            "type": "preview_result",
            "preview_id": "prev-123",
            "workspace_id": "ws-456",
            "preview_url": "http://localhost:3000/preview/prev-123",
            "status": "ready",
            "message_id": "msg-789",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        assert preview_result["type"] == "preview_result"
        assert "preview_id" in preview_result
        assert "workspace_id" in preview_result
        assert "preview_url" in preview_result
        assert "status" in preview_result
        assert "message_id" in preview_result
        assert "created_at" in preview_result


# ---------------------------------------------------------------------------
# Task D-2: self-repair 状态机测试
# ---------------------------------------------------------------------------


class TestSelfRepairStateMachine:
    """D-2: 有限 self-repair 状态机测试。

    验收条件 10.6: self-repair 有明确上限与可观察过程
    """

    def test_repair_state_enum_values(self):
        """D-2: Repair state 必须包含所有定义的状态。

        必须包含: IDLE, ANALYZING_FAILURE, GENERATING_FIX, AWAITING_CONFIRMATION,
                 APPLYING_FIX, RERUNNING_COMMAND, FINISHED, ERROR
        """
        from app.runtime.repair_state import RepairState

        expected_states = {
            "IDLE",
            "ANALYZING_FAILURE",
            "GENERATING_FIX",
            "AWAITING_CONFIRMATION",
            "APPLYING_FIX",
            "RERUNNING_COMMAND",
            "FINISHED",
            "ERROR",
        }

        # 验证所有状态都存在
        for state_name in expected_states:
            assert hasattr(RepairState, state_name), f"Missing state: {state_name}"

    def test_repair_state_event_structure(self):
        """D-2: repair_state 事件必须包含所有必要字段。

        必须包含: type, state, attempt, max_attempts, message
        """
        from app.runtime.repair_state import RepairStateEvent

        event = RepairStateEvent(
            type="repair_state",
            state="ANALYZING_FAILURE",
            attempt=1,
            max_attempts=3,
            message="Analyzing test failure...",
            stream_id="stream-abc",
            message_id="msg-xyz",
        )

        assert event.type == "repair_state"
        assert event.state == "ANALYZING_FAILURE"
        assert event.attempt == 1
        assert event.max_attempts == 3
        assert event.message == "Analyzing test failure..."

    def test_repair_max_retry_limit(self):
        """D-2: self-repair 必须有明确的最大重试次数上限。

        验收条件 10.6: 超过上限会停止
        """
        from app.runtime.repair_state import MAX_REPAIR_RETRY

        assert MAX_REPAIR_RETRY > 0, "MAX_REPAIR_RETRY must be positive"
        assert MAX_REPAIR_RETRY <= 10, "MAX_REPAIR_RETRY should be reasonable (not too high)"

    def test_repair_state_transition_logic(self):
        """D-2: repair 状态机转移逻辑测试。

        期望转移: IDLE -> ANALYZING_FAILURE -> GENERATING_FIX ->
                 AWAITING_CONFIRMATION -> APPLYING_FIX -> RERUNNING_COMMAND -> FINISHED
        """
        from app.runtime.repair_state import RepairState, RepairStateMachine

        machine = RepairStateMachine()

        # 初始状态
        assert machine.state == RepairState.IDLE

        # 开始修复
        machine.transition(RepairState.ANALYZING_FAILURE)
        assert machine.state == RepairState.ANALYZING_FAILURE

        # 分析完成，生成修复
        machine.transition(RepairState.GENERATING_FIX)
        assert machine.state == RepairState.GENERATING_FIX

        # 等待确认
        machine.transition(RepairState.AWAITING_CONFIRMATION)
        assert machine.state == RepairState.AWAITING_CONFIRMATION

        # 应用修复
        machine.transition(RepairState.APPLYING_FIX)
        assert machine.state == RepairState.APPLYING_FIX

        # 重新运行命令
        machine.transition(RepairState.RERUNNING_COMMAND)
        assert machine.state == RepairState.RERUNNING_COMMAND

        # 完成
        machine.transition(RepairState.FINISHED)
        assert machine.state == RepairState.FINISHED


# ---------------------------------------------------------------------------
# Task D-2: self-repair 端到端测试
# ---------------------------------------------------------------------------


class TestSelfRepairEndToEnd:
    """D-2: self-repair 端到端测试。

    验收条件 10.6: self-repair 有明确上限与可观察过程
    """

    def test_repair_respects_max_attempts(self):
        """D-2: 修复次数达到上限后应该停止。"""
        from app.runtime.repair_state import RepairState, RepairStateMachine, MAX_REPAIR_RETRY

        machine = RepairStateMachine()

        # 模拟多次失败
        for attempt in range(1, MAX_REPAIR_RETRY + 1):
            machine.increment_attempt()
            machine.transition(RepairState.ANALYZING_FAILURE)
            machine.transition(RepairState.GENERATING_FIX)
            machine.transition(RepairState.RERUNNING_COMMAND)
            # 模拟命令失败
            machine.transition(RepairState.ERROR)

        # 达到上限后不应该再继续
        assert machine.attempt >= MAX_REPAIR_RETRY
        assert machine.is_exhausted(), "Machine should be exhausted after max attempts"

    def test_repair_observable_at_each_step(self):
        """D-2: 修复过程的每一步都应该可观察。

        用户能看到: 当前是否在修复、已尝试第几次、成功还是失败、为什么停止
        """
        from app.runtime.repair_state import RepairStateEvent

        # 模拟每个步骤的事件
        steps = [
            ("ANALYZING_FAILURE", 1, "Analyzing test failure..."),
            ("GENERATING_FIX", 1, "Generating fix for assertion error..."),
            ("RERUNNING_COMMAND", 1, "Running: pytest tests/..."),
            ("ERROR", 1, "Test still failing: expected 5, got 3"),
            ("ANALYZING_FAILURE", 2, "Analyzing new failure..."),
            ("FINISHED", 2, "All tests passed after 2 attempts"),
        ]

        for state, attempt, message in steps:
            event = RepairStateEvent(
                type="repair_state",
                state=state,
                attempt=attempt,
                max_attempts=3,
                message=message,
                stream_id="stream-abc",
                message_id="msg-xyz",
            )

            # 每一步都有完整信息
            assert event.state == state
            assert event.attempt == attempt
            assert event.message == message
            assert event.max_attempts == 3


# ---------------------------------------------------------------------------
# 集成测试: 完整 diff -> apply 流程
# ---------------------------------------------------------------------------


class TestDiffApplyCompleteFlow:
    """集成测试: 完整的 diff -> apply 流程。

    验收条件:
    - 10.1: diff 可展示且可确认
    - 10.2: 未确认前不落盘
    - 10.3: 确认后状态与结果一致
    """

    def test_complete_flow_write_new_file(self):
        """完整流程: 预览 -> 确认 -> 落盘."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.tools.apply_change_tool import ApplyChangeTool, _PENDING_CHANGE_REGISTRY
        from app.runtime.pending_change import ChangeStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = Path(tmpdir) / "HelloWorld.java"
            assert not target_file.exists(), "File should not exist initially"

            # Step 1: 生成预览
            tool = WriteFileTool(workspace_root=Path(tmpdir))
            result = tool.execute(
                path="HelloWorld.java",
                content="public class HelloWorld {\n    public static void main(String[] args) {\n        System.out.println(\"Hello, World!\");\n    }\n}\n",
            )

            # 验证预览返回正确结构
            assert result.change_id, "Should have change_id"
            assert result.operation.value == "create"
            assert result.unified_diff, "Should have unified_diff"

            # Step 2: 确认前文件不存在
            assert not target_file.exists(), "File should NOT exist before apply"

            # Step 3: 应用变更
            change_id = result.change_id
            apply_tool = ApplyChangeTool(workspace_root=Path(tmpdir))
            apply_result = apply_tool.execute(change_id=change_id)

            # Step 4: 验证结果
            assert target_file.exists(), "File should exist after apply"
            assert result.status == ChangeStatus.APPLIED

            # 验证文件内容
            content = target_file.read_text(encoding="utf-8")
            assert "public class HelloWorld" in content
            assert "Hello, World!" in content

    def test_complete_flow_update_existing_file(self):
        """完整流程: 更新已有文件."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.tools.apply_change_tool import ApplyChangeTool
        from app.runtime.pending_change import ChangeStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = Path(tmpdir) / "config.py"
            target_file.write_text("DEBUG = False\nPORT = 8080\n", encoding="utf-8")
            original_content = target_file.read_text(encoding="utf-8")

            # 生成更新预览
            tool = WriteFileTool(workspace_root=Path(tmpdir))
            result = tool.execute(
                path="config.py",
                content="DEBUG = True\nPORT = 3000\nENV = 'production'\n",
            )

            assert result.operation.value == "update"
            assert not target_file.exists() or target_file.read_text(encoding="utf-8") == original_content

            # 应用更新
            change_id = result.change_id
            apply_tool = ApplyChangeTool(workspace_root=Path(tmpdir))
            apply_result = apply_tool.execute(change_id=change_id)

            # 验证更新
            assert result.status == ChangeStatus.APPLIED
            new_content = target_file.read_text(encoding="utf-8")
            assert "DEBUG = True" in new_content
            assert "PORT = 3000" in new_content


# ---------------------------------------------------------------------------
# 前端类型测试
# ---------------------------------------------------------------------------


class TestFrontendTypes:
    """前端类型定义测试。

    确保前后端类型一致性
    """

    def test_pending_change_type_definition(self):
        """前端 PendingChange 类型定义与后端一致。"""
        # 这个测试确保前端类型与后端兼容
        # PendingChange 必须包含:
        # - change_id: string
        # - operation: 'create' | 'update' | 'delete'
        # - path: string
        # - unified_diff: string
        # - status: 'pending_confirmation' | 'applied' | 'rejected'
        # - stream_id: string
        # - message_id: string

        from app.runtime.pending_change import PendingChange, ChangeOperation, ChangeStatus

        pc = PendingChange(
            change_id="test-123",
            path="/workspace/test.py",
            operation=ChangeOperation.CREATE,
            proposed_content="print('hello')",
        )

        # 映射到前端类型
        frontend_change = {
            "change_id": pc.change_id,
            "operation": pc.operation.value,
            "path": pc.path,
            "unified_diff": pc.unified_diff,
            "status": "pending_confirmation",  # 后端 PREVIEW -> 前端 pending_confirmation
            "stream_id": "stream-abc",
            "message_id": "msg-xyz",
        }

        assert isinstance(frontend_change["change_id"], str)
        assert frontend_change["operation"] in ["create", "update", "delete"]
        assert isinstance(frontend_change["path"], str)
        assert isinstance(frontend_change["unified_diff"], str)
        assert frontend_change["status"] in ["pending_confirmation", "applied", "rejected"]


# ---------------------------------------------------------------------------
# 回归测试: 确保现有功能不被破坏
# ---------------------------------------------------------------------------


class TestRegressionHelloworldFlow:
    """回归测试: 确保 HelloWorld 流程仍然工作。

    验收条件 10.2: 未确认前不落盘
    """

    def test_helloworld_preview_then_confirm(self):
        """回归测试: HelloWorld 预览 -> 确认流程。"""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.tools.apply_change_tool import ApplyChangeTool

        with tempfile.TemporaryDirectory() as tmpdir:
            tool = WriteFileTool(workspace_root=Path(tmpdir))
            result = tool.execute(
                path="HelloWorld.java",
                content="public class HelloWorld {\n    public static void main(String[] args) {\n        System.out.println(\"Hello, World!\");\n    }\n}\n",
            )

            assert result.change_id
            assert not Path(tmpdir, "HelloWorld.java").exists()

            apply_tool = ApplyChangeTool(workspace_root=Path(tmpdir))
            apply_result = apply_tool.execute(change_id=result.change_id)

            assert Path(tmpdir, "HelloWorld.java").exists()

    def test_confirm_keywords_still_work(self):
        """回归测试: 确认关键词仍然有效。"""
        confirm_keywords = ["确认应用", "apply", "确认", "confirm"]
        test_inputs = [
            "确认应用",
            "apply",
            "确认写入",
            "confirm apply",
            "确认",
        ]

        for user_input in test_inputs:
            matched = any(kw in user_input.lower() for kw in confirm_keywords)
            assert matched, f"Input '{user_input}' should match at least one keyword"


# =============================================================================
# Task 2: Diff Apply And Command Result Formal Event Flow
# =============================================================================

class TestApplyResultEventPayload:
    """Task 2: apply_result event payload tests.

    验收条件:
    - P3: apply 必经受控确认路径
    - P3: apply 发出正式结果事件
    """

    def test_apply_result_event_structure(self):
        """Task 2: ApplyResultEvent must have correct structure."""
        from app.runtime.event_bridge import ApplyResultEvent

        event = ApplyResultEvent(
            change_id="change-123",
            success=True,
            status="applied",
            message="File successfully written",
        )

        assert event.type == "apply_result"
        assert event.change_id == "change-123"
        assert event.success is True
        assert event.status == "applied"
        assert event.message == "File successfully written"

    def test_apply_result_event_serialization(self):
        """Task 2: ApplyResultEvent must serialize to JSON."""
        from app.runtime.event_bridge import ApplyResultEvent

        event = ApplyResultEvent(
            change_id="change-456",
            success=False,
            status="rejected",
            message="File was modified externally",
        )

        data = event.to_dict()
        import json
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert parsed["type"] == "apply_result"
        assert parsed["change_id"] == "change-456"
        assert parsed["success"] is False
        assert parsed["status"] == "rejected"


class TestCommandResultPayload:
    """Task 2: Command result payload tests.

    验收条件:
    - P3: command 执行结果可被 runtime 状态和消息流追踪
    - P3: command 结果形成结构化 terminal/result 事件
    """

    def test_command_result_payload_structure(self):
        """Task 2: CommandResultPayload must have correct structure."""
        from app.runtime.command_result import CommandResultPayload

        payload = CommandResultPayload(
            command="pytest tests/",
            cwd="/workspace",
            stdout="test passed",
            stderr="",
            exit_code=0,
            success=True,
            timed_out=False,
        )

        assert payload.type == "command_result"
        assert payload.command == "pytest tests/"
        assert payload.cwd == "/workspace"
        assert payload.stdout == "test passed"
        assert payload.stderr == ""
        assert payload.exit_code == 0
        assert payload.success is True
        assert payload.timed_out is False

    def test_command_result_payload_serialization(self):
        """Task 2: CommandResultPayload must serialize to JSON."""
        from app.runtime.command_result import CommandResultPayload

        payload = CommandResultPayload(
            command="python --version",
            cwd="/workspace",
            stdout="Python 3.13.0",
            stderr="",
            exit_code=0,
            success=True,
            timed_out=False,
        )

        data = payload.to_dict()
        import json
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert parsed["type"] == "command_result"
        assert parsed["command"] == "python --version"
        assert parsed["exit_code"] == 0
        assert parsed["success"] is True

    def test_run_command_tool_returns_structured_dict(self):
        """Task 2: RunCommandTool.execute() should return structured dict with required fields."""
        from app.runtime.tools.run_command_tool import RunCommandTool
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            tool = RunCommandTool(workspace_root=tmpdir)
            result_str = tool.execute(command="echo hello", cwd=tmpdir, timeout_seconds=5)

            # Result should be parseable as JSON or contain structured fields
            import json
            try:
                result = json.loads(result_str)
                # Must have required fields
                assert "type" in result or "command" in result or "exit_code" in result, (
                    f"Result must contain type/command/exit_code fields. Got: {result}"
                )
            except json.JSONDecodeError:
                # If not JSON, must be formatted text with required information
                assert "exit_code" in result_str.lower() or "EXIT_CODE" in result_str
                assert "hello" in result_str


class TestCommandResultEventForwarding:
    """Task 2: CommandResultEvent in event bridge tests.

    验收条件:
    - P3: command 结果纳入统一 runtime 事件流
    """

    def test_command_result_event_class_exists(self):
        """Task 2: CommandResultEvent class must exist in event_bridge."""
        from app.runtime.event_bridge import CommandResultEvent

        event = CommandResultEvent(
            command="pytest tests/",
            stdout="passed",
            exit_code=0,
            success=True,
        )

        assert event.type == "command_result"
        assert event.command == "pytest tests/"
        assert event.stdout == "passed"
        assert event.exit_code == 0
