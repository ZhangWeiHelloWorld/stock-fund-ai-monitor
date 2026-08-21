import { createApp } from 'vue'
import App from './App.vue'
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import Stocks from './views/Stocks.vue'
import Funds from './views/Funds.vue'
import Settings from './views/Settings.vue'
import Login from './views/Login.vue'
import './style.css'

const routes = [
  { path: '/login', component: Login, name: 'Login' },
  { path: '/', component: Dashboard, name: 'Dashboard' },
  { path: '/stocks', component: Stocks, name: 'Stocks' },
  { path: '/funds', component: Funds, name: 'Funds' },
  { path: '/settings', component: Settings, name: 'Settings' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.name !== 'Login' && !token) {
    next({ name: 'Login' })
  } else if (to.name === 'Login' && token) {
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

const app = createApp(App)
app.use(router)
app.mount('#app')
