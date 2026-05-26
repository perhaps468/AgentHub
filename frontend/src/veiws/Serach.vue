<template>
  <div
    class="input-wrapper"
    :style="`width:${props.width};
         border-radius:${props.radius};
         height:${props.height};
         font-size:${props.fontSize};
         padding:${props.padding};
         background-color: ${props.backgroundColor};`"
  >
    <!-- 搜索图标 -->
    <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="11" cy="11" r="8"/>
      <path d="M21 21l-4.35-4.35"/>
    </svg>

    <div v-if="props.label" class="input-label">{{ props.label }}</div>
    <input
      ref="inputRef"
      class="input"
      :type="props.type"
      :readonly="props.readonly"
      :placeholder="props.placeholder"
      v-model="value"
      @keydown.enter="(e) => emit('keydown.enter', e)"
      @input="handleInput"
    />
    <div v-if="props.limit" class="input-limit">
      {{ value.toString().trim().length }}/{{ props.limit }}
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const inputRef = ref()
const props = defineProps({
  placeholder: String,
  type: String,
  label: String,
  limit: Number,
  readonly: {
    type: Boolean,
    default: false,
  },
  width: {
    type: String,
    default: '100%',
  },
  height: {
    type: String,
    default: '42px',
  },
  fontSize: {
    type: String,
    default: '14px',
  },
  radius: {
    type: String,
    default: '10px',
  },
  padding: {
    type: String,
    default: '0 12px',
  },
  backgroundColor: {
    type: String,
    default: 'rgba(255, 255, 255, 0.6)',
  },
})

// 简化 v-model 的双向绑定实现
const value = defineModel('value')

const handleInput = (event) => {
  const inputValue = event.target.value.toString().trim()
  if (props.limit && inputValue.length > props.limit) {
    value.value = inputValue.slice(0, props.limit)
  } else {
    value.value = inputValue
  }
}

defineExpose({
  focus() {
    inputRef.value?.focus()
  },
  getInput() {
    return inputRef.value
  },
})

const emit = defineEmits(['keydown.enter'])
</script>

<style scoped lang="less">
.input-wrapper {
  position: relative;
  padding: 0 12px;
  width: 100%;
  height: 42px;
  font-size: 14px;
  background-color: rgba(255, 255, 255, 0.6);
  border: 1.5px solid rgba(59, 130, 246, 0.15);
  border-radius: 10px;
  display: flex;
  align-items: center;
  color: #1e293b;
  transition: all 0.25s ease;

  &:focus-within {
    background-color: rgba(255, 255, 255, 0.9);
    border-color: #3b82f6;
    box-shadow:
      0 0 0 3px rgba(59, 130, 246, 0.1),
      0 4px 12px rgba(59, 130, 246, 0.08);
  }

  .search-icon {
    width: 18px;
    height: 18px;
    margin-right: 8px;
    color: #94a3b8;
    flex-shrink: 0;
    transition: color 0.2s ease;
  }

  &:focus-within .search-icon {
    color: #3b82f6;
  }

  .input-label {
    margin-right: 10px;
    min-width: 70px;
    max-width: 70px;
    font-weight: 500;
    flex-shrink: 1;
    color: #64748b;
  }

  .input {
    width: 100%;
    outline: none;
    background-color: transparent;
    border: none;
    color: #1e293b;
    font-size: 14px;

    &::placeholder {
      color: #94a3b8;
    }
  }

  .input-limit {
    width: 50px;
    flex-shrink: 1;
    display: flex;
    justify-content: flex-end;
    color: #94a3b8;
    font-size: 12px;
  }
}
</style>
