from dataclasses import replace

from app.agents.builtin import PM_AGENT_SYSTEM_PROMPT, BuiltinAgent

from app.core.config import get_settings

_agents: dict[str, BuiltinAgent] = {}


def _register_agent(agent: BuiltinAgent) -> None:
    _agents[agent.id] = agent


def get_agent(agent_id: str) -> BuiltinAgent | None:
    return _agents.get(agent_id)


def get_default_agent() -> BuiltinAgent:
    agent = _agents["pm_agent"]
    return replace(agent, model=get_settings().qwen_model)


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


_init_registry()
