<template>
  <div class="auth-shell" data-testid="auth-shell">
    <div class="auth-hero">
      <p class="auth-kicker">AgentHub</p>
      <h1>简洁、稳定、专注协作的聊天工作台</h1>
      <p class="auth-copy">
        登录后继续你的会话、消息和预览工作区。界面保持轻量，内容始终居中。
      </p>
    </div>

    <section
      v-if="isLoginMode"
      class="auth-card"
      data-testid="auth-card-login"
    >
      <div class="auth-card-header">
        <h2>登录账号</h2>
        <p>继续进入当前聊天工作区</p>
      </div>

      <form class="auth-form" @submit.prevent="loging">
        <label class="auth-field">
          <span>账号</span>
          <input
            v-model="loginParam.userName"
            type="text"
            placeholder="请输入账号"
          />
        </label>

        <label class="auth-field">
          <span>密码</span>
          <input
            v-model="loginParam.password"
            type="password"
            placeholder="请输入密码"
          />
        </label>

        <button class="auth-submit" type="submit">
          用户登录
        </button>
      </form>

      <p class="auth-switch-row">
        还没有账号？
        <button
          type="button"
          class="auth-switch-button"
          data-testid="auth-switch-register"
          @click="change_register"
        >
          去注册
        </button>
      </p>
    </section>

    <section
      v-else
      class="auth-card"
      data-testid="auth-card-register"
    >
      <div class="auth-card-header">
        <h2>注册账号</h2>
        <p>创建一个新的协作身份</p>
      </div>

      <form class="auth-form" @submit.prevent="registering">
        <label class="auth-field">
          <span>用户名</span>
          <input
            v-model="registerParam.userName"
            type="text"
            placeholder="请输入用户名"
          />
        </label>

        <label class="auth-field">
          <span>邮箱</span>
          <input
            v-model="registerParam.email"
            type="email"
            placeholder="请输入邮箱"
          />
        </label>

        <div class="auth-inline-field">
          <label class="auth-field">
            <span>验证码</span>
            <input
              v-model="registerParam.emailCode"
              type="text"
              placeholder="邮箱验证码"
            />
          </label>
          <button
            type="button"
            class="auth-code-button"
            :disabled="!isEmail || cutdown > 0"
            @click="sendCode"
          >
            <span v-if="cutdown > 0">{{ cutdown }}s</span>
            <span v-else>获取验证码</span>
          </button>
        </div>

        <label class="auth-field">
          <span>密码</span>
          <input
            v-model="registerParam.password"
            type="password"
            placeholder="请输入密码"
          />
        </label>

        <button class="auth-submit" type="submit">
          注册
        </button>
      </form>

      <p class="auth-switch-row">
        已有账号？
        <button
          type="button"
          class="auth-switch-button"
          @click="change_login"
        >
          去登录
        </button>
      </p>
    </section>
  </div>
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { getCode, login, register } from '../api/login'
import type { CodeResponese, LoginResponse, RegisterResponese, UserInfo } from '../types/login'
import { useUserInfoStore } from '../store/module/useUserStore'

const router = useRouter()
const userStore = useUserInfoStore()

const loginParam = ref({
  userName: '',
  password: '',
})

const registerParam = ref({
  userName: '',
  email: '',
  emailCode: '',
  password: '',
  confirmPassword: '',
})

const cutdown = ref(0)
const isLoginMode = ref(true)

const isEmail = computed(() => {
  const reg = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return reg.test(registerParam.value.email)
})

function change_register() {
  isLoginMode.value = false
}

function change_login() {
  isLoginMode.value = true
}

const sendCode = async () => {
  if (!isEmail.value) {
    ElMessage.error('请输入有效邮箱')
    return
  }

  try {
    const res = await getCode({ email: registerParam.value.email }) as CodeResponese
    if (res.code === 0) {
      ElMessage.success('验证码已发送')
      cutdown.value = 60
      const timer = setInterval(() => {
        cutdown.value--
        if (cutdown.value <= 0) {
          clearInterval(timer)
        }
      }, 1000)
    } else {
      ElMessage.error(res.msg || '发送验证码失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '发送验证码失败，请重试')
  }
}

const loging = async () => {
  try {
    const res = await login(loginParam.value) as LoginResponse
    if (res.code === 0) {
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
  if (
    !registerParam.value.userName ||
    !registerParam.value.email ||
    !registerParam.value.password ||
    !registerParam.value.emailCode
  ) {
    ElMessage.error('请填写所有必填项')
    return
  }

  if (!isEmail.value) {
    ElMessage.error('请输入正确的邮箱格式')
    return
  }

  try {
    const res = await register({
      userName: registerParam.value.userName,
      email: registerParam.value.email,
      password: registerParam.value.password,
      emailCode: registerParam.value.emailCode,
    }) as RegisterResponese

    if (res.code === 0) {
      ElMessage.success('注册成功')
      registerParam.value = {
        userName: '',
        email: '',
        emailCode: '',
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
.auth-shell {
  min-height: 100vh;
  padding: 48px 32px;
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(360px, 460px);
  gap: 32px;
  align-items: center;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 248, 0.98));
}

.auth-hero {
  max-width: 560px;
  padding: 24px;
}

.auth-kicker {
  margin: 0 0 16px;
  color: rgb(var(--primary-strong));
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.auth-hero h1 {
  margin: 0 0 16px;
  font-size: clamp(32px, 4vw, 52px);
  line-height: 1.08;
  color: rgb(var(--text-color));
}

.auth-copy {
  margin: 0;
  max-width: 420px;
  color: rgb(var(--text-secondary));
  font-size: 16px;
  line-height: 1.75;
}

.auth-card {
  padding: 32px;
  border-radius: var(--radius-lg);
  border: 1px solid rgb(var(--border-color));
  background: rgb(var(--surface-color));
  box-shadow: var(--shadow-soft);
}

.auth-card-header {
  margin-bottom: 24px;
}

.auth-card-header h2 {
  margin: 0 0 8px;
  font-size: 28px;
  line-height: 1.15;
  color: rgb(var(--text-color));
}

.auth-card-header p {
  margin: 0;
  color: rgb(var(--text-secondary));
  font-size: 14px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.auth-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.auth-field span {
  color: rgb(var(--text-secondary));
  font-size: 13px;
  font-weight: 600;
}

.auth-field input {
  width: 100%;
  min-height: 48px;
  padding: 0 14px;
  border-radius: var(--radius-sm);
  border: 1px solid rgb(var(--border-color));
  background: rgb(var(--surface-muted));
  color: rgb(var(--text-color));
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
}

.auth-field input:focus {
  border-color: rgb(var(--primary-color));
  background: rgb(var(--surface-color));
  box-shadow: 0 0 0 3px rgba(var(--primary-color), 0.12);
}

.auth-inline-field {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 120px;
  gap: 12px;
  align-items: end;
}

.auth-submit,
.auth-code-button,
.auth-switch-button {
  transition: transform 0.2s ease, background-color 0.2s ease, border-color 0.2s ease;
}

.auth-submit {
  min-height: 48px;
  border-radius: var(--radius-sm);
  background: rgb(var(--primary-color));
  color: #fff;
  font-weight: 600;
}

.auth-submit:hover {
  transform: translateY(-1px);
  background: rgb(var(--primary-strong));
}

.auth-code-button {
  min-height: 48px;
  padding: 0 14px;
  border-radius: var(--radius-sm);
  border: 1px solid rgb(var(--border-color));
  background: rgb(var(--surface-color));
  color: rgb(var(--text-color));
  font-weight: 600;
}

.auth-code-button:disabled {
  cursor: not-allowed;
  color: rgb(var(--text-muted));
  background: rgb(var(--surface-muted));
}

.auth-code-button:not(:disabled):hover {
  border-color: rgb(var(--primary-color));
  color: rgb(var(--primary-strong));
}

.auth-switch-row {
  margin: 20px 0 0;
  color: rgb(var(--text-secondary));
  font-size: 14px;
}

.auth-switch-button {
  padding: 0 4px;
  color: rgb(var(--primary-strong));
  font-weight: 600;
}

@media (max-width: 920px) {
  .auth-shell {
    grid-template-columns: 1fr;
    padding: 24px 16px 32px;
  }

  .auth-hero {
    padding: 8px 0;
  }
}

@media (max-width: 640px) {
  .auth-card {
    padding: 24px 18px;
  }

  .auth-inline-field {
    grid-template-columns: 1fr;
  }
}
</style>
