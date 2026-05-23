<template>
  <template v-if="visible">
    <draggable-window v-if="!isReady" :rounded="20" :resize="false" >
      <div class="file-answer">
        <div class="answer-content-wrapper">
          <avatar :info="props.targetInfo" class="mr-[10px]" />
          <div class="answer-content">
            <div class="flex">
              <div class="answer-content-name">{{ props.targetInfo.name }}</div>
              <div class="answer-content-label flex items-center">
                {{ props.isSend ? '等待对方接收' : `请求发送文件` }}
                <loading_dots />
              </div>
            </div>
            <div class="flex text-[10px]">
              <!-- <div class="answer-content-label mr-[5px]" style="font-size: 12px">
                {{ formatSize(props.file.size) }}
              </div> -->
              <div class="answer-content-label ellipsis" style="font-size: 12px">
                {{ props.file.name }}
              </div>
            </div>
          </div>
        </div>
        <div class="answer-operation">
          <div
            v-if="!props.isSend"
            class="operation-button bg-[rgb(var(--primary-color))]"
            style="box-shadow: 0 0 15px rgba(var(--primary-color))"
            @click="onAccept"
          >
            <svg t="1760184466348" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="6203" width="48" height="48"><path d="M974.631304 356.675652a48.872297 48.872297 0 0 0-48.872297 48.872297v442.665308a76.76277 76.76277 0 0 1-76.76277 76.76277H175.530868a76.76277 76.76277 0 0 1-76.762771-76.76277v-442.665308a48.872297 48.872297 0 1 0-97.744593 0v442.665308A175.786743 175.786743 0 0 0 175.530868 1024h672.697741A175.530868 175.530868 0 0 0 1023.503601 848.213257v-442.665308a48.872297 48.872297 0 0 0-48.872297-48.872297z" p-id="6204" fill="#ffffff"></path><path d="M386.372609 749.189283h245.89674a51.17518 51.17518 0 0 1 51.17518 41.707772 48.872297 48.872297 0 0 1-48.360545 55.780946h-244.873236a51.17518 51.17518 0 0 1-51.17518-41.451896 49.128173 49.128173 0 0 1 47.337041-56.036822zM527.616106 599.501882l-204.70072-234.382325a12.793795 12.793795 0 0 1 9.723284-21.2377h110.538389a13.049671 13.049671 0 0 0 12.793795-13.049671 999.963018 999.963018 0 0 0-7.420401-122.30868A274.043089 274.043089 0 0 0 349.52648 23.52523a12.793795 12.793795 0 0 1 10.490912-23.028831c215.703384 35.822626 261.249294 277.1136 268.925571 332.63867a12.537919 12.537919 0 0 0 12.537919 11.002664H742.040111a12.793795 12.793795 0 0 1 9.723284 21.2377l-204.70072 234.382324a12.793795 12.793795 0 0 1-19.446569-0.255875z" p-id="6205" fill="#ffffff"></path></svg>
            <i class="iconfont icon-yunxu" style="font-size: 20px" />
          </div>
          <div
            class="operation-button bg-[#FFF]"
            style="box-shadow: 0 0 15px #fff"
            @click="onCancel"
          > 
            <svg t="1759136517771" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="2427" width="18" height="18"><path d="M494.6 75.8C258 75.8 66 267.7 66 504.3s192 428.6 428.6 428.6 428.6-192 428.6-428.6-192-428.5-428.6-428.5z m-35.8 160.7c0-19.6 16.1-35.7 35.7-35.7s35.7 16.1 35.7 35.7v267.8c0 19.6-16.1 35.7-35.7 35.7s-35.7-16.1-35.7-35.7V236.5z m21.8 535.3c-137.1-7-248.9-120.7-253.7-257.8-3.2-90 38-170.4 103.6-221.2 6.4-5 13.7-7.3 20.9-7.3 18.4 0 36.1 15 36.1 36.1 0 10.7-4.8 21.1-13.2 27.7-46.2 36.1-76.1 92.1-76.1 155.2 0 116.1 100.9 208.7 219.6 195.2 89.5-10.4 162-83 172-172.5 8-72.1-23-137.5-74.6-177.8-8.6-6.6-13.4-17-13.4-27.7 0-29.3 33.7-46.8 57-28.7 63.2 48.9 103.7 125.5 103.7 211.6-0.1 152.2-127.8 275.1-281.9 267.2z" fill="#d81e06" p-id="2428"></path></svg>
            <i class="iconfont icon-quxiao" style="font-size: 18px; color: #6c6c6c" />
          </div>
        </div>
      </div>
    </draggable-window>
    <draggable-window v-if="isReady" :rounded="10" :resize="false">
      <div class="file-receive">
        <circle-progress :progress="progress" :size="60" :strokeWidth="6" />
        <div class="file-receive-label flex items-center">
          {{ progress >= 100 ? '传输完成' : '传输中' }}
          <loading_dots v-if="progress < 100" />
        </div>
        <div class="flex gap-[5px]">
          <div
            v-if="!isSend && progress >= 100"
            class="operation-button bg-[#FFF]"
            style="box-shadow: 0 0 15px #fff"
            @click="onDownload"
          >
            <i class="iconfont icon-xiazai" style="font-size: 20px; color: #6c6c6c" />
          </div>
          <div
            class="operation-button bg-[#FFF]"
            style="box-shadow: 0 0 15px #fff"
            @click="onCancel"
          >
            <i class="iconfont icon-quxiao" style="font-size: 18px; color: #6c6c6c" />
            <svg t="1759136517771" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="2427" width="18" height="18"><path d="M494.6 75.8C258 75.8 66 267.7 66 504.3s192 428.6 428.6 428.6 428.6-192 428.6-428.6-192-428.5-428.6-428.5z m-35.8 160.7c0-19.6 16.1-35.7 35.7-35.7s35.7 16.1 35.7 35.7v267.8c0 19.6-16.1 35.7-35.7 35.7s-35.7-16.1-35.7-35.7V236.5z m21.8 535.3c-137.1-7-248.9-120.7-253.7-257.8-3.2-90 38-170.4 103.6-221.2 6.4-5 13.7-7.3 20.9-7.3 18.4 0 36.1 15 36.1 36.1 0 10.7-4.8 21.1-13.2 27.7-46.2 36.1-76.1 92.1-76.1 155.2 0 116.1 100.9 208.7 219.6 195.2 89.5-10.4 162-83 172-172.5 8-72.1-23-137.5-74.6-177.8-8.6-6.6-13.4-17-13.4-27.7 0-29.3 33.7-46.8 57-28.7 63.2 48.9 103.7 125.5 103.7 211.6-0.1 152.2-127.8 275.1-281.9 267.2z" fill="#d81e06" p-id="2428"></path></svg>

          </div>
        </div>
      </div>
    </draggable-window>
  </template>
</template>

<script setup>
import {offer,candidate,answer,cancel,accept}from '../../api/file'
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import EventBus from '../../utils/EventBus'
import DraggableWindow from '../shape/Draggable-window.vue'
import Avatar from '../../veiws/img/avatar.vue'
import loading_dots from '../loading-dots.vue'
import CircleProgress from '../shape/circle-progress-wrapper.vue'

import { useToast } from '../useToast'

const props = defineProps({ targetInfo: Object, isSend: Boolean, file: Object })

const visible = defineModel('visible')
const showToast = useToast()

const pc = ref()
const dataChannel = ref(null)
const isReady = ref(false)
const progress = ref(0)
const receivedChunks = ref([])
const receivedSize = ref(0)
const chunkMap = ref(new Map()) // 用于存储带序号的分片

// 发送方：分片状态跟踪
const sentChunks = ref(new Map()) // 已发送的分片 {index: {data, timestamp, retries}}
const acknowledgedChunks = ref(new Set()) // 已确认的分片索引
const maxRetries = 3 // 最大重试次数
const ackTimeout = 5000 // ACK超时时间（毫秒）
const pendingAcks = ref(new Map()) // 等待确认的分片 {index: timeoutId}

const handlerFileMsg = (msg) => {
  switch (msg.type) {
    case 'offer': {
      handleFileOfferMsg(msg)
      break
    }
    case 'answer': {
      showToast('对方回答~', true)
      handleFileAnswerMsg(msg)
      break
    }
    case 'candidate': {
      handleNewICECandidateMsg(msg)
      break
    }
    case 'cancel': {
      console.log(msg)
      showToast('对方已取消~', true)
      visible.value = false
      break
    }
    case 'accept': {
      console.log('收到');
      showToast('对方收到~', true)
        console.log(`收到文件传输信令: ${msg.type}`, msg);
      onOffer()
      break
    }
  }
}

onMounted(async () => {
  EventBus.on('on-receive-file', handlerFileMsg)
})

onUnmounted(async () => {
  EventBus.off('on-receive-file', handlerFileMsg)
})

const initRTCPeerConnection = () => {
  const iceServer = {
    iceServers: [
      {
        url: 'stun:stun.l.google.com:19302',
      },
      {
        url: 'turn:numb.viagenie.ca',
        username: 'webrtc@live.com',
        credential: 'muazkh',
      },
    ],
  }
  pc.value = new RTCPeerConnection(iceServer)
  // 设置 DataChannel 监听
  if (props.isSend) {
    //发送方主动创建名为'fileTransfer'的数据通道
    dataChannel.value = pc.value.createDataChannel('fileTransfer')
    setupDataChannel()
  } else {
    //接收方监听ondatachannel事件
    pc.value.ondatachannel = (event) => {
      dataChannel.value = event.channel
      setupDataChannel()
    }
  }
  //ICE候选时触发
  pc.value.onicecandidate = handleICECandidateEvent
  //ICE连接状态监控
  pc.value.oniceconnectionstatechange = handleICEConnectionStateChangeEvent
}

const setupDataChannel = () => {
  dataChannel.value.onopen = () => {
    if (props.isSend && props.file) {
      //发送文件
      sendFile(props.file)
    }
  }
  dataChannel.value.onclose = () => console.log('DataChannel closed')
  dataChannel.value.onmessage = (e) => {
    // 先检查是否是ACK消息
    if (typeof e.data === 'string') {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'ACK' && props.isSend) {
          // 发送方收到ACK确认
          handleAck(msg.chunkIndex)
          return
        }
      } catch (e) {
        // 不是JSON，继续处理
      }
    }
    // 处理文件分片数据
    handleDataChannelMessage(e)
  }
}

const handleICECandidateEvent = (event) => {
  if (event.candidate) {
    candidate({ userId: props.targetInfo.id, candidate: event.candidate })
  }
}

const handleICEConnectionStateChangeEvent = () => {
  // if (pc.value?.iceConnectionState === "disconnected") {}
}

watch(visible, () => {
  if (!visible.value) {
    isReady.value = false
    if (dataChannel.value) dataChannel.value.close()
    pc.value = null
    progress.value = 0
    receivedChunks.value = []
    chunkMap.value.clear()
    receivedSize.value = 0
    // 清理发送方状态
    sentChunks.value.clear()
    acknowledgedChunks.value.clear()
    // 清理所有等待的ACK超时定时器
    pendingAcks.value.forEach((timeoutId) => clearTimeout(timeoutId))
    pendingAcks.value.clear()
  }
})

const handleFileOfferMsg = async (data) => {
  const desc = new RTCSessionDescription(data.desc)
  await pc.value.setRemoteDescription(desc)
  await pc.value.setLocalDescription(await pc.value.createAnswer())
  await answer({ userId: props.targetInfo.id, desc: pc.value.localDescription })
}

const handleFileAnswerMsg = async (data) => {
  const desc = new RTCSessionDescription(data.desc)
  await pc.value.setRemoteDescription(desc).catch(reportError)
}

const handleNewICECandidateMsg = async (data) => {
  const candidate = new RTCIceCandidate(data.candidate)
  try {
    await pc.value.addIceCandidate(candidate)
  } catch (err) {
    console.log(err)
  }
}

const onAccept = async () => {
  isReady.value = true
  await nextTick(async () => {
    initRTCPeerConnection()
  })
 await accept({ userId: props.targetInfo.id })
}

const onCancel = () => {
  visible.value = false
  if (progress.value < 100) {
    cancel({ userId: props.targetInfo.id })
  }
}
// 发送方创建offer
const onOffer = async () => {
  isReady.value = true
  await nextTick(async () => {
    initRTCPeerConnection()
    const offer = await pc.value.createOffer()
    await pc.value.setLocalDescription(offer)
    await offer({ userId: props.targetInfo.id, desc: pc.value.localDescription })
  })
}
// 接收方处理offer
const handleDataChannelMessage = (e) => {
  const message = e.data
  
  // 检查是否是文本消息（ACK确认）
  if (typeof message === 'string') {
    try {
      const msg = JSON.parse(message)
      if (msg.type === 'ACK') {
        // 接收方收到ACK（这种情况不应该发生，ACK是接收方发送的）
        console.log('收到ACK确认:', msg.chunkIndex)
      } else if (msg.type === 'FILE_META') {
        // 文件元数据（可选，用于初始化）
        console.log('收到文件元数据:', msg)
      }
    } catch (e) {
      // 不是JSON，继续处理为二进制数据
    }
  }
  
  if (typeof message === 'object') {
    if (!receivedChunks.value) {
      console.error('No active file transfer, ignoring binary message.')
      return
    }
    if (message instanceof ArrayBuffer || message instanceof Uint8Array) {
      const buffer = message instanceof ArrayBuffer ? message : message.buffer
      
      // 检查消息类型：前1字节是消息类型
      const view = new DataView(buffer)
      const messageType = view.getUint8(0)
      
      if (messageType === 0) {
        // 类型0：文件分片数据
        // 格式：1字节类型 + 4字节序号 + 数据
        if (buffer.byteLength < 5) {
          console.error('分片数据格式错误：长度不足')
          return
        }
        
        const chunkIndex = view.getUint32(1, true) // 小端序读取序号
        const chunkData = buffer.slice(5) // 获取实际数据部分
        
        // 存储分片（带序号），如果已存在则跳过（去重）
        if (!chunkMap.value.has(chunkIndex)) {
          chunkMap.value.set(chunkIndex, chunkData)
          receivedSize.value += chunkData.byteLength
          
          // 发送ACK确认
          sendAck(chunkIndex)
        }
        
        // 更新进度（基于已接收的字节数）
        progress.value = Math.floor((receivedSize.value / props.file.size) * 100)
        
        // 检查是否所有分片都已接收
        const chunkSize = 16 * 1024
        const totalChunks = Math.ceil(props.file.size / chunkSize)
        if (chunkMap.value.size === totalChunks) {
          // 按序号排序并组装
          const sortedChunks = []
          for (let i = 0; i < totalChunks; i++) {
            const chunk = chunkMap.value.get(i)
            if (chunk) {
              sortedChunks.push(chunk)
            } else {
              console.error(`缺少分片 ${i}`)
              return
            }
          }
          receivedChunks.value = sortedChunks
          
          // 验证总大小是否匹配（允许1字节误差）
          const totalReceivedSize = sortedChunks.reduce((sum, chunk) => sum + chunk.byteLength, 0)
          if (Math.abs(totalReceivedSize - props.file.size) <= 1) {
            try {
              //下载
              onDownload()
            } catch (error) {
              console.error('Error finalizing file transfer', error)
            } finally {
              receivedSize.value = 0
              chunkMap.value.clear()
            }
          } else {
            console.error(`文件大小不匹配: 期望 ${props.file.size}, 实际 ${totalReceivedSize}`)
          }
        }
      }
    } else {
      console.error('Unknown binary message type', message)
    }
  }
}

// 发送ACK确认消息
const sendAck = (chunkIndex) => {
  if (dataChannel.value && dataChannel.value.readyState === 'open') {
    const ackMessage = JSON.stringify({
      type: 'ACK',
      chunkIndex: chunkIndex
    })
    try {
      dataChannel.value.send(ackMessage)
      console.log(`发送ACK确认: 分片 ${chunkIndex}`)
    } catch (error) {
      console.error('发送ACK失败:', error)
    }
  }
}

const onDownload = () => {
  if (receivedChunks.value && receivedChunks.value.length > 0) {
    //分片拼装
    const blob = new Blob(receivedChunks.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = props.file.name
    document.body.appendChild(a)
    a.click()
    URL.revokeObjectURL(url)
    a.remove()
  }
}

// 处理ACK确认消息
const handleAck = (chunkIndex) => {
  // 清除等待确认的定时器
  if (pendingAcks.value.has(chunkIndex)) {
    clearTimeout(pendingAcks.value.get(chunkIndex))
    pendingAcks.value.delete(chunkIndex)
  }
  
  // 标记为已确认
  acknowledgedChunks.value.add(chunkIndex)
  console.log(`分片 ${chunkIndex} 已确认`)
  
  // 更新进度（基于已确认的分片）
  const chunkSize = 16 * 1024
  const totalChunks = Math.ceil(props.file.size / chunkSize)
  const confirmedSize = acknowledgedChunks.value.size * chunkSize
  progress.value = Math.floor((confirmedSize / props.file.size) * 100)
}

// 重传分片
const retryChunk = (chunkIndex) => {
  const chunkInfo = sentChunks.value.get(chunkIndex)
  if (!chunkInfo) {
    console.error(`无法重传分片 ${chunkIndex}: 数据不存在`)
    return
  }
  
  chunkInfo.retries++
  if (chunkInfo.retries > maxRetries) {
    console.error(`分片 ${chunkIndex} 重传次数超过限制，传输失败`)
    return
  }
  
  console.log(`重传分片 ${chunkIndex} (第 ${chunkInfo.retries} 次重试)`)
  sendChunkWithIndex(chunkIndex, chunkInfo.data)
}

// 发送带序号的分片
const sendChunkWithIndex = (chunkIndex, chunkData) => {
  if (dataChannel.value && dataChannel.value.readyState === 'open') {
    try {
      // 格式：1字节类型(0=分片) + 4字节序号 + 数据
      const chunkWithIndex = new ArrayBuffer(5 + chunkData.byteLength)
      const view = new DataView(chunkWithIndex)
      const dataView = new Uint8Array(chunkWithIndex, 5)
      
      // 写入消息类型
      view.setUint8(0, 0) // 0表示文件分片
      // 写入序号（小端序）
      view.setUint32(1, chunkIndex, true)
      // 写入分片数据
      dataView.set(new Uint8Array(chunkData))
      
      dataChannel.value.send(chunkWithIndex)
      
      // 设置ACK超时检测
      const timeoutId = setTimeout(() => {
        if (!acknowledgedChunks.value.has(chunkIndex)) {
          console.warn(`分片 ${chunkIndex} ACK超时，准备重传`)
          retryChunk(chunkIndex)
        }
      }, ackTimeout)
      
      pendingAcks.value.set(chunkIndex, timeoutId)
      
      // 保存分片信息用于重传
      if (!sentChunks.value.has(chunkIndex)) {
        sentChunks.value.set(chunkIndex, {
          data: chunkData,
          timestamp: Date.now(),
          retries: 0
        })
      }
    } catch (e) {
      console.error(`发送分片 ${chunkIndex} 失败:`, e)
    }
  }
}

const sendFile = (file) => {
  return new Promise((resolve, reject) => {
    const chunkSize = 16 * 1024
    const totalChunks = Math.ceil(file.size / chunkSize)
    let currentChunk = 0
    let totalSent = 0
    let lastProgressUpdate = Date.now()
    
    // 重置状态
    sentChunks.value.clear()
    acknowledgedChunks.value.clear()
    pendingAcks.value.clear()
    
    //使用 FileReader API 来读取文件分片
    const fileReader = new FileReader()
    const sendNextChunk = () => {
      try {
        const start = currentChunk * chunkSize
        const end = Math.min(start + chunkSize, file.size)
        const chunk = file.slice(start, end)
        // 将分片读取为 ArrayBuffer 格式
        fileReader.readAsArrayBuffer(chunk)
      } catch (e) {
        reject(e)
      }
    }
    
    fileReader.onload = async () => {
      if (dataChannel.value && dataChannel.value.readyState === 'open') {
        try {
          const chunkData = fileReader.result
          
          // 发送带序号的分片
          sendChunkWithIndex(currentChunk, chunkData)
          
          totalSent += chunkData.byteLength
          //用来控制进度更新的频率
          const now = Date.now()
          if (now - lastProgressUpdate > 100) {
            progress.value = Math.floor((totalSent / file.size) * 100)
            lastProgressUpdate = now
          }
          
          currentChunk++
          if (currentChunk < totalChunks) {
            // 继续发送下一个分片（不等待ACK，使用流水线方式）
            setTimeout(() => sendNextChunk(), 0)
          } else {
            // 所有分片都已发送，等待所有ACK
            waitForAllAcks(totalChunks, resolve, reject)
          }
        } catch (e) {
          reject(e)
        }
      }
    }
    
    // 开始发送第一个分片
    sendNextChunk()
  })
}

// 等待所有分片确认
const waitForAllAcks = (totalChunks, resolve, reject) => {
  const checkInterval = setInterval(() => {
    if (acknowledgedChunks.value.size === totalChunks) {
      clearInterval(checkInterval)
      progress.value = 100
      console.log('所有分片已确认，传输完成')
      resolve()
    } else {
      // 检查是否有超时的分片需要重传
      const missingChunks = []
      for (let i = 0; i < totalChunks; i++) {
        if (!acknowledgedChunks.value.has(i)) {
          missingChunks.push(i)
        }
      }
      if (missingChunks.length > 0) {
        console.log(`等待确认的分片: ${missingChunks.join(', ')}`)
      }
    }
  }, 1000) // 每秒检查一次
  
  // 设置总超时（30秒）
  setTimeout(() => {
    clearInterval(checkInterval)
    const missingCount = totalChunks - acknowledgedChunks.value.size
    if (missingCount > 0) {
      reject(new Error(`传输超时：还有 ${missingCount} 个分片未确认`))
    }
  }, 30000)
}
</script>

<style lang="less" scoped>
.file-answer {
  width: 320px;
  background-color: rgba(48, 48, 75, 0.9);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  padding: 10px;
  border-radius: 20px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  border: 1px solid #ccc;
  .answer-content-wrapper {
    display: flex;
    align-items: center;
    flex: 1;

    .answer-content {
      .answer-content-name {
        color: #ffffff;
        font-weight: 600;
        margin-right: 5px;
      }

      .answer-content-label {
        color: rgba(255, 255, 255, 0.7);
        font-size: 14px;

        &.ellipsis {
          width: 100px;
          overflow: hidden;
          white-space: nowrap;
          text-overflow: ellipsis;
          word-break: break-word;
        }
      }
    }
  }

  .answer-operation {
    display: flex;
    align-items: center;
    gap: 15px;
  }
}

.file-receive {
  width: 90px;
  background-color: rgba(48, 48, 75, 0.9);
  backdrop-filter: blur(4px);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 5px;
  border-radius: 10px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  border: 1px solid #ccc;
  justify-content: center;

  .file-receive-label {
    color: rgba(255, 255, 255, 0.7);
    font-size: 14px;
    margin: 5px 0;
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
