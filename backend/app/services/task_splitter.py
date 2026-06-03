# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PlannedTask:
    title: str
    assigned_agent_id: str
    goal: str
    input_payload: dict
    kind: str = "file_write"


_TRIGGER_PATTERN = re.compile(r"(?:创建|create|新增|添加)\s+([^\n；;。]+)", re.IGNORECASE)
_CONNECTOR_PATTERN = re.compile(r"\s+(?:and|then|并且|然后)\s+", re.IGNORECASE)
_FILE_PREFIX_PATTERN = re.compile(r"^(?:file|文件)\s+", re.IGNORECASE)


def _normalize_title(raw: str) -> str:
    title = raw.strip().strip("，,。. ")
    if title.lower().startswith("create "):
        title = title[7:].strip()
    if title.startswith("创建"):
        title = title[2:].strip()
    title = _FILE_PREFIX_PATTERN.sub("", title)
    return title.strip()


def plan_tasks_from_message(user_message: str, agent_ids: list[str]) -> list[PlannedTask]:
    raw_matches = _TRIGGER_PATTERN.findall(user_message)
    if not raw_matches:
        return []

    assigned_agent_id = agent_ids[0] if agent_ids else "primary_pm_agent"
    tasks: list[PlannedTask] = []
    index = 1

    for raw_match in raw_matches:
        segments = [segment.strip() for segment in _CONNECTOR_PATTERN.split(raw_match) if segment.strip()]
        for segment in segments:
            title = _normalize_title(segment)
            if not title:
                continue
            tasks.append(
                PlannedTask(
                    title=f"Task {index}: {title}",
                    assigned_agent_id=assigned_agent_id,
                    goal=f"完成：{title}",
                    input_payload={"raw": title, "index": index},
                )
            )
            index += 1

    return tasks
