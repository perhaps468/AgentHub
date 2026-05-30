<template>
  <span v-if="isArrayContents" class="text-msg">
    <template v-for="item in contents" :key="item.id">
      <span v-if="item.type === TextContentType.At" class="text-msg-at">
        {{ `@${getUserInfo(item.content).name}` }}
      </span>
      <span
        v-else-if="item.type === TextContentType.Text"
        v-html="parseMarkdown(item.content)"
      ></span>
    </template>
  </span>
  <div v-else-if="hasDiffPreview" class="diff-wrapper">
    <DiffPreview
      v-for="diff in parsedDiffs"
      :key="diff.change_id"
      :change="diff"
      @confirm="handleConfirmDiff"
      @cancel="handleCancelDiff"
    />
    <div v-if="nonDiffContent" v-html="parseMarkdown(nonDiffContent)"></div>
  </div>
  <div v-else v-html="parseMarkdown(displayContent)"></div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

import { TextContentType } from '../../types/textContentType'
import { normalizeRuntimeTextForDisplay, accumulateAndFilterStreaming, isLowSignalChunk } from '../../utils/runtime-text'
import type { PendingChange } from '../../types/agenthub'
import DiffPreview from './DiffPreview.vue'

marked.setOptions({
  breaks: true,
  gfm: true,
})

const parseMarkdown = (text) => {
  if (!text) return ''

  try {
    const normalizedText = normalizeRuntimeTextForDisplay(text)
    const rawHtml = marked.parse(normalizedText)
    return DOMPurify.sanitize(rawHtml)
  } catch {
    return normalizeRuntimeTextForDisplay(text)
  }
}

const props = defineProps<{
  msg: {
    message?: string
    pending_diffs?: PendingChange[]
  }
  right?: boolean
}>()

const emit = defineEmits<{
  (e: 'confirmDiff', changeId: string): void
  (e: 'cancelDiff', changeId: string): void
}>()

const contents = ref()
const _rawMessage = ref('')

/**
 * Parse diff content from message text.
 * Detects unified diff format in the message and extracts pending change info.
 */
interface ParsedDiff {
  change_id: string
  operation: 'create' | 'update' | 'delete'
  path: string
  unified_diff: string
  status: 'pending_confirmation' | 'applied' | 'rejected'
  stream_id?: string
  message_id?: string
}

const parseDiffsFromText = (text: string): ParsedDiff[] => {
  const diffs: ParsedDiff[] = []

  // Pattern to match CREATE/UPDATE diff blocks
  const diffPattern = /\[(CREATE|UPDATE|DELETE)\]\s*(.+?)(?=\[CREATE\]|\[UPDATE\]|\[DELETE\]|$)/gs
  let match

  while ((match = diffPattern.exec(text)) !== null) {
    const operation = match[1].toLowerCase() as 'create' | 'update' | 'delete'
    const diffContent = match[2].trim()

    // Extract file path from diff (looks for +++ b/path pattern)
    const pathMatch = diffContent.match(/\+\+\+ b\/(.+)/)
    const path = pathMatch ? pathMatch[1] : 'unknown'

    // Extract change_id if present (looks for (change_id=xxx))
    const changeIdMatch = diffContent.match(/\(change_id=([a-zA-Z0-9-]+)\)/)
    const change_id = changeIdMatch ? changeIdMatch[1] : `diff-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

    // Check if already applied
    const isApplied = diffContent.includes('[Applied]') || diffContent.includes('[applied]')

    diffs.push({
      change_id,
      operation,
      path,
      unified_diff: diffContent,
      status: isApplied ? 'applied' : 'pending_confirmation',
    })
  }

  return diffs
}

// Check if message has diff content
const hasDiffPreview = computed(() => {
  if (props.msg?.pending_diffs?.length) return true
  const text = props.msg?.message || ''
  return /\[(CREATE|UPDATE|DELETE)\]/i.test(text) && /(\+\+\+ b\/|--- \/dev\/null)/.test(text)
})

// Parse diffs from props or text
const parsedDiffs = computed((): ParsedDiff[] => {
  // First check for explicit pending_diffs
  if (props.msg?.pending_diffs?.length) {
    return props.msg.pending_diffs.map(d => ({
      change_id: d.change_id,
      operation: d.operation,
      path: d.path,
      unified_diff: d.unified_diff,
      status: d.status,
      stream_id: d.stream_id,
      message_id: d.message_id,
    }))
  }

  // Otherwise parse from text
  const text = props.msg?.message || ''
  return parseDiffsFromText(text)
})

// Get non-diff content (message text without diff blocks)
const nonDiffContent = computed(() => {
  if (props.msg?.pending_diffs?.length) return ''
  const text = props.msg?.message || ''

  // Remove diff blocks from text
  return text.replace(/\[(CREATE|UPDATE|DELETE)\]\s*.+?(?=\[CREATE\]|\[UPDATE\]|\[DELETE\]|$)/gs, '').trim()
})

/**
 * Accumulated streaming content with leading low-signal chunks filtered out.
 * This ensures users do not see "####" flash at the start of a streaming message.
 * Once meaningful content has been seen, subsequent content is displayed as-is
 * to preserve visual continuity (e.g. markdown headers mid-stream).
 */
const displayContent = computed(() => {
  const raw = _rawMessage.value
  if (!raw) return ''

  // If we have diffs, don't show the raw diff text
  if (hasDiffPreview.value) return ''

  const chunks = Array.from(raw)
  const filtered = chunks.reduce((acc, chunk) => {
    const current = acc + chunk
    if (!acc && isLowSignalChunk(current)) {
      return ''
    }
    return current
  }, '')

  return filtered || raw
})

watch(
  () => props.msg,
  (msg) => {
    _rawMessage.value = ''
    try {
      contents.value = JSON.parse(msg?.message).map((item) => {
        if (typeof item.content === 'string') {
          try {
            item.content = JSON.parse(item.content)
          } catch {
          }
        }
        return item
      })
    } catch {
      contents.value = msg?.message
    }
    if (typeof msg?.message === 'string') {
      _rawMessage.value = msg.message
    }
  },
  { immediate: true },
)

const isArrayContents = computed(() => Array.isArray(contents.value))

const getUserInfo = (content) => {
  try {
    if (typeof content === 'object') {
      return content
    }
    return JSON.parse(content)
  } catch {
    return content
  }
}

// Handle diff confirm/cancel events
const handleConfirmDiff = (changeId: string) => {
  emit('confirmDiff', changeId)
}

const handleCancelDiff = (changeId: string) => {
  emit('cancelDiff', changeId)
}
</script>

<style lang="less" scoped>
.text-msg {
  .text-msg-at {
    color: aqua;
    font-style: italic;
    margin: 0 2px;
    cursor: pointer;
    font-weight: 600;
    display: inline-block;

    &.right {
      color: white;
    }
  }
}
</style>
