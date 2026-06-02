# -*- coding: utf-8 -*-
"""Task D-2: Self-Repair 状态机定义。

本文档定义 self-repair 的状态机和事件结构。

状态定义 (4.6):
- IDLE: 空闲，等待任务
- ANALYZING_FAILURE: 分析失败原因
- GENERATING_FIX: 生成修复方案
- AWAITING_CONFIRMATION: 等待用户确认
- APPLYING_FIX: 应用修复
- RERUNNING_COMMAND: 重新运行命令
- FINISHED: 完成（成功或失败）
- ERROR: 错误状态

最大重试次数: MAX_REPAIR_RETRY (默认 3)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class RepairState(str, Enum):
    """Self-repair 状态枚举。"""

    IDLE = "IDLE"
    ANALYZING_FAILURE = "ANALYZING_FAILURE"
    GENERATING_FIX = "GENERATING_FIX"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    APPLYING_FIX = "APPLYING_FIX"
    RERUNNING_COMMAND = "RERUNNING_COMMAND"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


# 默认最大重试次数
MAX_REPAIR_RETRY = 3


@dataclass
class RepairStateEvent:
    """D-2: Self-repair 状态变化事件。

    属性:
        type: 事件类型，固定为 "repair_state"
        state: 当前状态
        attempt: 当前尝试次数
        max_attempts: 最大尝试次数
        message: 状态描述信息
        stream_id: 流 ID
        message_id: 消息 ID
        timestamp: ISO8601 时间戳
    """

    type: str = "repair_state"
    state: str = RepairState.IDLE.value
    attempt: int = 0
    max_attempts: int = MAX_REPAIR_RETRY
    message: str = ""
    stream_id: str = ""
    message_id: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """转换为字典用于 JSON 序列化。"""
        return {
            "type": self.type,
            "state": self.state,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "message": self.message,
            "stream_id": self.stream_id,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
        }


@dataclass
class RepairStateMachine:
    """D-2: Self-repair 状态机。

    管理 self-repair 的状态转换和重试逻辑。
    """

    state: RepairState = RepairState.IDLE
    attempt: int = 0
    max_attempts: int = MAX_REPAIR_RETRY
    last_error: str = ""
    _history: list[RepairState] = field(default_factory=list)

    # 允许的状态转移映射
    _valid_transitions: dict[RepairState, set[RepairState]] = field(default_factory=lambda: {
        RepairState.IDLE: {RepairState.ANALYZING_FAILURE, RepairState.ERROR},
        RepairState.ANALYZING_FAILURE: {RepairState.GENERATING_FIX, RepairState.ERROR, RepairState.FINISHED},
        RepairState.GENERATING_FIX: {RepairState.AWAITING_CONFIRMATION, RepairState.ERROR},
        RepairState.AWAITING_CONFIRMATION: {RepairState.APPLYING_FIX, RepairState.IDLE},
        RepairState.APPLYING_FIX: {RepairState.RERUNNING_COMMAND, RepairState.ERROR},
        RepairState.RERUNNING_COMMAND: {RepairState.FINISHED, RepairState.ANALYZING_FAILURE, RepairState.ERROR},
        RepairState.FINISHED: {RepairState.IDLE},
        RepairState.ERROR: {RepairState.ANALYZING_FAILURE, RepairState.FINISHED, RepairState.IDLE},
    })

    def transition(self, new_state: RepairState) -> bool:
        """状态转移。

        Args:
            new_state: 目标状态

        Returns:
            True 如果转移成功，否则 False
        """
        if new_state not in self._valid_transitions.get(self.state, set()):
            return False

        self._history.append(self.state)
        self.state = new_state

        # 重置逻辑
        if new_state == RepairState.ANALYZING_FAILURE:
            self.last_error = ""

        return True

    def increment_attempt(self) -> None:
        """增加尝试次数。"""
        self.attempt += 1

    def is_exhausted(self) -> bool:
        """检查是否已达到最大重试次数。"""
        return self.attempt >= self.max_attempts

    def should_continue(self) -> bool:
        """判断是否应该继续修复。

        条件:
        - 未达到最大重试次数
        - 当前状态不是 FINISHED 或 ERROR
        """
        if self.is_exhausted():
            return False
        if self.state in (RepairState.FINISHED, RepairState.ERROR):
            return False
        return True

    def get_event(self, message: str = "") -> RepairStateEvent:
        """获取当前状态的事件。

        Args:
            message: 状态描述信息

        Returns:
            RepairStateEvent 对象
        """
        return RepairStateEvent(
            state=self.state.value,
            attempt=self.attempt,
            max_attempts=self.max_attempts,
            message=message or self.state.value,
            stream_id="",
            message_id="",
        )

    def reset(self) -> None:
        """重置状态机到初始状态。"""
        self.state = RepairState.IDLE
        self.attempt = 0
        self.last_error = ""
        self._history.clear()

    def get_history(self) -> list[str]:
        """获取状态转移历史。"""
        return [s.value for s in self._history]
