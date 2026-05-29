from app.services.sentence_chunker import SentenceChunker
import time

c = SentenceChunker(char_threshold=1000, time_threshold_ms=100)
c.feed("hello")
c._last_feed_time = time.time() - 0.2
elapsed = (time.time() - c._last_feed_time) * 1000
print(f"Elapsed: {elapsed}ms, threshold: {c.time_threshold_ms}ms")
print(f"Buffer before: {repr(c._buffer)}")

chunks = c._timed_flush()
print(f"Chunks: {chunks}")
print(f"Buffer after: {repr(c._buffer)}")
