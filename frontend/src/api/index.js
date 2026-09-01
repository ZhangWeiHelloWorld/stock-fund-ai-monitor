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
  getMarketIndices: () => api.get('/market/indices').then(res => res.data),
  getMarketHistory: (days) => api.get(`/market/history?days=${days}`).then(res => res.data),

  // Settings
  getSettings: () => api.get('/settings').then(res => res.data),
  updateSettings: (data) => api.put('/settings', data).then(res => res.data),
  testPush: () => api.post('/settings/test-push').then(res => res.data),
  testFormatPush: () => api.post('/settings/test-format-push').then(res => res.data),
  testDeepseekReview: () => api.post('/settings/test-deepseek-review').then(res => res.data),
  testAiNewsAnalysis: () => api.post('/settings/test-ai-news-analysis').then(res => res.data),
  testAlertPush: () => api.post('/settings/test-alert-push').then(res => res.data),

  // Trading Strategies
  getStrategyTemplates: () => api.get('/strategies/templates').then(res => res.data),
  getFundFeeStructure: (code) => api.get(`/strategies/fee-structure/${code}`).then(res => res.data),
  getStockFeeStructure: (code) => api.get(`/strategies/stock-fee-structure/${code}`).then(res => res.data),
  getFundHistory: (code, startDate, endDate) => {
    let url = `/strategies/history/${code}`
    const params = []
    if (startDate) params.push(`start_date=${startDate}`)
    if (endDate) params.push(`end_date=${endDate}`)
    if (params.length) url += `?${params.join('&')}`
    return api.get(url).then(res => res.data)
  },
  getStockHistory: (code, startDate, endDate) => {
    let url = `/strategies/stock-history/${code}`
    const params = []
    if (startDate) params.push(`start_date=${startDate}`)
    if (endDate) params.push(`end_date=${endDate}`)
    if (params.length) url += `?${params.join('&')}`
    return api.get(url).then(res => res.data)
  },
  getStockTimeline: (code) => api.get(`/strategies/stock-timeline/${code}`).then(res => res.data),
  getStockMinuteHistory: (code, period = 'm1', count = 640) => api.get(`/strategies/stock-minute-history/${code}?period=${period}&count=${count}`).then(res => res.data),
  runStrategyBacktest: (data) => api.post('/strategies/backtest', data).then(res => res.data),
  getStrategies: (assetType = 'fund') => api.get(`/strategies?asset_type=${assetType}`).then(res => res.data),
  createStrategy: (data) => api.post('/strategies', data).then(res => res.data),
  getStrategy: (id) => api.get(`/strategies/${id}`).then(res => res.data),
  updateStrategy: (id, data) => api.put(`/strategies/${id}`, data).then(res => res.data),
  deleteStrategy: (id) => api.delete(`/strategies/${id}`).then(res => res.data),
  scanStrategySignals: () => api.post('/strategies/scan-signals').then(res => res.data),
  getStrategySignals: (status = 'pending') => api.get(`/strategies/signals/list?status=${status}`).then(res => res.data),
  executeStrategySignal: (id, data) => api.post(`/strategies/signals/${id}/execute`, data).then(res => res.data),
  getStrategyTrades: (id) => api.get(`/strategies/${id}/trades`).then(res => res.data)
}
