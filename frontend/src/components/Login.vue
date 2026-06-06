<template>
  <div class="auth-container">
    <div class="glow-orb glow-orb-1"></div>
    <div class="glow-orb glow-orb-2"></div>
    <div class="glow-orb glow-orb-3"></div>
    <div class="grid-pattern"></div>

    <div class="auth-content">
      <div class="brand-section">
        <div class="brand-logo">
          <div class="logo-icon">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="20" cy="20" r="18" stroke="currentColor" stroke-width="2"/>
              <path d="M14 20h12M20 14v12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <span class="logo-text">AgentHub</span>
        </div>

        <h1 class="brand-title">
          <span class="title-line">智能协作</span>
          <span class="title-line gradient-text">全新体验</span>
        </h1>

        <p class="brand-desc">
          融合 AI 与协作的未来工作空间，让每一次对话都充满可能。
        </p>

        <div class="floating-cards">
          <div class="float-card float-card-1">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
              </svg>
            </div>
            <span>极速响应</span>
          </div>
          <div class="float-card float-card-2">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="9" cy="7" r="4"/>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
              </svg>
            </div>
            <span>团队协作</span>
          </div>
          <div class="float-card float-card-3">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
            </div>
            <span>安全加密</span>
          </div>
        </div>
      </div>

      <div class="form-section">
        <div class="glass-card">
          <div class="tab-header">
            <button
              class="tab-btn"
              :class="{ active: isLoginMode }"
              @click="isLoginMode = true"
            >
              <span class="tab-text">登录</span>
            </button>
            <button
              class="tab-btn"
              :class="{ active: !isLoginMode }"
              @click="isLoginMode = false"
            >
              <span class="tab-text">注册</span>
            </button>
          </div>

          <Transition name="form-slide" mode="out-in">
            <form v-if="isLoginMode" key="login" class="auth-form" @submit.prevent="loging">
              <h2 class="form-title">欢迎回来</h2>
              <p class="form-subtitle">请登录您的账户继续使用</p>

              <div class="input-group">
                <label class="input-label">账号</label>
                <div class="input-wrapper" :class="{ focused: loginFocused.userName }">
                  <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                    <circle cx="12" cy="7" r="4"/>
                  </svg>
                  <input
                    v-model="loginParam.userName"
                    type="text"
                    class="input-field"
                    placeholder="请输入账号"
                    @focus="loginFocused.userName = true"
                    @blur="loginFocused.userName = false"
                  />
                </div>
              </div>

              <div class="input-group">
                <label class="input-label">密码</label>
                <div class="input-wrapper" :class="{ focused: loginFocused.password }">
                  <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                  </svg>
                  <input
                    v-model="loginParam.password"
                    type="password"
                    class="input-field"
                    placeholder="请输入密码"
                    @focus="loginFocused.password = true"
                    @blur="loginFocused.password = false"
                  />
                </div>
              </div>

              <button class="submit-btn" type="submit">
                <span class="btn-text">登录</span>
                <svg class="btn-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M5 12h14M12 5l7 7-7 7"/>
                </svg>
              </button>

              <p class="form-footer">
                还没有账号？
                <button type="button" class="link-btn" @click="isLoginMode = false">
                  立即注册
                </button>
              </p>
            </form>

            <form v-else key="register" class="auth-form" @submit.prevent="registering">
              <h2 class="form-title">创建账户</h2>
              <p class="form-subtitle">开启您的智能协作之旅</p>

              <div class="input-group">
                <label class="input-label">用户名</label>
                <div class="input-wrapper" :class="{ focused: registerFocused.userName }">
                  <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                    <circle cx="12" cy="7" r="4"/>
                  </svg>
                  <input
                    v-model="registerParam.userName"
                    type="text"
                    class="input-field"
                    placeholder="请输入用户名"
                    @focus="registerFocused.userName = true"
                    @blur="registerFocused.userName = false"
                  />
                </div>
              </div>

              <div class="input-group">
                <label class="input-label">密码</label>
                <div class="input-wrapper" :class="{ focused: registerFocused.password }">
                  <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                  </svg>
                  <input
                    v-model="registerParam.password"
                    type="password"
                    class="input-field"
                    placeholder="请输入密码"
                    @focus="registerFocused.password = true"
                    @blur="registerFocused.password = false"
                  />
                </div>
              </div>

              <div class="input-group">
                <label class="input-label">确认密码</label>
                <div class="input-wrapper" :class="{ focused: registerFocused.confirmPassword }">
                  <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                  </svg>
                  <input
                    v-model="registerParam.confirmPassword"
                    type="password"
                    class="input-field"
                    placeholder="请再次输入密码"
                    @focus="registerFocused.confirmPassword = true"
                    @blur="registerFocused.confirmPassword = false"
                  />
                </div>
              </div>

              <button class="submit-btn" type="submit">
                <span class="btn-text">注册</span>
                <svg class="btn-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M5 12h14M12 5l7 7-7 7"/>
                </svg>
              </button>

              <p class="form-footer">
                已有账号？
                <button type="button" class="link-btn" @click="isLoginMode = true">
                  立即登录
                </button>
              </p>
            </form>
          </Transition>
        </div>
      </div>

      <div class="formFlow"></div>
      <div class="form-inner"></div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { login, register } from '../api/login'
import type { LoginResponse, RegisterResponese, UserInfo } from '../types/login'
import { useUserInfoStore } from '../store/module/useUserStore'

const userStore = useUserInfoStore()

const loginParam = ref({
  userName: '',
  password: '',
})

const registerParam = ref({
  userName: '',
  password: '',
  confirmPassword: '',
})

const isLoginMode = ref(true)

const loginFocused = reactive({
  userName: false,
  password: false,
})

const registerFocused = reactive({
  userName: false,
  password: false,
  confirmPassword: false,
})

const loging = async () => {
  try {
    localStorage.removeItem('x-token')
    localStorage.removeItem('user')
    localStorage.removeItem('session-store')
    userStore.clearUserInfo()
    const res = await login(loginParam.value) as LoginResponse
    if (res.code === 0 && res.data) {
      localStorage.setItem('x-token', res.data.token)
      userStore.setUserInfo(res.data as UserInfo)
      localStorage.setItem('user', JSON.stringify(res.data))
      ElMessage.success('登录成功')
      window.location.href = '/#/zhu'
      return
    }

    ElMessage.error(res.msg || '登录失败')
  } catch (error: any) {
    ElMessage.error(error.message || '登录失败，请稍后重试')
  }
}

const registering = async () => {
  if (!registerParam.value.userName || !registerParam.value.password || !registerParam.value.confirmPassword) {
    ElMessage.error('请填写所有必填项')
    return
  }

  if (registerParam.value.password !== registerParam.value.confirmPassword) {
    ElMessage.error('两次输入的密码不一致')
    return
  }

  try {
    localStorage.removeItem('x-token')
    localStorage.removeItem('user')
    localStorage.removeItem('session-store')
    userStore.clearUserInfo()
    const res = await register({
      userName: registerParam.value.userName,
      password: registerParam.value.password,
    }) as RegisterResponese

    if (res.code === 0) {
      ElMessage.success('注册成功')
      registerParam.value = {
        userName: '',
        password: '',
        confirmPassword: '',
      }
      isLoginMode.value = true
      return
    }

    ElMessage.error(res.msg || '注册失败')
  } catch (error: any) {
    ElMessage.error(error.message || '注册失败，请稍后重试')
  }
}
</script>

<style scoped>
.auth-container {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: linear-gradient(
    135deg,
    #ffffff 0%,
    #eff6ff 30%,
    #dbeafe 60%,
    #bfdbfe 100%
  );
}

.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  animation: float 8s ease-in-out infinite;
}

.glow-orb-1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.4) 0%, transparent 70%);
  top: -150px;
  right: -100px;
  animation-delay: 0s;
  opacity: 0.8;
}

.glow-orb-2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.3) 0%, transparent 70%);
  bottom: -100px;
  left: -50px;
  animation-delay: -3s;
  opacity: 0.6;
}

.glow-orb-3 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.2) 0%, transparent 70%);
  top: 50%;
  left: 30%;
  transform: translate(-50%, -50%);
  animation-delay: -5s;
  opacity: 0.5;
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  33% {
    transform: translate(30px, -30px) scale(1.05);
  }
  66% {
    transform: translate(-20px, 20px) scale(0.95);
  }
}

.grid-pattern {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle at 1px 1px, rgba(59, 130, 246, 0.08) 1px, transparent 0);
  background-size: 40px 40px;
  pointer-events: none;
}

.auth-content {
  position: relative;
  z-index: 10;
  display: grid;
  grid-template-columns: 1fr 480px;
  gap: 80px;
  max-width: 1200px;
  width: 100%;
  padding: 40px;
  align-items: center;
}

.brand-section {
  color: #1e40af;
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 48px;
  animation: fadeInUp 0.6s ease-out;
}

.logo-icon {
  width: 48px;
  height: 48px;
  color: #3b82f6;
  animation: pulse-glow 2s ease-in-out infinite;
}

@keyframes pulse-glow {
  0%, 100% {
    filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.4));
  }
  50% {
    filter: drop-shadow(0 0 20px rgba(59, 130, 246, 0.8));
  }
}

.logo-icon svg {
  width: 100%;
  height: 100%;
}

.logo-text {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: #1e40af;
}

.brand-title {
  margin: 0 0 24px;
  font-size: 56px;
  font-weight: 800;
  line-height: 1.1;
  animation: fadeInUp 0.6s ease-out 0.1s both;
}

.title-line {
  display: block;
  color: #1e40af;
}

.gradient-text {
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 50%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.brand-desc {
  margin: 0 0 48px;
  font-size: 18px;
  line-height: 1.8;
  color: #64748b;
  max-width: 420px;
  animation: fadeInUp 0.6s ease-out 0.2s both;
}

.floating-cards {
  position: relative;
  height: 120px;
  animation: fadeInUp 0.6s ease-out 0.3s both;
}

.float-card {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 12px;
  color: #1e40af;
  font-size: 14px;
  font-weight: 500;
  box-shadow:
    0 8px 32px rgba(59, 130, 246, 0.1),
    0 2px 8px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.float-card:hover {
  transform: translateY(-4px);
  box-shadow:
    0 12px 40px rgba(59, 130, 246, 0.15),
    0 4px 12px rgba(0, 0, 0, 0.08);
}

.card-icon {
  width: 24px;
  height: 24px;
  color: #3b82f6;
}

.card-icon svg {
  width: 100%;
  height: 100%;
}

.float-card-1 {
  left: 0;
  top: 0;
  animation: float1 4s ease-in-out infinite;
}

.float-card-2 {
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  animation: float2 4s ease-in-out infinite;
}

.float-card-3 {
  right: 0;
  bottom: 0;
  animation: float3 4s ease-in-out infinite;
}

@keyframes float1 {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

@keyframes float2 {
  0%, 100% { transform: translate(-50%, -50%); }
  50% { transform: translate(-50%, calc(-50% - 10px)); }
}

@keyframes float3 {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(10px); }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.form-section {
  animation: fadeInUp 0.6s ease-out 0.2s both;
}

.glass-card {
  position: relative;
  width: 100%;
  height: 100%;
  background: rgba(246, 246, 246, 0.4);
  border-radius: 24px;
  padding: 40px;
  z-index: 2;
  box-shadow: 0 25px 50px -12px rgba(59, 130, 246, 0.15),
              0 12px 24px -8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.glass-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 24px;
  padding: 3px;
  background: linear-gradient(
    90deg,
    #60a5fa,
    #e9e7f0,
    #f3f1f2,
    #60a5fa
  );
  background-size: 300% 100%;
  animation: border-flow 3s linear infinite;
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask-composite: exclude;
  pointer-events: none;
}

@keyframes border-flow {
  0% {
    background-position: 0% 50%;
  }
  100% {
    background-position: 200% 50%;
  }
}

.tab-header {
  display: flex;
  gap: 8px;
  margin-bottom: 32px;
  padding: 6px;
  background: rgba(59, 130, 246, 0.08);
  border-radius: 14px;
}

.tab-btn {
  position: relative;
  flex: 1;
  padding: 12px 20px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #64748b;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.tab-btn.active {
  background: #ffffff;
  color: #1e40af;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.form-title {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 700;
  color: #1e40af;
}

.form-subtitle {
  margin: 0 0 28px;
  font-size: 14px;
  color: #64748b;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-label {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.9);
  border: 1.5px solid #e2e8f0;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.input-wrapper.focused {
  background: #ffffff;
  border-color: #3b82f6;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
}

.input-icon {
  width: 20px;
  height: 20px;
  margin-left: 14px;
  color: #94a3b8;
  flex-shrink: 0;
  transition: color 0.3s ease;
}

.input-wrapper.focused .input-icon {
  color: #3b82f6;
}

.input-field {
  flex: 1;
  padding: 14px 14px 14px 10px;
  border: none;
  background: transparent;
  color: #1e293b;
  font-size: 14px;
  outline: none;
}

.input-field::placeholder {
  color: #94a3b8;
}

.submit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px 24px;
  margin-top: 8px;
  border: none;
  border-radius: 14px;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.35);
  transition: all 0.3s ease;
  overflow: hidden;
  position: relative;
}

.submit-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 0.5s ease;
}

.submit-btn:hover::before {
  left: 100%;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(59, 130, 246, 0.45);
}

.submit-btn:active {
  transform: translateY(0);
}

.btn-arrow {
  width: 20px;
  height: 20px;
  transition: transform 0.3s ease;
}

.submit-btn:hover .btn-arrow {
  transform: translateX(4px);
}

.form-footer {
  margin: 16px 0 0;
  text-align: center;
  font-size: 14px;
  color: #64748b;
}

.link-btn {
  background: none;
  border: none;
  color: #3b82f6;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.2s ease;
}

.link-btn:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

.form-slide-enter-active,
.form-slide-leave-active {
  transition: all 0.3s ease;
}

.form-slide-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.form-slide-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

@media (max-width: 1024px) {
  .auth-content {
    grid-template-columns: 1fr;
    gap: 48px;
    padding: 24px;
    max-width: 520px;
  }

  .brand-section {
    text-align: center;
  }

  .brand-logo {
    justify-content: center;
  }

  .brand-desc {
    margin-left: auto;
    margin-right: auto;
  }

  .floating-cards {
    display: flex;
    justify-content: center;
    gap: 16px;
    height: auto;
    flex-wrap: wrap;
  }

  .float-card {
    position: static;
    animation: none !important;
  }
}

@media (max-width: 480px) {
  .glass-card {
    padding: 28px 24px;
  }

  .brand-title {
    font-size: 40px;
  }

  .brand-desc {
    font-size: 16px;
  }
}
</style>
