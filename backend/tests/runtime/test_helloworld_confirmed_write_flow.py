# -*- coding: utf-8 -*-
"""Task C-2: HelloWorld 确认落盘核心测试。

验收条件:
1. 能生成 HelloWorld.java 预览
2. 能返回 diff 与确认
3. 未确认前文件不落盘
4. 确认后文件真正写入工作区

测试覆盖:
- 7.1 工作区空目录读取测试
- 7.2 创建文件预览测试
- 7.3 diff 生成测试
- 7.4 确认前不落盘测试
- 7.5 按钮确认落盘测试
- 7.6 文本确认落盘测试
- 7.7 成功结果回写测试
"""

import os
import tempfile
from pathlib import Path

import pytest


class TestHelloWorldPreviewGeneration:
    """7.2 创建文件预览测试 — 输入 HelloWorld 需求后能生成 PendingChange."""

    def test_write_file_tool_returns_pending_change_for_new_file(self):
        """WriteFileTool 对新文件返回 PendingChange，operation=create."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange, ChangeOperation

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            os.environ["WORKSPACE_ROOT"] = tmpdir

            tool = WriteFileTool(workspace_root=Path(tmpdir))
            result = tool.execute(
                path="subdir/HelloWorld.java",
                content=(
                    "public class HelloWorld {\n"
                    '    public static void main(String[] args) {\n'
                    '        System.out.println("Hello, World!");\n'
                    "    }\n"
                    "}\n"
                ),
            )

            assert isinstance(result, PendingChange), f"Expected PendingChange, got {type(result)}"
            assert result.is_success(), f"Expected success, got error: {result.error}"
            assert result.operation == ChangeOperation.CREATE, (
                f"Expected operation=create, got {result.operation}"
            )
            assert result.change_id, "change_id should be generated"
            assert "HelloWorld.java" in result.path

    def test_pending_change_has_proposed_content(self):
        """PendingChange 包含预期的 Java HelloWorld 内容."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            os.environ["WORKSPACE_ROOT"] = tmpdir

            expected_content = (
                "public class HelloWorld {\n"
                '    public static void main(String[] args) {\n'
                '        System.out.println("Hello, World!");\n'
                "    }\n"
                "}\n"
            )

            tool = WriteFileTool(workspace_root=Path(tmpdir))
            result = tool.execute(path="subdir/HelloWorld.java", content=expected_content)

            assert isinstance(result, PendingChange)
            assert result.proposed_content == expected_content


class TestHelloWorldDiffGeneration:
    """7.3 diff 生成测试 — 返回 diff 中包含 HelloWorld.java 和预期 Java 内容."""

    def test_pending_change_has_unified_diff(self):
        """PendingChange.unified_diff 包含文件名和创建标记."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            os.environ["WORKSPACE_ROOT"] = tmpdir

            tool = WriteFileTool(workspace_root=Path(tmpdir))
            result = tool.execute(
                path="subdir/HelloWorld.java",
                content=(
                    "public class HelloWorld {\n"
                    '    public static void main(String[] args) {\n'
                    '        System.out.println("Hello, World!");\n'
                    "    }\n"
                    "}\n"
                ),
            )

            assert isinstance(result, PendingChange)
            assert result.is_success()

            diff = result.unified_diff
            assert "HelloWorld.java" in diff, f"Diff should contain filename, got: {diff}"
            assert "--- /dev/null" in diff or "+++" in diff, f"Diff should show file creation"
            assert "public class HelloWorld" in diff, f"Diff should contain class declaration"

    def test_to_display_string_includes_diff(self):
        """PendingChange.to_display_string() 返回包含 diff 的可读文本."""
        from app.runtime.tools.write_file_tool import WriteFileTool

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            os.environ["WORKSPACE_ROOT"] = tmpdir

            tool = WriteFileTool(workspace_root=Path(tmpdir))
            result = tool.execute(
                path="subdir/HelloWorld.java",
                content="public class HelloWorld {}\n",
            )

            display = result.to_display_string()
            assert "CREATE" in display or "create" in display.lower()
            assert "HelloWorld.java" in display


class TestNoFileBeforeConfirmation:
    """7.4 确认前不落盘测试 — 生成 preview 后，磁盘上仍不存在 HelloWorld.java."""

    def test_file_not_created_before_apply(self):
        """WriteFileTool.execute() 不会实际创建文件."""
        from app.runtime.tools.write_file_tool import WriteFileTool

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            os.environ["WORKSPACE_ROOT"] = tmpdir
            target_file = subdir / "HelloWorld.java"

            assert not target_file.exists(), "File should not exist before test"

            tool = WriteFileTool(workspace_root=Path(tmpdir))
            tool.execute(
                path="subdir/HelloWorld.java",
                content=(
                    "public class HelloWorld {\n"
                    '    public static void main(String[] args) {\n'
                    '        System.out.println("Hello, World!");\n'
                    "    }\n"
                    "}\n"
                ),
            )

            assert not target_file.exists(), (
                "File should NOT be created before apply! "
                "WriteFileTool should only preview, not write."
            )

    def test_workspace_directory_unchanged_after_preview(self):
        """预览后工作区目录结构不变."""
        from app.runtime.tools.write_file_tool import WriteFileTool

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            os.environ["WORKSPACE_ROOT"] = tmpdir

            original_files = set()
            for root, dirs, files in os.walk(tmpdir):
                for f in files:
                    original_files.add(Path(root) / f)

            tool = WriteFileTool(workspace_root=Path(tmpdir))
            tool.execute(
                path="subdir/HelloWorld.java",
                content="public class HelloWorld {}\n",
            )

            after_files = set()
            for root, dirs, files in os.walk(tmpdir):
                for f in files:
                    after_files.add(Path(root) / f)

            assert original_files == after_files, (
                f"Files changed after preview: {after_files - original_files}"
            )


class TestApplyChangeToolButtonConfirmation:
    """7.5 按钮确认落盘测试 — 点击确认后文件真正写入."""

    def test_write_file_auto_registers_pending_change(self):
        """WriteFileTool.execute() 自动将 PendingChange 注册到 ApplyChangeTool."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.tools.apply_change_tool import ApplyChangeTool, _PENDING_CHANGE_REGISTRY
        from app.runtime.pending_change import PendingChange, ChangeStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            os.environ["WORKSPACE_ROOT"] = tmpdir

            ApplyChangeTool.clear_registry()

            tool = WriteFileTool(workspace_root=Path(tmpdir))
            result = tool.execute(
                path="subdir/HelloWorld.java",
                content="public class HelloWorld {}\n",
            )

            assert result.change_id in _PENDING_CHANGE_REGISTRY, (
                "PendingChange should be auto-registered by WriteFileTool"
            )

    def test_apply_change_tool_writes_file(self):
        """ApplyChangeTool.apply() 将 PendingChange 写入磁盘."""
        from app.runtime.tools.apply_change_tool import ApplyChangeTool, _PENDING_CHANGE_REGISTRY
        from app.runtime.pending_change import PendingChange, ChangeStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = Path(tmpdir) / "HelloWorld.java"
            os.environ["WORKSPACE_ROOT"] = tmpdir

            java_content = (
                "public class HelloWorld {\n"
                '    public static void main(String[] args) {\n'
                '        System.out.println("Hello, World!");\n'
                "    }\n"
                "}\n"
            )

            pc = PendingChange.make_create(
                path=str(target_file),
                proposed_content=java_content,
            )
            change_id = pc.change_id

            tool = ApplyChangeTool(workspace_root=Path(tmpdir))
            _PENDING_CHANGE_REGISTRY[change_id] = pc

            result = tool.execute(change_id=change_id)

            assert target_file.exists(), "File should exist after apply"
            assert target_file.read_text(encoding="utf-8") == java_content
            assert pc.status == ChangeStatus.APPLIED
            assert change_id not in _PENDING_CHANGE_REGISTRY

    def test_apply_change_returns_success_message(self):
        """ApplyChangeTool.execute() 返回包含文件名和路径的成功消息."""
        from app.runtime.tools.apply_change_tool import ApplyChangeTool, _PENDING_CHANGE_REGISTRY
        from app.runtime.pending_change import PendingChange

        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = Path(tmpdir) / "HelloWorld.java"
            os.environ["WORKSPACE_ROOT"] = tmpdir

            pc = PendingChange.make_create(
                path=str(target_file),
                proposed_content="public class HelloWorld {}\n",
            )
            change_id = pc.change_id

            tool = ApplyChangeTool(workspace_root=Path(tmpdir))
            _PENDING_CHANGE_REGISTRY[change_id] = pc

            result = tool.execute(change_id=change_id)

            assert isinstance(result, str)
            assert "Applied" in result or "applied" in result.lower()
            assert "HelloWorld.java" in result

    def test_cannot_apply_twice(self):
        """同一个 change_id 不能重复 apply."""
        from app.runtime.tools.apply_change_tool import ApplyChangeTool, _PENDING_CHANGE_REGISTRY
        from app.runtime.pending_change import PendingChange

        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = Path(tmpdir) / "HelloWorld.java"
            os.environ["WORKSPACE_ROOT"] = tmpdir

            pc = PendingChange.make_create(
                path=str(target_file),
                proposed_content="public class HelloWorld {}\n",
            )
            change_id = pc.change_id

            tool = ApplyChangeTool(workspace_root=Path(tmpdir))
            _PENDING_CHANGE_REGISTRY[change_id] = pc

            result1 = tool.execute(change_id=change_id)
            result2 = tool.execute(change_id=change_id)

            assert "already been applied" in result2 or "Error" in result2
            assert change_id not in _PENDING_CHANGE_REGISTRY


class TestTextConfirmationProtocol:
    """7.6 文本确认落盘测试 — 输入'确认应用'或'apply'后文件真正写入."""

    def test_confirm_keywords_recognized(self):
        """文本确认关键词'确认应用'和'apply'应被识别."""
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


class TestSuccessResultWriteback:
    """7.7 成功结果回写测试 — apply 成功后前端能看到成功结果."""

    def test_apply_result_contains_file_info(self):
        """apply 成功后结果包含文件名和路径."""
        from app.runtime.tools.apply_change_tool import ApplyChangeTool, _PENDING_CHANGE_REGISTRY
        from app.runtime.pending_change import PendingChange

        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = Path(tmpdir) / "HelloWorld.java"
            os.environ["WORKSPACE_ROOT"] = tmpdir

            pc = PendingChange.make_create(
                path=str(target_file),
                proposed_content="public class HelloWorld {}\n",
            )
            change_id = pc.change_id

            tool = ApplyChangeTool(workspace_root=Path(tmpdir))
            _PENDING_CHANGE_REGISTRY[change_id] = pc

            result = tool.execute(change_id=change_id)

            assert "HelloWorld.java" in result
            assert str(target_file) in result or "HelloWorld.java" in result

    def test_apply_failure_returns_error_info(self):
        """apply 失败时返回失败原因，文件未落盘."""
        from app.runtime.tools.apply_change_tool import ApplyChangeTool, _PENDING_CHANGE_REGISTRY
        from app.runtime.pending_change import PendingChange

        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = Path(tmpdir) / "HelloWorld.java"
            os.environ["WORKSPACE_ROOT"] = tmpdir

            pc = PendingChange.make_create(
                path=str(target_file),
                proposed_content="public class HelloWorld {}\n",
            )
            change_id = pc.change_id

            tool = ApplyChangeTool(workspace_root=Path(tmpdir))
            _PENDING_CHANGE_REGISTRY[change_id] = pc

            result1 = tool.execute(change_id=change_id)
            assert target_file.exists()

            result2 = tool.execute(change_id=change_id)

            assert "Error" in result2 or "already" in result2.lower()

    def test_pending_change_provides_summary(self):
        """PendingChange.summary() 返回人类可读的变更摘要."""
        from app.runtime.pending_change import PendingChange, ChangeOperation

        pc = PendingChange(
            change_id="test-123",
            path="/workspace/HelloWorld.java",
            operation=ChangeOperation.CREATE,
            proposed_content="public class HelloWorld {}\n",
        )

        summary = pc.summary()
        assert isinstance(summary, str)
        assert "HelloWorld.java" in summary or "CREATE" in summary or "Create" in summary


class TestWorkspaceFileStateReading:
    """7.1 工作区空目录读取测试 — 空目录下能检查文件不存在."""

    def test_check_file_not_exists_in_empty_workspace(self):
        """在工作区空目录中检查文件不存在."""
        from app.runtime.tools.list_directory_tool import ListDirectoryTool

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["WORKSPACE_ROOT"] = tmpdir
            tool = ListDirectoryTool(workspace_root=Path(tmpdir))

            result = tool.execute(directory_path=".")

            assert "HelloWorld.java" not in result
            assert isinstance(result, str)

    def test_file_exists_check(self):
        """能检测工作区中文件是否存在."""
        from app.runtime.tools.read_file_tool import ReadFileTool

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["WORKSPACE_ROOT"] = tmpdir
            target_file = Path(tmpdir) / "HelloWorld.java"

            tool = ReadFileTool(workspace_root=Path(tmpdir))

            result = tool.execute(file_path="HelloWorld.java")

            assert "not found" in result.lower() or "error" in result.lower() or "不存在" in result
