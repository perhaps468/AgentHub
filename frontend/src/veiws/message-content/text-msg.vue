<template>
  <span v-if="isArrayContents" class="text-msg">
    <template v-for="item in contents" :key="item.id">
      <!-- @提及用户 -->
      <span v-if="item.type === TextContentType.At" class="text-msg-at">
        {{ `@${getUserInfo(item.content).name}` }}
      </span>
      <!-- 普通文本：使用 Markdown 渲染 -->
      <span v-else-if="item.type === TextContentType.Text" v-html="parseMarkdown(item.content)"></span>
    </template>
  </span>
  <!-- 非数组内容直接渲染（也支持 Markdown） -->
  <div v-else v-html="parseMarkdown(props.msg?.message)"></div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { TextContentType } from '../../types/textContentType'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// 配置 marked 选项（可选自定义）
marked.setOptions({
  breaks: true, // 允许 GFM 换行（单行换行转换为 <br>）
  gfm: true // 启用 GitHub  flavored Markdown
})

/**
 * 解析 Markdown 文本为安全的 HTML
 * @param text - 原始文本（可能包含 Markdown 语法）
 * @returns  sanitized HTML 字符串
 */
const parseMarkdown = (text) => {
  if (!text) return ''
  try {
    // 将 Markdown 转换为 HTML
    const rawHtml = marked.parse(text)
    // 使用 DOMPurify 清理 HTML，防止 XSS 攻击
    return DOMPurify.sanitize(rawHtml)
  } catch {
    // 解析失败时返回转义的原文
    return text
  }
}

const props = defineProps({ msg: Object, right: Boolean })
const contents = ref()
// 监听消息变化，解析 JSON 格式的消息内容
watch(
  () => props.msg,
  () => {
    try {
      contents.value = JSON.parse(props.msg?.message).map((item) => {
        // 如果 item.content 是字符串，尝试解析为对象
        if (typeof item.content === 'string') {
          try {
            item.content = JSON.parse(item.content)
          } catch {
            // 解析失败，保持原样
          }
        }
        return item
      })
    } catch {
      // JSON 解析失败，说明是纯文本消息
      contents.value = props.msg?.message
    }
  },
  { immediate: true }
)

const isArrayContents = computed(() => Array.isArray(contents.value))

/**
 * 获取用户信息（用于 @提及）
 * @param content - 内容（可能是对象或 JSON 字符串）
 */
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
</script>

<style lang="less" scoped>
.text-msg {
  .text-msg-at {
    color:aqua;
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