<template>
  <div class="custom-button" :class="[props.class, props.type]" :style="props.style">
    <slot />
  </div>
</template>
<script setup>
const props = defineProps({
  class: String,
  style: Object,
  type: String,
})
</script>
<style lang="less" scoped>
.custom-button {
  width: 70px;
  height: 32px;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: rgb(var(--primary-color));
  border-radius: var(--radius-sm);
  color: #ffffff;
  user-select: none;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s ease;

  &:hover {
    background-color: rgb(var(--primary-strong));
    transform: translateY(-1px);
  }

  &.minor {
    color: rgb(var(--text-secondary));
    background-color: rgb(var(--surface-muted));
    border: 1px solid rgb(var(--border-color));

    &:hover {
      background-color: rgb(var(--surface-color));
      border-color: rgb(--border-strong);
    }
  }

  &.error {
    background-color: rgb(var(--danger-color));

    &:hover {
      background-color: rgba(239, 68, 68, 0.85);
    }
  }
}
</style>
