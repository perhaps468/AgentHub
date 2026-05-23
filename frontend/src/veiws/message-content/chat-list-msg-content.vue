<template>
  <div class="chat-list-msg-content">
    <!-- 群聊消息的发送者名称 -->
    <div v-if="props.isGroup">{{ `${msg?.fromInfo?.name}&nbsp;:&nbsp;` }}</div>
    
    <!-- 文本消息 -->
    <div v-if="msg?.type === MessageType.Text">
      <text_msg :msg="props.msg" />
    </div>
    
    <!-- 撤回消息 -->
    <div v-if="msg?.type === MessageType.Recall">撤回一条消息</div>
    
    <!-- 表情消息 -->
    <div v-if="msg?.type === MessageType.Emoji" class="flex items-center">
      <emoji_msg :src="msg?.message" height="18px" width="18px" padding="0" />
    </div>
    
    <!-- 音视频通话消息 -->
    <div v-if="msg?.type === MessageType.Call" class="flex items-center">[音视频通话]</div>
  </div>
</template>
<script setup>
import emoji_msg  from '../message-content/emoji-msg.vue'
import text_msg  from'../message-content/text-msg.vue'
import { MessageType} from '../../types/messageType'
const props = defineProps({
  msg: Object,
  isGroup: {
    type: Boolean,
    default: true,
  },
})
</script>
<style lang="less" scoped>
.chat-list-msg-content {
  width: 100%;
  display: flex;
  align-items: center;
}
</style>