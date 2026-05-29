<template>
  <div class="msg-box" :class="{ 'is-own': isOwn }">
    <template v-if="props.msg">
      <time-msg v-if="props.msg.isShowTime" :content="props.msg.createTime" class="msg-time" />
      <div v-if="props.msg.type === 'recall'" class="recall-msg">这条消息已撤回</div>
      <div v-else class="msg-box-wrapper">
        <Avatar :info="displayUser" size="40px" class="msg-avatar" />
        <div class="msg-box-info">
          <div class="msg-user-row">
            <div class="msg-username" v-if="!isOwn">
              {{ displayUser?.name || '未知用户' }}
            </div>
            <div class="msg-role" v-if="!isOwn">
              {{ roleLabel }}
            </div>
            <div v-if="props.msg.deliveryStatus === 'interrupted'" class="msg-status-badge interrupted">
              已中断
            </div>
            <div v-if="props.msg.isStreaming && props.msg.streamStatus === 'thinking'" class="msg-status-badge thinking">
              思考中...
            </div>
            <div v-if="props.msg.isStreaming && props.msg.streamStatus === 'streaming'" class="msg-status-badge streaming">
              <span class="streaming-dot"></span>
            </div>
          </div>
          <msg_content :right="isOwn" :msg="props.msg" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import { useAgentStore } from '../../store/module/useAgentStore'
import { useUserInfoStore } from '../../store/module/useUserStore'
import Avatar from '../img/avatar.vue'
import msg_content from '../message-content/msg_content .vue'
import TimeMsg from '../message-content/TimeMsg.vue'

const props = defineProps({
  msg: Object,
  user: Object,
})

const userStore = useUserInfoStore()
const agentStore = useAgentStore()
const isOwn = computed(() => props.msg?.fromId === userStore.userId)
const displayUser = computed(() => props.user || props.msg?.fromInfo)

const roleLabel = computed(() => {
  return agentStore.agent?.role ?? '成员'
})
</script>

<style scoped>
.msg-box {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 0;
}

.msg-time {
  text-align: center;
  justify-content: center;
}

.msg-box-wrapper {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.is-own .msg-box-wrapper {
  flex-direction: row-reverse;
}

.is-own .msg-avatar {
  margin-left: 0;
}

.recall-msg {
  margin-left: 52px;
  color: rgb(var(--text-muted));
  font-size: 12px;
}

.is-own .recall-msg {
  margin-left: 0;
  margin-right: 52px;
  text-align: right;
}

.msg-avatar {
  margin-top: 2px;
}

.msg-box-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.msg-user-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.msg-username {
  color: rgb(var(--text-color));
  font-size: 14px;
  font-weight: 600;
}

.msg-role {
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgb(var(--border-color));
  color: rgb(var(--text-secondary));
  font-size: 11px;
  line-height: 1.4;
}

.is-own .msg-role {
  border-color: rgba(var(--primary-color), 0.9);
  color: rgb(var(--text-color));
  background: rgb(var(--surface-color),0.1);
}

.msg-status-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  line-height: 1.4;
  display: flex;
  align-items: center;
  gap: 4px;
}

.msg-status-badge.interrupted {
  border: 1px solid rgba(215, 96, 96, 0.3);
  color: rgb(215, 96, 96);
  background: rgba(215, 96, 96, 0.08);
}

.msg-status-badge.thinking {
  border: 1px solid rgba(var(--primary-color), 0.3);
  color: rgb(var(--primary-color));
  background: rgba(var(--primary-color), 0.08);
}

.msg-status-badge.streaming {
  border: 1px solid rgba(var(--primary-color), 0.3);
  background: rgba(var(--primary-color), 0.08);
  padding: 4px 8px;
}

.streaming-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgb(var(--primary-color));
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(0.8);
  }
}
</style>
