<template>
  <div class="file-upload">
    <div class="upload-area" 
         :class="{ 'drag-over': isDragOver }"
         @drop="handleDrop"
         @dragover="handleDragOver"
         @dragleave="handleDragLeave">
      
      <input 
        type="file" 
        ref="fileInput"
        :multiple="multiple"
        :accept="accept"
        @change="handleFileSelect"
        style="display: none"
      />
      
      <div class="upload-content" @click="$refs.fileInput.click()">
        <div class="upload-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
        </div>
        <p class="upload-text">点击或拖拽文件到此处上传</p>
        <p class="upload-hint" v-if="accept">支持格式: {{ accept }}</p>
      </div>
    </div>

    <div class="file-list" v-if="files.length > 0">
      <div v-for="(file, index) in files" :key="index" class="file-item">
        <div class="file-info">
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">{{ formatSize(file.size) }}</span>
        </div>
        
        <div class="file-progress" v-if="file.progress !== undefined">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: file.progress + '%' }"></div>
          </div>
          <span class="progress-text">{{ file.progress }}%</span>
        </div>
        
        <div class="file-actions">
          <button 
            v-if="file.progress > 0 && file.progress < 100 && props.resumable" 
            @click="resumeUpload(index)" 
            class="resume-btn"
          >
            继续上传
          </button>
          <button @click="removeFile(index)" class="remove-btn">删除</button>
        </div>
      </div>
    </div>

    <div class="upload-actions" v-if="files.length > 0">
      <button @click="uploadFiles" :disabled="uploading" class="upload-btn">
        {{ uploading ? '上传中...' : '开始上传' }}
      </button>
      <button @click="clearFiles" class="clear-btn">清空</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Http from '../utils/request'

const props = defineProps({
  multiple: {
    type: Boolean,
    default: false
  },
  accept: {
    type: String,
    default: ''
  },
  uploadUrl: {
    type: String,
    required: true
  },
  // 是否启用断点续传
  resumable: {
    type: Boolean,
    default: false
  },
  // 分片大小（字节），默认 2MB
  chunkSize: {
    type: Number,
    default: 2 * 1024 * 1024
  },
  // 分片上传接口（如果与 uploadUrl 不同）
  chunkUploadUrl: {
    type: String,
    default: ''
  },
  // 合并分片接口
  mergeUrl: {
    type: String,
    default: ''
  },
  // 检查上传进度接口
  checkProgressUrl: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['upload-success', 'upload-error', 'progress'])

const fileInput = ref(null)
const files = ref([])
const uploading = ref(false)
const isDragOver = ref(false)

// 断点续传相关
const uploadTasks = ref(new Map()) // 存储上传任务 {fileId: {fileObj, chunks, uploadedChunks, uploadId}}

const handleFileSelect = (event) => {
  const selectedFiles = Array.from(event.target.files)
  addFiles(selectedFiles)
}

const handleDrop = (event) => {
  event.preventDefault()
  isDragOver.value = false
  
  const droppedFiles = Array.from(event.dataTransfer.files)
  addFiles(droppedFiles)
}

const handleDragOver = (event) => {
  event.preventDefault()
  isDragOver.value = true
}

const handleDragLeave = (event) => {
  event.preventDefault()
  isDragOver.value = false
}

// 生成文件唯一标识（基于文件名、大小、修改时间）
const generateFileId = (file) => {
  return `${file.name}_${file.size}_${file.lastModified}`
}

// 从 localStorage 恢复上传进度
const restoreUploadProgress = (fileId, fileObj) => {
  const key = `upload_progress_${fileId}`
  const saved = localStorage.getItem(key)
  if (saved) {
    try {
      const progress = JSON.parse(saved)
      fileObj.progress = progress.progress || 0
      fileObj.uploadId = progress.uploadId
      fileObj.uploadedChunks = new Set(progress.uploadedChunks || [])
      return progress
    } catch (e) {
      console.error('恢复上传进度失败:', e)
    }
  }
  return null
}

// 保存上传进度到 localStorage
const saveUploadProgress = (fileId, progress, uploadId, uploadedChunks) => {
  const key = `upload_progress_${fileId}`
  const data = {
    progress,
    uploadId,
    uploadedChunks: Array.from(uploadedChunks)
  }
  localStorage.setItem(key, JSON.stringify(data))
}

// 清除上传进度
const clearUploadProgress = (fileId) => {
  const key = `upload_progress_${fileId}`
  localStorage.removeItem(key)
}

const addFiles = (newFiles) => {
  if (!props.multiple) {
    files.value = newFiles.map(file => {
      const fileId = generateFileId(file)
      const fileObj = {
        file,
        name: file.name,
        size: file.size,
        progress: 0,
        fileId,
        uploadId: null,
        uploadedChunks: new Set()
      }
      
      // 如果启用断点续传，尝试恢复进度
      if (props.resumable) {
        restoreUploadProgress(fileId, fileObj)
      }
      
      return fileObj
    })
  } else {
    const fileObjects = newFiles.map(file => {
      const fileId = generateFileId(file)
      const fileObj = {
        file,
        name: file.name,
        size: file.size,
        progress: 0,
        fileId,
        uploadId: null,
        uploadedChunks: new Set()
      }
      
      if (props.resumable) {
        restoreUploadProgress(fileId, fileObj)
      }
      
      return fileObj
    })
    files.value.push(...fileObjects)
  }
}

const removeFile = (index) => {
  const fileObj = files.value[index]
  // 如果启用断点续传，清除上传进度
  if (props.resumable && fileObj.fileId) {
    clearUploadProgress(fileObj.fileId)
  }
  files.value.splice(index, 1)
}

// 继续上传（断点续传）
const resumeUpload = async (index) => {
  const fileObj = files.value[index]
  if (!fileObj || uploading.value) return
  
  uploading.value = true
  try {
    await uploadSingleFile(fileObj)
  } catch (error) {
    emit('upload-error', error)
  } finally {
    uploading.value = false
  }
}

const clearFiles = () => {
  files.value = []
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const uploadFiles = async () => {
  if (files.value.length === 0) return
  
  uploading.value = true
  
  try {
    if (!props.multiple) {
      await uploadSingleFile(files.value[0])
    } else {
      await uploadMultipleFiles()
    }
  } catch (error) {
    emit('upload-error', error)
  } finally {
    uploading.value = false
  }
}

// 检查上传进度（服务器端）
const checkUploadProgress = async (fileId, uploadId) => {
  if (!props.checkProgressUrl || !uploadId) {
    return null
  }
  
  try {
    const response = await Http.post(props.checkProgressUrl, {
      fileId,
      uploadId
    })
    if (response.code === 200 && response.data) {
      return response.data.uploadedChunks || []
    }
  } catch (error) {
    console.warn('检查上传进度失败:', error)
  }
  return null
}

// 上传单个分片
const uploadChunk = async (fileObj, chunkIndex, chunk, uploadId) => {
  const chunkUrl = props.chunkUploadUrl || props.uploadUrl
  const formData = new FormData()
  formData.append('chunk', chunk)
  formData.append('chunkIndex', chunkIndex)
  formData.append('totalChunks', Math.ceil(fileObj.file.size / props.chunkSize))
  formData.append('fileName', fileObj.file.name)
  formData.append('fileSize', fileObj.file.size)
  if (uploadId) {
    formData.append('uploadId', uploadId)
  }
  
  const response = await Http.upload(chunkUrl, formData, false)
  
  if (response.code === 200) {
    // 返回 uploadId（首次上传时服务器返回）
    return response.data?.uploadId || uploadId
  } else {
    throw new Error(response.message || `分片 ${chunkIndex} 上传失败`)
  }
}

// 合并分片
const mergeChunks = async (fileObj, uploadId) => {
  if (!props.mergeUrl) {
    throw new Error('未配置合并接口')
  }
  
  const response = await Http.post(props.mergeUrl, {
    uploadId,
    fileName: fileObj.file.name,
    fileSize: fileObj.file.size,
    totalChunks: Math.ceil(fileObj.file.size / props.chunkSize)
  })
  
  if (response.code === 200) {
    return response.data
  } else {
    throw new Error(response.message || '合并分片失败')
  }
}

// 断点续传上传
const uploadSingleFileResumable = async (fileObj) => {
  const fileId = fileObj.fileId
  const file = fileObj.file
  const chunkSize = props.chunkSize
  const totalChunks = Math.ceil(file.size / chunkSize)
  
  let uploadId = fileObj.uploadId
  
  // 如果没有 uploadId，先初始化上传（获取 uploadId）
  if (!uploadId) {
    try {
      const initResponse = await Http.post(props.uploadUrl + '/init', {
        fileName: file.name,
        fileSize: file.size,
        totalChunks
      })
      if (initResponse.code === 200) {
        uploadId = initResponse.data.uploadId
        fileObj.uploadId = uploadId
      }
    } catch (error) {
      console.warn('初始化上传失败，尝试直接上传:', error)
    }
  }
  
  // 检查服务器端已上传的分片
  if (uploadId && props.checkProgressUrl) {
    const serverChunks = await checkUploadProgress(fileId, uploadId)
    if (serverChunks && serverChunks.length > 0) {
      serverChunks.forEach(index => fileObj.uploadedChunks.add(index))
    }
  }
  
  // 上传未完成的分片
  const chunksToUpload = []
  for (let i = 0; i < totalChunks; i++) {
    if (!fileObj.uploadedChunks.has(i)) {
      chunksToUpload.push(i)
    }
  }
  
  // 并发上传分片（限制并发数）
  const concurrency = 3 // 最多同时上传3个分片
  let currentIndex = 0
  
  const uploadNext = async () => {
    while (currentIndex < chunksToUpload.length) {
      const chunkIndex = chunksToUpload[currentIndex++]
      const start = chunkIndex * chunkSize
      const end = Math.min(start + chunkSize, file.size)
      const chunk = file.slice(start, end)
      
      try {
        uploadId = await uploadChunk(fileObj, chunkIndex, chunk, uploadId)
        fileObj.uploadId = uploadId
        fileObj.uploadedChunks.add(chunkIndex)
        
        // 更新进度
        const uploadedSize = fileObj.uploadedChunks.size * chunkSize
        fileObj.progress = Math.min(
          Math.round((uploadedSize / file.size) * 100),
          99 // 合并前最多99%
        )
        
        // 保存进度
        saveUploadProgress(
          fileId,
          fileObj.progress,
          uploadId,
          fileObj.uploadedChunks
        )
        
        emit('progress', fileObj.progress, fileObj)
        
        // 继续上传下一个
        await uploadNext()
      } catch (error) {
        console.error(`分片 ${chunkIndex} 上传失败:`, error)
        throw error
      }
    }
  }
  
  // 启动并发上传
  const uploadPromises = []
  for (let i = 0; i < Math.min(concurrency, chunksToUpload.length); i++) {
    uploadPromises.push(uploadNext())
  }
  await Promise.all(uploadPromises)
  
  // 所有分片上传完成，合并
  if (uploadId) {
    fileObj.progress = 100
    saveUploadProgress(fileId, 100, uploadId, fileObj.uploadedChunks)
    emit('progress', 100, fileObj)
    
    const result = await mergeChunks(fileObj, uploadId)
    
    // 清除本地进度
    clearUploadProgress(fileId)
    
    emit('upload-success', result, fileObj)
  } else {
    throw new Error('上传ID不存在，无法合并')
  }
}

// 普通上传（不分片）
const uploadSingleFileNormal = async (fileObj) => {
  const formData = new FormData()
  formData.append('file', fileObj.file)
  
  const onProgress = (progressEvent) => {
    const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
    fileObj.progress = progress
    emit('progress', progress, fileObj)
  }
  
  const response = await Http.upload(props.uploadUrl, formData, true, onProgress)
  
  if (response.code === 200) {
    emit('upload-success', response.data, fileObj)
  } else {
    throw new Error(response.message || '上传失败')
  }
}

const uploadSingleFile = async (fileObj) => {
  if (props.resumable && fileObj.file.size > props.chunkSize) {
    // 大文件使用断点续传
    await uploadSingleFileResumable(fileObj)
  } else {
    // 小文件或未启用断点续传，使用普通上传
    await uploadSingleFileNormal(fileObj)
  }
}

const uploadMultipleFiles = async () => {
  const formData = new FormData()
  
  files.value.forEach((fileObj, index) => {
    formData.append(`files[${index}]`, fileObj.file)
  })
  
  const onProgress = (progressEvent) => {
    const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
    files.value.forEach(fileObj => {
      fileObj.progress = progress
    })
    emit('progress', progress, files.value)
  }
  
  const response = await Http.upload(props.uploadUrl, formData, true, onProgress)
  
  if (response.code === 200) {
    emit('upload-success', response.data, files.value)
  } else {
    throw new Error(response.message || '上传失败')
  }
}

const formatSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style scoped>
.file-upload {
  max-width: 500px;
  margin: 0 auto;
}

.upload-area {
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background-color: #f9fafb;
}

.upload-area:hover,
.upload-area.drag-over {
  border-color: #3b82f6;
  background-color: #eff6ff;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.upload-icon {
  color: #6b7280;
}

.upload-text {
  color: #374151;
  font-weight: 500;
  margin: 0;
}

.upload-hint {
  color: #6b7280;
  font-size: 14px;
  margin: 0;
}

.file-list {
  margin-top: 20px;
}

.file-item {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
}

.file-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.file-name {
  font-weight: 500;
  color: #374151;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  color: #6b7280;
  font-size: 14px;
  margin-left: 10px;
}

.file-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background-color: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: #3b82f6;
  transition: width 0.3s ease;
}

.progress-text {
  color: #6b7280;
  font-size: 12px;
  min-width: 40px;
}

.file-actions {
  display: flex;
  justify-content: flex-end;
}

.remove-btn {
  background: #ef4444;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.remove-btn:hover {
  background: #dc2626;
}

.upload-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  justify-content: center;
}

.upload-btn,
.clear-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}

.upload-btn {
  background: #3b82f6;
  color: white;
}

.upload-btn:hover:not(:disabled) {
  background: #2563eb;
}

.upload-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.clear-btn {
  background: #6b7280;
  color: white;
}

.clear-btn:hover {
  background: #4b5563;
}

.resume-btn {
  background: #10b981;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  margin-right: 8px;
}

.resume-btn:hover {
  background: #059669;
}
</style>
