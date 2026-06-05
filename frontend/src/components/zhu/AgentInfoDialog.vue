<template>
  <BaseDialog v-model="visible" title="Agent 详情" :show-footer="false">
    <div class="agent-detail">
      <div class="agent-header">
        <avatar :info="{ name: agent?.name, avatar: agent?.avatar }" size="72px" />
        <div class="agent-title">
          <h2>{{ agent?.name }}</h2>
          <span class="agent-badge" >
            {{ agent?.isCustom ? '自建' : '内置' }}
          </span>
        </div>
      </div>

      <div class="info-section">
        <div class="info-row">
          <span class="info-label">平台</span>
          <span class="info-value">{{ getPlatformLabel(agent?.platform) }}</span>
        </div>
        <div v-if="agent?.model" class="info-row">
          <span class="info-label">模型</span>
          <span class="info-value">{{ agent?.model }}</span>
        </div>
        <div v-if="agent?.role" class="info-row">
          <span class="info-label">角色</span>
          <span class="info-value">{{ agent?.role }}</span>
        </div>
      </div>

      <div v-if="agent?.description" class="info-section">
        <div class="section-title">简介</div>
        <p class="description">{{ agent?.description }}</p>
      </div>

      <div v-if="agent?.capabilityTags?.length" class="info-section">
        <div class="section-title">能力标签</div>
        <div class="tags">
          <span v-for="tag in agent.capabilityTags" :key="tag" class="tag">{{ tag }}</span>
        </div>
      </div>

      <div v-if="agent?.system_prompt" class="info-section">
        <div class="section-title">系统提示词</div>
        <div class="system-prompt">{{ agent?.system_prompt }}</div>
      </div>
    </div>
  </BaseDialog>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import type { SidebarAgent } from '../../types/agenthub'
import BaseDialog from './BaseDialog.vue'
import avatar from '../../veiws/img/avatar.vue'

const props = defineProps<{
  modelValue: boolean
  agent: SidebarAgent | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const getPlatformLabel = (platform?: string) => {
  const labels: Record<string, string> = {
    'claude-code': 'Claude Code',
    codex: 'Codex',
    opencode: 'OpenCode',
    custom: '自建平台',
  }
  return labels[platform || ''] || platform || '未知'
}
</script>

<style scoped lang="less">
.agent-detail {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.agent-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
}

.agent-title {
  display: flex;
  flex-direction: column;
  gap: 6px;

  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    color: #1e293b;
  }
}

.agent-badge {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #3b82f6;
  margin-bottom: 4px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.info-label {
  min-width: 60px;
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

.info-value {
  font-size: 13px;
  color: #1e293b;
  font-weight: 500;
}

.description {
  margin: 0;
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(59, 130, 246, 0.08);
  color: #3b82f6;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid rgba(59, 130, 246, 0.12);
}

.system-prompt {
  padding: 12px;
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.05);
  font-size: 12px;
  color: #475569;
  line-height: 1.6;
  max-height: 150px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(59, 130, 246, 0.2);
    border-radius: 2px;
  }
}
</style>
