# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PlannedTask:
    title: str
    assigned_agent_id: str
    goal: str
    input_payload: dict
    kind: str = "file_write"


_LANG_SUFFIX_MAP = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".R": "r",
    ".lua": "lua",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".ps1": "powershell",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
    ".csv": "csv",
    ".vue": "vue",
    ".svelte": "svelte",
}

_ACTION_WORDS = re.compile(r"(?:创建|create|新增|add|添加|生成|make|写一个|写个|帮我写一个|帮我写个)", re.IGNORECASE)
_SEMICOLON = re.compile(r"(?:；|;)\s*")
_FILENAME_PATTERN = re.compile(r"([a-zA-Z_][a-zA-Z0-9_\-./\\]*\.[a-zA-Z]+)")
_CONTENT_SEPARATORS = ["内容为", "内容是", "内容:", "内容："]


def _extract_target_path(raw_segment: str) -> Optional[str]:
    segment = raw_segment.strip()
    segment = _ACTION_WORDS.sub("", segment).strip()

    for sep in _CONTENT_SEPARATORS:
        if sep in segment:
            segment = segment.split(sep)[0].strip()

    if len(segment) < 2:
        return None

    quoted = re.search(r"['\"]([^'\"]+)['\"]", segment)
    if quoted:
        candidate = quoted.group(1).strip()
        if candidate:
            return candidate

    filename_pattern = _FILENAME_PATTERN.search(segment)
    if filename_pattern:
        candidate = filename_pattern.group(1).strip()
        if candidate:
            return candidate

    return None


def _infer_language(target_path: str) -> Optional[str]:
    if not target_path:
        return None

    basename = target_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
    for suffix, lang in _LANG_SUFFIX_MAP.items():
        if basename.endswith(suffix.lower()):
            return lang
    return None


def _infer_content_kind(target_path: str, raw_segment: str) -> str:
    segment_lower = raw_segment.lower()
    greeting_indicators = ["hello world", "helloworld", "hello.py", "world", "你好"]
    if any(ind in segment_lower for ind in greeting_indicators):
        return "greeting"

    code_indicators = [
        "class ", "function ", "def ", "func ", "fn ", "public ", "private ",
        "import ", "from ", "const ", "let ", "var ", "return ",
        "if ", "for ", "while ", "switch ", "try ", "except ",
    ]
    if any(kw in segment_lower for kw in code_indicators):
        return "code"

    return "template"


def _normalize_title(raw_segment: str, target_path: Optional[str]) -> str:
    segment = raw_segment.strip()
    for sep in _CONTENT_SEPARATORS:
        if sep in segment:
            segment = segment.split(sep)[0].strip()
            break

    if target_path:
        basename = target_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return f"创建 {basename}"

    segment = segment.strip("，。:： ")
    if len(segment) > 30:
        segment = segment[:30] + "..."
    if not segment:
        return "新建任务"
    return f"任务: {segment}"


def _round_robin_assign(agent_ids: list[str], task_count: int) -> list[str]:
    if not agent_ids:
        return []
    if len(agent_ids) == 1:
        return [agent_ids[0]] * task_count
    return [agent_ids[i % len(agent_ids)] for i in range(task_count)]


def _build_segment_from_filename(message: str, filename: str, next_filename: str | None) -> str:
    start = message.find(filename)
    if start < 0:
        return filename

    action_positions = [pos for pos in (
        message.rfind("创建", 0, start),
        message.rfind("写一个", 0, start),
        message.rfind("写个", 0, start),
        message.rfind("帮我写一个", 0, start),
        message.rfind("帮我写个", 0, start),
    ) if pos >= 0]
    segment_start = min(action_positions) if action_positions else start

    if next_filename:
        next_start = message.find(next_filename, start + len(filename))
        segment_end = next_start if next_start > start else len(message)
    else:
        segment_end = len(message)

    segment = message[segment_start:segment_end].strip("，。:： ")
    if "创建" not in segment and "写" not in segment:
        segment = f"创建 {segment}"
    return segment


def _split_by_multiple_filenames(part: str) -> list[str]:
    filenames = []
    for match in _FILENAME_PATTERN.findall(part):
        if match not in filenames:
            filenames.append(match)

    if len(filenames) < 2:
        return [part]

    segments: list[str] = []
    for index, filename in enumerate(filenames):
        next_filename = filenames[index + 1] if index + 1 < len(filenames) else None
        segment = _build_segment_from_filename(part, filename, next_filename)
        if segment:
            segments.append(segment)
    return segments or [part]


def _split_into_task_segments(message: str) -> list[str]:
    parts = _SEMICOLON.split(message)
    segments: list[str] = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        matches = list(_ACTION_WORDS.finditer(part))
        if len(matches) > 1:
            for index, match in enumerate(matches):
                next_start = matches[index + 1].start() if index < len(matches) - 1 else len(part)
                segment = part[match.start():next_start].strip("，。:： ")
                if segment:
                    segments.append(segment)
            continue

        segments.extend(_split_by_multiple_filenames(part))

    return segments


def _create_task_from_segment(segment: str, index: int) -> PlannedTask | None:
    target_path = _extract_target_path(segment)
    language = _infer_language(target_path or "")
    content_kind = _infer_content_kind(target_path or "", segment)
    title = _normalize_title(segment, target_path)

    requested_content = ""
    for sep in _CONTENT_SEPARATORS:
        if sep in segment:
            requested_content = segment.split(sep, 1)[1].strip()
            break

    if not target_path and not requested_content and not content_kind:
        return None

    return PlannedTask(
        title=title,
        assigned_agent_id="",
        goal=f"完成：{title}",
        input_payload={
            "target_path": target_path or "",
            "content_kind": content_kind,
            "language": language or "text",
            "requested_content": requested_content,
            "raw_segment": segment,
            "index": index,
        },
    )


def plan_tasks_from_message(user_message: str, agent_ids: list[str]) -> list[PlannedTask]:
    if not _ACTION_WORDS.findall(user_message):
        return []

    segments = _split_into_task_segments(user_message)
    tasks: list[PlannedTask] = []
    for idx, segment in enumerate(segments):
        task = _create_task_from_segment(segment, idx + 1)
        if task is not None:
            tasks.append(task)

    if not tasks:
        return []

    if len(agent_ids) == 1:
        assignments = [agent_ids[0]] * len(tasks)
    elif len(agent_ids) > 1:
        assignments = [agent_ids[0]] * len(tasks)
    else:
        assignments = []

    return [
        PlannedTask(
            title=task.title,
            assigned_agent_id=agent_id,
            goal=task.goal,
            input_payload=task.input_payload,
            kind=task.kind,
        )
        for task, agent_id in zip(tasks, assignments)
    ]
