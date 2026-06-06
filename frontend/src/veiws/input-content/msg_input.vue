<template>
  <div class="msg-input-wrapper">
    <div class="input-block">
      <div
        ref="inputRef"
        tabindex="0"
        contenteditable
        class="msg-input"
        :class="{ 'is-empty': !hasContent }"
        :data-placeholder="placeholder || '输入消息...'"
        @input="syncFromDom"
        @click="handleInputClick"
        @keyup="handleMentionInput"
        @keydown="handleKeyDown"
        @compositionstart="handleCompositionStart"
        @compositionend="handleCompositionEnd"
      ></div>

      <div class="composer-toolbar" role="toolbar" aria-label="消息工具">
        <button type="button" class="tool-btn" aria-label="表情" title="表情" @click="showEmoji = !showEmoji">
          <span class="tool-icon">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.6"/>
              <path d="M8.5 13.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" fill="currentColor"/>
              <path d="M15.5 13.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" fill="currentColor"/>
              <path d="M8.5 16.5c.8 1 2.2 1.5 3.5 1.5s2.7-.5 3.5-1.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            </svg>
          </span>
        </button>
        <button type="button" class="tool-btn" aria-label="附件" title="发送文件" @click="triggerFileUpload">
          <span class="tool-icon">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
        </button>
        <!-- Send button -->
        <button
          type="button"
          class="send-btn"
          :class="{ active: hasContent }"
          :disabled="!hasContent"
          aria-label="发送消息"
          @click="handleSendClick"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8.3125 0.981587C8.66767 1.0545 8.97902 1.20558 9.2627 1.43374C9.48724 1.61438 9.73029 1.85933 9.97949 2.10854L14.707 6.83608L13.293 8.25014L9 3.95717V15.0431H7V3.95717L2.70703 8.25014L1.29297 6.83608L6.02051 2.10854C6.26971 1.85933 6.51277 1.61438 6.7373 1.43374C6.97662 1.24126 7.28445 1.04542 7.6875 0.981587C7.8973 0.94841 8.1031 0.956564 8.3125 0.981587Z" fill="currentColor"></path></svg>
        </button>
        
        <!-- Send button -->
        <button
          type="button"
          class="send-btn"
          :class="{ active: hasContent }"
          :disabled="!hasContent"
          aria-label="发送消息"
          @click="handleSendClick"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8.3125 0.981587C8.66767 1.0545 8.97902 1.20558 9.2627 1.43374C9.48724 1.61438 9.73029 1.85933 9.97949 2.10854L14.707 6.83608L13.293 8.25014L9 3.95717V15.0431H7V3.95717L2.70703 8.25014L1.29297 6.83608L6.02051 2.10854C6.26971 1.85933 6.51277 1.61438 6.7373 1.43374C6.97662 1.24126 7.28445 1.04542 7.6875 0.981587C7.8973 0.94841 8.1031 0.956564 8.3125 0.981587Z" fill="currentColor"></path></svg>
        </button>
      </div>
    </div>

    <input
      ref="fileInputRef"
      type="file"
      class="file-input-hidden"
      multiple
      @change="handleFileSelect"
    />

    <teleport to="#app">
      <transition name="emoji-slide">
        <div v-if="showEmoji" class="emoji-panel">
          <div class="emoji-header">
            <span class="emoji-title">表情</span>
            <button type="button" class="emoji-close" @click="showEmoji = false">
              <svg viewBox="0 0 16 16" fill="none">
                <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
          <div class="emoji-grid">
            <button
              v-for="e in emojis"
              :key="e.icon"
              type="button"
              class="emoji-item"
              :title="e.name"
              @click="insertEmoji(e.icon)"
            >
              {{ e.icon }}
            </button>
          </div>
        </div>
      </transition>

      <div v-if="showMentionPanel" class="agent-mention-panel" :style="mentionPanelStyle">
        <button
          v-for="(agent, index) in filteredSessionAgentOptions"
          :key="agent.id"
          type="button"
          class="agent-mention-item"
          :class="{ 'is-active': index === selectedMentionIndex }"
          @mouseenter="selectedMentionIndex = index"
          @click="selectMentionAgent(agent)"
        >
          <img v-if="agent.avatar" class="agent-mention-avatar" :src="agent.avatar" :alt="agent.name" />
          <div v-else class="agent-mention-avatar agent-mention-avatar-fallback">{{ agent.name.slice(0, 1) }}</div>
          <div class="agent-mention-copy">
            <div class="agent-mention-name">{{ agent.name }}</div>
            <div class="agent-mention-meta">
              {{ agent.status }}<span v-if="agent.isPrimary"> · primary</span>
            </div>
          </div>
        </button>
      </div>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

import type {
  ComposerAgent,
  ComposerMention,
  ComposerNode,
  ComposerSubmitPayload,
  SessionAgentOption,
  SessionMemberStatus,
} from '@/types/agenthub'
import emojis from '../../utils/emoji/emoji'

const inputValue = defineModel<string>('value', { default: '' })

const emit = defineEmits<{
  send: [payload: ComposerSubmitPayload]
  'file-selected': [files: File[]]
  'structured-change': [payload: ComposerSubmitPayload]
}>()

const props = defineProps<{
  placeholder?: string
  sessionAgentOptions?: SessionAgentOption[]
  handlerSubmitMsg?: (payload: ComposerSubmitPayload) => void
}>()

const inputRef = ref<HTMLDivElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const nodes = ref<ComposerNode[]>([])
const hasContent = ref(false)
const showEmoji = ref(false)
const mentionKeyword = ref('')
const showMentionPanel = ref(false)
const selectedMentionIndex = ref(0)
const isComposing = ref(false)
const mentionPanelStyle = ref<Record<string, string>>({})

const statusRank: Record<SessionMemberStatus, number> = {
  online: 0,
  busy: 1,
  offline: 2,
}

const filteredSessionAgentOptions = computed(() => {
  const keyword = mentionKeyword.value.trim().toLowerCase()
  const options = [...(props.sessionAgentOptions ?? [])].sort((left, right) => {
    const rankDiff = statusRank[left.status] - statusRank[right.status]
    if (rankDiff !== 0) return rankDiff
    return left.name.localeCompare(right.name)
  })

  if (!keyword) return options
  return options.filter((agent) => agent.name.toLowerCase().includes(keyword))
})

function createTextNode(content: string): ComposerNode {
  return { type: 'text', content }
}

function normalizeAgent(agent: ComposerAgent): ComposerAgent {
  return {
    id: agent.id,
    name: agent.name,
    avatar: agent.avatar ?? null,
    status: agent.status,
    role: agent.role ?? null,
  }
}

function createAgentChipElement(agent: ComposerAgent): HTMLButtonElement {
  const el = document.createElement('button')
  el.type = 'button'
  el.className = 'agent-chip'
  el.contentEditable = 'false'
  el.setAttribute('contenteditable', 'false')
  el.dataset.agent = JSON.stringify(normalizeAgent(agent))

  const status = document.createElement('span')
  status.className = `agent-chip-status status-${agent.status}`
  status.setAttribute('aria-hidden', 'true')

  const label = document.createElement('span')
  label.className = 'agent-chip-label'
  label.textContent = `@${agent.name}`

  const remove = document.createElement('span')
  remove.className = 'agent-chip-remove'
  remove.setAttribute('aria-hidden', 'true')
  remove.textContent = '×'

  el.append(status, label, remove)
  return el
}

function parseAgentChipElement(el: Element): ComposerAgent | null {
  const raw = el.getAttribute('data-agent')
  if (!raw) return null
  try {
    return normalizeAgent(JSON.parse(raw))
  } catch {
    return null
  }
}

function buildNodesFromDom(): ComposerNode[] {
  const root = inputRef.value
  if (!root) return []

  const nextNodes: ComposerNode[] = []
  Array.from(root.childNodes).forEach((node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      const content = node.textContent ?? ''
      if (content.length > 0) nextNodes.push(createTextNode(content))
      return
    }

    if (node.nodeType === Node.ELEMENT_NODE) {
      const element = node as Element
      if (element.classList.contains('agent-chip')) {
        const agent = parseAgentChipElement(element)
        if (agent) {
          nextNodes.push({ type: 'agent-chip', agent })
          return
        }
      }
      const content = element.textContent ?? ''
      if (content.length > 0) nextNodes.push(createTextNode(content))
    }
  })

  return nextNodes
}

function getStructuredValue(): ComposerSubmitPayload {
  const currentNodes = nodes.value
  const selectedAgents = currentNodes
    .filter((node): node is Extract<ComposerNode, { type: 'agent-chip' }> => node.type === 'agent-chip')
    .map((node) => normalizeAgent(node.agent))
  const mentions: ComposerMention[] = selectedAgents.map((agent) => ({
    agentId: agent.id,
    agentName: agent.name,
  }))
  const text = currentNodes
    .filter((node): node is Extract<ComposerNode, { type: 'text' }> => node.type === 'text')
    .map((node) => node.content)
    .join('')

  return {
    text,
    targetAgentIds: selectedAgents.map((agent) => agent.id),
    selectedAgents,
    mentions,
    nodes: [...currentNodes],
  }
}

function syncFromDom() {
  nodes.value = buildNodesFromDom()
  const payload = getStructuredValue()
  inputValue.value = payload.text
  hasContent.value = payload.text.trim().length > 0 || payload.selectedAgents.length > 0
  emit('structured-change', payload)
}

function focusComposer() {
  inputRef.value?.focus()
}

function placeCaretAfter(node: Node) {
  const selection = window.getSelection()
  if (!selection) return
  const range = document.createRange()
  range.setStartAfter(node)
  range.collapse(true)
  selection.removeAllRanges()
  selection.addRange(range)
}

function placeCaretAtEnd() {
  if (!inputRef.value) return
  const selection = window.getSelection()
  if (!selection) return
  const range = document.createRange()
  range.selectNodeContents(inputRef.value)
  range.collapse(false)
  selection.removeAllRanges()
  selection.addRange(range)
}

function insertTextAtCaret(text: string) {
  if (!inputRef.value || !text) return
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) {
    focusComposer()
  }
  const activeSelection = window.getSelection()
  if (!activeSelection || activeSelection.rangeCount === 0) {
    inputRef.value.appendChild(document.createTextNode(text))
    syncFromDom()
    return
  }
  const range = activeSelection.getRangeAt(0)
  if (!inputRef.value.contains(range.startContainer)) {
    focusComposer()
    inputRef.value.appendChild(document.createTextNode(text))
    syncFromDom()
    return
  }
  range.deleteContents()
  const textNode = document.createTextNode(text)
  range.insertNode(textNode)
  placeCaretAfter(textNode)
  syncFromDom()
}

function insertAgentChip(agent: ComposerAgent) {
  if (!inputRef.value) return
  const normalized = normalizeAgent(agent)
  const exists = nodes.value.some(
    (node) => node.type === 'agent-chip' && node.agent.id === normalized.id,
  )
  if (exists) return

  const chip = createAgentChipElement(normalized)
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) {
    inputRef.value.appendChild(chip)
    inputRef.value.appendChild(document.createTextNode(' '))
    placeCaretAtEnd()
    syncFromDom()
    return
  }

  const range = selection.getRangeAt(0)
  if (!inputRef.value.contains(range.startContainer)) {
    inputRef.value.appendChild(chip)
    inputRef.value.appendChild(document.createTextNode(' '))
    placeCaretAtEnd()
    syncFromDom()
    return
  }

  range.deleteContents()
  range.insertNode(document.createTextNode(' '))
  range.insertNode(chip)
  placeCaretAfter(chip.nextSibling ?? chip)
  syncFromDom()
}

function closeMentionPanel() {
  showMentionPanel.value = false
  mentionKeyword.value = ''
  selectedMentionIndex.value = 0
}

function updateMentionPanelPosition() {
  if (!showMentionPanel.value || !inputRef.value) return
  const rootRect = inputRef.value.getBoundingClientRect()
  const selection = window.getSelection()
  let left = 0
  let top = -8

  if (selection && selection.rangeCount > 0) {
    const range = selection.getRangeAt(0).cloneRange()
    range.collapse(true)
    const rect = range.getBoundingClientRect()
    if (rect.width || rect.height) {
      left = Math.max(rect.left - rootRect.left, 0)
      top = rect.top - rootRect.top - 8
    }
  }

  mentionPanelStyle.value = {
    left: `${left}px`,
    top: `${top}px`,
    transform: 'translateY(-100%)',
  }
}

async function openMentionPanel() {
  showMentionPanel.value = filteredSessionAgentOptions.value.length > 0
  if (!showMentionPanel.value) return
  await nextTick()
  updateMentionPanelPosition()
}

function getMentionTargetTextNode() {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return null
  const range = selection.getRangeAt(0)
  if (!inputRef.value?.contains(range.startContainer)) return null

  if (range.startContainer.nodeType === Node.TEXT_NODE) {
    return range.startContainer as Text
  }

  const container = range.startContainer
  const offset = range.startOffset
  const previousNode = container.childNodes[offset - 1]
  if (previousNode?.nodeType === Node.TEXT_NODE) return previousNode as Text
  const currentNode = container.childNodes[offset]
  if (currentNode?.nodeType === Node.TEXT_NODE) return currentNode as Text
  return null
}

function replaceTrailingMentionWithChip(agent: ComposerAgent) {
  if (!inputRef.value) return
  const mentionNode = getMentionTargetTextNode()
  if (mentionNode) {
    const text = mentionNode.textContent ?? ''
    const mentionMatch = text.match(/(?:^|\s)@([^@\s]*)$/)
    if (mentionMatch?.index !== undefined) {
      const prefixIndex = mentionMatch.index
      const preservedPrefix = text.slice(0, prefixIndex)
      const fragment = document.createDocumentFragment()
      if (preservedPrefix) fragment.appendChild(document.createTextNode(preservedPrefix))
      const chip = createAgentChipElement(normalizeAgent(agent))
      fragment.appendChild(chip)
      const spacer = document.createTextNode(' ')
      fragment.appendChild(spacer)
      mentionNode.parentNode?.replaceChild(fragment, mentionNode)
      placeCaretAfter(spacer)
      syncFromDom()
      closeMentionPanel()
      return
    }
  }

  insertAgentChip(agent)
  closeMentionPanel()
}

function selectMentionAgent(agent: SessionAgentOption) {
  replaceTrailingMentionWithChip(agent)
}

function getTrailingMentionMatch() {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0 || !inputRef.value?.contains(selection.anchorNode)) {
    return null
  }
  const textNode = getMentionTargetTextNode()
  const text = textNode?.textContent ?? inputRef.value?.textContent ?? ''
  return text.match(/(?:^|\s)@([^@\s]*)$/)
}

function handleMentionInput() {
  if (isComposing.value) return
  const match = getTrailingMentionMatch()
  if (!match) {
    closeMentionPanel()
    return
  }

  mentionKeyword.value = match[1] ?? ''
  if (filteredSessionAgentOptions.value.length === 0) {
    showMentionPanel.value = false
    selectedMentionIndex.value = 0
    return
  }
  if (selectedMentionIndex.value >= filteredSessionAgentOptions.value.length) {
    selectedMentionIndex.value = 0
  }
  void openMentionPanel()
}

function handleCompositionStart() {
  isComposing.value = true
}

function handleCompositionEnd() {
  isComposing.value = false
  syncFromDom()
  handleMentionInput()
}

function getAdjacentChipFromSelection(direction: 'backward' | 'forward'): Element | null {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return null
  const range = selection.getRangeAt(0)
  if (!range.collapsed || !inputRef.value?.contains(range.startContainer)) return null

  if (range.startContainer.nodeType === Node.TEXT_NODE) {
    const textNode = range.startContainer as Text
    if (direction === 'backward' && range.startOffset === 0) {
      return textNode.previousSibling instanceof Element && textNode.previousSibling.classList.contains('agent-chip')
        ? textNode.previousSibling
        : null
    }
    if (direction === 'forward' && range.startOffset === (textNode.textContent?.length ?? 0)) {
      return textNode.nextSibling instanceof Element && textNode.nextSibling.classList.contains('agent-chip')
        ? textNode.nextSibling
        : null
    }
    return null
  }

  const container = range.startContainer
  const childIndex = range.startOffset
  const sibling = direction === 'backward' ? container.childNodes[childIndex - 1] : container.childNodes[childIndex]
  return sibling instanceof Element && sibling.classList.contains('agent-chip') ? sibling : null
}

function handleKeyDown(event: KeyboardEvent) {
  if (showMentionPanel.value) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      selectedMentionIndex.value = (selectedMentionIndex.value + 1) % filteredSessionAgentOptions.value.length
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      selectedMentionIndex.value =
        (selectedMentionIndex.value - 1 + filteredSessionAgentOptions.value.length) % filteredSessionAgentOptions.value.length
      return
    }
    if (event.key === 'Enter') {
      event.preventDefault()
      const selected = filteredSessionAgentOptions.value[selectedMentionIndex.value]
      if (selected) selectMentionAgent(selected)
      return
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      closeMentionPanel()
      return
    }
  }

  if (event.key === 'Enter' && !event.shiftKey && !isComposing.value) {
    event.preventDefault()
    const payload = getStructuredValue()
    if (!payload.text.trim()) return
    emit('send', payload)
    return
  }

  if (event.key === 'Backspace') {
    const previousChip = getAdjacentChipFromSelection('backward')
    if (previousChip) {
      event.preventDefault()
      previousChip.remove()
      syncFromDom()
      return
    }
  }

  if (event.key === 'Delete') {
    const nextChip = getAdjacentChipFromSelection('forward')
    if (nextChip) {
      event.preventDefault()
      nextChip.remove()
      syncFromDom()
    }
  }
}

function handleInputClick(event: MouseEvent) {
  const target = event.target
  if (!(target instanceof Element)) return
  const removeButton = target.closest('.agent-chip-remove')
  if (!removeButton) return
  const chip = removeButton.closest('.agent-chip')
  if (!chip) return
  event.preventDefault()
  event.stopPropagation()
  chip.remove()
  syncFromDom()
  placeCaretAtEnd()
}

function clear() {
  if (!inputRef.value) return
  inputRef.value.innerHTML = ''
  nodes.value = []
  inputValue.value = ''
  hasContent.value = false
  closeMentionPanel()
}

function insertEmoji(emoji: string) {
  insertTextAtCaret(emoji)
  showEmoji.value = false
}

function removeAgentChip(agentId: string) {
  if (!inputRef.value) return
  inputRef.value.querySelectorAll('.agent-chip').forEach((node) => {
    const agent = parseAgentChipElement(node)
    if (agent?.id === agentId) node.remove()
  })
  syncFromDom()
}

function triggerFileUpload() {
  fileInputRef.value?.click()
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const files = target.files
  if (files && files.length > 0) {
    emit('file-selected', Array.from(files))
  }
  // 清空 input 以便再次选择相同文件
  event.target.value = ''
}

// 发送按钮点击处理
const handleSendClick = () => {
  if (!hasContent.value) return
  // 构建消息数据
  const messageData = buildMessageData()
  emit('send', messageData)
  // 清空输入框
  inputValue.value = ''
  inputRef.value.innerHTML = ''
  nodeList = []
  hasContent.value = false
}
</script>

<style scoped lang="less">
.msg-input-wrapper {
  position: relative;
  width: 100%;
}

  .input-block {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    background: rgb(var(--surface-color));
    border-radius: var(--radius-lg);
    border: 1px solid rgb(var(--border-color));
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    &:focus-within {
      border-color: rgba(0, 112, 243, 0.4);
      box-shadow:
        0 0 0 3px rgba(0, 112, 243, 0.08),
        0 4px 12px rgba(0, 112, 243, 0.1);
          }
        }

  .msg-input {
    flex: 1;
    min-height: 40px;
    max-height: 140px;
    overflow-y: auto;
    overflow-x: hidden;
    padding-left: 10px;
    border-radius: var(--radius-md);
    border: none;
    background: transparent;
    color: rgb(var(--text-color));
    font-size: 14px;
    line-height: 1.6;
    outline: none;
    resize: none;
    white-space: pre-wrap;
    word-wrap: break-word;
    word-break: break-all;
    transition: all 0.15s ease;
    cursor: text;
  }

  /* Toolbar */
  .composer-toolbar {
    display: flex;
    flex-direction: row;
    gap: 2px;
    flex-shrink: 0;
    padding: 4px 2px;
  }

  .tool-btn {
    position: relative;
    display: flex;
    justify-content: center;
    margin-top: 4px;
    width: 40px;
    height: 40px;
    border-radius: 20px;
    color: rgb(var(--text-muted));

.tool-icon {
  display: flex;
  align-items: center;
  justify-content: center;

      svg {
        width: 30px;
        height: 30px;
        transition: transform 0.2s ease;
      }
    }

    .tool-ripple {
      position: absolute;
      inset: 0;
      border-radius: 10px;
      opacity: 0;
      transform: scale(0.8);
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }

    &::before {
      content: '';
      position: absolute;
      inset: 0;
      border-radius: 10px;
      opacity: 0;
      transform: scale(0);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    &:hover {
      color: rgb(var(--primary-color));
      border: 1px solid rgba(0, 112, 243, 0.4);
      transform: translateY(-1px);

      .tool-icon svg {
        transform: scale(1.1);
      }

      .tool-ripple {
        opacity: 1;
        transform: scale(1);
      }

      &::before {
        opacity: 0.5;
        transform: scale(1);
      }
    }

    &:active {
      transform: translateY(0) scale(0.96);

      .tool-icon svg {
        transform: scale(0.95);
      }
    }
  }

  /* Send button */
  .send-btn {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 20px;
    background: rgb(var(--text-muted));
    color: #fff;
    border: none;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    margin: 4px;

    svg {
      width: 18px;
      height: 18px;
    }

    &.active {
      background: rgb(var(--primary-color));
    }

    &:hover {
      &.active {
        background: rgb(var(--primary-strong));
        transform: scale(1.05);
      }
    }

    &:active {
      &.active {
        transform: scale(0.95);
      }
    }

    &:disabled {
      cursor: not-allowed;
      opacity: 0.6;
    }
  }
}

/* 隐藏的文件上传 input */
.file-input-hidden {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.emoji-panel {
  position: fixed;
  right: -5%;
  bottom: 90px;
  transform: translateX(-50%);
  z-index: 9999;
  width: 340px;
  max-height: 320px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(99, 102, 241, 0.15);
  box-shadow:
    0 20px 40px rgba(99, 102, 241, 0.15),
    0 8px 16px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.emoji-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.12);
}

.emoji-title {
  font-size: 14px;
  font-weight: 600;
}

.emoji-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  cursor: pointer;
}

.emoji-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 8px;
  padding: 16px;
}

.emoji-item {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;

  &:hover {
    background: rgba(0, 112, 243, 0.08);
  }
}

.agent-mention-panel {
  position: fixed;
  z-index: 10000;
  min-width: 240px;
  max-width: 320px;
  padding: 8px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.18);
}

.agent-mention-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border: none;
  border-radius: 10px;
  background: transparent;
  cursor: pointer;
  text-align: left;

  &:hover,
  &.is-active {
    background: rgba(0, 112, 243, 0.08);
  }
}

.agent-mention-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
}

.agent-mention-avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 112, 243, 0.12);
  color: rgb(var(--primary-color));
  font-size: 12px;
  font-weight: 700;
}

.agent-mention-copy {
  min-width: 0;
}

.agent-mention-name {
  font-size: 13px;
  font-weight: 600;
}

.agent-mention-meta {
  font-size: 12px;
  color: rgb(var(--text-muted));
}

:deep(.agent-chip) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0 2px;
  padding: 2px 8px;
  border: none;
  border-radius: 999px;
  background: rgba(0, 112, 243, 0.12);
  color: rgb(var(--primary-color));
  font-size: 13px;
  line-height: 1.4;
}

:deep(.agent-chip-status) {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}

:deep(.status-online) {
  background: #22c55e;
}

:deep(.status-busy) {
  background: #f59e0b;
}

:deep(.status-offline) {
  background: #94a3b8;
}

:deep(.agent-chip-remove) {
  font-size: 12px;
  opacity: 0.7;
}
</style>
