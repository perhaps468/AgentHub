<template>
  <div class="welcome-container">
    <div class="welcome-content">
      <!-- 欢迎图标 -->
      <div class="welcome-icon">👋</div>

      <!-- 主标题 -->
      <h1 class="welcome-title">欢迎使用 AgentHub,很高兴见到你！</h1>


      <!-- 项目介绍区域 -->
      <div class="project-intro">
        <p>AgentHub 是一个智能协作平台，帮助您与 AI Agent 进行高效对话和任务协作。</p>
      </div>

      <!-- 功能特点展示 -->
      <div class="features">
        <div class="feature-item">
          <span class="feature-icon">💬</span>
          <span>智能对话</span>
        </div>
        <div class="feature-item">
          <span class="feature-icon">🤖</span>
          <span>Agent 协作</span>
        </div>
        <div class="feature-item">
          <span class="feature-icon">📁</span>
          <span>文件管理</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 欢迎组件 - 登录后显示的引导页面
 * 当用户点击"开始对话"或选择会话时，通过 emit 事件通知父组件切换视图
 */
defineEmits<{
  (e: 'enter-chat'): void
}>()

/**
 * 处理进入聊天按钮点击事件
 * 向父组件 emit enter-chat 事件，触发视图切换
 */
const handleEnterChat = () => {
  // 通过 emit 通知父组件，用户准备进入聊天界面
  // 父组件收到事件后会设置 showWelcome = false，显示 ChatWorkspace
}
</script>

<style scoped>
/* 容器样式 - 居中显示 */
.welcome-container {
  height: 100%;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

/* 内容区域样式 */
.welcome-content {
  text-align: center;
  max-width: 600px;
}

/* 欢迎图标样式 */
.welcome-icon {
  font-size: 64px;
  margin-bottom: 50px;
}

/* 主标题样式 - 品牌蓝色 */
.welcome-title {
  font-size: 32px;
  font-weight: 600;
  color: #0d0d0d;
  margin: 0 0px 10px 50px;
}


/* 项目介绍区域样式 - 浅蓝色背景 */
.project-intro {
  width:720px ;
  border-radius: 16px;
  padding: 2px;
  margin-bottom: 20px;
  font-size: 20px;
}



/* 项目介绍内容 */
.project-intro p {
  color: #4b5563;
  line-height: 2;
  margin: 0;
}

/* 功能特点区域 - 横向排列 */
.features {
  display: flex;
  gap: 24px;
  justify-content: center;
  margin-bottom: 40px;
  flex-wrap: wrap;
}

/* 单个功能项样式 */
.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
}

/* 功能图标 */
.feature-icon {
  font-size: 24px;
}
</style>
