<template>
  <div class="msg-box" :class="{ 'is-own': isOwn }">
    <template v-if="props.msg">
      <time-msg v-if="props.msg.isShowTime" :content="props.msg.createTime" class="msg-time" />
      <div v-if="props.msg.type === 'recall'" class="recall-msg">这条消息已撤回</div>
      <div v-else class="msg-box-wrapper">
        <Avatar :info="displayUser" size="40px" class="msg-avatar" />
        <div class="msg-box-info">
          <div class="msg-user-row">
            <div class="msg-username">
              {{ displayUser?.name || '未知用户' }}
            </div>
            <div class="msg-role">
              {{ isOwn ? '我' : '成员' }}
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

import { useUserInfoStore } from '../../store/module/useUserStore'
import Avatar from '../img/avatar.vue'
import msg_content from '../message-content/msg_content .vue'
import TimeMsg from '../message-content/TimeMsg.vue'

const props = defineProps({
  msg: Object,
  user: Object,
})

const userStore = useUserInfoStore()
const isOwn = computed(() => props.msg?.fromId === userStore.userId)
const displayUser = computed(() => props.user || props.msg?.fromInfo)
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
  margin-left: 52px;
}

.msg-box-wrapper {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.recall-msg {
  margin-left: 52px;
  color: rgb(var(--text-muted));
  font-size: 12px;
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
  border-color: rgba(var(--primary-color), 0.45);
  color: rgb(var(--primary-strong));
  background: rgb(var(--primary-soft));
}
</style>
