import re

STRONG_BOUNDARIES = re.compile(r"([。！？!?;；]\s*|(\n\s*){2,})")

# Test semicolon
print("Semicolon test:")
for m in STRONG_BOUNDARIES.finditer("abc;def"):
    print(f"  match: {repr(m.group())}, span: {m.span()}")

# Test double newline
print("Double newline test:")
text = "abc\n\ndef"
for m in STRONG_BOUNDARIES.finditer(text):
    print(f"  match: {repr(m.group())}, span: {m.span()}")

# Test single newline
print("Single newline test:")
text2 = "abc\ndef"
for m in STRONG_BOUNDARIES.finditer(text2):
    print(f"  match: {repr(m.group())}, span: {m.span()}")

# Now test the chunker
from app.services.sentence_chunker import SentenceChunker

c = SentenceChunker()
chunks = c.chunk_stream(["abc", "def"])
print(f"chunk_stream(['abc', 'def']) = {chunks}")

chunks2 = c.chunk_stream(["abc", "123", "def"])
print(f"chunk_stream(['abc', '123', 'def']) = {chunks2}")
