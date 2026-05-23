<template>
<template v-if="visible">
    <draggable_window >
        <div class="video-answer">
            <avatar :info="props.targetInfo" class="mr-[10px]"/>
             <div class="answer-content">
                <div class="answer-content-name">{{ props.targetInfo?.name }}</div>
                <div class="answer-content-label flex items-center">
                {{
                    props.isSend
                    ? '正在等待对方接听'
                    : `邀请你${props.isOnlyAudio ? '语音' : '视频'}通话`
                }}
                </div>
            <loading_dots />
             <div class="flex gap-[15px]">
                <div
                  v-if="!props.isSend"
                  class="operation-button bg-[rgb(var(--primary-color))]"
                  @click="onAccept"
                  style="box-shadow: 0 0 15px rgba(var(--primary-color))"
                >
                  <svg t="1759155258698" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="8864" width="48" height="48"><path d="M511.868892 1023.999069A512.008492 512.008492 0 0 1 312.627803 40.489527a512.000737 512.000737 0 0 1 398.482177 943.289056A508.665833 508.665833 0 0 1 511.868892 1023.999069zM343.05298 313.881805L324.183631 334.232471a86.443798 86.443798 0 0 0-17.992967 30.386399 115.054167 115.054167 0 0 0-6.095893 43.04352c0.961693 27.865832 14.851953 65.302062 39.119192 105.398458a511.155378 511.155378 0 0 0 85.683751 105.848283c64.891015 60.67973 146.782283 99.899745 208.625351 99.899745a105.778482 105.778482 0 0 0 42.764319-8.073568 88.475762 88.475762 0 0 0 23.794148-15.511179h0.054289l1.985431-1.326206a13.184502 13.184502 0 0 0 2.443011-2.03972l19.854308-21.366648a13.471459 13.471459 0 0 0 3.598594-9.609175 13.316347 13.316347 0 0 0-4.265574-9.306707l-9.616931-8.965462-83.496674-78.106539a13.300836 13.300836 0 0 0-9.120573-3.598594h-0.473091a13.424925 13.424925 0 0 0-9.306707 4.281086l-20.839269 22.390386-14.130683 15.216466a56.282311 56.282311 0 0 1-9.384263 0.65147 112.936891 112.936891 0 0 1-38.731413-7.429855 171.739769 171.739769 0 0 1-57.391361-36.668426 161.432591 161.432591 0 0 1-46.59558-70.971397 86.986689 86.986689 0 0 1-4.203529-31.301559l35.202619-37.824009a13.432681 13.432681 0 0 0-0.66698-18.95466l-93.067072-87.048734a13.331858 13.331858 0 0 0-9.128328-3.598593h-0.473091a13.277569 13.277569 0 0 0-9.306707 4.250063z" fill="#47E08E" p-id="8865"></path></svg>
                </div>
                <div
                  class="operation-button bg-[#FF4C4C]"
                  style="box-shadow: 0 0 15px #ff4c4c"
                  @click="onHangup"
                >
                  <svg t="1759155181499" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="4698" width="48" height="48"><path d="M509.64 63c-247.7 0-448.5 200.8-448.5 448.5S261.94 960 509.64 960s448.5-200.8 448.5-448.5S757.34 63 509.64 63z m215.61 530.32c-24.18 0-67.4-13.89-84.9-19.55s-24.18-12.86-28.81-39.62-23.15-36-44.25-37c-14.07-0.68-36.82-0.68-50.42-0.61v0.1l-5.66-0.06-5.66 0.06v-0.1c-13.61-0.07-36.36-0.07-50.43 0.61-21.09 1-39.62 10.29-44.25 37s-11.32 34-28.81 39.62-60.71 19.55-84.9 19.55-28.3-58.66-28.3-58.66c0-76.66 190.89-97.76 216.14-97.76h52.48c25.21 0 216.1 21.1 216.1 97.76-0.03 0-4.14 58.66-28.33 58.66z" fill="#FF3B30" p-id="4699"></path></svg>
                </div>
              </div>
          </div>
        </div>
    </draggable_window  v-if="!isReady"   :rounded="20" :resize="false">
    <!--  语音通话-->
    <draggable_window
      v-if="isReady && props.isOnlyAudio"
      :rounded="20"
      :resize="false"
      :refresh="reducedSize"
    >
      <div class="audio-call" :class="{ reduced: isReduced }">
        <div class="audio-call-info">
          <avatar :info="props.targetInfo" class="info-avatar" @click="isReduced = false" />
          <div class="info-content">
            <template v-if="!isReduced">
              <div class="content-name">{{ props.targetInfo.name }}</div>
              <div class="content-time flex items-center">
                {{ formatTimingTime(time) }}
              </div>
            </template>
            <div v-else class="content-time">
              {{ formatTimingTime(time) }}
            </div>
          </div>
        </div>
        <div v-if="!isReduced" class="flex gap-[15px]">
          <div
            class="operation-button bg-[#FFF]"
            style="box-shadow: 0 0 15px #fff"
            @click="isAudioEnabled = !isAudioEnabled"
          >
            <i
              :class="`iconfont icon-${!isAudioEnabled ? 'maikefengguan' : 'maikefengkai'}`"
              style="font-size: 18px; color: #6c6c6c"
            />
          </div>
          <div
            class="operation-button bg-[#FF4C4C]"
            style="box-shadow: 0 0 15px #ff4c4c"
            @click="onHangup"
          >
            <svg t="1759155181499" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="4698" width="48" height="48"><path d="M509.64 63c-247.7 0-448.5 200.8-448.5 448.5S261.94 960 509.64 960s448.5-200.8 448.5-448.5S757.34 63 509.64 63z m215.61 530.32c-24.18 0-67.4-13.89-84.9-19.55s-24.18-12.86-28.81-39.62-23.15-36-44.25-37c-14.07-0.68-36.82-0.68-50.42-0.61v0.1l-5.66-0.06-5.66 0.06v-0.1c-13.61-0.07-36.36-0.07-50.43 0.61-21.09 1-39.62 10.29-44.25 37s-11.32 34-28.81 39.62-60.71 19.55-84.9 19.55-28.3-58.66-28.3-58.66c0-76.66 190.89-97.76 216.14-97.76h52.48c25.21 0 216.1 21.1 216.1 97.76-0.03 0-4.14 58.66-28.33 58.66z" fill="#FF3B30" p-id="4699"></path></svg>
          </div>
          <div
            class="operation-button bg-[#FFF]"
            style="box-shadow: 0 0 15px #fff"
            @click="isReduced = true"
          >
            <i class="iconfont icon-shousuo" style="font-size: 24px; color: #6c6c6c" />
          </div>
        </div>
        <video ref="local" autoPlay class="hidden" />
        <video ref="remote" autoPlay class="hidden" />
      </div>
    </draggable_window>
    <!--  视频通话-->
    <draggable_window v-if="isReady && !props.isOnlyAudio" :rounded="20" :resize="false">
      <div class="video-call">
        <video
          ref="local"
          autoPlay
          :class="`${isVideoSwitch ? 'max-window' : 'min-window'}`"
          @click="isVideoSwitch = !isVideoSwitch"
        />
        <video
          ref="remote"
          autoPlay
          :class="`${isVideoSwitch ? 'min-window' : 'max-window'}`"
          @click="isVideoSwitch = !isVideoSwitch"
        />
        <div class="video-call-operation">
          <div class="text-white mb-[2px]">
            {{ formatTimingTime(time) }}
          </div>
          <div class="flex gap-[10px]">
            <div
              class="operation-button bg-[#FFF]"
              style="box-shadow: 0 0 15px #fff"
              @click="isAudioEnabled = !isAudioEnabled"
            >
              <i
                :class="`iconfont icon-${!isAudioEnabled ? 'maikefengguan' : 'maikefengkai'}`"
                style="font-size: 18px; color: #6c6c6c"
              />
            </div>
            <div
              class="operation-button bg-[#FF4C4C]"
              style="box-shadow: 0 0 15px #ff4c4c"
              @click="onHangup"
            >
              <i class="iconfont icon-guaduan" style="font-size: 24px" />
              <svg t="1759155181499" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="4698" width="48" height="48"><path d="M509.64 63c-247.7 0-448.5 200.8-448.5 448.5S261.94 960 509.64 960s448.5-200.8 448.5-448.5S757.34 63 509.64 63z m215.61 530.32c-24.18 0-67.4-13.89-84.9-19.55s-24.18-12.86-28.81-39.62-23.15-36-44.25-37c-14.07-0.68-36.82-0.68-50.42-0.61v0.1l-5.66-0.06-5.66 0.06v-0.1c-13.61-0.07-36.36-0.07-50.43 0.61-21.09 1-39.62 10.29-44.25 37s-11.32 34-28.81 39.62-60.71 19.55-84.9 19.55-28.3-58.66-28.3-58.66c0-76.66 190.89-97.76 216.14-97.76h52.48c25.21 0 216.1 21.1 216.1 97.76-0.03 0-4.14 58.66-28.33 58.66z" fill="#FF3B30" p-id="4699"></path></svg>

            </div>
            <div
              class="operation-button bg-[#FFF]"
              style="box-shadow: 0 0 15px #fff"
              @click="isVideoEnabled = !isVideoEnabled"
            >
              <i
                :class="`iconfont icon-${!isVideoEnabled ? 'shexiangtou_guanbi' : 'shexiangtou'}`"
                style="font-size: 18px; color: #6c6c6c"
              />
            </div>
          </div>
        </div>
      </div>
    </draggable_window>
</template>
</template>
<script setup>
import draggable_window from '../shape/Draggable-window.vue'
import  avatar from '../img/avatar.vue'
import loading_dots from '../loading-dots.vue' 
import {accept,hangup,candidate,offer,answer} from '../../api/video'
import {send}  from '../../api/message'
import {MessageSource} from '../../types/messageSource'
import { useToast } from '../useToast'
import { ref ,onMounted,watch,computed,onUnmounted,nextTick} from 'vue'
import { formatTimingTime } from '../../utils/date'
import EventBus from '../../utils/EventBus'
import {MessageType} from '../../types/messageType'
const props = defineProps({ targetInfo: Object, isSend: Boolean, isOnlyAudio: Boolean })
const visible = defineModel('visible')
const pc = ref()
const isReady = ref(false)
const isReduced = ref(false)
const webcamStream = ref()
const time = ref(0)
const remote = ref()
const timerId = ref()
const showToast =useToast()
const isVideoSwitch = ref(false)
const isAudioEnabled = ref(true)
const isVideoEnabled = ref(true)
const local = ref()
const reducedSize = computed(() => {
  if (isReduced.value) {
    return { width: 90 }
  } else {
    return { width: 320 }
  }
})
const initRTCPeerConnection =()=>{
    const iceServer = {
        iceServers:[
           {
                url: 'stun:stun.l.google.com:19302',
            },
            {
                url: 'turn:numb.viagenie.ca',
                username: 'webrtc@live.com',
                credential: 'muazkh',
            },
        ]
    }
    pc.value = new RTCPeerConnection(iceServer)
    pc.value.onicecandidate = handleICECandidateEvent
    pc.value.oniceconnectionstatechange = handleICEConnectionStateChangeEvent
    //媒体流显示在页面
    pc.value.ontrack = handleTrackEvent
}
const handleICECandidateEvent = (event) => {
  if (event.candidate) {
    candidate({ userId: props.targetInfo.id, candidate: event.candidate })
  }
}
const handleNewICECandidateMsg = async (data) => {
  const candidate = new RTCIceCandidate(data.candidate)
  try {
    await pc.value.addIceCandidate(candidate)
  } catch (err) {
    console.log(err)
  }
}
const handleICEConnectionStateChangeEvent = () => {
  if (pc.value?.iceConnectionState === 'disconnected') {
    showToast('对方通话异常~', true)
    onHangup()
  } else {
    handlerDestroyTime()
    timerId.value = setInterval(() => {
      time.value = time.value + 1
    }, 1000)
  }
}

const handlerVideoMsg = (msg) => {
  switch (msg.type) {
    case 'offer': {
      handleVideoOfferMsg(msg)
      break
    }
    case 'answer': {
      handleVideoAnswerMsg(msg)
      break
    }
    case 'candidate': {
      handleNewICECandidateMsg(msg)
      break
    }
    case 'hangup': {
      handlerDestroyTime()
      showToast('对方已挂断~', true)
      setTimeout(async function () {
        visible.value = false
      }, 2000)
      break
    }
    case 'accept': {
      onOffer()
      break
    }
  }
}
const handleVideoOfferMsg = async (data) => {
  const desc = new RTCSessionDescription(data.desc)
  await pc.value.setRemoteDescription(desc)
  await pc.value.setLocalDescription(await pc.value.createAnswer())
  await answer({ userId: props.targetInfo.id, desc: pc.value.localDescription })
}
const handleVideoAnswerMsg = async (data) => {
  const desc = new RTCSessionDescription(data.desc)
  await pc.value.setRemoteDescription(desc).catch(reportError)
}
const handleTrackEvent = (event) => {
  remote.value.srcObject = event.streams[0]
}
const videoCall = async () => {
  try {
    webcamStream.value = await navigator.mediaDevices.getUserMedia({
      video: !props.isOnlyAudio,
      audio: true,
    })
    local.value.srcObject = webcamStream.value
    local.value.muted = true
    webcamStream.value.getTracks().forEach((track) => pc.value.addTrack(track, webcamStream.value))
    console.log('local element:', local.value)
  } catch {
    showToast('相机/麦克风权限未允许~', true)
  }
}
const onOffer = async () => {
  isReady.value = true
  await nextTick(async () => {
    initRTCPeerConnection()
    await videoCall()
    const offer = await pc.value.createOffer()
    await pc.value.setLocalDescription(offer)
    await offer({ userId: props.targetInfo.id, desc: pc.value.localDescription })
  })
}

const onAccept = async () => {
  isReady.value = true
  await nextTick(async () => {
    initRTCPeerConnection()
    await videoCall()
  })
    accept({ userId: props.targetInfo.id }).then(() => {
    isReady.value = true
  })
}
const handlerDestroyTime = () => {
  if (timerId.value) clearInterval(timerId.value)
}
const onHangup = () => {
  handlerDestroyTime()
  hangup({ userId: props.targetInfo.id }).then(() => {
    visible.value = false
  })
    send({
    targetId: props.targetInfo.id,
    source: MessageSource.User,
    msgContent: time.value,
    type: MessageType.Call,
  })
}
watch(visible, () => {
  if (!visible.value) {
    isReady.value = false
    isReduced.value = false
    if (webcamStream.value) {
      webcamStream.value.getTracks().forEach((track) => track.stop())
      webcamStream.value = null
    }
    pc.value = null
    time.value = 0
  }
})
watch(isVideoEnabled, () => {
  if (webcamStream.value) {
    webcamStream.value.getVideoTracks().forEach((track) => {
      track.enabled = isVideoEnabled.value
    })
  }
})

watch(isAudioEnabled, () => {
  if (webcamStream.value) {
    webcamStream.value.getAudioTracks().forEach((track) => {
      track.enabled = isAudioEnabled.value
    })
  }
})
onMounted(()=>{
    console.log('vi',visible.value);
    EventBus.on('on-receive-video', handlerVideoMsg);
    
})
onUnmounted(async () => {
  EventBus.off('on-receive-video', handlerVideoMsg)
})
</script>
<style lang="less" scoped>
.video-answer {
  width: 320px;
  background-color: rgba(48, 48, 75, 0.9);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px;
  border-radius: 20px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  border: 1px solid #ccc;

  .answer-content {
    .answer-content-name {
      color: #ffffff;
      font-weight: 600;
    }

    .answer-content-label {
      color: rgba(255, 255, 255, 0.7);
      font-size: 14px;
    }
  }
}

.audio-call {
  background-color: rgba(48, 48, 75, 0.9);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px;
  border-radius: 20px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  border: 1px solid #ccc;
  width: 320px;

  &.reduced {
    width: 90px;
    justify-content: center;

    .audio-call-info {
      flex-direction: column;
      justify-content: center;

      .info-avatar {
        margin-right: 0;
        margin-bottom: 5px;
      }
    }
  }

  .audio-call-info {
    display: flex;
    align-items: center;

    .info-avatar {
      margin-right: 10px;
    }

    .info-content {
      display: flex;
      flex-direction: column;

      .content-name {
        color: #ffffff;
        font-weight: 600;
      }

      .content-time {
        color: rgba(255, 255, 255, 0.7);
        font-size: 14px;
      }
    }
  }
}

.video-call {
  width: 600px;
  background-color: rgba(48, 48, 75, 0.9);
  backdrop-filter: blur(4px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  padding: 10px 5px;
  border-radius: 5px;

  .video-call-operation {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    margin-top: 10px;
  }

  .max-window {
    width: 100%;
    border-radius: 10px;
    transform: scaleX(-1);
  }

  .min-window {
    position: absolute;
    width: 30%;
    border-radius: 5px;
    top: 5px;
    right: 5px;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
    z-index: 100;
    transform: scaleX(-1);
    cursor: pointer;
    background-color: #fff;
  }
}

.operation-button {
  width: 32px;
  height: 32px;
  border-radius: 40px;
  cursor: pointer;
  color: #ffffff;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
