<template>
  <div class="login-container">
    <div class="login-card">
      <div class="header">
        <div class="logo-icon">📈</div>
        <h2>股票基金监控系统</h2>
        <p class="subtitle">请使用管理员分配的账号密码登录系统</p>
      </div>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username">账号 / 用户名</label>
          <input
            id="username"
            v-model="form.username"
            type="text"
            placeholder="请输入账号"
            required
            autocomplete="username"
          />
        </div>

        <div class="form-group">
          <label for="password">密码</label>
          <input
            id="password"
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            required
            autocomplete="current-password"
          />
        </div>

        <div v-if="errorMessage" class="error-alert">
          <span>⚠️ {{ errorMessage }}</span>
        </div>

        <button type="submit" class="submit-btn" :disabled="loading">
          <span v-if="loading">登录中...</span>
          <span v-else>登 录</span>
        </button>
      </form>

      <div class="footer-tip">
        <span>如忘记密码，请联系管理员在后台 <code>admin_config.json</code> 重置</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const loading = ref(false)
const errorMessage = ref('')

const form = reactive({
  username: '',
  password: ''
})

const handleLogin = async () => {
  errorMessage.value = ''
  loading.value = true
  try {
    const res = await api.login(form)
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('user', JSON.stringify(res.user))
    router.push('/')
  } catch (err) {
    if (err.response && err.response.data && err.response.data.detail) {
      errorMessage.value = err.response.data.detail
    } else {
      errorMessage.value = '登录失败，请检查网络连接或服务器状态'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at top right, #1a1f3c, #0d1117);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: rgba(22, 27, 34, 0.75);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 36px 32px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.4);
}

.header {
  text-align: center;
  margin-bottom: 28px;
}

.logo-icon {
  width: 54px;
  height: 54px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, #00d2ff, #3a7bd5);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.8rem;
  box-shadow: 0 4px 14px rgba(0, 212, 255, 0.3);
}

.header h2 {
  font-size: 1.5rem;
  color: var(--text-primary, #f0f6fc);
  font-weight: 600;
  margin-bottom: 8px;
}

.subtitle {
  font-size: 0.88rem;
  color: var(--text-secondary, #8b949e);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary, #8b949e);
}

.form-group input {
  padding: 12px 16px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #fff;
  font-size: 0.95rem;
  outline: none;
  transition: all 0.2s ease;
}

.form-group input:focus {
  border-color: #00d2ff;
  background: rgba(0, 212, 255, 0.05);
  box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.15);
}

.error-alert {
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(248, 81, 73, 0.15);
  border: 1px solid rgba(248, 81, 73, 0.3);
  color: #f85149;
  font-size: 0.88rem;
}

.submit-btn {
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #00d2ff, #3a7bd5);
  color: #fff;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 14px rgba(0, 212, 255, 0.25);
  margin-top: 4px;
}

.submit-btn:hover:not(:disabled) {
  opacity: 0.92;
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(0, 212, 255, 0.35);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.footer-tip {
  margin-top: 24px;
  text-align: center;
  font-size: 0.78rem;
  color: #6e7681;
}

.footer-tip code {
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  color: #58a6ff;
}
</style>
