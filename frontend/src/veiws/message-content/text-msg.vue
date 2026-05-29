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
  <div v-else v-html="parseMarkdown(displayContent)"></div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

import { TextContentType } from '../../types/textContentType'
import { normalizeRuntimeTextForDisplay, accumulateAndFilterStreaming, isLowSignalChunk } from '../../utils/runtime-text'

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

const props = defineProps({ msg: Object, right: Boolean })
const contents = ref()
const _rawMessage = ref('')

/**
 * Accumulated streaming content with leading low-signal chunks filtered out.
 * This ensures users do not see "####" flash at the start of a streaming message.
 * Once meaningful content has been seen, subsequent content is displayed as-is
 * to preserve visual continuity (e.g. markdown headers mid-stream).
 */
const displayContent = computed(() => {
  const raw = _rawMessage.value
  if (!raw) return ''

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
