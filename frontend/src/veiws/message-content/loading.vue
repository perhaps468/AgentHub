<template>
  <div class="linyu-loading">
    <div class="loading-bounce-wrap">
      <img class="loading-bounce-image" src="../../../public/msg12.png" alt="loading">
    </div>
    <div v-if="props.label" class="mt-[10px]">{{ props.label }}</div>
  </div>
</template>
<script setup>
const props = defineProps({
  label: String,
})
</script>

<style scoped>
.linyu-loading {
  color: rgba(var(--text-color), 0.7);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  font-size: 14px;
  user-select: none;
}

.loading-bounce-wrap {
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-bounce-image {
  width: 100px;
  height: 100px;
  object-fit: contain;
  animation: image-bounce 0.9s ease-in-out infinite;
  will-change: transform;
}

@keyframes image-bounce {
  0%, 100% {
    transform: translateY(6px);
  }
  50% {
    transform: translateY(-6px);
  }
}
</style>
