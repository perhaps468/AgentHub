import os
from pathlib import Path
from typing import Dict

from jinja2 import Environment, FileSystemLoader
from loguru import logger

from app.runtime.version import get_version

SYSTEM_PROMPTS: Dict[str, str] = {
    "react": "system_prompt.j2",
    "chat": "chat_system_prompt.j2",
    "code": "code_system_prompt.j2",
    "code_enhanced": "code_2_system_prompt.j2",
    "legal": "legal_system_prompt.j2",
    "legal_enhanced": "legal_2_system_prompt.j2",
    "doc": "doc_system_prompt.j2",
    "default": "system_prompt.j2"
}


def system_prompt(tools: str, environment: str, expertise: str = "", agent_mode: str = "react"):
    """System prompt for the ReAct chatbot with enhanced cognitive architecture.

    Uses a Jinja2 template from the prompts directory based on agent_mode.
    """
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    template_dir = current_dir / 'prompts'
    env = Environment(loader=FileSystemLoader(template_dir))

    template_name = SYSTEM_PROMPTS.get(agent_mode, "system_prompt.j2")
    try:
        template = env.get_template(template_name)
    except Exception as e:
        logger.warning(f"Template {template_name} not found, using default")
        template = env.get_template("system_prompt.j2")

    # chat_system_prompt.j2 expects 'persona' + 'tools_prompt';
    # all other templates expect 'expertise' + 'tools'.
    render_kwargs = {
        "version": get_version(),
        "tools": tools,
        "environment": environment,
        "expertise": expertise,
    }
    if template_name == "chat_system_prompt.j2":
        render_kwargs["persona"] = expertise  # expertise is the persona in chat mode
        render_kwargs["tools_prompt"] = tools
        del render_kwargs["expertise"]
        del render_kwargs["tools"]

    return template.render(**render_kwargs)
