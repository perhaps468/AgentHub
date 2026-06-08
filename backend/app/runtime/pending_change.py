"""Unified PendingChange / Patch data structure for AgentHub runtime write tools.

M6 scope: All write-related tools (replace_in_file / unified_diff / write_file)
must produce a consistent PendingChange structure so that:
- The agent can display structured diffs to users
- A separate apply path (M7) can consume these structures
- No tool directly overwrites files by default
"""

import difflib
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class ChangeOperation(str, Enum):
    """The type of change being proposed."""

    CREATE = "create"   # New file
    UPDATE = "update"  # Modify existing file
    DELETE = "delete"  # Remove file
    RENAME = "rename"  # Move/rename file (future use)


class ChangeStatus(str, Enum):
    """The status of a pending change."""

    PREVIEW = "preview"   # Computed but not committed
    PENDING = "pending"   # Committed to apply queue (M7)
    APPLIED = "applied"   # Successfully written (M7)
    REJECTED = "rejected"  # User rejected / apply failed (M7)


@dataclass
class PendingChange:
    """Represents a proposed file change.

    All write tools produce this structure. It is never directly written
    to disk; it is returned to the agent as a structured preview.
    The apply() method is for testing and M7 integration only.

    Attributes:
        change_id: Unique identifier for this change.
        path: Absolute path of the target file (must be within workspace).
        operation: The type of change (create / update / delete).
        original_content: The file's current content (None for new files).
        proposed_content: The proposed new content (None for deletions).
        unified_diff: Human-readable unified diff string (computed on demand).
        status: Current status (always 'preview' in M6).
        error: Error message if the change could not be computed, else None.
        created_at: ISO timestamp when this change was created.
    """

    change_id: str
    path: str
    operation: ChangeOperation
    original_content: Optional[str] = None
    proposed_content: Optional[str] = None
    unified_diff: str = ""
    status: ChangeStatus = ChangeStatus.PREVIEW
    error: Optional[str] = None
    created_at: str = ""
    _diff_computed: bool = field(default=False, repr=False)

    def __post_init__(self):
        if not self.change_id:
            self.change_id = str(uuid.uuid4())[:8]
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        # Task C-3: Auto-compute unified_diff for frontend display
        self._compute_diff()

    def ensure_diff_computed(self) -> None:
        """Ensure unified_diff is computed. Call this before accessing unified_diff."""
        if not self._diff_computed:
            self._compute_diff()

    @property
    def file_path(self) -> str:
        """Alias for path, for compatibility across tool naming conventions."""
        return self.path

    def _compute_diff(self) -> None:
        """Compute unified_diff lazily if not already computed."""
        if self._diff_computed:
            return

        if self.operation == ChangeOperation.DELETE:
            self.unified_diff = ""
        elif self.operation == ChangeOperation.CREATE:
            self.unified_diff = self._make_create_diff()
        elif self.operation == ChangeOperation.UPDATE:
            self.unified_diff = self._make_update_diff()
        else:
            self.unified_diff = ""

        self._diff_computed = True

    def _make_create_diff(self) -> str:
        """Generate unified diff for a new file."""
        if self.proposed_content is None:
            return ""
        path = self.path
        lines = []
        lines.append(f"--- /dev/null")
        lines.append(f"+++ b/{path}")
        line_count = self.proposed_content.count("\n") + (1 if self.proposed_content and not self.proposed_content.endswith("\n") else 0)
        lines.append(f"@@ -0,0 +1,{max(1, line_count)} @@")
        for l in self.proposed_content.splitlines(keepends=True):
            lines.append(f"+{l.rstrip()}")
        return "\n".join(lines)

    def _make_update_diff(self) -> str:
        """Generate unified diff for an updated file."""
        if self.original_content is None or self.proposed_content is None:
            return ""
        path = self.path
        orig_lines = self.original_content.splitlines(keepends=True)
        prop_lines = self.proposed_content.splitlines(keepends=True)

        # Normalize: ensure last line ends with newline for diff
        if orig_lines and not orig_lines[-1].endswith("\n"):
            orig_lines[-1] += "\n"
        if prop_lines and not prop_lines[-1].endswith("\n"):
            prop_lines[-1] += "\n"

        diff = difflib.unified_diff(
            orig_lines,
            prop_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="\n",
        )
        result = "".join(diff)
        return result if result else ""

    def is_error(self) -> bool:
        """Return True if this change represents an error."""
        return self.error is not None

    def is_success(self) -> bool:
        """Return True if this change represents a successful computation."""
        return self.error is None

    def summary(self) -> str:
        """Return a one-line summary suitable for the agent."""
        if self.is_error():
            return f"[Error] {self.error}"
        op_map = {
            ChangeOperation.CREATE: "Create",
            ChangeOperation.UPDATE: "Update",
            ChangeOperation.DELETE: "Delete",
            ChangeOperation.RENAME: "Rename",
        }
        return f"{op_map.get(self.operation, 'Change')} {self.path}: status={self.status.value}"

    def to_display_string(self) -> str:
        """Return a human-readable string describing the change.

        This is what the agent returns to the runtime text stream.
        """
        if self.is_error():
            return f"Error computing change for '{self.path}': {self.error}"

        self._compute_diff()
        lines = [f"[{self.operation.value.upper()}] {self.path}"]

        if self.unified_diff:
            lines.append(self.unified_diff)

        return "\n".join(lines)

    # --------------------------------------------------------------------------
    # PPT 转换：HTML 幻灯片 -> 结构化 PPT JSON
    # --------------------------------------------------------------------------

    def _extract_slide_title(self, slide_html: str) -> str:
        """从单张幻灯片 HTML 中提取标题文字。"""
        import re
        # 优先取 h1/h2，其次取 title 标签
        for tag in ("h1", "h2", "h3"):
            m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", slide_html, re.DOTALL)
            if m:
                return re.sub(r"<[^>]+>", "", m.group(1)).strip()[:20]
        m = re.search(r"<title[^>]*>(.*?)</title>", slide_html, re.DOTALL)
        if m:
            return re.sub(r"<[^>]+>", "", m.group(1)).strip()[:20]
        return "无标题"

    def _extract_bullets(self, slide_html: str) -> list[str]:
        """从单张幻灯片 HTML 中提取要点列表文字。"""
        import re
        bullets: list[str] = []
        # 找所有 <li> 标签文字
        for m in re.finditer(r"<li[^>]*>(.*?)</li>", slide_html, re.DOTALL):
            text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if text:
                bullets.append(text[:50])
        # 找 <p> 标签（排除标题段落）
        if not bullets:
            for m in re.finditer(r"<p[^>]*>(.*?)</p>", slide_html, re.DOTALL):
                text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
                # 跳过只含图片或空白的 p
                if text and len(text) > 4:
                    bullets.append(text[:50])
        return bullets[:5]  # 最多 5 条

    def _guess_img_tag(self, slide_html: str) -> str:
        """根据幻灯片内容猜测 imgTag 主题词。"""
        import re
        text = re.sub(r"<[^>]+>", " ", slide_html).lower()
        if any(k in text for k in ("金融", "银行", "投资", "风控", "财务", "stock", "finance")):
            return "金融"
        if any(k in text for k in ("教育", "学校", "课程", "学习", "课堂", "edu")):
            return "教育"
        if any(k in text for k in ("科技", "ai", "人工智能", "智能", "tech", "code", "算法")):
            return "科技"
        if any(k in text for k in ("医疗", "健康", "医院", "med", "health")):
            return "医疗"
        if any(k in text for k in ("商务", "企业", "公司", "汇报", "business", "meeting")):
            return "商务"
        if any(k in text for k in ("创意", "设计", "艺术", "creative", "design", "color")):
            return "创意"
        if any(k in text for k in ("自然", "环保", "户外", "nature", "green")):
            return "自然"
        return "简约"

    def to_ppt_json(self) -> dict | None:
        """将 HTML 幻灯片内容转换为前端 PptPreviewModel 结构。

        仅当 path 结尾是 .html / .htm 且内容看起来像幻灯片时才转换。
        解析成功返回 dict，失败返回 None（不抛出异常）。
        """
        import re

        if self.is_error():
            return None

        path = (self.path or "").lower()
        if not (path.endswith(".html") or path.endswith(".htm")):
            return None

        content = self.proposed_content or ""
        if not content or len(content) < 200:
            return None

        # 提取各张幻灯片
        slide_pattern = re.compile(
            r'<div\s+class=["\']?slide["\']?[^>]*>(.*?)</div>',
            re.DOTALL | re.IGNORECASE,
        )
        slides = slide_pattern.findall(content)
        if not slides:
            # 兜底：按 <div ...> 分段（不含 class 的 div）
            parts = re.split(r"<div(?:\s[^>]*)?>(?=[\s\S]*?<(?:h1|h2|p|ul|li))", content)
            slides = [p for p in parts if re.search(r"<h[123]|<li|<p[^>]*>", p)]

        if not slides:
            return None

        ppt_data: list[dict] = []
        for idx, slide_html in enumerate(slides):
            title = self._extract_slide_title(slide_html)
            if not title or title == "无标题":
                title = f"第 {idx + 1} 页"
            bullets = self._extract_bullets(slide_html)
            img_tag = self._guess_img_tag(slide_html)
            ppt_data.append({
                "pageTitle": title,
                "pageContent": bullets or ["本页无要点"],
                "imgTag": img_tag,
            })

        if not ppt_data:
            return None

        # 提取文档标题（用于 PPT title）
        doc_title = "演示文稿"
        m = re.search(r"<title[^>]*>(.*?)</title>", content, re.DOTALL)
        if m:
            doc_title = re.sub(r"<[^>]+>", "", m.group(1)).strip()[:30] or doc_title

        return {
            "title": doc_title,
            "slides": ppt_data,
        }

    def apply(self) -> bool:
        """Apply the pending change to disk.

        This is used for testing and M7 integration only.
        Returns True on success, False on failure.

        The method verifies that the file hasn't changed since preview
        (using content hash) before applying.
        """
        if self.is_error():
            return False

        file_path = Path(self.path)

        # Verify original content hasn't changed
        if self.operation == ChangeOperation.UPDATE:
            if file_path.exists():
                current = file_path.read_text(encoding="utf-8")
                if current != self.original_content:
                    self.error = "File was modified after preview; rejecting apply"
                    return False

        try:
            if self.operation == ChangeOperation.DELETE:
                file_path.unlink(missing_ok=True)
            elif self.operation == ChangeOperation.CREATE:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(self.proposed_content or "", encoding="utf-8")
            elif self.operation == ChangeOperation.UPDATE:
                file_path.write_text(self.proposed_content or "", encoding="utf-8")

            self.status = ChangeStatus.APPLIED
            return True
        except Exception as e:
            self.error = f"Failed to apply change: {e}"
            return False

    @classmethod
    def make_update(
        cls,
        path: str,
        original_content: str,
        proposed_content: str,
        error: Optional[str] = None,
    ) -> "PendingChange":
        """Factory: create an UPDATE PendingChange."""
        obj = cls(
            change_id="",
            path=path,
            operation=ChangeOperation.UPDATE,
            original_content=original_content,
            proposed_content=proposed_content,
            error=error,
        )
        obj._compute_diff()
        return obj

    @classmethod
    def make_create(
        cls,
        path: str,
        proposed_content: str,
        error: Optional[str] = None,
    ) -> "PendingChange":
        """Factory: create a CREATE PendingChange."""
        obj = cls(
            change_id="",
            path=path,
            operation=ChangeOperation.CREATE,
            original_content=None,
            proposed_content=proposed_content,
            error=error,
        )
        obj._compute_diff()
        return obj

    @classmethod
    def make_error(cls, path: str, error: str) -> "PendingChange":
        """Factory: create an error PendingChange."""
        return cls(
            change_id="",
            path=path,
            operation=ChangeOperation.UPDATE,
            error=error,
        )
