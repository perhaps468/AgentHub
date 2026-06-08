<template>
  <!-- PPT 数据优先渲染（包含在普通文本 JSON 里的 ppt_data） -->
  <PptMsg
    v-if="hasPptData"
    :msg="props.msg"
    :right="right"
    @preview="handlePreviewPpt"
  />
  <!-- Diff 变更卡片 -->
  <div v-else-if="hasDiffPreview" class="diff-wrapper">
    <div v-if="nonDiffContent && parsedDiffs.length > 0" v-html="parseMarkdown(nonDiffContent)" class="non-diff-content"></div>
    <DiffPreview
      v-for="diff in normalizedDiffs"
      :key="diff.change_id"
      :change="diff"
      :contentHtml="parsedDiffs.length > 0 ? '' : parseMarkdown(displayContent)"
      @confirm="handleConfirmDiff"
      @cancel="handleCancelDiff"
      @preview="handlePreviewDiff"
    />
  </div>
  <!-- 普通文本渲染 -->
  <span v-else-if="isArrayContents" class="text-msg">
    <template v-for="item in (contents as MessageContentItem[])" :key="item.id">
      <span v-if="item.type === TextContentType.At" class="text-msg-at">
        {{ `@${getUserInfo(item.content).name}` }}
      </span>
      <span
        v-else-if="item.type === TextContentType.Text"
        v-html="parseMarkdown(typeof item.content === 'string' ? item.content : '')"
      ></span>
    </template>
  </span>
  <div v-else>
    <div v-html="parseMarkdown(displayContent)"></div>
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
import type { PendingChange, PendingChangeStatus, PptPreviewModel } from '../../types/agenthub'
import DiffPreview from './DiffPreview.vue'
import PptMsg from './PptMsg.vue'

marked.setOptions({
  breaks: true,
  gfm: true,
})

const parseMarkdown = (text?: string): string => {
  if (!text) return ''

  try {
    const normalizedText = normalizeRuntimeTextForDisplay(text)
    const rawHtml = marked.parse(normalizedText)
    return typeof rawHtml === 'string'
      ? DOMPurify.sanitize(rawHtml)
      : normalizedText
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

const contents = ref<MessageContentItem[] | string>()
const _rawMessage = ref('')
const pendingReviewLoading = ref(false)
const sessionStore = useSessionStore()

/**
 * Parse diff content from message text.
 * Detects unified diff format in the message and extracts pending change info.
 */
type MessageContentItem = {
  id?: string | number
  type: (typeof TextContentType)[keyof typeof TextContentType]
  content: string | Record<string, unknown>
}

interface ParsedDiff extends PendingChange {
  status: PendingChangeStatus
}

const parseDiffsFromText = (text: string): ParsedDiff[] => {
  const diffs: ParsedDiff[] = []

  // Pattern to match CREATE/UPDATE diff blocks
  const diffPattern = /\[(CREATE|UPDATE|DELETE)\]\s*(.+?)(?=\[CREATE\]|\[UPDATE\]|\[DELETE\]|$)/gs
  let match

  while ((match = diffPattern.exec(text)) !== null) {
    const operation = match[1].toLowerCase() as PendingChange['operation']
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
      session_id: sessionStore.currentSessionId || '',
      operation,
      path,
      unified_diff: diffContent,
      status: isApplied ? 'applied' : 'pending_confirmation',
    })
  }

  return diffs
}

// Check if message should render a diff preview card
const hasDiffPreview = computed(() => {
  if (props.msg?.pending_diffs?.length) return true
  return !!pendingReviewInfo.value
})
// Parse diffs from props or text
const parsedDiffs = computed((): ParsedDiff[] => {
  // First check for explicit pending_diffs
  if (props.msg?.pending_diffs?.length) {
    return props.msg.pending_diffs.map(d => ({
      change_id: d.change_id,
      session_id: d.session_id || sessionStore.currentSessionId || '',
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

  // If we have real diffs, don't show the raw diff text
  if (parsedDiffs.value.length > 0) return ''

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

const pendingReviewStatus = ref<PendingChangeStatus>('pending_confirmation')

const normalizedDiffs = computed<PendingChange[]>(() => {
  if (parsedDiffs.value.length > 0) {
    return parsedDiffs.value
  }

  const info = pendingReviewInfo.value
  if (!info) return []

  return [{
    change_id: info.changeId,
    session_id: sessionStore.currentSessionId || '',
    operation: 'update',
    path: info.fileName,
    unified_diff: '',
    status: pendingReviewStatus.value,
  }]
})

watch(
  () => {
    const changeId = pendingReviewInfo.value?.changeId
    if (!changeId) return 'pending_confirmation'
    // Defensive: ensure streamState and pendingChanges are available
    const pendingMap = sessionStore?.streamState?.pendingChanges
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
      contents.value = JSON.parse(msg?.message || '[]').map((item: MessageContentItem) => {
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

/** 检测 message 内容是否包含 ppt_data（嵌入在 JSON 字符串内） */
const hasPptData = computed(() => {
  try {
    const parsed = JSON.parse(props.msg.message || '{}')
    return !!(parsed && typeof parsed === 'object' && parsed.ppt_data && (parsed.ppt_data as unknown[]).length > 0)
  } catch {
    return false
  }
})

/** 处理 PPT 预览事件：写入 streamState，打开右侧预览区 */
const handlePreviewPpt = (payload: PptPreviewModel) => {
  sessionStore.streamState?.setPreviewPpt(payload)
}

const getUserInfo = (content: unknown) => {
  try {
    if (content && typeof content === 'object') {
      return content as { name?: string }
    }
    return JSON.parse(String(content)) as { name?: string }
  } catch {
    return { name: String(content ?? '') }
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

// M6: Handle preview button click - set preview diff state
const handlePreviewDiff = (change: PendingChange) => {
  sessionStore.streamState?.setPreviewDiff(change)
}

const handlePreviewPendingReview = () => {
  const info = pendingReviewInfo.value
  if (!info) return

  const change: PendingChange = {
    change_id: info.changeId,
    session_id: sessionStore.currentSessionId || '',
    operation: 'update',
    path: info.fileName,
    unified_diff: _rawMessage.value || displayContent.value || '',
    status: pendingReviewStatus.value,
  }

  sessionStore.streamState?.setPreviewDiff(change)
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
