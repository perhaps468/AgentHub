import { describe, expect, it } from 'vitest'

import { normalizeRuntimeTextForDisplay } from './runtime-text'

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
})
