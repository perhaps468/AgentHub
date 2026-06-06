<template>
  <div class="msg-input-wrapper">
    <teleport to="#app">
      <!-- 表情面板 -->
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

      <!-- @ 提及弹窗 -->
      <div
        v-if="isAtPopup && showMentionsPopup && userList.length > 0"
        class="at-mentions-popup"
        :style="`top:${popupPosition.y - 10}px;left:${popupPosition.x}px`"
        :data-theme="themeStore.theme"
      >
        <div
          v-for="(item, index) in userList"
          :key="item.id"
          class="user-item"
          :class="{ selected: index === selectedUserIndex }"
          @click="() => onSelectUser(item)"
        >
          {{ item.name }}
        </div>
      </div>
    </teleport>

    <div class="input-block">
      <div
        ref="inputRef"
        tabindex="0"
        contenteditable
        class="msg-input"
        :class="{ 'is-empty': !hasContent }"
        :data-placeholder="placeholder || '输入消息...'"
<<<<<<< Updated upstream
        @keyup="onInputKeyUp"
        @keydown="onInputKeyDown"
        @input="onInputText"
        @blur="onInputBlur"
        @focus="onInputFocus"
=======
        @input="syncFromDom"
        @click="handleInputClick"
        @keyup="handleMentionInput"
        @keydown="handleKeyDown"
        @compositionstart="handleCompositionStart"
        @compositionend="handleCompositionEnd"
>>>>>>> Stashed changes
      ></div>
      <!-- Toolbar -->
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
          <span class="tool-ripple"></span>
        </button>
        <button type="button" class="tool-btn" aria-label="附件" title="发送文件" @click="triggerFileUpload">
          <span class="tool-icon">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          <span class="tool-ripple"></span>
        </button>
      </div>
    </div>

<<<<<<< Updated upstream
    <!-- 隐藏的文件上传 input -->
    <input
      ref="fileInputRef"
      type="file"
      class="file-input-hidden"
      multiple
      @change="handleFileSelect"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useThemeStore } from '../../store/module/useThemeStore'
import emojis from '../../utils/emoji/emoji'
const themeStore = useThemeStore()

const inputRef = ref()
const fileInputRef = ref()
const popupPosition = ref({ x: 0, y: 0 })
const showMentionsPopup = ref(false)
const showEmoji = ref(false)
const searchKey = ref('')
const selectedUserIndex = ref(0)
=======
    <div v-if="showMentionPanel" class="agent-mention-panel" :style="mentionPanelStyle">
      <button
        v-for="(agent, index) in filteredSessionAgentOptions"
        :key="agent.id"
        type="button"
        class="agent-mention-item"
        :class="{ 'is-active': index === selectedMentionIndex }"
        :data-agent-id="agent.id"
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
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import type {
  ComposerAgent,
  ComposerMention,
  ComposerNode,
  ComposerSubmitPayload,
  SessionAgentOption,
  SessionMemberStatus,
} from '@/types/agenthub'
>>>>>>> Stashed changes

const inputValue = defineModel('value')
let nodeList = []
const hasContent = ref(false)

<<<<<<< Updated upstream
const selection = ref({
  sel: null,
  range: null,
  node: null,
  offset: 0,
  text: '',
})
const emit = defineEmits(['send', 'file-selected'])

const props = defineProps({
  user: Object,
  isAtPopup: Boolean,
  placeholder: String,
})

const userList = computed(() => {
  if (props.user) {
    return props.user.filter((item) => item.name.includes(searchKey.value))
  } else {
    return props.user
=======
const emit = defineEmits<{
  send: [payload: ComposerSubmitPayload]
  'file-selected': [files: File[]]
  'toggle-emoji': []
  'structured-change': [payload: ComposerSubmitPayload]
}>()

const props = defineProps<{
  user?: Array<{ id: string; name: string }>
  isAtPopup?: boolean
  placeholder?: string
  sessionAgentOptions?: SessionAgentOption[]
  handlerSubmitMsg?: (payload: ComposerSubmitPayload) => void
}>()

const inputRef = ref<HTMLDivElement | null>(null)
const nodes = ref<ComposerNode[]>([])
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
  remove.textContent = 'x'

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
      if (content.length > 0) {
        nextNodes.push(createTextNode(content))
      }
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
      if (content.length > 0) {
        nextNodes.push(createTextNode(content))
      }
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

function insertTextAtEnd(text: string) {
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

  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) {
    focusComposer()
  }
  const activeSelection = window.getSelection()
  const chip = createAgentChipElement(normalized)
  if (!activeSelection || activeSelection.rangeCount === 0) {
    inputRef.value.appendChild(chip)
    placeCaretAfter(chip)
    syncFromDom()
    return
  }
  const range = activeSelection.getRangeAt(0)
  if (!inputRef.value.contains(range.startContainer)) {
    focusComposer()
    inputRef.value.appendChild(chip)
    placeCaretAfter(chip)
    syncFromDom()
    return
  }

  if (range.startContainer.nodeType === Node.TEXT_NODE) {
    const textNode = range.startContainer as Text
    const beforeText = textNode.textContent?.slice(0, range.startOffset) ?? ''
    const afterText = textNode.textContent?.slice(range.startOffset) ?? ''
    const fragment = document.createDocumentFragment()
    if (beforeText) fragment.appendChild(document.createTextNode(beforeText))
    fragment.appendChild(chip)
    if (afterText) fragment.appendChild(document.createTextNode(afterText))
    textNode.parentNode?.replaceChild(fragment, textNode)
    placeCaretAfter(chip)
    syncFromDom()
    return
  }

  range.deleteContents()
  range.insertNode(chip)
  placeCaretAfter(chip)
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
    let rect = range.getBoundingClientRect()

    if (!rect.width && !rect.height && inputRef.value.lastChild) {
      const fallbackRange = document.createRange()
      fallbackRange.selectNodeContents(inputRef.value)
      fallbackRange.collapse(false)
      rect = fallbackRange.getBoundingClientRect()
    }

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

function openAgentPicker() {
  mentionKeyword.value = ''
  selectedMentionIndex.value = 0
  void openMentionPanel()
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
  if (previousNode?.nodeType === Node.TEXT_NODE) {
    return previousNode as Text
  }
  const currentNode = container.childNodes[offset]
  if (currentNode?.nodeType === Node.TEXT_NODE) {
    return currentNode as Text
  }
  return null
}

function replaceTrailingMentionWithChip(agent: ComposerAgent) {
  if (!inputRef.value) return

  const normalized = normalizeAgent(agent)
  const exists = nodes.value.some(
    (node) => node.type === 'agent-chip' && node.agent.id === normalized.id,
  )
  if (exists) {
    syncFromDom()
    closeMentionPanel()
    return
  }

  const mentionNode = getMentionTargetTextNode()
  if (mentionNode) {
    const text = mentionNode.textContent ?? ''
    const mentionMatch = text.match(/(?:^|\s)@([^@\s]*)$/)
    if (mentionMatch?.index !== undefined) {
      const prefixIndex = mentionMatch.index
      const preservedPrefix = text.slice(0, prefixIndex)
      const fragment = document.createDocumentFragment()
      if (preservedPrefix) {
        fragment.appendChild(document.createTextNode(preservedPrefix))
      }
      const chip = createAgentChipElement(normalized)
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

  const chip = createAgentChipElement(normalized)
  inputRef.value.appendChild(chip)
  const spacer = document.createTextNode(' ')
  inputRef.value.appendChild(spacer)
  placeCaretAfter(spacer)
  syncFromDom()
  closeMentionPanel()
}

function removeAgentChip(agentId: string) {
  if (!inputRef.value) return
  if (!agentId) {
    inputRef.value.innerHTML = ''
    syncFromDom()
    return
  }
  inputRef.value.querySelectorAll('.agent-chip').forEach((node) => {
    const agent = parseAgentChipElement(node)
    if (agent?.id === agentId) {
      node.remove()
    }
  })
  syncFromDom()
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

function selectMentionAgent(agent: SessionAgentOption) {
  replaceTrailingMentionWithChip(agent)
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
  const sibling =
    direction === 'backward'
      ? container.childNodes[childIndex - 1]
      : container.childNodes[childIndex]
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
        (selectedMentionIndex.value - 1 + filteredSessionAgentOptions.value.length) %
        filteredSessionAgentOptions.value.length
      return
    }

    if (event.key === 'Enter') {
      event.preventDefault()
      const selected = filteredSessionAgentOptions.value[selectedMentionIndex.value]
      if (selected) {
        selectMentionAgent(selected)
      }
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
  closeMentionPanel()
}

watch(
  () => inputValue.value,
  (value) => {
    if (!inputRef.value) return
    const currentText = getStructuredValue().text
    if (!value) {
      clear()
      return
    }
    if (nodes.value.length === 0 && currentText !== value) {
      inputRef.value.textContent = value
      syncFromDom()
    }
  },
)

watch(
  () => filteredSessionAgentOptions.value.length,
  (length) => {
    if (!showMentionPanel.value) return
    if (length === 0) {
      closeMentionPanel()
      return
    }
    if (selectedMentionIndex.value >= length) {
      selectedMentionIndex.value = 0
    }
    void nextTick().then(updateMentionPanelPosition)
  },
)

onMounted(() => {
  if (inputValue.value && inputRef.value) {
    inputRef.value.textContent = inputValue.value
    syncFromDom()
>>>>>>> Stashed changes
  }
})

const onInputText = () => {
  inputValue.value = inputRef.value.innerText
  hasContent.value = inputRef.value.innerText.trim().length > 0
}

watch(inputValue, (val) => {
  hasContent.value = !!val?.trim()
  if (!val) {
    inputRef.value.innerText = ''
  } else {
    onDataChange()
  }
})

const onInputBlur = () => {
  updateSelection()
  setTimeout(() => {
    showMentionsPopup.value = false
  }, 200)
}

const onInputFocus = () => {
  checkIsShowSelectPopup()
}

const onInputKeyDown = (e) => {
  const isEnterKey = e.key === 'Enter'
  const isArrowUp = e.key === 'ArrowUp'
  const isArrowDown = e.key === 'ArrowDown'
  const isTabKey = e.key === 'Tab'
  const isCtrlOrMeta = e.ctrlKey || e.metaKey

  if (showMentionsPopup.value && userList.value.length > 0) {
    if (isArrowUp) {
      e.preventDefault()
      if (selectedUserIndex.value > 0) {
        selectedUserIndex.value--
        scrollToSelectedUser()
      }
    } else if (isArrowDown) {
      e.preventDefault()
      if (selectedUserIndex.value < userList.value.length - 1) {
        selectedUserIndex.value++
        scrollToSelectedUser()
      }
    } else if (isEnterKey) {
      e.preventDefault()
      onSelectUser(userList.value[selectedUserIndex.value])
    }
  } else {
    if (isEnterKey) {
      if (e.ctrlKey || e.shiftKey || e.metaKey) {
        e.preventDefault()
      } else {
        e.preventDefault()
        // 构建正确的消息内容
        const messageData = buildMessageData()
        emit('send', messageData)
        // 清空输入框
        inputValue.value = ''
        inputRef.value.innerHTML = ''
        nodeList = []
      }
    }
  }
  if (isCtrlOrMeta) {
    if (['B', '2', 'I', '9', 'U', 'F6'].includes(e.key)) {
      e.preventDefault()
    }
  }
  if (isTabKey) {
    e.preventDefault()
  }
}

// 构建消息数据的函数
const buildMessageData = () => {
  // 获取纯文本内容（包含 @ 用户名）
  const textContent = getTextContentWithMentions()
  
  // 获取提及的用户列表
  const mentions = nodeList
    .filter(item => item.type === 'at')
    .map(item => {
      try {
        return typeof item.content === 'string' ? JSON.parse(item.content) : item.content
      } catch {
         console.error('解析用户数据失败:', item.content)
        return item.content
      }
    }).filter(Boolean)
  console.log('mentions',mentions);
  
  return {
    text: textContent,
    mentions: mentions,
    rawContent: nodeList
  }
}

// 获取包含 @ 提及的文本内容
const getTextContentWithMentions = () => {
  if (!inputRef.value) return ''
  
  // 克隆输入框内容进行处理
  const clone = inputRef.value.cloneNode(true)
  const buttons = clone.querySelectorAll('button.mention-button')
  
  // 将 @ 按钮替换为文本
  buttons.forEach(button => {
    const userData = button.getAttribute('data-user')
    if (userData) {
      try {
        const user = JSON.parse(userData)
        const textNode = document.createTextNode(`@${user.name}`)
        button.parentNode.replaceChild(textNode, button)
      } catch (error) {
        console.error('解析用户数据失败:', error)
        button.parentNode.replaceChild(document.createTextNode(button.textContent), button)
      }
    } else {
      button.parentNode.replaceChild(document.createTextNode(button.textContent), button)
    }
  })
  
  return clone.innerText || clone.textContent || ''
}



//  onDataChange 函数
const onDataChange = () => {
  if (inputRef.value) {
    const newNodeList = []
    const editorChildNodes = [].slice.call(inputRef.value.childNodes)
    
    if (editorChildNodes.length > 0) {
      editorChildNodes.forEach((element) => {
        // 文本节点
        if (element.nodeType === Node.TEXT_NODE) {
          if (element.textContent && element.textContent.trim().length > 0) {
            newNodeList.push({
              type: 'text',
              content: element.textContent,
            })
          }
        }
        // 判断条件
        else if (element.nodeType === Node.ELEMENT_NODE && element.nodeName === 'BUTTON') {
          // 检查是否是提及按钮
          if (element.classList.contains('mention-button') || element.hasAttribute('data-user')) {
            const userData = element.getAttribute('data-user') || element.user
            if (userData) {
              try {
                const user = typeof userData === 'string' ? JSON.parse(userData) : userData
                newNodeList.push({
                  type: 'at',
                  content: user
                })
              } catch (error) {
                console.error('解析用户数据失败:', error)
                // 如果解析失败，至少保留文本内容
                newNodeList.push({
                  type: 'text',
                  content: element.textContent
                })
              }
            } else {
              // 如果没有用户数据，当作普通文本处理
              newNodeList.push({
                type: 'text',
                content: element.textContent
              })
            }
          } else {
            // 普通按钮当作文本处理
            newNodeList.push({
              type: 'text',
              content: element.textContent
            })
          }
        }
        // 其他元素节点
        else if (element.nodeType === Node.ELEMENT_NODE) {
          // 递归处理嵌套的元素
          const processElement = (el) => {
            const childNodes = [].slice.call(el.childNodes)
            childNodes.forEach(child => {
              if (child.nodeType === Node.TEXT_NODE) {
                if (child.textContent && child.textContent.trim().length > 0) {
                  newNodeList.push({
                    type: 'text',
                    content: child.textContent,
                  })
                }
              } else if (child.nodeType === Node.ELEMENT_NODE) {
                processElement(child)
              }
            })
          }
          processElement(element)
        }
      })
    }
    nodeList = newNodeList
    console.log('更新后的 nodeList:', nodeList) // 调试用
      // 触发输入事件，让父组件知道内容已更新
    inputValue.value = inputRef.value.innerText;
  }
}

// 确保正确设置 data-user 属性
const onSelectUser = (selectedUser) => {
  if (!props.isAtPopup) return
  const input = inputRef.value
  if (!input || !selection.value.node) return

  const range = document.createRange()
  let node = selection.value.node
  let offset = selection.value.offset

  // 向前查找 @ 符号
  while (offset > 0) {
    if (node.textContent[offset - 1] === '@') {
      break
    }
    offset--
  }

  // 创建新范围并插入提及按钮
  range.setStart(node, offset - 1)
  range.setEnd(node, selection.value.offset)
  range.deleteContents()

  const button = document.createElement('button')
  button.textContent = `@${selectedUser.name}`
  // 确保使用 data-user 属性
  button.setAttribute('data-user', JSON.stringify(selectedUser))
  button.contentEditable = 'false'
  button.className = 'mention-button'
  button.setAttribute(
    'style',
    `color: aqua;
    border: none;
    background: transparent;
    margin: 0 2px;
    font-size: inherit;
    pointer-events: none;`
  )

  range.insertNode(button)
  
  // 在按钮后添加一个空格
  const spaceNode = document.createTextNode(' ')
  range.insertNode(spaceNode)
  
  range.setStartAfter(spaceNode)
  range.setEndAfter(spaceNode)
  
  // 更新选区
  const newSel = document.getSelection()
  newSel.removeAllRanges()
  newSel.addRange(range)
  
  showMentionsPopup.value = false
  
  // 立即更新 nodeList
  onDataChange()
  
  input.dispatchEvent(
    new Event('input', {
      bubbles: true,
      cancelable: true,
    }),
  )
}

// 添加调试函数，在控制台检查 DOM 结构
const debugDOMStructure = () => {
  if (inputRef.value) {
    console.log('输入框的 innerHTML:', inputRef.value.innerHTML)
    console.log('输入框的 childNodes:', inputRef.value.childNodes)
    const buttons = inputRef.value.querySelectorAll('button')
    console.log('找到的按钮数量:', buttons.length)
    buttons.forEach((btn, index) => {
      console.log(`按钮 ${index}:`, {
        textContent: btn.textContent,
        className: btn.className,
        dataset: btn.dataset,
        attributes: btn.attributes
      })
    })
  }
}
const insertEmoji = (emoji) => {
  if (!inputRef.value) return;
  // 获取当前选区
  const sel = window.getSelection();
  if (sel.rangeCount > 0) {
    const range = sel.getRangeAt(0);
    range.deleteContents();
    // 创建表情文本节点
    const textNode = document.createTextNode(emoji);
     // 插入文本节点
    range.insertNode(textNode);
    
    // 移动光标到表情后面
    range.setStartAfter(textNode);
    range.setEndAfter(textNode);
    sel.removeAllRanges();
    sel.addRange(range);
  }
  
  // 触发数据更新
  onDataChange();
  inputRef.value.dispatchEvent(new Event('input', { bubbles: true }));
};

// 其他函数保持不变...
watch(showMentionsPopup, () => {
  if (showMentionsPopup.value) {
    popupPosition.value = getAtMentionsPosition()
  }
})

const scrollToSelectedUser = () => {
  const listElement = document.querySelector('.at-mentions-popup')
  const selectedElement = listElement?.children[selectedUserIndex.value]
  if (selectedElement && listElement) {
    const listRect = listElement.getBoundingClientRect()
    const selectedRect = selectedElement.getBoundingClientRect()
    if (selectedRect.top < listRect.top) {
      listElement.scrollTop -= listRect.top - selectedRect.top
    } else if (selectedRect.bottom > listRect.bottom) {
      listElement.scrollTop += selectedRect.bottom - listRect.bottom
    }
  }
}

const onInputKeyUp = (e) => {
  updateSelection()
  if (e.key === '@') {
    selectedUserIndex.value = 0
    showMentionsPopup.value = true
    searchKey.value = ''
  } else {
    checkIsShowSelectPopup()
  }
}

const updateSelection = () => {
  const input = inputRef.value
  if (!input) return
  const sel = document.getSelection()
  if (sel.rangeCount > 0) {
    const range = sel.getRangeAt(0)
    selection.value = {
      sel: sel,
      range: range,
      node: range.endContainer,
      offset: range.endOffset,
      text: range.toString(),
    }
  }
}

const checkIsShowSelectPopup = () => {
  if (!selection.value.node || selection.value.node.nodeName !== '#text') {
    showMentionsPopup.value = false
    return
  }

  const searchStr = selection.value.node.textContent.slice(0, selection.value.offset)
  const keywords = /@([^@]*)$/.exec(searchStr)

  if (keywords && keywords.length >= 2) {
    const [, keyWord] = keywords
    showMentionsPopup.value = true
    searchKey.value = keyWord
  } else {
    searchKey.value = ''
    showMentionsPopup.value = false
  }
}

const getAtMentionsPosition = () => {
  if (!selection.value.node) return { x: 0, y: 0 }

  const range = document.createRange()
  range.setStart(selection.value.node, selection.value.offset)
  range.collapse(true)

  const rect = range.getBoundingClientRect()
  let x = rect.left
  let y = rect.top

  if (inputRef.value) {
    const inputWidth = inputRef.value.offsetWidth
    const inputLeft = inputRef.value.getBoundingClientRect().left
    const inputRight = inputLeft + inputWidth
    const popupWidth = 150

    if (x + popupWidth > inputRight) {
      x = inputRight - popupWidth
    }
  }

  return { x, y }
}

const insertInputText = (content) => {
  const sel = selection.value.sel
  const range = selection.value.range
  if (!sel || !range || !content) return
  if (sel.getRangeAt(0) && sel.rangeCount) {
    range.deleteContents()
    const el = document.createElement('div')
    const text = document.createTextNode(content)
    el.appendChild(text)
    const frag = document.createDocumentFragment()
    let node
    let lastNode
    while ((node = el.firstChild)) {
      lastNode = frag.appendChild(node)
    }
    range.insertNode(frag)
    if (lastNode) {
      const newRange = range.cloneRange()
      if (!newRange) return
      newRange.setStartAfter(lastNode)
      newRange.collapse(true)
      sel.removeAllRanges()
      sel.addRange(newRange)
    }
  }
  inputValue.value = inputRef.value.innerText
}


const clear = () => {
  if (inputRef.value) {
    inputRef.value.innerHTML = '';
    inputValue.value = '';
    nodeList = [];
    hasContent.value = false;
    console.log('输入框已清空');
  }
};
onMounted(()=>{
  debugDOMStructure()
})
defineExpose({
  focus() {
    inputRef.value?.focus()
  },
  getRange() {
    return selection.value.range
  },
<<<<<<< Updated upstream
  insertInputText(text) {
    insertInputText(text)
=======
  insertAgentChip,
  removeAgentChip,
  openAgentPicker() {
    openAgentPicker()
>>>>>>> Stashed changes
  },
  getNodeList() {
    return nodeList;
  },
  clear,
  insertEmoji
})

// 文件上传
const triggerFileUpload = () => {
  fileInputRef.value?.click()
}

const handleFileSelect = (event) => {
  const files = event.target.files
  if (files && files.length > 0) {
    emit('file-selected', Array.from(files))
  }
  // 清空 input 以便再次选择相同文件
  event.target.value = ''
}
</script>

<style scoped lang="less">
.msg-input-wrapper {
  position: relative;
  width: 100%;

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
    padding: 10px 10px;
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
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    border-radius: 20px;
    color: rgb(var(--text-muted));
    background: transparent;
    border: none;
    cursor: pointer;
    overflow: hidden;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);

    .tool-icon {
      position: relative;
      z-index: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;

      svg {
        width: 18px;
        height: 18px;
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
}

<<<<<<< Updated upstream
/* 隐藏的文件上传 input */
.file-input-hidden {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

/* 表情面板 */
.emoji-panel {
  position: fixed;
  right: 10%;
  bottom: 100px;
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
    0 8px 16px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  overflow: hidden;
  display: flex;
  flex-direction: column;
=======
.input-block {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: rgb(var(--surface-color));
  border-radius: var(--radius-lg);
  border: 1px solid rgb(var(--border-color));
}

.msg-input {
  flex: 1;
  min-height: 40px;
  max-height: 140px;
  overflow-y: auto;
  padding: 10px;
  outline: none;
  white-space: pre-wrap;
  word-break: break-word;
}

.msg-input:empty::before {
  content: attr(data-placeholder);
  color: rgb(var(--text-muted));
}

.composer-toolbar {
  display: flex;
  gap: 4px;
  padding: 4px;
}

.tool-btn {
  width: 32px;
  height: 32px;
}

.agent-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0 4px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(59, 130, 246, 0.18);
  background: rgba(59, 130, 246, 0.08);
  color: rgb(var(--primary-color));
  font-size: 13px;
  line-height: 1.4;
}

.agent-chip-status {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #22c55e;
  flex-shrink: 0;
}

.status-busy {
  background: #f59e0b;
}

.status-offline {
  background: #94a3b8;
}

.agent-chip-label {
  white-space: nowrap;
}

.agent-chip-remove {
  color: rgb(var(--text-secondary));
  font-size: 11px;
  line-height: 1;
}

.agent-mention-panel {
  position: absolute;
  z-index: 30;
  min-width: 220px;
  max-width: min(320px, 100%);
  padding: 8px;
  border-radius: var(--radius-md);
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgb(var(--surface-color));
  box-shadow: var(--shadow-md);
>>>>>>> Stashed changes
}

.emoji-header {
  display: flex;
  width: 100%;
  align-items: center;
<<<<<<< Updated upstream
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.08);

  .emoji-title {
    font-size: 13px;
    font-weight: 600;
    color: rgb(var(--text-primary));
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .emoji-close {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 8px;
    border: none;
    background: rgba(99, 102, 241, 0.06);
    color: rgb(var(--text-muted));
    cursor: pointer;
    transition: all 0.15s ease;

    svg {
      width: 14px;
      height: 14px;
    }

    &:hover {
      background: rgba(239, 68, 68, 0.1);
      color: #ef4444;
    }
  }
=======
  gap: 10px;
  padding: 8px;
  border-radius: var(--radius-sm);
  text-align: left;
  background: transparent;
>>>>>>> Stashed changes
}

.emoji-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 4px;
  padding: 12px;
  overflow-y: auto;
  max-height: 260px;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(99, 102, 241, 0.2);
    border-radius: 2px;
  }
}

<<<<<<< Updated upstream
.emoji-item {
  display: flex;
=======
.agent-mention-avatar {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  object-fit: cover;
  flex-shrink: 0;
}

.agent-mention-avatar-fallback {
  display: inline-flex;
>>>>>>> Stashed changes
  align-items: center;
  justify-content: center;
  width: 100%;
  aspect-ratio: 1;
  border-radius: 10px;
  font-size: 22px;
  line-height: 1;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(139, 92, 246, 0.08));
    transform: scale(1.2);
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
  }

  &:active {
    transform: scale(0.9);
  }
}

/* 表情面板动画 */
.emoji-slide-enter-active,
.emoji-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.emoji-slide-enter-from,
.emoji-slide-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px) scale(0.9);
}

.emoji-slide-enter-to,
.emoji-slide-leave-from {
  opacity: 1;
  transform: translateX(-50%) translateY(0) scale(1);
}

.mention-button {
  display: inline;
  background: transparent;
  border: none;
  color: rgb(var(--primary-color));
<<<<<<< Updated upstream
  cursor: default;
  padding: 0 2px;
  margin: 0 2px;
  font-size: 14px;
  line-height: inherit;
  pointer-events: none;
  font-style: normal;
=======
>>>>>>> Stashed changes
}

.at-mentions-popup {
  position: fixed;
  width: 180px;
  max-height: 160px;
  transform: translateY(-100%);
  background-color: rgb(var(--surface-color));
  border-radius: var(--radius-md);
  padding: 6px;
  overflow-y: auto;
  color: rgb(var(--text-color));
  border: 1px solid rgb(var(--border-color));
  box-shadow: var(--shadow-md);

<<<<<<< Updated upstream
  .user-item {
    padding: 8px 12px;
    display: flex;
    align-items: center;
    border-radius: var(--radius-sm);
    font-size: 14px;
    color: rgb(var(--text-secondary));
    transition: all 0.12s ease;
=======
.agent-mention-name {
  color: rgb(var(--text-primary));
  font-size: 13px;
  font-weight: 600;
}
>>>>>>> Stashed changes

    &:hover {
      background-color: rgb(var(--primary-soft));
      color: rgb(var(--primary-color));
      cursor: pointer;
    }

    &.selected {
      background-color: rgb(var(--primary-soft));
      color: rgb(var(--primary-color));
    }
  }
}
</style>
