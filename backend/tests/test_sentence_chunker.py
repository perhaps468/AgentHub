"""P1-2-2: 句段聚合器测试。

覆盖：
- 标点 flush：。！？!?；;
- 双换行 flush
- 固定 50 字符阈值 flush
- 固定 700ms 时间阈值 flush
- 流结束尾缓冲 flush
"""

import asyncio
from unittest.mock import MagicMock

import pytest


class TestSentenceChunkerPunctuationFlush:
    """标点 flush 测试。"""

    def _chunker(self):
        from app.services.sentence_chunker import SentenceChunker

        return SentenceChunker()

    def test_fullwidth_period_flushes(self):
        """中文句号 flush。"""
        c = self._chunker()
        chunks = list(c.chunk_stream(["你好", "世界", "。", "下一句。"]))
        assert chunks == ["你好世界。", "下一句。"]

    def test_exclamation_flushes(self):
        """感叹号 flush。"""
        c = self._chunker()
        chunks = list(c.chunk_stream(["太棒了", "！"]))
        assert chunks == ["太棒了！"]

    def test_question_flushes(self):
        """问号 flush。"""
        c = self._chunker()
        chunks = list(c.chunk_stream(["你", "好", "？"]))
        assert chunks == ["你好？"]

    def test_halfwidth_punctuation_flushes(self):
        """半角标点 flush。"""
        c = self._chunker()
        chunks = list(c.chunk_stream(["Wait", ", what", "?"]))
        assert chunks == ["Wait, what?"]

    def test_semicolon_flushes(self):
        """分号 flush。"""
        c = self._chunker()
        chunks = list(c.chunk_stream(["第一句", "；", "第二句"]))
        assert chunks == ["第一句；", "第二句"]


class TestSentenceChunkerDoubleNewlineFlush:
    """双换行 flush 测试。"""

    def _chunker(self):
        from app.services.sentence_chunker import SentenceChunker

        return SentenceChunker()

    def test_double_newline_flushes(self):
        """双换行 flush。"""
        c = self._chunker()
        chunks = list(c.chunk_stream(["第一段", "\n", "\n", "第二段"]))
        assert chunks == ["第一段\n\n", "第二段"]

    def test_single_newline_does_not_flush(self):
        """单换行不 flush。"""
        c = self._chunker()
        chunks = list(c.chunk_stream(["第一行", "\n", "第二行"]))
        assert chunks == ["第一行\n第二行"]


class TestSentenceChunkerCharacterThresholdFlush:
    """固定 50 字符阈值 flush 测试。"""

    def _chunker(self):
        from app.services.sentence_chunker import SentenceChunker

        return SentenceChunker(char_threshold=50)

    def test_50_chars_flushes(self):
        """正好 50 字符 flush。"""
        c = self._chunker()
        text_50 = "a" * 50
        chunks = list(c.chunk_stream([text_50]))
        assert chunks == [text_50]

    def test_under_50_chars_not_auto_flushed(self):
        """低于 50 字符时 feed() 不自动 flush。"""
        c = self._chunker()
        chunks = c.feed("a" * 49)
        assert chunks == []
        assert c._buffer == "a" * 49

    def test_over_50_chars_flushed_and_tail(self):
        """超过 50 字符时 flush 50 字符，剩余 1 字符留在 buffer。"""
        c = self._chunker()
        chunks = c.chunk_stream(["a" * 51])
        # 50 chars flush + tail via flush(force=True)
        assert "a" * 50 in chunks
        assert "a" in chunks

    def test_mixed_threshold_and_punctuation(self):
        """混合：字符阈值和标点同时满足时先按标点 flush。"""
        c = self._chunker()
        text_48 = "a" * 48 + "。"
        chunks = list(c.chunk_stream([text_48]))
        assert chunks == [text_48]


class TestSentenceChunkerTimeThresholdFlush:
    """固定 700ms 时间阈值 flush 测试。

    时间阈值在异步消费场景有意义（流式服务层会并发运行 timer）。
    单元测试中通过 patch asyncio.sleep 来验证 timer 逻辑。
    """

    def _chunker(self):
        from app.services.sentence_chunker import SentenceChunker

        return SentenceChunker()

    def test_time_threshold_flush_triggers(self):
        """当距上次 feed 超过 time_threshold_ms 时触发 flush。"""
        from app.services.sentence_chunker import SentenceChunker

        c = SentenceChunker(char_threshold=1000, time_threshold_ms=100)
        c.feed("hello")
        # Override _last_feed_time to simulate elapsed time
        import time as real_time_module

        c._last_feed_time = real_time_module.time() - 0.15
        chunks = c._timed_flush()
        assert chunks == ["hello"]
        assert c._buffer == ""

    def test_under_time_threshold_no_flush(self):
        """未达到时间阈值时不触发 flush。"""
        from app.services.sentence_chunker import SentenceChunker

        c = SentenceChunker(char_threshold=1000, time_threshold_ms=200)
        c.feed("short")
        assert c._buffer == "short"
        chunks = c._timed_flush()
        assert chunks == []
        assert c._buffer == "short"


class TestSentenceChunkerTailBufferFlush:
    """流结束尾缓冲 flush 测试。"""

    def _chunker(self):
        from app.services.sentence_chunker import SentenceChunker

        return SentenceChunker()

    def test_tail_buffer_flushed_on_finish(self):
        """流结束时剩余 buffer 必须全部 flush。"""
        c = self._chunker()
        chunks = list(c.chunk_stream(["你好", "世界"]))
        assert chunks == ["你好世界"]

    def test_empty_tail_not_yielded(self):
        """空 buffer finish 不产生空 chunk。"""
        c = self._chunker()
        c.feed("only ")
        c.feed("chunk。")
        list(c.flush())
        remaining = list(c.chunk_stream([]))
        assert remaining == []

    def test_trailing_punctuation_in_tail(self):
        """尾缓冲包含标点时 flush 该句段。"""
        c = self._chunker()
        chunks = list(c.chunk_stream(["你好", "世界", "！"]))
        assert chunks == ["你好世界！"]
