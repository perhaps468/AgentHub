# -*- coding: utf-8 -*-
"""Task CE: Write Intent Detector.

This module provides high-confidence detection of user messages that indicate
an intent to write files to the workspace. When detected, the runtime enforces
that the response must go through the preview-confirm flow rather than allowing
the model to directly output code as plain text.

From migration doc section 5.1:
- Identifies write file intent with high confidence patterns
- Does NOT directly write files - only produces PendingChange
- Must not bypass existing workspace guard
"""

import re
from dataclasses import dataclass


@dataclass
class WriteIntentResult:
    """Result of write intent detection."""
    is_write_intent: bool
    confidence: float  # 0.0 to 1.0
    matched_patterns: list[str]
    enforcement_guidance: dict


class WriteIntentDetector:
    """Detects user messages with explicit file write intent.

    Detection strategy (high-confidence patterns only):
    - Chinese patterns: "写/生成/创建" + "文件/代码" + "到/保存"
    - English patterns: "write/create/generate" + "file" + "to/save/in"

    NOT triggered by:
    - Regular Q&A (greetings, explanations, questions)
    - Read-only operations (read, list, search)
    - Code explanation requests
    """

    # Chinese write intent patterns (high confidence)
    _CHINESE_WRITE_PATTERNS = [
        # 帮我写...到文件夹里 / 到...里
        re.compile(r"帮我写.+?到.+?里"),
        re.compile(r"帮我写.+?到文件夹"),
        re.compile(r"帮我写.+?到目录"),
        re.compile(r"帮我写.+?保存到"),
        # 写一个/写个 + 文件
        re.compile(r"写.{0,15}个?文件"),
        re.compile(r"写.{0,15}代码"),
        re.compile(r"写入.{0,15}"),
        # 生成文件
        re.compile(r"生成.{0,30}文件"),
        re.compile(r"生成.{0,30}代码"),
        # 创建文件
        re.compile(r"创建.{0,30}文件"),
        re.compile(r"创建.{0,30}代码"),
        # 保存到
        re.compile(r"保存到.{0,30}"),
        # 写到
        re.compile(r"把.+?写到"),
        re.compile(r"把代码写到"),
        # 单独的文件写入 (xxx.py 写入)
        re.compile(r"\w+\.\w+.{0,30}写"),
    ]

    # English write intent patterns (high confidence)
    _ENGLISH_WRITE_PATTERNS = [
        re.compile(r"write.+?file", re.IGNORECASE),
        re.compile(r"write.+?to.{0,20}workspace", re.IGNORECASE),
        re.compile(r"write.+?to.{0,20}folder", re.IGNORECASE),
        re.compile(r"write.+?to.{0,20}directory", re.IGNORECASE),
        re.compile(r"write.+?to.{0,20}project", re.IGNORECASE),
        re.compile(r"create.+?file", re.IGNORECASE),
        re.compile(r"create.+?new.{0,10}file", re.IGNORECASE),
        re.compile(r"generate.+?file", re.IGNORECASE),
        re.compile(r"save.+?to.{0,20}file", re.IGNORECASE),
        re.compile(r"save.+?to.{0,20}project", re.IGNORECASE),
        re.compile(r"save this to a file", re.IGNORECASE),
        re.compile(r"put.+?in a file", re.IGNORECASE),
    ]

    # Patterns that explicitly indicate read-only operations (should NOT trigger)
    _READ_ONLY_PATTERNS = [
        re.compile(r"读取.{0,20}文件"),
        re.compile(r"打开文件"),
        re.compile(r"列出.{0,10}目录"),
        re.compile(r"列出.{0,10}文件"),
        re.compile(r"搜索代码"),
        re.compile(r"查看项目"),
        re.compile(r"read the file", re.IGNORECASE),
        re.compile(r"read file", re.IGNORECASE),
        re.compile(r"list files", re.IGNORECASE),
        re.compile(r"show me the", re.IGNORECASE),
    ]

    # Patterns that indicate explanation (should NOT trigger)
    _EXPLAIN_PATTERNS = [
        re.compile(r"解释.{0,20}代码"),
        re.compile(r"解释.{0,20}这段"),
        re.compile(r"这段代码.{0,10}什么"),
        re.compile(r"帮我理解"),
        re.compile(r"\?$"),  # 简单问句结尾
        re.compile(r"是什么意思"),
        re.compile(r"explain", re.IGNORECASE),
        re.compile(r"what does", re.IGNORECASE),
        re.compile(r"what is", re.IGNORECASE),
        re.compile(r"how does", re.IGNORECASE),
    ]

    def __init__(self):
        self._chinese_patterns = self._CHINESE_WRITE_PATTERNS
        self._english_patterns = self._ENGLISH_WRITE_PATTERNS

    def is_write_intent(self, user_message: str) -> bool:
        """Check if the user message indicates file write intent.

        Args:
            user_message: The user's message to analyze.

        Returns:
            True if write intent is detected with high confidence.
        """
        result = self.detect(user_message)
        return result.is_write_intent

    def detect(self, user_message: str) -> WriteIntentResult:
        """Analyze user message for write intent.

        Args:
            user_message: The user's message to analyze.

        Returns:
            WriteIntentResult with detection details.
        """
        if not user_message or not user_message.strip():
            return WriteIntentResult(
                is_write_intent=False,
                confidence=0.0,
                matched_patterns=[],
                enforcement_guidance=self._get_no_intent_guidance()
            )

        user_message = user_message.strip()
        matched_patterns = []
        base_confidence = 0.0

        # Check for read-only operations first (should NOT trigger)
        for pattern in self._READ_ONLY_PATTERNS:
            if pattern.search(user_message):
                return WriteIntentResult(
                    is_write_intent=False,
                    confidence=0.0,
                    matched_patterns=["read_only_detected"],
                    enforcement_guidance=self._get_no_intent_guidance()
                )

        # Check for explanation requests (should NOT trigger)
        for pattern in self._EXPLAIN_PATTERNS:
            if pattern.search(user_message):
                return WriteIntentResult(
                    is_write_intent=False,
                    confidence=0.0,
                    matched_patterns=["explain_request_detected"],
                    enforcement_guidance=self._get_no_intent_guidance()
                )

        # Check Chinese write patterns
        for pattern in self._chinese_patterns:
            if pattern.search(user_message):
                matched_patterns.append(f"chinese:{pattern.pattern}")
                base_confidence += 0.35

        # Check English write patterns
        for pattern in self._english_patterns:
            if pattern.search(user_message):
                matched_patterns.append(f"english:{pattern.pattern}")
                base_confidence += 0.35

        # Cap confidence at 1.0
        confidence = min(base_confidence, 1.0)

        is_write_intent = confidence >= 0.35

        return WriteIntentResult(
            is_write_intent=is_write_intent,
            confidence=confidence,
            matched_patterns=matched_patterns,
            enforcement_guidance=self._get_enforcement_guidance(is_write_intent)
        )

    def get_confidence_score(self, user_message: str) -> float:
        """Get confidence score for write intent (0.0 to 1.0).

        Args:
            user_message: The user's message to analyze.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        result = self.detect(user_message)
        return result.confidence

    def get_enforcement_guidance(self) -> dict:
        """Get guidance for how to handle write intent enforcement.

        Returns:
            Dict with enforcement guidance.
        """
        return {
            "force_preview": True,
            "require_tool": True,
            "allow_fallback": False,
            "error_on_direct_text": True,
        }

    def _get_enforcement_guidance(self, is_write_intent: bool) -> dict:
        """Get enforcement guidance based on detection result."""
        if is_write_intent:
            return {
                "force_preview": True,
                "require_tool": True,
                "allow_fallback": False,
                "error_on_direct_text": True,
                "message": "Write intent detected: response must use PendingChange preview flow"
            }
        return self._get_no_intent_guidance()

    def _get_no_intent_guidance(self) -> dict:
        """Get default guidance when no write intent detected."""
        return {
            "force_preview": False,
            "require_tool": False,
            "allow_fallback": True,
            "error_on_direct_text": False,
        }
