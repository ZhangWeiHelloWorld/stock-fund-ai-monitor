import { createApp } from 'vue'
import App from './App.vue'
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import Calendar from './views/Calendar.vue'
import Stocks from './views/Stocks.vue'
import Funds from './views/Funds.vue'
import Strategies from './views/Strategies.vue'
import RiskWarning from './views/RiskWarning.vue'
import Settings from './views/Settings.vue'
import Login from './views/Login.vue'
import './style.css'

const routes = [
  { path: '/login', component: Login, name: 'Login' },
  { path: '/', component: Dashboard, name: 'Dashboard' },
  { path: '/calendar', component: Calendar, name: 'Calendar' },
  { path: '/stocks', component: Stocks, name: 'Stocks' },
  { path: '/funds', component: Funds, name: 'Funds' },
  { path: '/strategies', component: Strategies, name: 'Strategies' },
  { path: '/risk-warning', component: RiskWarning, name: 'RiskWarning' },
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
