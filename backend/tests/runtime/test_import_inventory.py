"""M0 smoke test: validates that the runtime copied baseline is complete and inventory exists.

Per 02-implementation-guide.md Section 6.5:
- 复制文件路径存在
- 模板目录完整
- 旧链路状态说明存在

This test does NOT validate that runtime is functional (that is M1+ territory).
"""

from pathlib import Path


def _runtime_root() -> Path:
    backend = Path(__file__).resolve().parents[2]
    return backend / "app" / "runtime"


def _project_root() -> Path:
    backend = Path(__file__).resolve().parents[3]
    return backend


class TestRuntimeFilesExist:
    """Verify all copied runtime files are present on disk."""

    CORE_FILES = [
        "__init__.py",
        "react_agent.py",
        "memory.py",
        "generative_model.py",
        "tool_manager.py",
        "xml_parser.py",
        "xml_tool_parser.py",
        "prompts.py",
        "version.py",
    ]

    TOOL_FILES = [
        "tools/__init__.py",
        "tools/tool.py",
        "tools/read_file_tool.py",
        "tools/list_directory_tool.py",
        "tools/replace_in_file_tool.py",
        "tools/unified_diff_tool.py",
        "tools/task_complete_tool.py",
    ]

    UTIL_FILES = [
        "utils/__init__.py",
        "utils/get_environment.py",
        "utils/read_file.py",
    ]

    STUB_FILES = [
        "quantlitellm.py",
        "get_model_info.py",
    ]

    REQUIRED_TEMPLATES = [
        "prompts/system_prompt.j2",
        "prompts/task_prompt.j2",
        "prompts/tools_prompt.j2",
        "prompts/variables_prompt.j2",
        "prompts/task_summary_prompt.j2",
        "prompts/memory_compaction_prompt.j2",
        "prompts/observation_response_format.j2",
        "prompts/repeated_tool_call_error.j2",
        "prompts/chat_system_prompt.j2",
    ]

    @property
    def runtime_root(self) -> Path:
        return _runtime_root()

    def test_core_files_exist(self):
        for fname in self.CORE_FILES:
            path = self.runtime_root / fname
            assert path.exists(), f"Missing core file: {path}"

    def test_tool_files_exist(self):
        for fname in self.TOOL_FILES:
            path = self.runtime_root / fname
            assert path.exists(), f"Missing tool file: {path}"

    def test_util_files_exist(self):
        for fname in self.UTIL_FILES:
            path = self.runtime_root / fname
            assert path.exists(), f"Missing util file: {path}"

    def test_stub_files_exist(self):
        for fname in self.STUB_FILES:
            path = self.runtime_root / fname
            assert path.exists(), f"Missing stub file: {path}"


class TestTemplateDirectoryComplete:
    """Verify the prompts/ template directory has all required templates."""

    REQUIRED_TEMPLATES = [
        "prompts/system_prompt.j2",
        "prompts/task_prompt.j2",
        "prompts/tools_prompt.j2",
        "prompts/variables_prompt.j2",
        "prompts/task_summary_prompt.j2",
        "prompts/memory_compaction_prompt.j2",
        "prompts/observation_response_format.j2",
        "prompts/repeated_tool_call_error.j2",
        "prompts/chat_system_prompt.j2",
        "prompts/code_system_prompt.j2",
        "prompts/code_2_system_prompt.j2",
        "prompts/doc_system_prompt.j2",
        "prompts/legal_system_prompt.j2",
        "prompts/legal_2_system_prompt.j2",
    ]

    @property
    def runtime_root(self) -> Path:
        return _runtime_root()

    def test_required_templates_exist(self):
        for tmpl in self.REQUIRED_TEMPLATES:
            path = self.runtime_root / tmpl
            assert path.exists(), f"Missing required template: {path}"
            assert path.is_file(), f"Template path is not a file: {path}"

    def test_template_directory_not_empty(self):
        prompts_dir = self.runtime_root / "prompts"
        j2_files = list(prompts_dir.glob("*.j2"))
        assert len(j2_files) >= 14, (
            f"Expected at least 14 .j2 templates, found {len(j2_files)}. "
            "Check that all templates from 01-compatibility-analysis.md were copied."
        )


class TestLegacyPipelineDocumentation:
    """Verify legacy pipeline state is documented."""

    @property
    def project_root(self) -> Path:
        return _project_root()

    def test_m0_inventory_exists(self):
        inventory = self.project_root / "openspec" / "docs" / "migration" / "M0-inventory.md"
        assert inventory.exists(), (
            "M0-inventory.md not found. "
            "M0 requires a migration inventory document per 02-implementation-guide.md Section 6.3."
        )

    def test_agent_stream_service_deprecated_notice(self):
        """Verify agent_stream_service.py has a deprecation/legacy notice in its docstring."""
        service_path = (
            self.project_root / "backend" / "app" / "services" / "agent_stream_service.py"
        )
        assert service_path.exists(), "agent_stream_service.py not found"
        content = service_path.read_text(encoding="utf-8")
        assert "废弃声明" in content or "废弃" in content, (
            "agent_stream_service.py must contain a legacy/deprecation notice per "
            "02-implementation-guide.md Section 6.4.3 and 01-compatibility-analysis.md Section 2.3."
        )
        assert "不是当前主链路" in content or "主链路" in content, (
            "agent_stream_service.py must clarify it is NOT the current main pipeline."
        )

    def test_fixed_agent_responder_is_main_pipeline(self):
        """Verify FixedAgentResponder exists and is the documented main responder."""
        responder_path = (
            self.project_root
            / "backend"
            / "app"
            / "services"
            / "fixed_agent_responder.py"
        )
        assert responder_path.exists(), "FixedAgentResponder not found"
        content = responder_path.read_text(encoding="utf-8")
        assert "FixedAgentResponder" in content, "FixedAgentResponder class not found"


class TestMigrationDocIntegrity:
    """Sanity-check the M0 inventory document contents."""

    @property
    def project_root(self) -> Path:
        return _project_root()

    def test_m0_inventory_has_unwired_section(self):
        """M0 inventory must list unwired (not-yet-plumbed) files."""
        inventory = (
            self.project_root
            / "openspec"
            / "docs"
            / "migration"
            / "M0-inventory.md"
        )
        content = inventory.read_text(encoding="utf-8")
        assert "未接线" in content, (
            "M0-inventory.md must document 'unwired' files per "
            "02-implementation-guide.md Section 6.4.1."
        )

    def test_m0_inventory_has_stub_section(self):
        """M0 inventory must list transition stubs."""
        inventory = (
            self.project_root
            / "openspec"
            / "docs"
            / "migration"
            / "M0-inventory.md"
        )
        content = inventory.read_text(encoding="utf-8")
        assert "过渡依赖" in content or "stub" in content.lower(), (
            "M0-inventory.md must list transition stubs (quantlitellm.py, get_model_info.py) "
            "per 02-implementation-guide.md Section 6.4."
        )

    def test_m0_inventory_has_old_pipeline_section(self):
        """M0 inventory must explain the current main pipeline and old service status."""
        inventory = (
            self.project_root
            / "openspec"
            / "docs"
            / "migration"
            / "M0-inventory.md"
        )
        content = inventory.read_text(encoding="utf-8")
        assert "旧链路" in content or "主链路" in content, (
            "M0-inventory.md must document old pipeline status per "
            "02-implementation-guide.md Section 6.4.3."
        )

    def test_m0_does_not_claim_runtime_is_ready(self):
        """Ensure M0 inventory does not overclaim."""
        inventory = (
            self.project_root
            / "openspec"
            / "docs"
            / "migration"
            / "M0-inventory.md"
        )
        content = inventory.read_text(encoding="utf-8")
        forbidden_claims = [
            "runtime 已可用",
            "迁移已完成",
            "runtime 可运行",
            "runtime 已就绪",
        ]
        for claim in forbidden_claims:
            assert claim not in content, (
                f"M0-inventory.md must not claim '{claim}'. "
                "M0 only does inventory; M1+ does actual integration."
            )
