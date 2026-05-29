import { describe, expect, it } from 'vitest'

import {
  normalizeRuntimeTextForDisplay,
  isLowSignalChunk,
  filterLowSignalChunks,
  accumulateAndFilterStreaming,
} from './runtime-text'

describe('normalizeRuntimeTextForDisplay', () => {
  it('extracts visible text from runtime protocol xml', () => {
    expect(
      normalizeRuntimeTextForDisplay(
        '<thinking><execution_analysis>你好，我可以帮你处理这个问题。</execution_analysis></thinking>',
      ),
    ).toBe('你好，我可以帮你处理这个问题。')
  })

  it('keeps normal markdown unchanged', () => {
    expect(normalizeRuntimeTextForDisplay('**hello**')).toBe('**hello**')
  })

  it('does not strip ordinary html-like text when it is not runtime protocol', () => {
    expect(normalizeRuntimeTextForDisplay('<div>hello</div>')).toBe('<div>hello</div>')
  })

  it('extracts answer tag content', () => {
    expect(
      normalizeRuntimeTextForDisplay('<answer>最终答案</answer>'),
    ).toBe('最终答案')
  })

  it('returns empty string for null/undefined', () => {
    expect(normalizeRuntimeTextForDisplay(null)).toBe('')
    expect(normalizeRuntimeTextForDisplay(undefined)).toBe('')
    expect(normalizeRuntimeTextForDisplay('')).toBe('')
  })
})

describe('isLowSignalChunk', () => {
  it('identifies hash-only as low signal', () => {
    expect(isLowSignalChunk('####')).toBe(true)
    expect(isLowSignalChunk('#')).toBe(true)
  })

  it('identifies pure markdown headers as low signal', () => {
    // Pure symbols-only headers: low-signal
    expect(isLowSignalChunk('## ')).toBe(true)
    expect(isLowSignalChunk('###')).toBe(true)
    // "# 标题" contains visible Chinese characters → NOT low-signal
    expect(isLowSignalChunk('# 标题')).toBe(false)
  })

  it('identifies protocol XML tags as low signal', () => {
    // After stripping tags and symbols, empty → low-signal
    expect(isLowSignalChunk('<thinking></thinking>')).toBe(true)
    expect(isLowSignalChunk('<thinking>...</thinking>')).toBe(true)
    expect(isLowSignalChunk('<action></action>')).toBe(true)
  })

  it('identifies whitespace-only as low signal', () => {
    expect(isLowSignalChunk('   ')).toBe(true)
    expect(isLowSignalChunk('\n\n')).toBe(true)
    expect(isLowSignalChunk('\t')).toBe(true)
  })

  it('identifies normal Chinese text as NOT low signal', () => {
    expect(isLowSignalChunk('你好')).toBe(false)
    expect(isLowSignalChunk('你好，世界')).toBe(false)
    expect(isLowSignalChunk('这是正常内容。')).toBe(false)
  })

  it('identifies normal English text as NOT low signal', () => {
    expect(isLowSignalChunk('hello')).toBe(false)
    expect(isLowSignalChunk('Hello world')).toBe(false)
  })

  it('identifies markdown with actual content as NOT low signal', () => {
    expect(isLowSignalChunk('### 标题\n实际内容')).toBe(false)
    expect(isLowSignalChunk('**bold text**')).toBe(false)
    expect(isLowSignalChunk('- item 1\n- item 2')).toBe(false)
  })

  it('identifies mixed low-signal prefix with content as NOT low signal', () => {
    // Header with visible content after it → NOT low-signal
    expect(isLowSignalChunk('#### 正常内容')).toBe(false)
    expect(isLowSignalChunk('## 标题\n正文')).toBe(false)
  })

  it('handles null/undefined', () => {
    expect(isLowSignalChunk(null)).toBe(true)
    expect(isLowSignalChunk(undefined)).toBe(true)
    expect(isLowSignalChunk('')).toBe(true)
  })
})

describe('filterLowSignalChunks', () => {
  it('filters out low-signal chunks', () => {
    const chunks = ['####', '你好', '## ', '正文']
    expect(filterLowSignalChunks(chunks)).toEqual(['你好', '正文'])
  })

  it('returns all chunks when none are low-signal', () => {
    const chunks = ['你好', '世界', '正常内容']
    expect(filterLowSignalChunks(chunks)).toEqual(chunks)
  })

  it('returns empty array when all chunks are low-signal', () => {
    const chunks = ['####', '## ', '   ']
    expect(filterLowSignalChunks(chunks)).toEqual([])
  })

  it('returns empty array for empty input', () => {
    expect(filterLowSignalChunks([])).toEqual([])
  })
})

describe('accumulateAndFilterStreaming', () => {
  it('accumulates and returns meaningful text', () => {
    const chunks = ['你好', '，', '世界', '！']
    expect(accumulateAndFilterStreaming(chunks)).toBe('你好，世界！')
  })

  it('skips leading low-signal chunks', () => {
    const chunks = ['####', '## ', '你好']
    expect(accumulateAndFilterStreaming(chunks)).toBe('你好')
  })

  it('skips all low-signal chunks with no meaningful content', () => {
    const chunks = ['####', '## ', '\n\n']
    expect(accumulateAndFilterStreaming(chunks)).toBe('')
  })

  it('returns empty string for empty input', () => {
    expect(accumulateAndFilterStreaming([])).toBe('')
  })

  it('handles mixed content correctly', () => {
    const chunks = ['####', '你好', '，', '## ', '这是', '正文']
    expect(accumulateAndFilterStreaming(chunks)).toBe('你好，这是正文')
  })

  it('does not skip low-signal chunks between meaningful chunks', () => {
    const chunks = ['你好', '####', '世界']
    expect(accumulateAndFilterStreaming(chunks)).toBe('你好世界')
  })
})
