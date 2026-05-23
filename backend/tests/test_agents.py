import pytest


class TestBuiltinAgentDefinition:
    def test_default_agent_is_pm_agent(self):
        from app.agents.registry import get_default_agent

        agent = get_default_agent()
        assert agent.id == "pm_agent"

    def test_default_agent_name_is_pm_agent(self):
        from app.agents.registry import get_default_agent

        agent = get_default_agent()
        assert agent.name == "PM Agent"

    def test_default_agent_role_is_pm(self):
        from app.agents.registry import get_default_agent

        agent = get_default_agent()
        assert agent.role == "PM"

    def test_default_agent_provider_is_qwen(self):
        from app.agents.registry import get_default_agent

        agent = get_default_agent()
        assert agent.provider == "qwen_openai_compatible"

    def test_default_agent_model_is_qwen_plus_by_default(self):
        from app.agents.registry import get_default_agent

        agent = get_default_agent()
        assert agent.model == "qwen-plus"

    def test_default_agent_has_system_prompt(self):
        from app.agents.registry import get_default_agent

        agent = get_default_agent()
        assert agent.system_prompt is not None
        assert len(agent.system_prompt) > 100
        assert "PM Agent" in agent.system_prompt

    def test_get_agent_by_id(self):
        from app.agents.registry import get_agent

        agent = get_agent("pm_agent")
        assert agent is not None
        assert agent.id == "pm_agent"

    def test_get_agent_unknown_returns_none(self):
        from app.agents.registry import get_agent

        agent = get_agent("unknown_agent")
        assert agent is None


class TestBuiltinAgentDisplayFields:
    """验证注册表返回的字段可用于 GET /api/agents/default 响应。"""

    def test_default_agent_has_id_name_role_avatar(self):
        from app.agents.registry import get_default_agent

        agent = get_default_agent()
        assert hasattr(agent, "id")
        assert hasattr(agent, "name")
        assert hasattr(agent, "role")
        assert hasattr(agent, "avatar_url")
        assert agent.avatar_url is None or isinstance(agent.avatar_url, str)

    def test_default_agent_display_dict_excludes_internal_fields(self):
        from app.agents.registry import get_default_agent

        agent = get_default_agent()
        display = agent.display_dict
        assert "id" in display
        assert "name" in display
        assert "role" in display
        assert "avatar_url" in display
        assert "system_prompt" not in display
        assert "model" not in display
        assert "provider" not in display
