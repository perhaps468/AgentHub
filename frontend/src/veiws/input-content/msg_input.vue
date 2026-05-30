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
        @keyup="onInputKeyUp"
        @keydown="onInputKeyDown"
        @input="onInputText"
        @blur="onInputBlur"
        @focus="onInputFocus"
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

const inputValue = defineModel('value')
let nodeList = []
const hasContent = ref(false)

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
  insertInputText(text) {
    insertInputText(text)
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
}

.emoji-header {
  display: flex;
  align-items: center;
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

.emoji-item {
  display: flex;
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
  cursor: default;
  padding: 0 2px;
  margin: 0 2px;
  font-size: 14px;
  line-height: inherit;
  pointer-events: none;
  font-style: normal;
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

  .user-item {
    padding: 8px 12px;
    display: flex;
    align-items: center;
    border-radius: var(--radius-sm);
    font-size: 14px;
    color: rgb(var(--text-secondary));
    transition: all 0.12s ease;

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
