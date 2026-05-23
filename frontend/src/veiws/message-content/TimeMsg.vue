<template>
  <div class="time-row">
    <span class="time-text">{{ formatTime(props.content) }}</span>
  </div>
</template>

<script setup>
import { formatTime } from '../../utils/date'

const props = defineProps({
  content: String,
})
</script>

<style scoped>
.time-row {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
}

.time-text {
  color: rgb(var(--text-muted));
  font-size: 12px;
  line-height: 1;
}
</style>
