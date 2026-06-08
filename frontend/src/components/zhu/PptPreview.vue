<template>
  <!--
    PptPreview.vue - 右侧预览区的完整 PPT 幻灯片展示组件
    职责：在右侧预览区渲染完整的 PPT 页面，支持翻页、缩略图导航、图文布局
    数据来源：由 zhu.vue 通过 previewState.type === 'ppt' 注入
  -->
  <div class="ppt-preview">
    <!-- 顶部信息栏 -->
    <div class="preview-topbar">
      <div class="ppt-title-row">
        <!-- PPT 图标 -->
        <svg class="ppt-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <path d="M8 21h8M12 17v4" />
          <path d="M6 8h2M6 11h5" stroke-linecap="round" />
        </svg>
        <h3 class="preview-title">{{ title }}</h3>
      </div>
      <!-- 元信息行 -->
      <div v-if="agentRole || createdAt" class="meta-row">
        <span v-if="agentRole" class="meta-tag">{{ agentRole }}</span>
        <span v-if="createdAt" class="meta-time">{{ formatTime(createdAt) }}</span>
      </div>
      <!-- 操作按钮行：导出 PPT -->
      <div class="topbar-actions">
        <button
          class="export-btn"
          type="button"
          :disabled="isExporting"
          :title="isExporting ? '导出中...' : '导出为 PPT 文件'"
          @click="handleExport"
        >
          <svg v-if="!isExporting" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span v-if="isExporting" class="export-spinner"></span>
          {{ isExporting ? '导出中...' : '导出 PPT' }}
        </button>
      </div>
    </div>

    <!-- 无幻灯片数据兜底 -->
    <div v-if="!slides || slides.length === 0" class="empty-state">
      <p>暂无可预览页面</p>
    </div>

    <!-- PPT 内容区 -->
    <div v-else class="ppt-content">
      <!-- 左侧：当前页主区域 -->
      <div class="slide-main">
        <!-- 当前页大图 -->
        <div class="slide-cover-wrap">
          <img
            :src="currentSlide.imageUrl"
            :alt="currentSlide.title"
            class="slide-cover-img"
            @error="handleImgError"
          />
          <!-- 图片上的标题遮罩 -->
          <div class="slide-title-overlay">
            <span class="slide-page-num">第 {{ currentIndex + 1 }} / {{ slides.length }} 页</span>
            <span class="slide-title-text">{{ currentSlide.title }}</span>
          </div>

          <!-- 图片上的要点遮罩 -->
          <div v-if="currentSlide.bullets.length > 0" class="slide-bullets-overlay">
            <ul class="slide-bullets">
              <li
                v-for="(bullet, idx) in currentSlide.bullets"
                :key="idx"
                class="slide-bullet"
              >
                {{ bullet }}
              </li>
            </ul>
          </div>

          <div v-else class="slide-no-bullets-overlay">
            <span>本页无要点内容</span>
          </div>
        </div>
      </div>

      <!-- 右侧：缩略图导航栏 -->
      <div class="slide-nav">
        <div
          v-for="(slide, idx) in slides"
          :key="slide.id"
          class="thumb-item"
          :class="{ active: idx === currentIndex }"
          @click="currentIndex = idx"
          :title="slide.title"
        >
          <img
            :src="slide.imageUrl"
            :alt="slide.title"
            class="thumb-img"
            @error="(e) => { (e.target as HTMLImageElement).src = '/PPT/动漫.jpg' }"
          />
          <span class="thumb-label">{{ idx + 1 }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { PptSlideViewModel } from '../../types/agenthub'
import { exportPpt } from '../../utils/ppt-export'

/** 从 previewState 注入的 props */
const props = defineProps<{
  title?: string
  agentRole?: string
  createdAt?: string
  slides: PptSlideViewModel[]
}>()

/** 当前页索引（从 0 开始） */
const currentIndex = ref(0)

/** 导出按钮加载状态，防止重复点击 */
const isExporting = ref(false)

/**
 * 点击"导出 PPT"按钮，将当前 PPT 数据生成为 .pptx 文件并下载
 * 捕获导出异常，避免打断用户操作
 */
async function handleExport() {
  if (isExporting.value || !props.slides?.length) return
  isExporting.value = true
  try {
    // 从 props 构建 PptPreviewModel，与渲染用的是同一份数据
    const model = {
      title: props.title ?? '汇报 PPT',
      agentRole: props.agentRole ?? '',
      createdAt: props.createdAt ?? '',
      slides: props.slides,
    }
    // 文件名取标题，去掉空格和特殊字符，最多 30 字符
    const fileName = (props.title ?? '汇报PPT')
      .replace(/[^\w\u4e00-\u9fa5]/g, '')
      .slice(0, 30)
    await exportPpt(model, fileName)
  } catch (err) {
    console.error('[ppt-export] 导出失败:', err)
    alert('导出失败，请重试')
  } finally {
    isExporting.value = false
  }
}

/** 当前页数据 */
const currentSlide = computed(() => {
  if (!props.slides || props.slides.length === 0) {
    return { imageUrl: '/PPT/动漫.jpg', title: 'PPT 预览', bullets: [] }
  }
  return props.slides[currentIndex.value] ?? props.slides[0]
})

/**
 * 将 ISO 时间字符串格式化为"月日 时:分"
 * 复用了 zhu.vue 中的 formatTime 逻辑
 */
const formatTime = (iso: string) => {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

/** 当前页封面图加载失败兜底到默认图 */
const handleImgError = (e: Event) => {
  const img = e.target as HTMLImageElement
  img.src = '/PPT/动漫.jpg'
}
</script>

<style scoped lang="less">
/* ==================== 根容器 ==================== */
.ppt-preview {
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

/* ==================== 顶部信息栏 ==================== */
.preview-topbar {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ppt-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ppt-icon-sm {
  width: 18px;
  height: 18px;
  color: rgba(59, 130, 246, 0.75);
  flex-shrink: 0;
}

.preview-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.meta-tag {
  font-size: 11px;
  font-weight: 600;
  color: rgba(59, 130, 246, 0.85);
  background: rgba(59, 130, 246, 0.08);
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(59, 130, 246, 0.18);
}

.meta-time {
  font-size: 11px;
  color: rgba(100, 116, 139, 0.7);
}

/* ==================== 空状态 ==================== */
.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(100, 116, 139, 0.5);
  font-size: 13px;
}

/* ==================== PPT 内容区 ==================== */
.ppt-content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

/* ==================== 主幻灯片展示区 ==================== */
.slide-main {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
}

.slide-cover-wrap {
  position: relative;
  width: 100%;
  height: 80%;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
  border: 1px solid rgba(59, 130, 246, 0.12);
}

.slide-cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.slide-title-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  padding: 12px 12px 18px;
  background: linear-gradient(to bottom, rgba(0, 0, 0, 0.68) 0%, transparent 100%);
  display: flex;
  flex-direction: column;
  gap: 2px;
  z-index: 2;
}

.slide-page-num {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.7);
}

.slide-title-text {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  display: -webkit-box;
  line-clamp: 1;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ==================== 图片上的要点遮罩 ==================== */
.slide-bullets-overlay {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 14px;
  z-index: 2;
  padding: 12px 14px;
  border-radius: 12px;
  max-height: calc(100% - 96px);
  overflow: hidden;
}

.slide-bullets {
  max-height: 100%;
  overflow-y: auto;
  padding-right: 4px;
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
}

.slide-bullet {
  font-size: 30px;
  color: rgba(255, 255, 255, 0.94);
  line-height: 1.65;
  padding-left: 14px;
  position: relative;
  letter-spacing: 5px; 
  font-weight: 600;
  font-family: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);

  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 8px;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.9);
  }
}

.slide-no-bullets-overlay {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 14px;
  z-index: 2;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.78);
  font-size: 12px;
  text-align: center;
}

/* ==================== 缩略图导航栏 ==================== */
.slide-nav {
  flex-shrink: 0;
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 2px;
  scrollbar-width: thin;
  scrollbar-color: rgba(59, 130, 246, 0.2) transparent;

  &::-webkit-scrollbar {
    height: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(59, 130, 246, 0.2);
    border-radius: 999px;
  }
}

.thumb-item {
  flex-shrink: 0;
  width: 52px;
  height: 52px;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid transparent;
  cursor: pointer;
  position: relative;
  transition: border-color 0.15s ease, transform 0.15s ease;
  background: rgba(241, 245, 249, 0.8);

  &:hover {
    border-color: rgba(59, 130, 246, 0.35);
    transform: translateY(-1px);
  }

  &.active {
    border-color: rgba(59, 130, 246, 0.7);
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
  }
}

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumb-label {
  position: absolute;
  bottom: 2px;
  right: 3px;
  font-size: 9px;
  font-weight: 700;
  color: #fff;
  background: rgba(0, 0, 0, 0.45);
  padding: 1px 4px;
  border-radius: 4px;
  line-height: 1.3;
}

/* ==================== 导出按钮 ==================== */
.topbar-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}

.export-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 7px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.28);
  color: rgba(59, 130, 246, 0.9);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.18s ease;
  white-space: nowrap;

  &:hover:not(:disabled) {
    background: rgba(59, 130, 246, 0.18);
    border-color: rgba(59, 130, 246, 0.45);
    color: rgba(59, 130, 246, 1);
  }

  &:active:not(:disabled) {
    transform: scale(0.96);
  }

  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
}

.export-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(59, 130, 246, 0.25);
  border-top-color: rgba(59, 130, 246, 0.8);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
