from dataclasses import replace

from app.agents.builtin import PM_AGENT_SYSTEM_PROMPT, GLM_CODER_SYSTEM_PROMPT, GLM_REVIEWER_SYSTEM_PROMPT, BuiltinAgent

_agents: dict[str, BuiltinAgent] = {}


def _register_agent(agent: BuiltinAgent) -> None:
    _agents[agent.id] = agent


def get_agent(agent_id: str) -> BuiltinAgent | None:
    return _agents.get(agent_id)


def get_default_agent() -> BuiltinAgent:
    agent = _agents["pm_agent"]
    return replace(agent, model="qwen-plus")


def _init_registry() -> None:
    _register_agent(
        BuiltinAgent(
            id="pm_agent",
            name="PM Agent",
            role="PM",
            avatar_url=None,
            provider="qwen_openai_compatible",
            model="qwen-plus",
            system_prompt=PM_AGENT_SYSTEM_PROMPT,
        )
    )
    _register_agent(
        BuiltinAgent(
            id="glm_coder",
            name="GLM Coder",
            role="Coder",
            avatar_url=None,
            provider="glm",
            model="glm-4.7-flash",
            system_prompt=GLM_CODER_SYSTEM_PROMPT,
        )
    )
    _register_agent(
        BuiltinAgent(
            id="glm_reviewer",
            name="GLM Reviewer",
            role="Reviewer",
            avatar_url=None,
            provider="glm",
            model="glm-4.7-flash",
            system_prompt=GLM_REVIEWER_SYSTEM_PROMPT,
        )
    )


_init_registry()
