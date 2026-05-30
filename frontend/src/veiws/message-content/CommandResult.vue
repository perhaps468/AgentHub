<template>
  <div class="command-result" :class="{ 'is-success': success, 'is-error': !success && exitCode !== 0, 'is-timeout': timedOut }">
    <div class="command-header">
      <span class="command-label">命令</span>
      <code class="command-text">{{ command }}</code>
      <span class="command-status">
        <span v-if="timedOut" class="status-badge timeout">超时</span>
        <span v-else-if="success" class="status-badge success">成功</span>
        <span v-else class="status-badge error">失败 ({{ exitCode }})</span>
      </span>
    </div>

    <div v-if="stdout" class="command-output">
      <div class="output-label">输出</div>
      <pre class="output-content stdout">{{ stdout }}</pre>
    </div>

    <div v-if="stderr" class="command-output error">
      <div class="output-label">错误</div>
      <pre class="output-content stderr">{{ stderr }}</pre>
    </div>

    <div v-if="!stdout && !stderr" class="command-output empty">
      <div class="output-label">输出</div>
      <pre class="output-content">(无输出)</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface CommandResultData {
  command: string
  cwd?: string
  stdout: string
  stderr: string
  exit_code: number
  success: boolean
  timed_out: boolean
}

const props = defineProps<{
  result: CommandResultData
}>()

const command = computed(() => props.result.command || 'unknown')
const stdout = computed(() => props.result.stdout || '')
const stderr = computed(() => props.result.stderr || '')
const exitCode = computed(() => props.result.exit_code ?? 0)
const success = computed(() => props.result.success ?? (exitCode.value === 0))
const timedOut = computed(() => props.result.timed_out ?? false)
</script>

<style scoped>
.command-result {
  border: 1px solid rgb(var(--border-color));
  border-radius: 8px;
  background: rgb(var(--surface-color));
  overflow: hidden;
  margin: 8px 0;
  font-size: 13px;
}

.command-result.is-success {
  border-color: rgba(34, 197, 94, 0.4);
}

.command-result.is-error {
  border-color: rgba(239, 68, 68, 0.4);
}

.command-result.is-timeout {
  border-color: rgba(251, 191, 36, 0.4);
}

.command-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: rgba(var(--surface-secondary), 0.5);
  border-bottom: 1px solid rgb(var(--border-color));
}

.command-label {
  font-weight: 600;
  color: rgb(var(--text-secondary));
  font-size: 11px;
  text-transform: uppercase;
}

.command-text {
  flex: 1;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 12px;
  color: rgb(var(--text-color));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.command-status {
  flex-shrink: 0;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.status-badge.success {
  background: rgba(34, 197, 94, 0.15);
  color: rgb(34, 197, 94);
}

.status-badge.error {
  background: rgba(239, 68, 68, 0.15);
  color: rgb(239, 68, 68);
}

.status-badge.timeout {
  background: rgba(251, 191, 36, 0.15);
  color: rgb(251, 191, 36);
}

.command-output {
  padding: 10px 14px;
  border-bottom: 1px solid rgb(var(--border-color));
}

.command-output:last-child {
  border-bottom: none;
}

.command-output.error {
  background: rgba(239, 68, 68, 0.05);
}

.command-output.empty {
  opacity: 0.6;
}

.output-label {
  font-weight: 600;
  color: rgb(var(--text-secondary));
  font-size: 11px;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.output-content {
  margin: 0;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: rgb(var(--text-color));
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
}

.command-output.error .output-content {
  color: rgb(239, 68, 68);
}
</style>
