<template>
  <div v-if="isLoginPage" class="login-layout">
    <router-view />
    <div class="toast" :class="{ show: toast.visible }">
      {{ toast.message }}
    </div>
  </div>

  <div v-else class="app-layout">
    <aside class="sidebar">
      <div class="sidebar-top">
        <div class="logo">
          <div class="logo-icon">📈</div>
          <h1>持仓看板</h1>
        </div>
        <nav class="nav-links">
          <router-link to="/" class="nav-item">
            <span class="icon">📊</span>
            <span class="text">行情看板</span>
          </router-link>
          <router-link to="/stocks" class="nav-item">
            <span class="icon">📈</span>
            <span class="text">股票管理</span>
          </router-link>
          <router-link to="/funds" class="nav-item">
            <span class="icon">💰</span>
            <span class="text">基金管理</span>
          </router-link>
          <router-link to="/settings" class="nav-item">
            <span class="icon">⚙️</span>
            <span class="text">系统设置</span>
          </router-link>
        </nav>
      </div>

      <div class="user-panel">
        <div class="user-info">
          <span class="avatar">👤</span>
          <div class="user-details">
            <span class="username">{{ currentUser?.username || '用户' }}</span>
            <span class="role-badge" :class="currentUser?.role">
              {{ currentUser?.role === 'admin' ? '管理员' : '普通用户' }}
            </span>
          </div>
        </div>
        <button @click="handleLogout" class="logout-btn" title="退出登录">
          🚪 退出
        </button>
      </div>
    </aside>

    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- Global Toast -->
    <div class="toast" :class="{ show: toast.visible }">
      {{ toast.message }}
    </div>
  </div>
</template>

<script setup>
import { reactive, provide, computed, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from './api'

const route = useRoute()
const router = useRouter()

const isLoginPage = computed(() => route.name === 'Login')
const currentUser = ref(null)

const loadUser = () => {
  try {
    const raw = localStorage.getItem('user')
    if (raw) {
      currentUser.value = JSON.parse(raw)
    } else {
      currentUser.value = null
    }
  } catch (e) {
    currentUser.value = null
  }
}

onMounted(() => {
  loadUser()
})

watch(() => route.path, () => {
  loadUser()
})

const handleLogout = async () => {
  try {
    await api.logout()
  } catch (e) {
    // Ignore error
  } finally {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    currentUser.value = null
    router.push('/login')
  }
}

const toast = reactive({
  visible: false,
  message: ''
})

const showToast = (msg, duration = 3000) => {
  toast.message = msg
  toast.visible = true
  setTimeout(() => {
    toast.visible = false
  }, duration)
}

provide('showToast', showToast)
</script>

<style scoped>
.login-layout {
  min-height: 100vh;
  width: 100vw;
}

.app-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 260px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-glass);
  padding: 24px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: #fff;
  font-size: 1.2rem;
}

.logo h1 {
  font-size: 1.4rem;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.nav-links {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  text-decoration: none;
  color: var(--text-secondary);
  transition: all 0.2s;
  font-weight: 500;
}

.nav-item:hover {
  background: var(--bg-glass);
  color: var(--text-primary);
}

.nav-item.router-link-active {
  background: rgba(0, 212, 255, 0.1);
  color: var(--accent-primary);
  border-left: 3px solid var(--accent-primary);
}

.user-panel {
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar {
  font-size: 1.4rem;
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.username {
  font-weight: 600;
  font-size: 0.92rem;
  color: var(--text-primary);
}

.role-badge {
  font-size: 0.72rem;
  padding: 1px 6px;
  border-radius: 4px;
  width: fit-content;
}

.role-badge.admin {
  background: rgba(255, 170, 0, 0.15);
  color: #ffaa00;
  border: 1px solid rgba(255, 170, 0, 0.3);
}

.role-badge.user {
  background: rgba(0, 212, 255, 0.15);
  color: #00d2ff;
  border: 1px solid rgba(0, 212, 255, 0.3);
}

.logout-btn {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: var(--text-secondary);
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.2s ease;
}

.logout-btn:hover {
  background: rgba(248, 81, 73, 0.15);
  border-color: rgba(248, 81, 73, 0.3);
  color: #f85149;
}

.main-content {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
  position: relative;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Responsive */
@media (max-width: 768px) {
  .app-layout {
    flex-direction: column;
  }
  .sidebar {
    width: 100%;
    padding: 16px;
    border-right: none;
    border-bottom: 1px solid var(--border-glass);
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
  .logo {
    margin-bottom: 0;
  }
  .nav-links {
    flex-direction: row;
  }
  .nav-item .text {
    display: none;
  }
  .nav-item {
    padding: 8px;
  }
  .main-content {
    padding: 16px;
  }
  .user-panel {
    border-top: none;
    padding-top: 0;
  }
}
</style>
