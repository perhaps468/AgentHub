const PROTOCOL_TAGS = [
  'thinking',
  'action',
  'context_analysis',
  'execution_analysis',
  'decision_matrix',
  'memory_pad',
  'task_complete',
  'answer',
]

function collapseWhitespace(text: string): string {
  // 保留 \n\n 作为段落分隔符，只合并同一行内的空白
  return text.replace(/[ \t]+\n/g, '\n').replace(/[ \t]{2,}/g, ' ').trim()
}

export function normalizeRuntimeTextForDisplay(text: string | null | undefined): string {
  if (!text) return ''

  const trimmed = text.trim()
  if (!trimmed) return ''

  const lowered = trimmed.toLowerCase()
  const looksLikeProtocol = PROTOCOL_TAGS.some(
    (tag) => lowered.includes(`<${tag}`) || lowered.includes(`</${tag}`),
  )

  if (!looksLikeProtocol) {
    return text
  }

  const preferredMatches = [
    /<answer[^>]*>([\s\S]*?)<\/answer>/i,
    /<execution_analysis[^>]*>([\s\S]*?)<\/execution_analysis>/i,
    /<decision_matrix[^>]*>([\s\S]*?)<\/decision_matrix>/i,
    /<memory_pad[^>]*>([\s\S]*?)<\/memory_pad>/i,
    /<context_analysis[^>]*>([\s\S]*?)<\/context_analysis>/i,
    /<thinking[^>]*>([\s\S]*?)<\/thinking>/i,
  ]

  for (const pattern of preferredMatches) {
    const match = trimmed.match(pattern)
    if (match?.[1]) {
      const stripped = collapseWhitespace(match[1].replace(/<[^>]+>/g, ' '))
      if (stripped) return stripped
    }
  }

  const stripped = collapseWhitespace(trimmed.replace(/<!--[\s\S]*?-->/g, ' ').replace(/<[^>]+>/g, ' '))
  return stripped || text
}

/**
 * Detects whether a chunk contains only low-signal content (no user-visible text).
 *
 * Low-signal patterns:
 * - Pure markdown headers with no visible content after them (e.g. "####", "# 标题")
 * - Whitespace-only strings
 * - Pure protocol XML tags (e.g. "<thinking></thinking>", "<action></action>")
 *
 * NOT low-signal:
 * - Any chunk that contains at least one visible character (Chinese, English, etc.)
 * - Mixed content where low-signal prefix is followed by real content
 */
const KNOWN_PROTOCOL_KEYWORDS = ['thinking', 'action', 'execution_analysis', 'decision_matrix', 'context_analysis', 'memory_pad', 'task_complete', 'answer']

export function isLowSignalChunk(chunk: string | null | undefined): boolean {
  if (!chunk) return true

  const trimmed = chunk.trim()
  if (!trimmed) return true

  // Strip protocol XML tags and collapse
  const stripped = trimmed.replace(/<!--[\s\S]*?-->/g, ' ').replace(/<[^>]+>/g, ' ')
  const collapsed = stripped.replace(/\s+/g, ' ').trim()

  // If nothing remains after stripping XML, it's low-signal
  if (!collapsed) return true

  // If the remaining text is only common protocol keywords, it's low-signal
  const words = collapsed.toLowerCase().split(/\s+/)
  const allProtocol = words.length > 0 && words.every(w => KNOWN_PROTOCOL_KEYWORDS.includes(w))
  if (allProtocol) return true

  // If removing markdown symbols leaves no visible characters, it's low-signal
  const semantic = collapsed.replace(/[#>*`_\-\s~=\[\]\(\)\.:!|]+/g, '')
  if (!semantic) return true

  return false
}

/**
 * Filters out low-signal chunks from an array of streaming chunks.
 * Useful for pre-filtering before rendering.
 */
export function filterLowSignalChunks(chunks: (string | null | undefined)[]): string[] {
  return chunks.filter((chunk) => !isLowSignalChunk(chunk))
}

/**
 * Accumulates an array of chunks into a single string, skipping leading
 * low-signal chunks. Does NOT skip low-signal chunks that appear between
 * meaningful chunks (those are preserved for visual continuity).
 *
 * Used during streaming: ensures the user does not see "####" as the first
 * visible text, while keeping any structural markers that appear mid-stream.
 */
export function accumulateAndFilterStreaming(chunks: (string | null | undefined)[]): string {
  const filtered = filterLowSignalChunks(chunks)
  return filtered.join('')
}
