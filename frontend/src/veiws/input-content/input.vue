<template>
  <div class="msg-input-container">
    <file_transfer
      v-model:visible="fileInfo.fileVisible"
      :target-info="fileInfo.fileTargetInfo || undefined"
      :is-send="fileInfo.fileIsSend"
      :file="fileInfo.file || undefined"
    />
    <video_chat
      v-model:visible="videoInfo.videoVisible"
      :target-info="videoInfo.videoTargetInfo"
      :is-send="videoInfo.videoIsSend"
      :is-only-audio="videoInfo.videoIsOnlyAudio"
    />

    <input
      ref="fileInput"
      type="file"
      class="hidden-file-input"
      @change="handlerSendFile"
    />

    <div class="chat-msg-input">
      <msg_input
        ref="msgInputRef"
        v-model:value="localValue"
        :handlerSubmitMsg="props.handlerSubmitMsg"
        :user="props.user"
        :is-at-popup="props.targetId === '1'"
        @input="updateValue"
        @send="onSendMsg"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'

import { invite } from '../../api/file'
import { currentTargetEventBus } from '../../utils/EventBus'
import EventBus from '../../utils/EventBus'
import { useToast, type ShowToast } from '../useToast'
import { useChatMsgStore } from '../../store/module/useChatMsgStore'
import { useUserInfoStore } from '../../store/module/useUserStore'
import type { UserInfo } from '../../types/message'
import file_transfer from './file-transfer.vue'
import msg_input from './msg_input.vue'
import video_chat from './video-chat.vue'

type CallTarget = {
  id: string | number
  targetInfo?: UserInfo | null
}

type InviteMessage = {
  fromId: string | number
  type: string
  isOnlyAudio?: boolean
  fileInfo?: File | null
}

type SendPayload = string | { text?: string }

type MsgInputExpose = {
  getNodeList?: () => unknown[]
  insertEmoji?: (emoji: string) => unknown
}

const props = defineProps<{
  value?: string
  targetId?: string
  user?: object
  handlerSubmitMsg?: (text: string) => void
}>()

const emit = defineEmits(['update:value'])

const showToast: ShowToast = useToast()
const msgStore = useChatMsgStore()
const userInfoStore = useUserInfoStore()
const currentSelectTarget = ref<CallTarget | null>(null)
const msgInputRef = ref<MsgInputExpose | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const localValue = ref(props.value || '')

const videoInfo = reactive({
  videoVisible: false,
  videoTargetInfo: null as UserInfo | null,
  videoIsSend: false,
  videoIsOnlyAudio: false,
})

const fileInfo = reactive({
  fileVisible: false,
  fileTargetInfo: null as UserInfo | null,
  fileIsSend: false,
  file: null as File | null,
})

watch(
  () => props.value,
  (newValue) => {
    localValue.value = newValue || ''
  },
)

const unsubscribe = currentTargetEventBus.subscribe((target) => {
  currentSelectTarget.value = target
})

const updateValue = () => {
  emit('update:value', localValue.value)
}

const onSendMsg = (data: SendPayload) => {
  if (props.handlerSubmitMsg) {
    const text = typeof data === 'string' ? data : (data?.text || localValue.value)
    props.handlerSubmitMsg(text)
  }
}

const getNodeList = () => {
  if (msgInputRef.value?.getNodeList) {
    return msgInputRef.value.getNodeList()
  }
  return []
}

const handlerVideoMsg = async (payload: unknown) => {
  const msg = payload as InviteMessage
  if (msg.fromId === userInfoStore.userId) return
  if (msg.type === 'invite') {
    const targetInfo = msgStore.userListMap.get(String(msg.fromId))
    videoInfo.videoVisible = true
    videoInfo.videoTargetInfo = targetInfo ?? null
    videoInfo.videoIsSend = false
    videoInfo.videoIsOnlyAudio = msg.isOnlyAudio ?? false
  }
}

const handlerFileMsg = async (payload: unknown) => {
  const msg = payload as InviteMessage
  if (msg.fromId === userInfoStore.userId) return
  if (msg.type === 'invite') {
    const targetInfo = msgStore.userListMap.get(String(msg.fromId))
    fileInfo.fileVisible = true
    fileInfo.fileTargetInfo = targetInfo ?? null
    fileInfo.fileIsSend = false
    fileInfo.file = msg.fileInfo ?? null
  }
}

const handlerSendFile = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const files = input.files
  if (files && files.length > 0) {
    if (!currentSelectTarget.value) {
      showToast('未选择目标用户', true)
      return
    }

    fileInfo.fileVisible = true
    fileInfo.fileTargetInfo = currentSelectTarget.value.targetInfo ?? null
    fileInfo.fileIsSend = true
    fileInfo.file = files[0]

    const targetInfo = fileInfo.fileTargetInfo
    const selectedFile = fileInfo.file
    if (!targetInfo || !selectedFile) return

    invite({
      userId: String(targetInfo.id),
      fileInfo: { name: selectedFile.name, size: selectedFile.size },
    })

    input.value = ''
  } else {
    showToast('文件无效', true)
  }
}

const openFilePicker = () => {
  fileInput.value?.click()
}

const handlerVideoCall = (info: UserInfo | null | undefined, isSend: boolean, isOnlyAudio: boolean) => {
  if (!info) return

  invite({ userId: info.id, isOnlyAudio })
  videoInfo.videoVisible = true
  videoInfo.videoTargetInfo = info
  videoInfo.videoIsSend = isSend
  videoInfo.videoIsOnlyAudio = isOnlyAudio
}

const startAudioCall = () => {
  handlerVideoCall(currentSelectTarget.value?.targetInfo, true, true)
}

const startVideoCall = () => {
  handlerVideoCall(currentSelectTarget.value?.targetInfo, true, false)
}

const insertEmoji = (emoji: string) => {
  return msgInputRef.value?.insertEmoji?.(emoji)
}

onMounted(() => {
  EventBus.on('on-receive-file', handlerFileMsg)
  EventBus.on('on-receive-video', handlerVideoMsg)
})

onUnmounted(() => {
  EventBus.off('on-receive-file', handlerFileMsg)
  EventBus.off('on-receive-video', handlerVideoMsg)
  unsubscribe()
})

defineExpose({
  getNodeList,
  insertEmoji,
  openFilePicker,
  startAudioCall,
  startVideoCall,
})
</script>

<style scoped>
.msg-input-container {
  display: flex;
  align-items: center;
  width: 100%;
}

.hidden-file-input {
  display: none;
}

.chat-msg-input {
  width: 100%;
  min-width: 0;
}
</style>
