<template>
  <div class="msg-input-wrapper">
    <teleport to="#app">
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
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useThemeStore } from '../../store/module/useThemeStore'
const themeStore = useThemeStore()

const inputRef = ref()
const popupPosition = ref({ x: 0, y: 0 })
const showMentionsPopup = ref(false)
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
const emit = defineEmits(['send'])

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
</script>

<style scoped lang="less">
.msg-input-wrapper {
  position: relative;
  width: 100%;

  .msg-input {
    width: 100%;
    min-height: 40px;
    max-height: 140px;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 10px 14px;
    border-radius: var(--radius-md);
    border: 1px solid rgb(var(--border-color));
    background: rgb(var(--surface-muted));
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

    &:focus {
      border-color: rgb(var(--primary-color));
      background: rgb(var(--surface-color));
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
  }
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
