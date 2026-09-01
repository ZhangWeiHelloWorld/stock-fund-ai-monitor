<template>
  <div class="dashboard">
    <header class="header">
      <div>
        <h2 class="page-title">行情看板</h2>
        <p class="text-secondary">实时持仓总览</p>
      </div>
      <div class="header-actions">
        <!-- 隐私小眼睛开关 -->
        <button class="btn btn-glass eye-btn" @click="toggleShowAmount" :title="showAmount ? '点击隐藏金额' : '点击显示金额'">
          <span>{{ showAmount ? '👁️' : '🙈' }}</span>
          <span>{{ showAmount ? '显示金额' : '已隐藏金额' }}</span>
        </button>

        <div class="market-status" :class="marketStatusClass">
          <span class="pulse-dot"></span>
          {{ marketData?.summary?.market_status || '加载中...' }}
        </div>
        <button class="btn btn-glass" @click="refreshData" :disabled="loading">
          <span :class="{ rotating: loading }">🔄</span>
          刷新
        </button>
      </div>
    </header>

    <div v-if="loading && !marketData" class="loading-state">
      <div class="spinner"></div>
      <p>正在获取行情数据...</p>
    </div>

    <template v-else-if="marketData">
      <!-- Market Indices Overview -->
      <div v-if="marketIndices && marketIndices.length" class="glass-card mb-4 indices-section">
        <div class="section-header">
          <div class="section-title-group">
            <h3>🏛️ 大盘指数</h3>
            <span v-if="totalMarketTurnover" class="market-turnover-tag">
              两市/全市场成交额: <strong>{{ totalMarketTurnover }}</strong>
            </span>
          </div>
          <div class="indices-actions">
            <button class="btn btn-glass btn-sm" @click="showAllIndices = !showAllIndices" :title="showAllIndices ? '收起仅显示4大核心指数' : '展开显示全部指数'">
              {{ showAllIndices ? '收起 (核心4指)' : '全部指数 (' + marketIndices.length + ')' }}
            </button>
          </div>
        </div>

        <div class="indices-grid">
          <div 
            v-for="idx in displayIndices" 
            :key="idx.code" 
            class="index-card"
            :class="[getIndexChangeClass(idx.change_pct)]"
          >
            <div class="index-top">
              <div class="index-name-wrap">
                <span class="index-name">{{ idx.name }}</span>
                <span class="index-symbol">{{ idx.symbol }}</span>
              </div>
              <span class="index-badge" :class="idx.change_pct >= 0 ? 'badge-up' : 'badge-down'">
                {{ idx.change_pct >= 0 ? '▲' : '▼' }} {{ formatIndexChange(idx.change_pct) }}%
              </span>
            </div>

            <div class="index-points" :class="colorClass(idx.change_pct)">
              {{ idx.current > 0 ? idx.current.toFixed(2) : '-' }}
            </div>

            <div class="index-change-row">
              <span class="index-change-amount" :class="colorClass(idx.change_amount)">
                {{ idx.change_amount > 0 ? '+' : '' }}{{ idx.change_amount != null ? idx.change_amount.toFixed(2) : '-' }}
              </span>
              <span class="index-turnover" title="成交额">
                成交 {{ idx.amount_formatted }}
              </span>
            </div>

            <!-- 日内波动进度条 -->
            <div class="index-range-bar-wrap" :title="`最低: ${idx.low > 0 ? idx.low.toFixed(2) : '-'} / 最高: ${idx.high > 0 ? idx.high.toFixed(2) : '-'} / 振幅: ${idx.amplitude ? idx.amplitude.toFixed(2) + '%' : '-'}`">
              <div class="range-labels">
                <span>低 {{ idx.low > 0 ? idx.low.toFixed(2) : '-' }}</span>
                <span class="amplitude-label">振幅 {{ idx.amplitude ? idx.amplitude.toFixed(2) + '%' : '-' }}</span>
                <span>高 {{ idx.high > 0 ? idx.high.toFixed(2) : '-' }}</span>
              </div>
              <div class="range-track">
                <div class="range-fill" :style="{ width: getIndexRangePercent(idx) + '%' }" :class="idx.change_pct >= 0 ? 'fill-up' : 'fill-down'"></div>
                <div class="range-marker" :style="{ left: getIndexRangePercent(idx) + '%' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- History Chart -->
      <div class="glass-card mb-4 history-chart-container">
        <div class="section-header">
          <div class="section-title-group">
            <h3>📈 历史收益折线图</h3>
          </div>
          <div class="chart-actions">
            <!-- 收益维度切换 -->
            <div class="btn-group-pill">
              <button class="btn btn-glass" :class="{active: chartViewType === 'total'}" @click="changeChartViewType('total')">总收益</button>
              <button class="btn btn-glass" :class="{active: chartViewType === 'fund'}" @click="changeChartViewType('fund')">基金收益</button>
              <button class="btn btn-glass" :class="{active: chartViewType === 'stock'}" @click="changeChartViewType('stock')">股票收益</button>
              <button class="btn btn-glass" :class="{active: chartViewType === 'all'}" @click="changeChartViewType('all')">综合对比</button>
            </div>
            <!-- 时间区间切换 -->
            <div class="btn-group-pill">
              <button class="btn btn-glass" :class="{active: historyDays === 7}" @click="fetchHistoryAndRender(7)">近一周</button>
              <button class="btn btn-glass" :class="{active: historyDays === 30}" @click="fetchHistoryAndRender(30)">近一月</button>
              <button class="btn btn-glass" :class="{active: historyDays === 90}" @click="fetchHistoryAndRender(90)">近三月</button>
            </div>
          </div>
        </div>
        <div ref="chartRef" style="width: 100%; height: 320px;"></div>
      </div>

      <!-- Summary Cards -->
      <div class="summary-cards">
        <!-- Asset Amount Card with Hover Tooltip -->
        <div class="glass-card summary-card asset-card-wrapper">
          <div class="card-icon">💵</div>
          <div class="card-title-row">
            <span>持仓资产</span>
            <span class="info-icon" title="鼠标悬停查看股票与基金资产收益分布">ℹ️</span>
          </div>
          <div class="card-value text-accent">
            {{ showAmount ? formatMoneyNoSign(marketData.summary.total_asset) + ' 元' : '**** 元' }}
          </div>

          <!-- Hover Tooltip Popup -->
          <div class="asset-tooltip">
            <div class="tooltip-header">📊 资产与收益率分布</div>
            <div class="tooltip-divider"></div>
            
            <div class="tooltip-item">
              <div class="item-title">📈 股票资产</div>
              <div class="item-value">{{ showAmount ? formatMoneyNoSign(marketData.summary.stock_asset) + ' 元' : '**** 元' }}</div>
              <div class="item-sub">
                收益率: <span :class="colorClass(marketData.summary.stock_profit_pct)">{{ formatPercent(marketData.summary.stock_profit_pct) }}</span>
                <span class="sub-profit" :class="colorClass(marketData.summary.stock_profit)">({{ showAmount ? formatMoney(marketData.summary.stock_profit) + '元' : '****' }})</span>
              </div>
            </div>
            
            <div class="tooltip-item" style="margin-top: 10px;">
              <div class="item-title">💰 基金资产</div>
              <div class="item-value">{{ showAmount ? formatMoneyNoSign(marketData.summary.fund_asset) + ' 元' : '**** 元' }}</div>
              <div class="item-sub">
                收益率: <span :class="colorClass(marketData.summary.fund_profit_pct)">{{ formatPercent(marketData.summary.fund_profit_pct) }}</span>
                <span class="sub-profit" :class="colorClass(marketData.summary.fund_profit)">({{ showAmount ? formatMoney(marketData.summary.fund_profit) + '元' : '****' }})</span>
              </div>
            </div>

            <div class="tooltip-divider"></div>

            <div class="tooltip-item total-item">
              <div class="item-title">🎯 整体收益率</div>
              <div class="item-value" :class="colorClass(marketData.summary.total_profit_pct)">
                {{ formatPercent(marketData.summary.total_profit_pct) }}
              </div>
            </div>
          </div>
        </div>

        <!-- Today's PnL Card with Hover Tooltip -->
        <div class="glass-card summary-card asset-card-wrapper">
          <div class="card-icon">📅</div>
          <div class="card-title-row">
            <span>今日盈亏</span>
            <span class="info-icon" title="鼠标悬停查看股票与基金各自今日盈亏">ℹ️</span>
          </div>
          <div class="card-value" :class="colorClass(marketData.summary.total_day_profit)">
            {{ showAmount ? formatMoney(marketData.summary.total_day_profit) + ' 元' : '**** 元' }}
          </div>

          <!-- Hover Tooltip Popup for Today's PnL -->
          <div class="asset-tooltip">
            <div class="tooltip-header">📅 今日盈亏明细</div>
            <div class="tooltip-divider"></div>
            
            <div class="tooltip-item">
              <div class="item-title">📈 股票今日盈亏</div>
              <div class="item-value" :class="colorClass(stockDayProfit)">
                {{ showAmount ? formatMoney(stockDayProfit) + ' 元' : '**** 元' }}
              </div>
            </div>
            
            <div class="tooltip-item" style="margin-top: 10px;">
              <div class="item-title">💰 基金今日盈亏</div>
              <div class="item-value" :class="colorClass(fundDayProfit)">
                {{ showAmount ? formatMoney(fundDayProfit) + ' 元' : '**** 元' }}
              </div>
            </div>

            <div class="tooltip-divider"></div>

            <div class="tooltip-item total-item">
              <div class="item-title">🎯 今日总盈亏</div>
              <div class="item-value" :class="colorClass(marketData.summary.total_day_profit)">
                {{ showAmount ? formatMoney(marketData.summary.total_day_profit) + ' 元' : '**** 元' }}
              </div>
            </div>
          </div>
        </div>

        <div class="glass-card summary-card">
          <div class="card-icon">💼</div>
          <div class="card-title">累计盈亏</div>
          <div class="card-value" :class="colorClass(marketData.summary.total_profit)">
            {{ showAmount ? formatMoney(marketData.summary.total_profit) + ' 元' : '**** 元' }}
          </div>
        </div>

        <div class="glass-card summary-card">
          <div class="card-icon">📊</div>
          <div class="card-title">持仓数量</div>
          <div class="card-value text-accent">
            {{ activeHoldingsCount }} 个
          </div>
        </div>
      </div>

      <!-- Stocks Table -->
      <div class="section-header">
        <div class="section-title-group">
          <h3>📈 股票列表</h3>
          <span class="badge">{{ displayStocks.length }} 只</span>
        </div>
        <div class="sort-controls">
          <span class="sort-label">排序:</span>
          <select class="form-control sort-select" v-model="stockSortKey">
            <option value="default">默认</option>
            <option value="change_pct">按涨跌幅</option>
            <option value="day_profit">按今日盈亏</option>
            <option value="total_profit">按总盈亏</option>
            <option value="total_profit_pct">按收益率</option>
            <option value="shares">按持仓股数</option>
            <option value="current_price">按现价</option>
          </select>
          <button class="btn btn-glass sort-order-btn" @click="stockSortOrder = stockSortOrder === 'desc' ? 'asc' : 'desc'" title="切换排序方向">
            {{ stockSortOrder === 'desc' ? '⬇ 降序' : '⬆ 升序' }}
          </button>
        </div>
      </div>
      <div class="glass-card mb-4">
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>代码</th>
                <th>名称</th>
                <th>状态</th>
                <th class="sortable" @click="changeStockSort('current_price')">
                  现价 <span class="sort-icon">{{ getSortIcon('stock', 'current_price') }}</span>
                </th>
                <th class="sortable" @click="changeStockSort('change_pct')">
                  涨跌幅 <span class="sort-icon">{{ getSortIcon('stock', 'change_pct') }}</span>
                </th>
                <th>涨跌额</th>
                <th class="sortable" @click="changeStockSort('shares')">
                  持仓股数 <span class="sort-icon">{{ getSortIcon('stock', 'shares') }}</span>
                </th>
                <th>成本价</th>
                <th class="sortable" @click="changeStockSort('day_profit')">
                  今日盈亏 <span class="sort-icon">{{ getSortIcon('stock', 'day_profit') }}</span>
                </th>
                <th class="sortable" @click="changeStockSort('total_profit')">
                  总盈亏 <span class="sort-icon">{{ getSortIcon('stock', 'total_profit') }}</span>
                </th>
                <th class="sortable" @click="changeStockSort('total_profit_pct')">
                  收益率 <span class="sort-icon">{{ getSortIcon('stock', 'total_profit_pct') }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="stock in sortedStocks" :key="stock.id" class="table-row">
                <td class="code-cell">{{ stock.code }}</td>
                <td class="name-cell">{{ stock.name }}</td>
                <td>
                  <span class="status-badge" :class="stock.is_holding ? 'active' : 'inactive'">
                    {{ stock.is_holding ? '持仓' : '未持仓' }}
                  </span>
                </td>
                <td class="price-cell" :class="colorClass(stock.change_pct)">
                  {{ showAmount ? (stock.current_price > 0 ? stock.current_price.toFixed(2) : '-') : '****' }}
                </td>
                <td :class="colorClass(stock.change_pct)">
                  {{ formatPercent(stock.change_pct) }}
                </td>
                <td :class="colorClass(stock.change_amount)">
                  {{ stock.change_amount != null ? (stock.change_amount > 0 ? '+' : '') + stock.change_amount.toFixed(2) : '-' }}
                </td>
                <td>{{ showAmount ? stock.shares : '****' }}</td>
                <td>{{ showAmount ? stock.cost_price?.toFixed(2) : '****' }}</td>
                <td :class="colorClass(stock.day_profit)">
                  {{ showAmount ? formatMoney(stock.day_profit) : '****' }}
                </td>
                <td :class="colorClass(stock.total_profit)">
                  {{ showAmount ? formatMoney(stock.total_profit) : '****' }}
                </td>
                <td :class="colorClass(stock.total_profit_pct)">
                  {{ formatPercent(stock.total_profit_pct) }}
                </td>
              </tr>
              <tr v-if="!sortedStocks.length">
                <td colspan="11" class="empty-row">暂无股票数据，请前往「股票管理」添加</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Funds Table -->
      <div class="section-header">
        <div class="section-title-group">
          <h3>💰 基金列表</h3>
          <span class="badge">{{ displayFunds.length }} 只</span>
        </div>
        <div class="sort-controls">
          <span class="sort-label">排序:</span>
          <select class="form-control sort-select" v-model="fundSortKey">
            <option value="default">默认</option>
            <option value="change_pct">按涨跌幅</option>
            <option value="day_profit">按今日盈亏</option>
            <option value="total_profit">按总盈亏</option>
            <option value="total_profit_pct">按收益率</option>
            <option value="shares">按持仓份额</option>
            <option value="current_nav">按净值/估值</option>
          </select>
          <button class="btn btn-glass sort-order-btn" @click="fundSortOrder = fundSortOrder === 'desc' ? 'asc' : 'desc'" title="切换排序方向">
            {{ fundSortOrder === 'desc' ? '⬇ 降序' : '⬆ 升序' }}
          </button>
        </div>
      </div>
      <div class="glass-card">
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>代码</th>
                <th>名称</th>
                <th>状态</th>
                <th class="sortable" @click="changeFundSort('current_nav')">
                  净值/估值 <span class="sort-icon">{{ getSortIcon('fund', 'current_nav') }}</span>
                </th>
                <th class="sortable" @click="changeFundSort('change_pct')">
                  涨跌幅 <span class="sort-icon">{{ getSortIcon('fund', 'change_pct') }}</span>
                </th>
                <th>更新状态</th>
                <th class="sortable" @click="changeFundSort('shares')">
                  持仓份额 <span class="sort-icon">{{ getSortIcon('fund', 'shares') }}</span>
                </th>
                <th>成本净值</th>
                <th class="sortable" @click="changeFundSort('day_profit')">
                  今日盈亏 <span class="sort-icon">{{ getSortIcon('fund', 'day_profit') }}</span>
                </th>
                <th class="sortable" @click="changeFundSort('total_profit')">
                  总盈亏 <span class="sort-icon">{{ getSortIcon('fund', 'total_profit') }}</span>
                </th>
                <th class="sortable" @click="changeFundSort('total_profit_pct')">
                  收益率 <span class="sort-icon">{{ getSortIcon('fund', 'total_profit_pct') }}</span>
                </th>
                <th>更新时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="fund in sortedFunds" :key="fund.id" class="table-row">
                <td class="code-cell">{{ fund.code }}</td>
                <td class="name-cell">{{ fund.name }}</td>
                <td>
                  <span class="status-badge" :class="fund.is_holding ? 'active' : 'inactive'">
                    {{ fund.is_holding ? '持仓' : '未持仓' }}
                  </span>
                </td>
                <td class="price-cell" :class="colorClass(fund.change_pct)">
                  {{ showAmount ? (fund.current_nav > 0 ? fund.current_nav.toFixed(4) : '-') : '****' }}
                </td>
                <td :class="colorClass(fund.change_pct)">
                  {{ formatPercent(fund.change_pct) }}
                </td>
                <td>
                  <span class="nav-status-badge" :class="fund.is_updated ? 'updated' : 'estimating'" :title="fund.is_updated ? '官方净值已更新' : '盘中估值数据'">
                    {{ fund.is_updated ? '🟢 官方净值' : '⚡ 实时估值' }}
                  </span>
                </td>
                <td>{{ showAmount ? fund.shares : '****' }}</td>
                <td>{{ showAmount ? fund.cost_nav?.toFixed(4) : '****' }}</td>
                <td :class="colorClass(fund.day_profit)">
                  {{ showAmount ? formatMoney(fund.day_profit) : '****' }}
                </td>
                <td :class="colorClass(fund.total_profit)">
                  {{ showAmount ? formatMoney(fund.total_profit) : '****' }}
                </td>
                <td :class="colorClass(fund.total_profit_pct)">
                  {{ formatPercent(fund.total_profit_pct) }}
                </td>
                <td class="time-cell">{{ fund.update_time || '-' }}</td>
              </tr>
              <tr v-if="!sortedFunds.length">
                <td colspan="12" class="empty-row">暂无基金数据，请前往「基金管理」添加</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="last-updated">
        最后更新：{{ marketData.summary.last_update || '-' }}
        <span v-if="autoRefreshCountdown > 0" class="countdown">（{{ autoRefreshCountdown }}s 后自动刷新）</span>
      </div>
    </template>

    <div v-else class="loading-state">
      <p>暂无数据</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, inject, nextTick, markRaw } from 'vue'
import * as echarts from 'echarts'
import api from '../api'

const showToast = inject('showToast')
const marketData = ref(null)
const loading = ref(false)
const autoRefreshCountdown = ref(0)
let refreshInterval = null
let countdownInterval = null

// History Chart State
const historyDays = ref(7)
const chartViewType = ref('total')
const chartRef = ref(null)
const currentHistoryData = ref([])
let chartInstance = null

const changeChartViewType = (type) => {
  chartViewType.value = type
  if (currentHistoryData.value && currentHistoryData.value.length > 0) {
    renderChart(currentHistoryData.value)
  }
}

const fetchHistoryAndRender = async (days) => {
  historyDays.value = days
  try {
    const data = await api.getMarketHistory(days)
    if (data && data.length > 0) {
      currentHistoryData.value = data
      renderChart(data)
    } else {
      currentHistoryData.value = []
      renderChart([])
    }
  } catch (err) {
    console.error('Failed to load history', err)
  }
}

// 动态紧凑区间计算函数：彻底告别0值死板刻度，让每一分波动铺满图表
const getTightMinMax = (values, padRatio = 0.08) => {
  const nums = values.filter(v => typeof v === 'number' && !isNaN(v))
  if (!nums.length) return { min: 0, max: 100 }
  const min = Math.min(...nums)
  const max = Math.max(...nums)
  const diff = max - min
  if (diff === 0) {
    const pad = Math.abs(min) * 0.05 || 100
    return { min: Math.floor(min - pad), max: Math.ceil(max + pad) }
  }
  const pad = diff * padRatio
  return {
    min: Math.floor(min - pad),
    max: Math.ceil(max + pad)
  }
}

const formatAxisLabel = (val) => {
  if (!showAmount.value) return '****'
  const abs = Math.abs(val)
  if (abs >= 10000) {
    const str = (val / 10000).toFixed(2).replace(/\.?0+$/, '')
    return str + '万'
  }
  return Number(val).toLocaleString()
}

const formatMarkPoint = (val) => {
  if (!showAmount.value) return '***'
  const abs = Math.abs(val)
  if (abs >= 10000) return (val / 10000).toFixed(1) + 'w'
  return Math.round(val).toLocaleString()
}

const renderChart = (data) => {
  if (!chartRef.value) return
  if (!chartInstance) {
    chartInstance = markRaw(echarts.init(chartRef.value))
    window.addEventListener('resize', () => chartInstance?.resize())
  }
  
  if (!data || data.length === 0) {
    chartInstance.clear()
    return
  }

  const dates = data.map(item => item.date)
  const totalProfits = data.map(item => item.total_profit)
  const stockProfits = data.map(item => item.stock_profit)
  const fundProfits = data.map(item => item.fund_profit)
  
  const baseTooltip = {
    trigger: 'axis',
    backgroundColor: 'rgba(22, 27, 34, 0.95)',
    borderColor: 'rgba(255, 255, 255, 0.15)',
    borderWidth: 1,
    textStyle: { color: '#f0f6fc' },
    padding: [10, 14],
    extraCssText: 'box-shadow: 0 8px 24px rgba(0,0,0,0.5); backdrop-filter: blur(12px); border-radius: 8px;',
    formatter: (params) => {
      if (!params || !params.length) return ''
      let res = `<div style="font-weight:600; margin-bottom:6px; color:#94a3b8; font-size:12px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:4px;">📅 ${params[0].axisValue}</div>`
      params.forEach(item => {
        const val = item.value
        const valStr = showAmount.value
          ? (val != null ? (val >= 0 ? '+' : '') + Number(val).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' 元' : '-')
          : '**** 元'
        const color = val > 0 ? '#ff4d4f' : val < 0 ? '#00e676' : '#cbd5e1'
        res += `
          <div style="display:flex; align-items:center; justify-content:space-between; gap:16px; font-size:12px; margin-top:4px;">
            <span style="display:flex; align-items:center; gap:6px;">
              <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${item.color};"></span>
              <span style="color:#e2e8f0;">${item.seriesName}</span>
            </span>
            <span style="font-weight:600; color:${color}; font-family:monospace;">${valStr}</span>
          </div>`
      })
      return res
    }
  }

  let option = {}

  if (chartViewType.value === 'total') {
    const bounds = getTightMinMax(totalProfits, 0.08)
    option = {
      tooltip: baseTooltip,
      grid: { left: '2%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { color: '#94a3b8', fontSize: 11 },
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
      },
      yAxis: {
        type: 'value',
        scale: true,
        min: bounds.min,
        max: bounds.max,
        splitNumber: 5,
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)', type: 'dashed' } },
        axisLabel: { color: '#94a3b8', fontSize: 11, formatter: formatAxisLabel }
      },
      series: [
        {
          name: '总收益',
          type: 'line',
          smooth: 0.35,
          showSymbol: true,
          symbol: 'circle',
          symbolSize: 7,
          data: totalProfits,
          itemStyle: { color: '#00d2ff' },
          lineStyle: { width: 3, shadowColor: 'rgba(0, 210, 255, 0.4)', shadowBlur: 8 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(0, 210, 255, 0.28)' },
              { offset: 1, color: 'rgba(0, 210, 255, 0.01)' }
            ])
          },
          markPoint: {
            data: [
              { type: 'max', name: '最高', symbolSize: 46, itemStyle: { color: 'rgba(255, 77, 79, 0.9)' } },
              { type: 'min', name: '最低', symbolSize: 46, itemStyle: { color: 'rgba(0, 230, 118, 0.9)' } }
            ],
            label: { color: '#fff', fontSize: 10, formatter: (p) => formatMarkPoint(p.value) }
          }
        }
      ]
    }
  } else if (chartViewType.value === 'fund') {
    const bounds = getTightMinMax(fundProfits, 0.08)
    option = {
      tooltip: baseTooltip,
      grid: { left: '2%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { color: '#94a3b8', fontSize: 11 },
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
      },
      yAxis: {
        type: 'value',
        scale: true,
        min: bounds.min,
        max: bounds.max,
        splitNumber: 5,
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)', type: 'dashed' } },
        axisLabel: { color: '#94a3b8', fontSize: 11, formatter: formatAxisLabel }
      },
      series: [
        {
          name: '基金收益',
          type: 'line',
          smooth: 0.35,
          showSymbol: true,
          symbol: 'circle',
          symbolSize: 7,
          data: fundProfits,
          itemStyle: { color: '#00e676' },
          lineStyle: { width: 3, shadowColor: 'rgba(0, 230, 118, 0.4)', shadowBlur: 8 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(0, 230, 118, 0.25)' },
              { offset: 1, color: 'rgba(0, 230, 118, 0.01)' }
            ])
          },
          markPoint: {
            data: [
              { type: 'max', name: '最高', symbolSize: 46, itemStyle: { color: 'rgba(255, 77, 79, 0.9)' } },
              { type: 'min', name: '最低', symbolSize: 46, itemStyle: { color: 'rgba(0, 230, 118, 0.9)' } }
            ],
            label: { color: '#fff', fontSize: 10, formatter: (p) => formatMarkPoint(p.value) }
          }
        }
      ]
    }
  } else if (chartViewType.value === 'stock') {
    const bounds = getTightMinMax(stockProfits, 0.08)
    option = {
      tooltip: baseTooltip,
      grid: { left: '2%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { color: '#94a3b8', fontSize: 11 },
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
      },
      yAxis: {
        type: 'value',
        scale: true,
        min: bounds.min,
        max: bounds.max,
        splitNumber: 5,
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)', type: 'dashed' } },
        axisLabel: { color: '#94a3b8', fontSize: 11, formatter: formatAxisLabel }
      },
      series: [
        {
          name: '股票收益',
          type: 'line',
          smooth: 0.35,
          showSymbol: true,
          symbol: 'circle',
          symbolSize: 7,
          data: stockProfits,
          itemStyle: { color: '#ff4d4f' },
          lineStyle: { width: 3, shadowColor: 'rgba(255, 77, 79, 0.4)', shadowBlur: 8 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(255, 77, 79, 0.25)' },
              { offset: 1, color: 'rgba(255, 77, 79, 0.01)' }
            ])
          },
          markPoint: {
            data: [
              { type: 'max', name: '最高', symbolSize: 46, itemStyle: { color: 'rgba(255, 77, 79, 0.9)' } },
              { type: 'min', name: '最低', symbolSize: 46, itemStyle: { color: 'rgba(0, 230, 118, 0.9)' } }
            ],
            label: { color: '#fff', fontSize: 10, formatter: (p) => formatMarkPoint(p.value) }
          }
        }
      ]
    }
  } else {
    // 'all': 双 Y 轴模式，总/基金走左轴，股票走右轴，两边独立缩放放大波动！
    const leftBounds = getTightMinMax([...totalProfits, ...fundProfits], 0.08)
    const rightBounds = getTightMinMax(stockProfits, 0.08)
    option = {
      tooltip: baseTooltip,
      legend: {
        data: ['总收益', '基金收益', '股票收益(右轴)'],
        textStyle: { color: '#cbd5e1', fontSize: 12 },
        top: '0%',
        itemGap: 16
      },
      grid: { left: '2%', right: '3%', bottom: '3%', top: '16%', containLabel: true },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { color: '#94a3b8', fontSize: 11 },
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
      },
      yAxis: [
        {
          type: 'value',
          scale: true,
          min: leftBounds.min,
          max: leftBounds.max,
          splitNumber: 5,
          splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)', type: 'dashed' } },
          axisLabel: { color: '#00d2ff', fontSize: 11, formatter: formatAxisLabel }
        },
        {
          type: 'value',
          scale: true,
          min: rightBounds.min,
          max: rightBounds.max,
          splitNumber: 5,
          splitLine: { show: false },
          axisLabel: { color: '#ff7875', fontSize: 11, formatter: formatAxisLabel }
        }
      ],
      series: [
        {
          name: '总收益',
          type: 'line',
          yAxisIndex: 0,
          smooth: 0.35,
          showSymbol: true,
          symbol: 'circle',
          symbolSize: 6,
          data: totalProfits,
          itemStyle: { color: '#00d2ff' },
          lineStyle: { width: 2.5, shadowColor: 'rgba(0, 210, 255, 0.3)', shadowBlur: 6 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(0, 210, 255, 0.18)' },
              { offset: 1, color: 'rgba(0, 210, 255, 0.00)' }
            ])
          }
        },
        {
          name: '基金收益',
          type: 'line',
          yAxisIndex: 0,
          smooth: 0.35,
          showSymbol: true,
          symbol: 'circle',
          symbolSize: 5,
          data: fundProfits,
          itemStyle: { color: '#00e676' },
          lineStyle: { width: 2, shadowColor: 'rgba(0, 230, 118, 0.3)', shadowBlur: 6 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(0, 230, 118, 0.12)' },
              { offset: 1, color: 'rgba(0, 230, 118, 0.00)' }
            ])
          }
        },
        {
          name: '股票收益(右轴)',
          type: 'line',
          yAxisIndex: 1,
          smooth: 0.35,
          showSymbol: true,
          symbol: 'circle',
          symbolSize: 5,
          data: stockProfits,
          itemStyle: { color: '#ff4d4f' },
          lineStyle: { width: 2, shadowColor: 'rgba(255, 77, 79, 0.3)', shadowBlur: 6 }
        }
      ]
    }
  }

  chartInstance.setOption(option, true)
}

// 金额隐藏小眼睛开关状态
const showAmount = ref(localStorage.getItem('stock_monitor_show_amount') !== 'false')

const toggleShowAmount = () => {
  showAmount.value = !showAmount.value
  localStorage.setItem('stock_monitor_show_amount', showAmount.value)
  if (currentHistoryData.value) {
    renderChart(currentHistoryData.value)
  }
}

// 大盘核心指数状态与计算
const showAllIndices = ref(false)
const marketIndices = computed(() => marketData.value?.indices || [])
const displayIndices = computed(() => {
  if (showAllIndices.value) return marketIndices.value
  return marketIndices.value.slice(0, 4)
})

const totalMarketTurnover = computed(() => {
  const indices = marketIndices.value
  if (!indices || !indices.length) return null
  const sh = indices.find(i => i.code === 'sh000001')?.amount || 0
  const sz = indices.find(i => i.code === 'sz399001')?.amount || 0
  const bj = indices.find(i => i.code === 'bj899050')?.amount || 0
  const total = sh + sz + bj
  if (total <= 0) return null
  if (total >= 100000000) {
    return (total / 100000000).toFixed(2) + ' 亿元'
  }
  return (total / 10000).toFixed(2) + ' 万元'
})

const getIndexRangePercent = (idx) => {
  if (!idx || !idx.high || !idx.low || idx.high === idx.low) return 50
  const pct = ((idx.current - idx.low) / (idx.high - idx.low)) * 100
  return Math.max(0, Math.min(100, pct))
}

const getIndexChangeClass = (pct) => {
  if (pct == null || pct === 0) return 'index-flat'
  return pct > 0 ? 'index-up' : 'index-down'
}

const formatIndexChange = (pct) => {
  if (pct == null) return '0.00'
  const num = Number(pct)
  return (num >= 0 ? '+' : '') + num.toFixed(2)
}

// 排序状态
const stockSortKey = ref('default')
const stockSortOrder = ref('desc')

const fundSortKey = ref('default')
const fundSortOrder = ref('desc')

const displayStocks = computed(() => marketData.value?.stocks || [])
const displayFunds = computed(() => marketData.value?.funds || [])

// 持仓计算
const activeHoldingsCount = computed(() => {
  const hStocks = displayStocks.value.filter(s => s.is_holding).length
  const hFunds = displayFunds.value.filter(f => f.is_holding).length
  return hStocks + hFunds
})

const stockDayProfit = computed(() => {
  if (!marketData.value) return 0
  if (marketData.value.summary && marketData.value.summary.stock_day_profit !== undefined) {
    return marketData.value.summary.stock_day_profit
  }
  return displayStocks.value
    .filter(s => s.is_holding)
    .reduce((acc, s) => acc + (s.day_profit || 0), 0)
})

const fundDayProfit = computed(() => {
  if (!marketData.value) return 0
  if (marketData.value.summary && marketData.value.summary.fund_day_profit !== undefined) {
    return marketData.value.summary.fund_day_profit
  }
  return displayFunds.value
    .filter(f => f.is_holding)
    .reduce((acc, f) => acc + (f.day_profit || 0), 0)
})

// 股票动态排序
const sortedStocks = computed(() => {
  const list = [...displayStocks.value]
  if (stockSortKey.value === 'default') return list

  return list.sort((a, b) => {
    let valA = a[stockSortKey.value] ?? 0
    let valB = b[stockSortKey.value] ?? 0
    if (valA < valB) return stockSortOrder.value === 'asc' ? -1 : 1
    if (valA > valB) return stockSortOrder.value === 'asc' ? 1 : -1
    return 0
  })
})

// 基金动态排序
const sortedFunds = computed(() => {
  const list = [...displayFunds.value]
  if (fundSortKey.value === 'default') return list

  return list.sort((a, b) => {
    let valA = a[fundSortKey.value] ?? 0
    let valB = b[fundSortKey.value] ?? 0
    if (valA < valB) return fundSortOrder.value === 'asc' ? -1 : 1
    if (valA > valB) return fundSortOrder.value === 'asc' ? 1 : -1
    return 0
  })
})

const changeStockSort = (key) => {
  if (stockSortKey.value === key) {
    stockSortOrder.value = stockSortOrder.value === 'desc' ? 'asc' : 'desc'
  } else {
    stockSortKey.value = key
    stockSortOrder.value = 'desc'
  }
}

const changeFundSort = (key) => {
  if (fundSortKey.value === key) {
    fundSortOrder.value = fundSortOrder.value === 'desc' ? 'asc' : 'desc'
  } else {
    fundSortKey.value = key
    fundSortOrder.value = 'desc'
  }
}

const getSortIcon = (type, key) => {
  const currentKey = type === 'stock' ? stockSortKey.value : fundSortKey.value
  const currentOrder = type === 'stock' ? stockSortOrder.value : fundSortOrder.value
  if (currentKey !== key) return '↕'
  return currentOrder === 'desc' ? '▼' : '▲'
}

const marketStatusClass = computed(() => {
  const status = marketData.value?.summary?.market_status || ''
  if (status === '交易中') return 'status-open'
  if (status === '已收盘') return 'status-closed'
  if (status === '午间休市') return 'status-noon'
  return 'status-inactive'
})

// 中国股市：红色=涨，绿色=跌
const colorClass = (val) => {
  if (val == null || val === 0) return ''
  return val > 0 ? 'text-red' : 'text-green'
}

const formatMoney = (val) => {
  if (val == null) return '-'
  const num = Number(val)
  return (num >= 0 ? '+' : '') + num.toFixed(2)
}

const formatMoneyNoSign = (val) => {
  if (val == null) return '-'
  const num = Number(val)
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatPercent = (val) => {
  if (val == null) return '-'
  const num = Number(val)
  return (num >= 0 ? '+' : '') + num.toFixed(2) + '%'
}

const fetchData = async () => {
  try {
    marketData.value = await api.getMarketOverview()
  } catch (err) {
    console.error(err)
    showToast('行情数据加载失败，请检查网络')
  }
}

const refreshData = async () => {
  loading.value = true
  try {
    marketData.value = await api.refreshMarket()
    showToast('✅ 数据已刷新')
  } catch (err) {
    console.error(err)
    showToast('❌ 刷新失败')
  } finally {
    loading.value = false
  }
}

const startAutoRefresh = () => {
  // Refresh every 30s during market hours
  refreshInterval = setInterval(() => {
    const status = marketData.value?.summary?.market_status || ''
    if (status === '交易中') {
      fetchData()
      autoRefreshCountdown.value = 30
    }
  }, 30000)

  // Countdown timer
  countdownInterval = setInterval(() => {
    const status = marketData.value?.summary?.market_status || ''
    if (status === '交易中' && autoRefreshCountdown.value > 0) {
      autoRefreshCountdown.value--
    } else if (status === '交易中') {
      autoRefreshCountdown.value = 30
    } else {
      autoRefreshCountdown.value = 0
    }
  }, 1000)
}

onMounted(async () => {
  loading.value = true
  await fetchData()
  loading.value = false
  nextTick(() => {
    fetchHistoryAndRender(historyDays.value)
  })
  startAutoRefresh()
  if (marketData.value?.summary?.market_status === '交易中') {
    autoRefreshCountdown.value = 30
  }
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
  if (countdownInterval) clearInterval(countdownInterval)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.history-chart-container {
  padding: 24px;
}

.chart-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.btn-group-pill {
  display: inline-flex;
  gap: 4px;
  background: rgba(255, 255, 255, 0.04);
  padding: 3px;
  border-radius: 12px;
  border: 1px solid var(--border-glass);
}

.btn-group-pill .btn {
  padding: 4px 12px;
  font-size: 0.82rem;
  border-radius: 9px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.btn-group-pill .btn:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.06);
}

.btn-group-pill .btn.active {
  background: rgba(0, 212, 255, 0.22);
  color: var(--accent-primary);
  font-weight: 600;
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.2);
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 4px;
  background: linear-gradient(135deg, var(--text-primary), var(--accent-primary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.eye-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 0.9rem;
}

.market-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  border-radius: 20px;
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  font-size: 0.9rem;
  font-weight: 500;
  backdrop-filter: blur(10px);
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-secondary);
  flex-shrink: 0;
}

.status-open .pulse-dot {
  background: var(--red);
  box-shadow: 0 0 10px var(--red);
  animation: pulse 2s infinite;
}
.status-closed .pulse-dot { background: var(--yellow); }
.status-noon .pulse-dot { background: var(--yellow); }
.status-inactive .pulse-dot { background: var(--text-secondary); }

@keyframes pulse {
  0%   { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 68, 68, 0.7); }
  70%  { transform: scale(1);    box-shadow: 0 0 0 6px rgba(255, 68, 68, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 68, 68, 0); }
}

.rotating { display: inline-block; animation: rotate 1s linear infinite; }
@keyframes rotate { 100% { transform: rotate(360deg); } }

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
  margin-bottom: 36px;
  position: relative;
  z-index: 100;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 24px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.summary-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(0, 212, 255, 0.15);
}

.asset-card-wrapper {
  position: relative;
  cursor: pointer;
  z-index: 20;
}

.asset-card-wrapper:hover {
  z-index: 999;
}

.card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-secondary);
  font-size: 0.85rem;
  letter-spacing: 0.5px;
}

.info-icon {
  font-size: 0.85rem;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.asset-card-wrapper:hover .info-icon {
  opacity: 1;
}

.asset-tooltip {
  position: absolute;
  top: 100%;
  left: 0;
  transform: translateY(8px);
  width: 300px;
  background: rgba(22, 28, 45, 0.98);
  border: 1px solid rgba(0, 212, 255, 0.4);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 14px;
  padding: 16px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8), 0 0 30px rgba(0, 212, 255, 0.25);
  z-index: 9999;
  opacity: 0;
  visibility: hidden;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
}

.asset-card-wrapper:hover .asset-tooltip {
  opacity: 1;
  visibility: visible;
  transform: translateY(4px);
}

.tooltip-header {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.tooltip-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
  margin: 8px 0;
}

.tooltip-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.item-title {
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.item-value {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text-primary);
}

.item-sub {
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.sub-profit {
  margin-left: 4px;
  font-size: 0.75rem;
}

.total-item {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
}

.nav-status-badge {
  padding: 3px 8px;
  border-radius: 10px;
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
}
.nav-status-badge.updated {
  background: rgba(0, 255, 136, 0.12);
  color: #00ff88;
  border: 1px solid rgba(0, 255, 136, 0.3);
}
.nav-status-badge.estimating {
  background: rgba(255, 170, 0, 0.12);
  color: #ffaa00;
  border: 1px solid rgba(255, 170, 0, 0.3);
}

.card-icon { font-size: 1.5rem; }

.card-title {
  color: var(--text-secondary);
  font-size: 0.85rem;
  letter-spacing: 0.5px;
}

.card-value {
  font-size: 1.8rem;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.text-accent { color: var(--accent-primary); }

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-header h3 { font-size: 1.1rem; font-weight: 600; }

.sort-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sort-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.sort-select {
  padding: 4px 10px;
  font-size: 0.85rem;
  width: auto;
}

.sort-order-btn {
  padding: 4px 10px;
  font-size: 0.82rem;
}

.sortable {
  cursor: pointer;
  user-select: none;
}

.sortable:hover {
  color: var(--accent-primary);
}

.sort-icon {
  font-size: 0.75rem;
  margin-left: 2px;
  opacity: 0.8;
}

.status-badge {
  padding: 3px 8px;
  border-radius: 10px;
  font-size: 0.75rem;
  font-weight: 500;
}
.status-badge.active {
  background: rgba(0, 255, 136, 0.15);
  color: var(--green);
  border: 1px solid rgba(0, 255, 136, 0.3);
}
.status-badge.inactive {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-secondary);
  border: 1px solid var(--border-glass);
}

.badge {
  background: rgba(0, 212, 255, 0.15);
  color: var(--accent-primary);
  border: 1px solid rgba(0, 212, 255, 0.3);
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
}

.mb-4 { margin-bottom: 32px; }

.table-row { transition: background 0.15s; }
.table-row:hover { background: rgba(255,255,255,0.03); }

.code-cell  { font-family: monospace; font-weight: 600; color: var(--accent-primary); }
.name-cell  { font-weight: 500; }
.price-cell { font-weight: 600; font-size: 1.05rem; }
.time-cell  { font-size: 0.8rem; color: var(--text-secondary); }

.empty-row {
  text-align: center;
  color: var(--text-secondary);
  padding: 32px !important;
  font-style: italic;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: 16px;
  color: var(--text-secondary);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-glass);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: rotate 1s linear infinite;
}

.last-updated {
  margin-top: 20px;
  text-align: right;
  font-size: 0.82rem;
  color: var(--text-secondary);
}

.countdown { margin-left: 8px; color: var(--accent-primary); }

/* Market Indices Section */
.indices-section {
  padding: 20px 24px;
}

.market-turnover-tag {
  font-size: 0.82rem;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.05);
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-glass);
}
.market-turnover-tag strong {
  color: var(--accent-primary);
  font-weight: 600;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 0.82rem;
}

.indices-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.index-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
}

.index-card:hover {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.06);
}

.index-card.index-up {
  border-left: 3px solid var(--red);
}
.index-card.index-up:hover {
  box-shadow: 0 6px 20px rgba(255, 68, 68, 0.15);
}

.index-card.index-down {
  border-left: 3px solid var(--green);
}
.index-card.index-down:hover {
  box-shadow: 0 6px 20px rgba(0, 255, 136, 0.15);
}

.index-card.index-flat {
  border-left: 3px solid var(--text-secondary);
}

.index-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.index-name-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.index-name {
  font-weight: 600;
  font-size: 0.96rem;
  color: var(--text-primary);
}

.index-symbol {
  font-size: 0.72rem;
  color: var(--text-secondary);
  font-family: monospace;
  background: rgba(255, 255, 255, 0.06);
  padding: 1px 5px;
  border-radius: 4px;
}

.index-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 8px;
  white-space: nowrap;
}

.index-badge.badge-up {
  background: rgba(255, 68, 68, 0.15);
  color: var(--red);
  border: 1px solid rgba(255, 68, 68, 0.3);
}

.index-badge.badge-down {
  background: rgba(0, 255, 136, 0.15);
  color: var(--green);
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.index-points {
  font-size: 1.55rem;
  font-weight: 700;
  font-family: monospace;
  letter-spacing: -0.5px;
  margin-top: -2px;
}

.index-change-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.82rem;
}

.index-change-amount {
  font-weight: 600;
  font-family: monospace;
}

.index-turnover {
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.index-range-bar-wrap {
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.range-labels {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.72rem;
  color: var(--text-secondary);
}

.amplitude-label {
  color: var(--accent-primary);
  opacity: 0.85;
}

.range-track {
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  position: relative;
  overflow: visible;
}

.range-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.fill-up {
  background: linear-gradient(90deg, rgba(255, 68, 68, 0.3), var(--red));
}

.fill-down {
  background: linear-gradient(90deg, rgba(0, 255, 136, 0.3), var(--green));
}

.range-marker {
  position: absolute;
  top: -3px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 0 6px rgba(255, 255, 255, 0.8);
  transform: translateX(-50%);
  pointer-events: none;
}
</style>
