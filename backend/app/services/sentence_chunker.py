"""句段聚合器 (Sentence Chunking)。

将 Provider 输出的原始文本 delta 聚合为"句段级 chunk"。

Flush 规则：
1. 命中强边界即 flush：。！？!?；;\n\n（双换行）
2. 强边界未命中但累计字符达到阈值时 flush。
3. 流结束时剩余 buffer 全部 flush。
"""

import re
import time
from dataclasses import dataclass, field


STRONG_BOUNDARIES = re.compile(
    r"(。|！|？|!|\?|;|；)\s*|(\n\s*){2,}"
)


@dataclass
class SentenceChunker:
    """句段聚合器。

    Attributes:
        char_threshold: 兜底 flush 字符阈值，默认 50。
        time_threshold_ms: 兜底 flush 时间阈值（毫秒），默认 700。
            设为 0 可禁用时间阈值。
    """

    char_threshold: int = 50
    time_threshold_ms: int = 700
    _buffer: str = field(default="", repr=False)
    _last_feed_time: float = field(default=0.0, repr=False)

    def feed(self, delta: str) -> list[str]:
        """追加文本增量，返回 flush 出的句段列表。"""
        self._last_feed_time = time.time()
        self._buffer += delta
        return self._flush()

    def flush(self, force: bool = False) -> list[str]:
        """强制 flush 当前 buffer。

        Args:
            force: 为 True 时无条件返回 buffer 内容（流结束时使用）。
                   为 False 时只返回达到触发条件的内容（正常 feed 循环中使用）。
        """
        if force:
            result = self._flush()
            if self._buffer:
                result.append(self._buffer)
                self._buffer = ""
            return result
        return self._flush()

    def chunk_stream(self, deltas: list[str]) -> list[str]:
        """将多个 delta 依次 feed 并全部 flush，返回所有句段。"""
        result: list[str] = []
        for delta in deltas:
            result.extend(self.feed(delta))
        result.extend(self.flush(force=True))
        return result

    def _flush(self) -> list[str]:
        chunks: list[str] = []

        while True:
            if not self._buffer:
                break

            m = STRONG_BOUNDARIES.search(self._buffer)
            if m:
                end = m.end()
                chunks.append(self._buffer[:end])
                self._buffer = self._buffer[end:]
                self._last_feed_time = time.time()
                continue

            if len(self._buffer) >= self.char_threshold:
                chunks.append(self._buffer[: self.char_threshold])
                self._buffer = self._buffer[self.char_threshold :]
                self._last_feed_time = time.time()
                continue

            break

        return chunks

    def _timed_flush(self) -> list[str]:
        """如果距上次 feed 超过 time_threshold_ms 则 flush buffer。"""
        if self.time_threshold_ms <= 0 or not self._buffer:
            return []
        elapsed = (time.time() - self._last_feed_time) * 1000
        if elapsed >= self.time_threshold_ms:
            result = self._flush()
            if self._buffer:
                result.append(self._buffer)
                self._buffer = ""
            return result
        return []
