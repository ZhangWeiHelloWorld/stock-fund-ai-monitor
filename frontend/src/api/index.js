import axios from 'axios'

const api = axios.create({
  baseURL: '/api'
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, error => {
  return Promise.reject(error)
})

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default {
  // Auth
  login: (data) => api.post('/auth/login', data).then(res => res.data),
  getMe: () => api.get('/auth/me').then(res => res.data),
  logout: () => api.post('/auth/logout').then(res => res.data),

  // Admin
  getUsers: () => api.get('/admin/users').then(res => res.data),
  createUser: (data) => api.post('/admin/users', data).then(res => res.data),
  resetPassword: (id, data) => api.put(`/admin/users/${id}/password`, data).then(res => res.data),
  deleteUser: (id) => api.delete(`/admin/users/${id}`).then(res => res.data),

  // Stocks
  getStocks: () => api.get('/stocks').then(res => res.data),
  createStock: (data) => api.post('/stocks', data).then(res => res.data),
  updateStock: (id, data) => api.put(`/stocks/${id}`, data).then(res => res.data),
  deleteStock: (id) => api.delete(`/stocks/${id}`).then(res => res.data),
  lookupStock: (code) => api.get(`/stocks/lookup/${code}`).then(res => res.data),

  // Funds
  getFunds: () => api.get('/funds').then(res => res.data),
  createFund: (data) => api.post('/funds', data).then(res => res.data),
  updateFund: (id, data) => api.put(`/funds/${id}`, data).then(res => res.data),
  deleteFund: (id) => api.delete(`/funds/${id}`).then(res => res.data),
  lookupFund: (code) => api.get(`/funds/lookup/${code}`).then(res => res.data),

  // Market
  getMarketOverview: () => api.get('/market/overview').then(res => res.data),
  refreshMarket: () => api.get('/market/refresh').then(res => res.data),
  getMarketHistory: (days) => api.get(`/market/history?days=${days}`).then(res => res.data),

  // Settings
  getSettings: () => api.get('/settings').then(res => res.data),
  updateSettings: (data) => api.put('/settings', data).then(res => res.data),
  testPush: () => api.post('/settings/test-push').then(res => res.data),
  testFormatPush: () => api.post('/settings/test-format-push').then(res => res.data),
  testDeepseekReview: () => api.post('/settings/test-deepseek-review').then(res => res.data),
  testAiNewsAnalysis: () => api.post('/settings/test-ai-news-analysis').then(res => res.data),
  testAlertPush: () => api.post('/settings/test-alert-push').then(res => res.data)
}
