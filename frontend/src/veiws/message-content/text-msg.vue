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
  <div v-else>
    <div v-html="parseMarkdown(displayContent)"></div>
    <div v-if="pendingReviewInfo" class="pending-review-card">
      <div class="pending-review-meta">
        <div class="pending-review-title">待确认写入</div>
        <div class="pending-review-file">{{ pendingReviewInfo.fileName }}</div>
        <div class="pending-review-id">变更 ID: {{ pendingReviewInfo.changeId }}</div>
      </div>
      <div class="pending-review-actions">
        <button
          v-if="pendingReviewStatus === 'pending_confirmation'"
          class="pending-review-confirm"
          type="button"
          :disabled="pendingReviewLoading"
          @click.stop.prevent="handleConfirmPendingReview"
        >
          {{ pendingReviewLoading ? '应用中...' : '确认写入' }}
        </button>
        <button
          v-if="pendingReviewStatus === 'pending_confirmation'"
          class="pending-review-cancel"
          type="button"
          @click.stop.prevent="handleCancelPendingReview"
        >
          取消
        </button>
        <span v-else-if="pendingReviewStatus === 'applied'" class="pending-review-status success">已写入</span>
        <span v-else-if="pendingReviewStatus === 'rejected'" class="pending-review-status muted">已取消</span>
        <span v-else-if="pendingReviewStatus === 'failed'" class="pending-review-status error">写入失败</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

import { applyPendingChange, rejectPendingChange } from '@/api/modules/pendingChanges'
import { useSessionStore } from '@/store/module/useSessionStore'
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

const contents = ref()
const _rawMessage = ref('')
const pendingReviewLoading = ref(false)
const sessionStore = useSessionStore()

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

const pendingReviewInfo = computed(() => {
  const explicitPending = props.msg?.pending_diffs?.[0]
  if (explicitPending) {
    return {
      changeId: explicitPending.change_id,
      fileName: explicitPending.path.split(/[/\\]/).pop() || 'target file',
    }
  }

  const text = normalizeRuntimeTextForDisplay(_rawMessage.value || '')
  const normalizedChangeIdMatch = text.match(/(?:变更|change)\s*id\s*[:：]?\s*([A-Za-z0-9-]+)/i)
    || text.match(/\b([a-f0-9]{8,})\b/i)
  const normalizedFileMatch = text.match(/(?:文件|file)\s*[:：]?\s*([^\n\r]+)/i)
  if (normalizedChangeIdMatch) {
    return {
      changeId: normalizedChangeIdMatch[1].trim(),
      fileName: (normalizedFileMatch?.[1] || 'target file').trim(),
    }
  }
  if (!text.includes('文件变更已生成') || !text.includes('确认写入')) {
    return null
  }

  const changeIdMatch = text.match(/变更\s*ID[:：]\s*([A-Za-z0-9-]+)/)
  if (!changeIdMatch) {
    return null
  }

  const fileMatch = text.match(/文件[:：]\s*([^\n\r]+)/)

  return {
    changeId: changeIdMatch[1].trim(),
    fileName: (fileMatch?.[1] || '目标文件').trim(),
  }
})

const pendingReviewStatus = ref<PendingChange['status']>('pending_confirmation')

// Sync local pendingReviewStatus with stream state (handles page refresh / reconnect)
watch(
  () => {
    const changeId = pendingReviewInfo.value?.changeId
    if (!changeId) return 'pending_confirmation'
    // Defensive: ensure streamState and pendingChanges are available
    const pendingMap = sessionStore?.streamState?.pendingChanges?.value
    if (!pendingMap) return 'pending_confirmation'
    const storedStatus = pendingMap.get(changeId)?.status
    // If not in pendingChanges map, default to pending_confirmation
    return storedStatus || 'pending_confirmation'
  },
  (newStatus) => {
    // Always update local status to match the stored status
    if (newStatus) {
      pendingReviewStatus.value = newStatus
    }
  },
  { immediate: true },
)

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
const handleConfirmDiff = async (changeId: string) => {
  if (!changeId || pendingReviewLoading.value) return

  pendingReviewLoading.value = true
  try {
    const sessionId = sessionStore.currentSessionId || undefined
    const result = await applyPendingChange({ change_id: changeId, session_id: sessionId })
    if (result.success || result.status === 'applied') {
      sessionStore.streamState?.updatePendingChangeStatus(changeId, 'applied')
    } else {
      sessionStore.streamState?.updatePendingChangeStatus(changeId, 'failed')
    }
  } catch (error) {
    console.error('确认写入失败', error)
    sessionStore.streamState?.updatePendingChangeStatus(changeId, 'failed')
  } finally {
    pendingReviewLoading.value = false
  }
}

const handleCancelDiff = async (changeId: string) => {
  if (!changeId) return
  try {
    const sessionId = sessionStore.currentSessionId || undefined
    await rejectPendingChange({ change_id: changeId, session_id: sessionId })
  } catch {
    // Fallback: mark as rejected locally
  }
  sessionStore.streamState?.updatePendingChangeStatus(changeId, 'rejected')
}

const handleConfirmPendingReview = async () => {
  const changeId = pendingReviewInfo.value?.changeId
  if (!changeId || pendingReviewLoading.value) return

  pendingReviewLoading.value = true
  try {
    const sessionId = sessionStore.currentSessionId || undefined
    const result = await applyPendingChange({ change_id: changeId, session_id: sessionId })
    if (result.success || result.status === 'applied') {
      pendingReviewStatus.value = 'applied'
    } else {
      pendingReviewStatus.value = 'failed'
    }
  } catch (error) {
    console.error('确认写入失败', error)
    pendingReviewStatus.value = 'failed'
  } finally {
    pendingReviewLoading.value = false
  }
}

const handleCancelPendingReview = async () => {
  const changeId = pendingReviewInfo.value?.changeId
  if (!changeId) return

  try {
    const sessionId = sessionStore.currentSessionId || undefined
    await rejectPendingChange({ change_id: changeId, session_id: sessionId })
    pendingReviewStatus.value = 'rejected'
  } catch {
    // Fallback: mark as rejected locally even if backend call fails
    pendingReviewStatus.value = 'rejected'
  }
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

.pending-review-card {
  margin-top: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(var(--border-color), 0.9);
  border-radius: 14px;
  background: rgba(var(--surface-secondary), 0.55);
  position: relative;
  z-index: 2;
  pointer-events: auto;
}

.pending-review-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pending-review-title {
  color: rgb(var(--text-color));
  font-size: 13px;
  font-weight: 700;
}

.pending-review-file {
  color: rgb(var(--text-color));
  font-size: 14px;
  font-weight: 600;
}

.pending-review-id {
  color: rgb(var(--text-secondary));
  font-size: 12px;
}

.pending-review-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
}

.pending-review-confirm,
.pending-review-cancel {
  border: 0;
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  position: relative;
  z-index: 3;
  pointer-events: auto;
}

.pending-review-confirm {
  background: rgb(var(--primary-color));
  color: #fff;
}

.pending-review-confirm:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.pending-review-cancel {
  background: rgba(var(--surface-color), 0.9);
  color: rgb(var(--text-secondary));
  border: 1px solid rgba(var(--border-color), 0.9);
}

.pending-review-status {
  font-size: 13px;
  font-weight: 600;
}

.pending-review-status.success {
  color: rgb(34, 197, 94);
}

.pending-review-status.error {
  color: rgb(239, 68, 68);
}

.pending-review-status.muted {
  color: rgb(var(--text-secondary));
}
</style>
