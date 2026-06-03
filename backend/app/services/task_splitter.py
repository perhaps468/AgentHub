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


# 语言推断后缀
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

# 动作词正则
_ACTION_WORDS = re.compile(r"(?:创建|create|新增|add|添加|生成|make)", re.IGNORECASE)

# 连接词正则（用于在同一段文本中检测任务分隔）
_CONNECTOR_WORDS = re.compile(
    r"(?:并且|然后|以及|and|then|also|,|，)\s*",
    re.IGNORECASE,
)

# 分号分隔符
_SEMICOLON = re.compile(r"(?:；|;)\s*")


def _extract_target_path(raw_segment: str) -> Optional[str]:
    """从原始片段中提取目标文件路径。

    支持模式：
    - "创建 hello.java" -> "hello.java"
    - "创建 hello.java 文件" -> "hello.java"
    - "创建 'hello.java' 内容为..." -> "hello.java"
    - "创建 hello.java，内容为..." -> "hello.java"
    - "随便聊聊天" -> None
    """
    segment = raw_segment.strip()

    # 去掉动作词前缀
    segment = _ACTION_WORDS.sub("", segment).strip()

    # 去掉"内容为..."后的部分
    for sep in ["内容为", "内容是", "内容:", "内容："]:
        if sep in segment:
            segment = segment.split(sep)[0].strip()

    # 如果剩余部分太短，不是有效文件名
    if len(segment) < 2:
        return None

    # 尝试直接匹配带引号的文件名
    quoted = re.search(r"['\"]([^'\"]+)['\"]", segment)
    if quoted:
        candidate = quoted.group(1).strip()
        if candidate:
            return candidate

    # 寻找带扩展名的文件名模式（如 hello.java, main.ts）
    filename_pattern = re.search(r"([a-zA-Z_][a-zA-Z0-9_\-\./\\]*\.[a-zA-Z]+)", segment)
    if filename_pattern:
        candidate = filename_pattern.group(1).strip()
        if candidate:
            return candidate

    return None


def _infer_language(target_path: str) -> Optional[str]:
    """从文件路径推断语言类型。"""
    if not target_path:
        return None

    # 取最后一部分（小写）
    basename = target_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()

    for suffix, lang in _LANG_SUFFIX_MAP.items():
        if basename.endswith(suffix.lower()):
            return lang

    return None


def _infer_content_kind(target_path: str, raw_segment: str) -> str:
    """推断内容类型。

    常见模式：
    - Hello World / hello world / "Hello World" -> greeting
    - 包含具体代码结构的 -> code
    - 其他 -> template
    """
    segment_lower = raw_segment.lower()

    # Hello World 模式
    greeting_indicators = [
        "hello world",
        "helloworld",
        "hello.py",
        "你好",
        "world",
    ]
    if any(ind in segment_lower for ind in greeting_indicators):
        return "greeting"

    # 包含代码关键字
    code_indicators = [
        "class ", "function ", "def ", "func ", "fn ", "public ", "private ",
        "import ", "from ", "const ", "let ", "var ", "return ",
        "if ", "for ", "while ", "switch ", "try ", "except ",
    ]
    if any(kw in segment_lower for kw in code_indicators):
        return "code"

    return "template"


def _normalize_title(raw_segment: str, target_path: Optional[str]) -> str:
    """生成规范化的任务标题。"""
    segment = raw_segment.strip()

    # 去掉"内容为..."后的部分
    for sep in ["内容为", "内容是", "内容:", "内容："]:
        if sep in segment:
            segment = segment.split(sep)[0].strip()
            break

    # 如果有目标路径，用"创建 {文件名}"作为标题
    if target_path:
        basename = target_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return f"创建 {basename}"

    # 否则截取前 30 个字符，保留动作词
    segment = segment.strip("，,。. ")
    if len(segment) > 30:
        segment = segment[:30] + "..."

    # 如果仍然没有有意义的内容，使用默认值
    if not segment:
        return "新建任务"

    return f"任务: {segment}"


def _round_robin_assign(agent_ids: list[str], task_count: int) -> list[str]:
    """轮询分配 agent。

    若 agent_ids 只有一个元素，则所有 task 都分配给该 agent。
    """
    if not agent_ids:
        return []

    if len(agent_ids) == 1:
        return [agent_ids[0]] * task_count

    # 轮询分配
    assignments = []
    for i in range(task_count):
        assignments.append(agent_ids[i % len(agent_ids)])
    return assignments


def _split_into_task_segments(message: str) -> list[str]:
    """将消息拆分为独立的"任务片段"。

    分割策略：
    1. 按分号分割
    2. 对于每个分片，检测其中的多个"创建/create"动作词
    """
    # 1. 先按分号分割
    parts = _SEMICOLON.split(message)
    segments: list[str] = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # 2. 在分片内寻找"创建"关键字
        matches = list(_ACTION_WORDS.finditer(part))

        if len(matches) > 1:
            # 有多个动作词，需要拆分
            for i, match in enumerate(matches):
                # 当前任务片段：从当前动作词开始，到下一个动作词之前（或字符串末尾）
                if i < len(matches) - 1:
                    # 不是最后一个，到下一个动作词之前
                    next_start = matches[i + 1].start()
                    segment = part[match.start():next_start].strip()
                else:
                    # 最后一个，到字符串末尾
                    segment = part[match.start():].strip()

                if segment:
                    segments.append(segment)
        else:
            # 只有一个动作词，直接添加
            segments.append(part)

    return segments


def _create_task_from_segment(segment: str, index: int) -> PlannedTask | None:
    """从任务片段创建 PlannedTask。

    返回 None 表示该片段不是有效的任务。
    """
    target_path = _extract_target_path(segment)
    language = _infer_language(target_path or "")
    content_kind = _infer_content_kind(target_path or "", segment)
    title = _normalize_title(segment, target_path)

    # 提取用户请求的具体内容（"内容为"后面的部分）
    requested_content = ""
    for sep in ["内容为", "内容是", "内容:", "内容："]:
        if sep in segment:
            requested_content = segment.split(sep, 1)[1].strip()
            break

    # 如果没有提取到任何有意义的内容，跳过
    if not target_path and not requested_content and not content_kind:
        return None

    return PlannedTask(
        title=title,
        assigned_agent_id="",  # 占位，轮询分配时填充
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
    """将用户消息拆分为结构化的 PlannedTask 列表。

    本函数是"文件写入任务规则器"，它从用户请求中提取：
    - 目标文件名
    - 语言/模板意图
    - 稳定的 input_payload: { target_path, content_kind, language, requested_content }

    多 task 场景下，按 agent_ids 轮询分配任务。

    Args:
        user_message: 用户发送的原始消息
        agent_ids: 可用的 agent ID 列表

    Returns:
        PlannedTask 列表，若无法解析出任务则返回空列表

    验收样例:
    - "创建 hello.java，内容为 Java Hello World" -> target_path=hello.java
    - "创建 hello.py，内容为 Python Hello World" -> target_path=hello.py
    - "创建 hello.java，内容为 Java Hello World，并且创建 hello.py，内容为 Python Hello World" -> 2 tasks
    """
    raw_matches = _ACTION_WORDS.findall(user_message)
    if not raw_matches:
        return []

    # 拆分消息为独立的任务片段
    segments = _split_into_task_segments(user_message)

    tasks: list[PlannedTask] = []
    for idx, segment in enumerate(segments):
        task = _create_task_from_segment(segment, idx + 1)
        if task is not None:
            tasks.append(task)

    if not tasks:
        return []

    # 轮询分配 agent
    assignments = _round_robin_assign(agent_ids, len(tasks))

    # 填充 assigned_agent_id
    result: list[PlannedTask] = []
    for task, agent_id in zip(tasks, assignments):
        result.append(
            PlannedTask(
                title=task.title,
                assigned_agent_id=agent_id,
                goal=task.goal,
                input_payload=task.input_payload,
                kind=task.kind,
            )
        )

    return result
