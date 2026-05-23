from fastapi import APIRouter

from app.agents.registry import get_default_agent

router = APIRouter(tags=["agents"])


@router.get("/api/agents/default")
def get_default_agent_endpoint():
    agent = get_default_agent()
    return agent.display_dict
