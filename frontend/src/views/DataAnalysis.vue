<template>
  <div class="data-analysis-page">
    <!-- 顶部状态栏与操作栏 -->
    <header class="page-header">
      <div class="header-left">
        <div class="title-row">
          <h2 class="page-title">📊 数据分析</h2>
          <!-- 市场状态与数据标签 -->
          <span class="status-badge" :class="statusClass">
            <span class="pulse-dot" :class="pulseClass"></span>
            {{ statusLabel }}
          </span>
          <span v-if="overview.data_label === 'yesterday'" class="yesterday-badge">
            📅 昨日数据
          </span>
          <span v-else-if="overview.data_label === 'realtime'" class="realtime-badge">
            ⚡ 盘中实时
          </span>
          <span v-else class="closed-badge">
            🔒 收盘结算
          </span>
        </div>
        <div class="meta-row">
          <span class="source-tag" :class="overview.provider_type">
            {{ overview.provider_type === 'mx' ? '💎 东方财富妙想' : '🌐 通用接口' }}
            <span v-if="overview.is_degraded" class="degraded-tag">(已降级)</span>
          </span>
          <span class="update-time">
            🕒 最后更新: {{ overview.last_updated || '未刷新' }}
          </span>
          <span class="schedule-tip">
            ⏰ 每日 09:15 / 20:30 主动刷新
          </span>
        </div>
      </div>

      <div class="header-right">
        <button 
          class="btn btn-primary refresh-btn" 
          @click="handleManualRefresh" 
          :disabled="refreshing"
        >
          <span class="refresh-icon" :class="{ rotating: refreshing }">🔄</span>
          <span>{{ refreshing ? '正在刷新...' : '手动刷新' }}</span>
        </button>
      </div>
    </header>

    <!-- 1. 全市场大盘成交量概览 -->
    <section class="section-block">
      <div class="section-header">
        <h3 class="section-title">
          <span class="title-icon">📈</span>
          <span>各大盘成交量与点位</span>
        </h3>
        <span class="section-hint">固定全量呈现 6 大核心指数</span>
      </div>

      <div class="indices-grid">
        <div 
          v-for="idx in overview.indices" 
          :key="idx.code"
          class="glass-card index-card"
          :class="idx.change_pct > 0 ? 'rise' : (idx.change_pct < 0 ? 'fall' : 'flat')"
        >
          <div class="index-top">
            <span class="index-name">{{ idx.name }}</span>
            <span class="index-code">{{ idx.code }}</span>
          </div>
          <div class="index-price-row">
            <span class="index-current">{{ idx.current?.toFixed(2) }}</span>
            <span class="index-change">
              {{ idx.change_pct > 0 ? '+' : '' }}{{ idx.change_pct?.toFixed(2) }}%
            </span>
          </div>
          <div class="index-data-grid">
            <div class="data-item">
              <span class="item-label">成交量</span>
              <span class="item-value">{{ idx.volume_formatted }}</span>
            </div>
            <div class="data-item">
              <span class="item-label">成交额</span>
              <span class="item-value">{{ idx.amount_formatted }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 2. 全市场机构 / 主力 / 散户 净成交量 -->
    <section class="section-block">
      <div class="section-header">
        <h3 class="section-title">
          <span class="title-icon">🌊</span>
          <span>全市场资金流向 (机构 / 主力 / 散户)</span>
        </h3>
        <span class="section-hint">红涨流入 / 绿跌流出</span>
      </div>

      <div class="glass-card flow-summary-card">
        <div v-if="!overview.fund_flow?.available" class="unavailable-notice">
          <span class="notice-icon">ℹ️</span>
          <span>{{ overview.fund_flow?.message || '当前数据源暂无法提供全市场资金流向' }}</span>
        </div>

        <div v-else class="flow-metrics-grid">
          <!-- 机构净流入 -->
          <div class="metric-card" :class="getFlowClass(overview.fund_flow.institution_net_inflow)">
            <div class="metric-header">
              <span class="metric-icon">🏛️</span>
              <span class="metric-title">机构净成交额</span>
            </div>
            <div class="metric-value">
              {{ overview.fund_flow.institution_net_inflow_formatted }}
            </div>
            <div class="metric-desc">超大单机构级资金净博弈</div>
          </div>

          <!-- 主力净流入 -->
          <div class="metric-card" :class="getFlowClass(overview.fund_flow.main_net_inflow)">
            <div class="metric-header">
              <span class="metric-icon">🚀</span>
              <span class="metric-title">主力净成交额</span>
            </div>
            <div class="metric-value">
              {{ overview.fund_flow.main_net_inflow_formatted }}
            </div>
            <div class="metric-desc">超大单 + 大单合计买卖净额</div>
          </div>

          <!-- 散户净流入 -->
          <div class="metric-card" :class="getFlowClass(overview.fund_flow.retail_net_inflow)">
            <div class="metric-header">
              <span class="metric-icon">👥</span>
              <span class="metric-title">散户净成交额</span>
            </div>
            <div class="metric-value">
              {{ overview.fund_flow.retail_net_inflow_formatted }}
            </div>
            <div class="metric-desc">中小单散户资金买卖净额</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 3. 个股与基金 深度数据 (成交量、散户/主力/机构净成交量) -->
    <section class="section-block">
      <div class="section-header wrap-header">
        <div>
          <h3 class="section-title">
            <span class="title-icon">🎯</span>
            <span>个股与基金监控面板</span>
          </h3>
          <span class="section-hint">
            最多展示 {{ statusConfig.max_panels || 6 }} 个面板 · 基金支持依据重仓成分股加权穿透测算
          </span>
        </div>

        <!-- 筛选与下拉框快速选择 -->
        <div class="filter-controls">
          <!-- 分类过滤 Tab（修复：点击即时切换展示对应类型的面板卡片） -->
          <div class="pill-tabs">
            <button 
              class="pill-btn" 
              :class="{ active: activeHoldingFilter === 'all' }" 
              @click="activeHoldingFilter = 'all'"
            >
              全部 ({{ displayedHoldingsAnalysis.length }})
            </button>
            <button 
              class="pill-btn" 
              :class="{ active: activeHoldingFilter === 'stock' }" 
              @click="activeHoldingFilter = 'stock'"
            >
              股票 ({{ displayedStockCount }})
            </button>
            <button 
              class="pill-btn" 
              :class="{ active: activeHoldingFilter === 'fund' }" 
              @click="activeHoldingFilter = 'fund'"
            >
              基金 ({{ displayedFundCount }})
            </button>
          </div>

          <!-- 下拉选择器切换关注标的 -->
          <div class="select-wrapper">
            <select v-model="selectedCodeToAdd" @change="handleSelectHoldingToAdd" class="holding-select">
              <option value="" disabled>➕ 下拉选择更多标的添加到面板...</option>
              <option 
                v-for="h in filteredHoldingsForSelect" 
                :key="h.code" 
                :value="h.code"
              >
                {{ h.type === 'stock' ? '📈' : '💰' }} {{ h.name }} ({{ h.code }})
              </option>
            </select>
          </div>
        </div>
      </div>

      <!-- 面板卡片网格 -->
      <div v-if="loadingHoldings && !displayedHoldingsAnalysis.length" class="glass-card loading-box">
        <span class="spinner">⏳</span>
        <span>正在加载持仓标的资金分析数据...</span>
      </div>

      <div v-else-if="!filteredDisplayedHoldings.length" class="glass-card empty-box">
        <span>当前分类下暂无展示的标的面板，可在上方下拉框添加关注标的。</span>
      </div>

      <div v-else class="holdings-grid">
        <div 
          v-for="item in filteredDisplayedHoldings" 
          :key="item.code" 
          class="glass-card holding-card"
          :class="item.change_pct > 0 ? 'rise' : (item.change_pct < 0 ? 'fall' : 'flat')"
        >
          <div class="holding-card-header">
            <div class="holding-title-wrap">
              <span class="type-badge" :class="item.type">
                {{ item.type === 'stock' ? '股票' : '基金' }}
              </span>
              <strong class="holding-name">{{ item.name }}</strong>
              <span class="holding-code">{{ item.code }}</span>
            </div>
            <button class="remove-card-btn" @click="removeHoldingFromDisplay(item.code)" title="从面板移除">
              ✕
            </button>
          </div>

          <div class="holding-price-wrap">
            <div class="main-price">
              <span class="price-val">
                {{ item.current ? item.current.toFixed(item.type === 'fund' ? 4 : 2) : '-' }}
              </span>
              <span class="price-chg">
                {{ item.change_pct > 0 ? '+' : '' }}{{ item.change_pct?.toFixed(2) }}%
              </span>
              <span v-if="item.type === 'fund'" class="nav-tag">
                {{ item.nav_type || '官方净值' }}
              </span>
            </div>
            <div class="volume-stat">
              <span>成交: {{ item.volume_formatted || (item.type === 'fund' ? '场外申赎' : '0') }}</span>
              <span>金额: {{ item.amount_formatted || (item.type === 'fund' ? '净值结算' : '0') }}</span>
            </div>
          </div>

          <!-- 成分股计算标记提示 -->
          <div v-if="item.calc_from_components" class="calc-component-tag">
            <span class="calc-icon">🔬</span>
            <span>依据前 {{ item.components_count || 10 }} 大重仓成分股加权穿透测算</span>
          </div>

          <!-- 资金流向三维条 (机构 / 主力 / 散户) -->
          <div class="holding-flow-list">
            <div class="flow-row">
              <span class="flow-name">机构净流入</span>
              <span class="flow-val" :class="getFlowClass(item.institution_net_inflow)">
                {{ item.institution_net_inflow_formatted }}
              </span>
            </div>
            <div class="flow-row">
              <span class="flow-name">主力净流入</span>
              <span class="flow-val" :class="getFlowClass(item.main_net_inflow)">
                {{ item.main_net_inflow_formatted }}
              </span>
            </div>
            <div class="flow-row">
              <span class="flow-name">散户净流入</span>
              <span class="flow-val" :class="getFlowClass(item.retail_net_inflow)">
                {{ item.retail_net_inflow_formatted }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 4. 板块资金流动拓扑与动效全景图 & 5. 申万行业板块轮动方向 -->
    <section class="section-block">
      <!-- 布局与全屏控制工具条 -->
      <div class="section-header wrap-header mb-3">
        <div>
          <h3 class="section-title">
            <span class="title-icon">🌌</span>
            <span>市场板块资金流动拓扑与轮动方向</span>
          </h3>
          <span class="section-hint">
            支持 8 大核心板块资金流向全景追踪 · 粒子动效飞线 · 纯净通栏大屏呈现
          </span>
        </div>
        <div class="layout-toggle-group">
          <button 
            class="layout-btn" 
            :class="{ active: chartLayoutMode === 'stacked' }" 
            @click="setLayoutMode('stacked')"
            title="通栏全景大屏模式，图表空间更大，超好点击"
          >
            ⛶ 通栏全景大图 (推荐)
          </button>
          <button 
            class="layout-btn" 
            :class="{ active: chartLayoutMode === 'split' }" 
            @click="setLayoutMode('split')"
            title="双栏并排紧凑模式"
          >
            ⚏ 左右双栏并排
          </button>
        </div>
      </div>

      <div :class="chartLayoutMode === 'split' ? 'grid-2col' : 'grid-stacked'">
        <!-- 板块资金流动图 (通栏全景模式下独占一整行，大幅扩展宽度与间距，圆球更大更好点击) -->
        <div class="glass-card chart-card" :class="{ 'is-fullwidth': chartLayoutMode === 'stacked' }">
          <div class="card-title-row">
            <div class="chart-tab-group">
              <button 
                class="chart-tab-btn" 
                :class="{ active: activeFlowChartTab === 'inflow' }"
                @click="switchChartTab('inflow')"
              >
                🔥 市场流入 Top 8 (动效飞线)
              </button>
              <button 
                class="chart-tab-btn" 
                :class="{ active: activeFlowChartTab === 'outflow' }"
                @click="switchChartTab('outflow')"
              >
                💧 市场流出 Top 8 (动效飞线)
              </button>
              <button 
                class="chart-tab-btn" 
                :class="{ active: activeFlowChartTab === 'sankey' }"
                @click="switchChartTab('sankey')"
              >
                🌊 资金分配桑基图
              </button>
            </div>
            <span class="badge-sub">
              {{ activeFlowChartTab === 'inflow' ? '市场流入 Top 8 主导 · 右侧为流入 Top 8 · 左侧为主要来源板块 · 动效流光' : (activeFlowChartTab === 'outflow' ? '市场流出 Top 8 主导 · 左侧为流出 Top 8 · 右侧为主要资金去向 · 动效流光' : '全市场资金来源与流向体量') }}
            </span>
          </div>

          <!-- 图表容器 (通栏大图高度 520px，左右两排节点间距充裕，点击非常轻松) -->
          <div class="chart-wrapper" :class="{ 'expanded-chart': chartLayoutMode === 'stacked' }">
            <div ref="flowChartRef" class="main-flow-chart"></div>
          </div>

          <!-- 动效图专属颜色与流向图例 -->
          <div v-if="activeFlowChartTab !== 'sankey'" class="flow-legend-bar">
            <!-- 单球聚焦高亮激活状态条 -->
            <div v-if="selectedSectorNode" class="focus-filter-pill">
              <span class="focus-icon">🎯</span>
              <span>已聚焦【{{ selectedSectorNode }}】: 仅显示其关联流向线</span>
              <button class="reset-focus-btn" @click.stop="clearNodeFocus" title="点击恢复显示全部连线">
                ✕ 恢复全景连线
              </button>
            </div>

            <!-- 常规图例展示 -->
            <template v-else>
              <div v-if="activeFlowChartTab === 'inflow'" class="legend-item">
                <span class="legend-dot deep-red"></span>
                <span>深红 (右侧): 市场流入 Top 8 目标</span>
              </div>
              <div v-else class="legend-item">
                <span class="legend-dot deep-green"></span>
                <span>深绿 (左侧): 市场流出 Top 8 源头</span>
              </div>
              <div class="legend-item">
                <span class="legend-arrow-anim">➔➔</span>
                <span>流光动画: 资金转移主路径 (每个板块最多4根线 · 球大小反映资金量)</span>
              </div>
              <div v-if="activeFlowChartTab === 'inflow'" class="legend-item">
                <span class="legend-dot deep-green"></span>
                <span>深绿 (左侧): 主要资金来源板块</span>
              </div>
              <div v-else class="legend-item">
                <span class="legend-dot deep-red"></span>
                <span>深红 (右侧): 资金承接去向目标板块</span>
              </div>
              <div class="legend-item">
                <span class="hint-click">💡 提示：点击任意圆球只显示该板块关联线，再次点击或点空白处恢复全景</span>
              </div>
            </template>
          </div>

          <!-- 动态对应的左/右侧板块极简摘要（点击任意胶囊标签也可直接聚焦/取消聚焦该板块关联连线） -->
          <div class="sankey-summary-row">
            <div class="top-list outflow-box">
              <span class="box-title">
                {{ activeFlowChartTab === 'inflow' ? '💧 左侧：主要资金来源板块:' : (activeFlowChartTab === 'outflow' ? '💧 左侧：市场流出 Top 8 板块:' : '💧 市场流出板块:') }}
              </span>
              <div class="pill-cloud">
                <span 
                  v-for="item in (activeFlowChartTab === 'inflow' ? (sectorFlowData.inflow_sources || sectorFlowData.top_outflows) : sectorFlowData.top_outflows)?.slice(0, 8)" 
                  :key="item.code" 
                  class="flow-pill fall clickable-pill"
                  :class="{ 'is-selected': selectedSectorNode === item.name }"
                  @click="toggleNodeFocus(item.name)"
                  :title="`点击聚焦【${item.name}】关联连线`"
                >
                  {{ item.name }} {{ item.main_net_inflow_formatted }}
                </span>
              </div>
            </div>
            <div class="top-list inflow-box">
              <span class="box-title">
                {{ activeFlowChartTab === 'inflow' ? '🔥 右侧：市场流入 Top 8 板块:' : (activeFlowChartTab === 'outflow' ? '🔥 右侧：资金承接去向板块:' : '🔥 市场流入 Top 8 板块:') }}
              </span>
              <div class="pill-cloud">
                <span 
                  v-for="item in (activeFlowChartTab === 'outflow' ? (sectorFlowData.outflow_targets || sectorFlowData.top_inflows) : sectorFlowData.top_inflows)?.slice(0, 8)" 
                  :key="item.code" 
                  class="flow-pill rise clickable-pill"
                  :class="{ 'is-selected': selectedSectorNode === item.name }"
                  @click="toggleNodeFocus(item.name)"
                  :title="`点击聚焦【${item.name}】关联连线`"
                >
                  {{ item.name }} {{ item.main_net_inflow_formatted }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 申万行业板块轮动方向 (在通栏模式下作为专属表格卡片，宽敞清晰) -->
        <div class="glass-card sector-card" :class="{ 'is-fullwidth': chartLayoutMode === 'stacked' }">
          <div class="card-title-row">
            <h4 class="card-title">
              <span class="title-icon">🧭</span>
              <span>申万行业板块轮动方向</span>
            </h4>
            <span class="badge-sub">按涨跌幅排名 · 全行业资金扫描</span>
          </div>

          <div class="sector-table-container">
            <table class="sector-table">
              <thead>
                <tr>
                  <th>行业板块</th>
                  <th>涨跌幅</th>
                  <th>主力净额</th>
                  <th>成交总额</th>
                  <th>轮动方向</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="sec in sectorRotationList" :key="sec.code">
                  <td class="sec-name font-bold">{{ sec.name }}</td>
                  <td :class="sec.change_pct > 0 ? 'rise' : (sec.change_pct < 0 ? 'fall' : 'flat')">
                    {{ sec.change_pct > 0 ? '+' : '' }}{{ sec.change_pct }}%
                  </td>
                  <td :class="getFlowClass(sec.main_net_inflow)">
                    {{ sec.main_net_inflow_formatted }}
                  </td>
                  <td class="text-secondary">{{ sec.amount_formatted }}</td>
                  <td>
                    <span class="trend-icon" :class="sec.trend">
                      {{ sec.trend === 'up' ? '🔥 领涨突破' : (sec.trend === 'down' ? '❄️ 承压走弱' : '⚖️ 蓄势震荡') }}
                    </span>
                  </td>
                </tr>
                <tr v-if="!sectorRotationList.length">
                  <td colspan="5" class="text-center text-secondary py-4">暂无板块轮动数据</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, inject } from 'vue'
import * as echarts from 'echarts'
import api from '../api'

const showToast = inject('showToast')

// 页面主要响应式数据
const refreshing = ref(false)
const loadingHoldings = ref(false)
const activeHoldingFilter = ref('all')
const activeFlowChartTab = ref('inflow') // 'inflow' (流入Top8动效飞线图), 'outflow' (流出Top8动效飞线图), 'sankey' (桑基图)
const chartLayoutMode = ref('stacked') // 'stacked' (通栏全景大屏模式，推荐), 'split' (左右双栏并排)
const selectedCodeToAdd = ref('')

const overview = reactive({
  indices: [],
  indices_available: true,
  fund_flow: null,
  market_status: 'closed',
  data_label: 'yesterday',
  provider_type: 'generic',
  is_degraded: false,
  last_updated: ''
})

const statusConfig = reactive({
  max_panels: 6,
  provider_type: 'generic'
})

const sectorRotationList = ref([])
const sectorFlowData = reactive({
  sankey: { nodes: [], links: [] },
  inflow_top8: { nodes: [], links: [], flow_lines: [] },
  outflow_top8: { nodes: [], links: [], flow_lines: [] },
  inter_sector: { nodes: [], links: [], flow_lines: [] },
  top_inflows: [],
  top_outflows: []
})

const holdingsList = ref([])
const displayedHoldingsAnalysis = ref([])
const manuallySelectedCodes = ref([])

// 本地持久化缓存键与交易时间判定
const STORAGE_KEY_HOLDINGS = 'lh_data_analysis_holdings_v2'
const STORAGE_KEY_OVERVIEW = 'lh_data_analysis_overview_v2'

const isMarketTradingTime = () => {
  const now = new Date()
  const day = now.getDay()
  if (day === 0 || day === 6) return false
  const hours = now.getHours()
  const mins = now.getMinutes()
  const timeNum = hours * 100 + mins
  return timeNum >= 915 && timeNum <= 1505
}

const loadCacheFromStorage = () => {
  try {
    const cachedHoldings = localStorage.getItem(STORAGE_KEY_HOLDINGS)
    if (cachedHoldings) {
      const parsed = JSON.parse(cachedHoldings)
      if (Array.isArray(parsed.displayedHoldingsAnalysis) && parsed.displayedHoldingsAnalysis.length > 0) {
        displayedHoldingsAnalysis.value = parsed.displayedHoldingsAnalysis
      }
      if (Array.isArray(parsed.holdingsList) && parsed.holdingsList.length > 0) {
        holdingsList.value = parsed.holdingsList
      }
      if (Array.isArray(parsed.manuallySelectedCodes) && parsed.manuallySelectedCodes.length > 0) {
        manuallySelectedCodes.value = parsed.manuallySelectedCodes
      }
    }
    const cachedOverview = localStorage.getItem(STORAGE_KEY_OVERVIEW)
    if (cachedOverview) {
      const parsedOv = JSON.parse(cachedOverview)
      if (parsedOv && typeof parsedOv === 'object') {
        Object.assign(overview, parsedOv)
      }
    }
    return displayedHoldingsAnalysis.value.length > 0
  } catch (e) {
    console.warn('读取本地数据分析缓存失败:', e)
  }
  return false
}

const saveCacheToStorage = () => {
  try {
    localStorage.setItem(STORAGE_KEY_HOLDINGS, JSON.stringify({
      displayedHoldingsAnalysis: displayedHoldingsAnalysis.value,
      holdingsList: holdingsList.value,
      manuallySelectedCodes: manuallySelectedCodes.value,
      savedAt: Date.now()
    }))
    localStorage.setItem(STORAGE_KEY_OVERVIEW, JSON.stringify(overview))
  } catch (e) {
    console.warn('保存本地数据分析缓存失败:', e)
  }
}

// 首次 setup 即时同步载入上次缓存数据，避免页面每次进入都出现加载闪烁
loadCacheFromStorage()

// 图表 DOM 与交互状态
const flowChartRef = ref(null)
let flowChart = null
const selectedSectorNode = ref(null)

// 状态文字与样式计算
const statusLabel = computed(() => {
  switch (overview.market_status) {
    case 'before_open':
      return '开盘前 (9:15前)'
    case 'pre_auction':
      return '集合竞价 (9:15~9:30)'
    case 'trading':
      return '交易进行中'
    case 'noon_break':
      return '午间休市'
    case 'closed':
    default:
      return '已收盘'
  }
})

const statusClass = computed(() => {
  switch (overview.market_status) {
    case 'trading':
      return 'status-trading'
    case 'pre_auction':
    case 'before_open':
      return 'status-premarket'
    case 'noon_break':
      return 'status-noon'
    case 'closed':
    default:
      return 'status-closed'
  }
})

const pulseClass = computed(() => {
  return overview.market_status === 'trading' ? 'pulse-green' : 'pulse-gray'
})

// 问题1修复：面板卡片按分类实时过滤
const displayedStockCount = computed(() => {
  return displayedHoldingsAnalysis.value.filter(h => h.type === 'stock').length
})

const displayedFundCount = computed(() => {
  return displayedHoldingsAnalysis.value.filter(h => h.type === 'fund').length
})

const filteredDisplayedHoldings = computed(() => {
  if (activeHoldingFilter.value === 'stock') {
    return displayedHoldingsAnalysis.value.filter(h => h.type === 'stock')
  }
  if (activeHoldingFilter.value === 'fund') {
    return displayedHoldingsAnalysis.value.filter(h => h.type === 'fund')
  }
  return displayedHoldingsAnalysis.value
})

const filteredHoldingsForSelect = computed(() => {
  const currentShownCodes = new Set(displayedHoldingsAnalysis.value.map(d => d.code))
  return holdingsList.value.filter(h => {
    if (currentShownCodes.has(h.code)) return false
    if (activeHoldingFilter.value === 'stock') return h.type === 'stock'
    if (activeHoldingFilter.value === 'fund') return h.type === 'fund'
    return true
  })
})

const getFlowClass = (val) => {
  if (!val || val === 0) return 'flat'
  return val > 0 ? 'rise' : 'fall'
}

// 加载数据
const loadOverview = async () => {
  try {
    const res = await api.getDataAnalysisOverview()
    if (res) {
      Object.assign(overview, res)
      saveCacheToStorage()
    }
  } catch (e) {
    console.error('加载概览失败:', e)
  }
}

const loadSectorRotation = async () => {
  try {
    const res = await api.getDataAnalysisSectorRotation()
    sectorRotationList.value = res || []
  } catch (e) {
    console.error('加载板块轮动失败:', e)
  }
}

const loadSectorFlow = async () => {
  try {
    const res = await api.getDataAnalysisSectorFlow()
    if (res) {
      Object.assign(sectorFlowData, res)
      renderActiveChart()
    }
  } catch (e) {
    console.error('加载板块流向失败:', e)
  }
}

const loadStatusConfig = async () => {
  try {
    const res = await api.getDataAnalysisStatus()
    Object.assign(statusConfig, res)
  } catch (e) {
    console.error('加载状态失败:', e)
  }
}

const loadHoldingsAndAnalysis = async (isSilent = false) => {
  // 仅在无任何缓存且非静默模式下才触发全屏阻塞 loading，避免每次进入都闪烁等待
  if (!isSilent && !displayedHoldingsAnalysis.value.length) {
    loadingHoldings.value = true
  }
  try {
    const list = await api.getDataAnalysisHoldings()
    holdingsList.value = list || []

    // 默认展示用户配置的 max_panels 数量的标的
    const max = statusConfig.max_panels || 6
    let initialItems = []

    if (manuallySelectedCodes.value.length) {
      initialItems = holdingsList.value.filter(h => manuallySelectedCodes.value.includes(h.code))
    } else {
      initialItems = holdingsList.value.slice(0, max)
    }

    if (initialItems.length) {
      const itemsToQuery = initialItems.map(h => ({
        code: h.code,
        name: h.name,
        type: h.type
      }))
      const analysisData = await api.getHoldingsAnalysis(itemsToQuery)
      if (analysisData && analysisData.length) {
        displayedHoldingsAnalysis.value = analysisData
        saveCacheToStorage()
      }
    } else {
      displayedHoldingsAnalysis.value = []
      saveCacheToStorage()
    }
  } catch (e) {
    console.error('加载标的分析失败:', e)
  } finally {
    loadingHoldings.value = false
  }
}

const handleSelectHoldingToAdd = async () => {
  if (!selectedCodeToAdd.value) return
  const code = selectedCodeToAdd.value
  selectedCodeToAdd.value = ''

  const target = holdingsList.value.find(h => h.code === code)
  if (!target) return

  if (!manuallySelectedCodes.value.includes(code)) {
    manuallySelectedCodes.value.push(code)
  }

  try {
    const res = await api.getDataAnalysisStock(code, target.type === 'fund')
    res.type = target.type
    displayedHoldingsAnalysis.value.unshift(res)
    saveCacheToStorage()
    showToast(`✅ 已将【${target.name}】加入数据分析面板`)
  } catch (e) {
    showToast(`❌ 查询标的数据失败: ${e.message}`)
  }
}

const removeHoldingFromDisplay = (code) => {
  displayedHoldingsAnalysis.value = displayedHoldingsAnalysis.value.filter(d => d.code !== code)
  manuallySelectedCodes.value = manuallySelectedCodes.value.filter(c => c !== code)
  saveCacheToStorage()
}

// 手动刷新 (支持开盘前/收盘后及交易时间强制更新最新数据)
const handleManualRefresh = async () => {
  refreshing.value = true
  try {
    await api.refreshDataAnalysis()
    await Promise.all([
      loadOverview(),
      loadSectorRotation(),
      loadSectorFlow(),
      loadHoldingsAndAnalysis(false),
      loadStatusConfig()
    ])
    saveCacheToStorage()
    showToast('✅ 数据分析已刷新完成')
  } catch (e) {
    showToast(`❌ 刷新失败: ${e.message}`)
  } finally {
    refreshing.value = false
  }
}

// 切换图表 Tab 时清除单球选中状态
const switchChartTab = (tab) => {
  activeFlowChartTab.value = tab
  selectedSectorNode.value = null
  renderActiveChart()
}

// 记录最后一次节点点击时间戳，防止与画布空白点击冲突
let lastNodeClickTime = 0

// 单球聚焦/取消聚焦核心方法（供画布点击、底部胶囊标签点击、重置按钮调用）
const toggleNodeFocus = (name) => {
  if (!name || selectedSectorNode.value === name) {
    selectedSectorNode.value = null
    if (showToast) {
      showToast('已恢复显示全景连线', 'info')
    }
  } else {
    selectedSectorNode.value = name
    const netData = activeFlowChartTab.value === 'inflow'
      ? (sectorFlowData.inflow_top8 || sectorFlowData.inter_sector || {})
      : (sectorFlowData.outflow_top8 || {})
    const links = netData.links || []
    const relatedCount = links.filter(l => l.source === name || l.target === name).length
    const isTarget = (netData.nodes || []).find(n => n.name === name)?.category === 'inflow'
    const prefix = isTarget ? '🔥 流入核心' : '💧 流出源头'
    if (showToast) {
      showToast(`已聚焦【${name}】(${prefix}): 仅展示其关联的 ${relatedCount} 根流向线`, 'info')
    }
  }
  renderSectorFlowChart(activeFlowChartTab.value)
}

// 清除单球高亮聚焦，恢复全景连线
const clearNodeFocus = () => {
  toggleNodeFocus(null)
}

// 切换图表排版模式 (通栏全景大屏 / 左右双栏并排)
const setLayoutMode = (mode) => {
  chartLayoutMode.value = mode
  nextTick(() => {
    if (flowChart) {
      flowChart.resize()
    }
  })
}

// 统一调度渲染图表
const renderActiveChart = () => {
  nextTick(() => {
    if (!flowChartRef.value) return
    if (!flowChart) {
      flowChart = echarts.init(flowChartRef.value)
      window.flowChartInstance = flowChart
      window.selectSectorNode = toggleNodeFocus
      window.toggleNodeFocus = toggleNodeFocus

      // 绑定节点点击事件（在初始化时绑定一次，绝不能使用无参数的 getZr().off('click')，以免破坏 ECharts 内部事件派发链）
      flowChart.on('click', (params) => {
        if (params.dataType === 'node' || (params.seriesType === 'graph' && params.name && params.dataType !== 'edge')) {
          const nodeName = params.name || params.data?.name
          if (nodeName) {
            lastNodeClickTime = Date.now()
            toggleNodeFocus(nodeName)
          }
        }
      })

      // 点击画布空白区域恢复全部连线（防抖避免与节点点击冲突）
      flowChart.getZr().on('click', (event) => {
        if (Date.now() - lastNodeClickTime < 250) {
          return
        }
        if (!event.target && selectedSectorNode.value) {
          toggleNodeFocus(null)
        }
      })
    }

    if (activeFlowChartTab.value === 'inflow') {
      renderSectorFlowChart('inflow')
    } else if (activeFlowChartTab.value === 'outflow') {
      renderSectorFlowChart('outflow')
    } else {
      renderSankeyChart()
    }
  })
}

// 板块资金流动与转移路径拓扑图（支持流入 Top 8 / 流出 Top 8 模式，带流光飞线动效 + 流向箭头 + 深红深绿配色）
const renderSectorFlowChart = (mode = 'inflow') => {
  const netData = mode === 'inflow'
    ? (sectorFlowData.inflow_top8 || sectorFlowData.inter_sector || {})
    : (sectorFlowData.outflow_top8 || {})
  const nodes = netData.nodes || []
  const links = netData.links || []
  const flowLines = netData.flow_lines || []

  if (!nodes.length) {
    flowChart.clear()
    return
  }

  const targetNodeName = selectedSectorNode.value

  // 1. 连线过滤：当点击某个圆球时，只显示该圆球直接相关的连线（出向或入向）
  const activeLinks = targetNodeName
    ? links.filter(l => l.source === targetNodeName || l.target === targetNodeName)
    : links

  // 2. 动效飞线过滤：只在该圆球关联的通道上展示流光飞线粒子
  const activeFlowLines = targetNodeName
    ? flowLines.filter(fl => fl.fromName === targetNodeName || fl.toName === targetNodeName)
    : flowLines

  // 3. 统计关联节点集合（包括自身与直接相连的对端板块）
  const connectedNodeNames = new Set()
  if (targetNodeName) {
    connectedNodeNames.add(targetNodeName)
    activeLinks.forEach(l => {
      connectedNodeNames.add(l.source)
      connectedNodeNames.add(l.target)
    })
  }

  // 4. 节点高亮处理：选中的球突出白边发光，相连的球保持全亮，未相连的球半透明淡化
  const activeNodes = nodes.map(n => {
    const isSelected = n.name === targetNodeName
    const isConnected = !targetNodeName || connectedNodeNames.has(n.name)
    return {
      name: n.name,
      value: [n.x, n.y],
      flowValue: n.value,
      change_pct: n.change_pct,
      category: n.category,
      symbolSize: isSelected ? Math.min(84, n.symbolSize + 6) : n.symbolSize,
      itemStyle: {
        color: n.color,
        opacity: isConnected ? 1 : 0.22,
        shadowBlur: isSelected ? 30 : (isConnected ? 14 : 0),
        shadowColor: isSelected ? '#ffffff' : n.color,
        borderColor: isSelected ? '#ffffff' : (isConnected && targetNodeName ? 'rgba(255, 255, 255, 0.5)' : 'transparent'),
        borderWidth: isSelected ? 3 : (isConnected && targetNodeName ? 1.5 : 0)
      },
      label: {
        opacity: isConnected ? 1 : 0.25
      }
    }
  })

  // 5. 连线样式微调：单球聚焦模式下稍微加粗连线并增强不透明度
  const styledLinks = activeLinks.map(l => {
    if (targetNodeName) {
      return {
        ...l,
        lineStyle: {
          ...l.lineStyle,
          opacity: 0.78,
          width: Math.max(2.4, (l.lineStyle?.width || 1.6) * 1.3)
        }
      }
    }
    return l
  })

  // 6. 飞线粒子样式微调
  const styledFlowLines = activeFlowLines.map(fl => {
    if (targetNodeName) {
      return {
        ...fl,
        lineStyle: {
          ...fl.lineStyle,
          opacity: 0.35
        }
      }
    }
    return fl
  })

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(22, 27, 34, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.15)',
      textStyle: { color: '#e6edf3' },
      formatter: (params) => {
        if (params.seriesType === 'lines') {
          return `<div style="font-size:12px;">
            <b>⚡ ${mode === 'inflow' ? '资金汇聚流入通道' : '资金撤离流出通道'}</b><br/>
            ${params.data.fromName} ➔ ${params.data.toName}<br/>
            <span style="color:#f85149;">转移强度指数: ${params.data.value}</span>
          </div>`
        }
        if (params.dataType === 'edge') {
          return `<b>板块资金转移</b><br/>${params.data.source} ➔ ${params.data.target}`
        }
        const d = params.data
        const typeStr = d.category === 'inflow'
          ? (mode === 'inflow' ? '<span style="color:#f85149;">🔥 市场流入 Top 8 (吸血池)</span>' : '<span style="color:#f85149;">🔥 资金承接板块 (吸血池)</span>')
          : (mode === 'outflow' ? '<span style="color:#00ff88;">💧 市场流出 Top 8 (失血源)</span>' : '<span style="color:#00ff88;">💧 资金来源板块 (失血源)</span>')
        return `<b>${d.name}</b> (${typeStr})<br/>
          主力净额: <b>${d.flowValue > 0 ? '+' : ''}${d.flowValue} 亿元</b><br/>
          涨跌幅: <b>${d.change_pct > 0 ? '+' : ''}${d.change_pct}%</b>`
      }
    },
    grid: {
      left: 25,
      right: 25,
      top: 20,
      bottom: 20
    },
    xAxis: {
      type: 'value',
      min: 0,
      max: 1000,
      show: false
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 500,
      show: false
    },
    series: [
      // 1. 基础关系拓扑图（节点带有深红深绿颜色、连线带有明确箭头，置于上层可直接点击）
      {
        type: 'graph',
        coordinateSystem: 'cartesian2d',
        z: 10,
        cursor: 'pointer',
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 8],
        label: {
          show: true,
          position: 'inside',
          color: '#ffffff',
          fontSize: 10.5,
          fontWeight: 700,
          lineHeight: 13,
          formatter: (p) => `${p.data.name}\n${p.data.flowValue > 0 ? '+' : ''}${p.data.flowValue}亿`
        },
        lineStyle: {
          curveness: 0.16,
          opacity: 0.26,
          width: 1.6
        },
        data: activeNodes,
        links: styledLinks
      },
      // 2. 动画流动效果 (Lines 系列：静默不拦截鼠标事件，作为背景流光)
      {
        type: 'lines',
        coordinateSystem: 'cartesian2d',
        z: 2,
        silent: true,
        effect: {
          show: true,
          period: 3.0,
          trailLength: 0.28,
          symbol: 'arrow',
          symbolSize: 6,
          color: mode === 'inflow' ? '#ff4d4f' : '#34d399'
        },
        lineStyle: {
          curveness: 0.16,
          opacity: 0.12,
          width: 1.6
        },
        data: styledFlowLines
      }
    ]
  }

  flowChart.setOption(option, true)
}

// 桑基图 (Sankey) 渲染
const renderSankeyChart = () => {
  const sk = sectorFlowData.sankey || {}
  const nodes = sk.nodes || []
  const links = sk.links || []

  if (!nodes.length || !links.length) {
    flowChart.clear()
    return
  }

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove',
      backgroundColor: 'rgba(22, 27, 34, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.15)',
      textStyle: { color: '#e6edf3' },
      formatter: (params) => {
        if (params.dataType === 'edge') {
          return `${params.data.source} ➔ ${params.data.target}<br/><b>净流动金额: ${params.data.value} 亿元</b>`
        }
        return `<b>${params.name}</b>`
      }
    },
    series: [
      {
        type: 'sankey',
        layout: 'none',
        nodeGap: 24,
        nodeWidth: 22,
        top: 25,
        bottom: 25,
        left: 45,
        right: 130,
        emphasis: {
          focus: 'adjacency'
        },
        data: nodes,
        links: links,
        lineStyle: {
          curveness: 0.5
        },
        label: {
          color: '#e6edf3',
          fontSize: 12,
          fontWeight: 600,
          distance: 8
        },
        itemStyle: {
          borderWidth: 0
        }
      }
    ]
  }

  flowChart.setOption(option, true)
}

// 窗口 resize 监听
const handleResize = () => {
  if (flowChart) {
    flowChart.resize()
  }
}

onMounted(async () => {
  window.addEventListener('resize', handleResize)

  // 1. 同步尝试从本地缓存恢复
  const hasCache = loadCacheFromStorage()
  const isTrading = isMarketTradingTime()

  await loadStatusConfig()

  // 2. 无论是否交易时间：
  // 若已有本地缓存，则已在同步阶段显示，避免任何白屏闪烁；
  // 随后均在后台拉取全量最新数据（包括概览、板块以及个股/基金监控面板），静默平滑替换
  await Promise.all([
    loadOverview(),
    loadSectorRotation(),
    loadSectorFlow(),
    loadHoldingsAndAnalysis(hasCache)
  ])
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (flowChart) {
    flowChart.dispose()
    flowChart = null
  }
})
</script>

<style scoped>
.data-analysis-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 顶部状态栏 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 16px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 1.8rem;
  font-weight: 700;
  margin: 0;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 0.82rem;
  font-weight: 600;
}

.status-badge.status-trading {
  background: rgba(0, 255, 136, 0.15);
  border: 1px solid rgba(0, 255, 136, 0.4);
  color: #00ff88;
}

.status-badge.status-premarket {
  background: rgba(255, 170, 0, 0.15);
  border: 1px solid rgba(255, 170, 0, 0.4);
  color: #ffaa00;
}

.status-badge.status-noon {
  background: rgba(0, 212, 255, 0.15);
  border: 1px solid rgba(0, 212, 255, 0.4);
  color: #00d2ff;
}

.status-badge.status-closed {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #8b949e;
}

.yesterday-badge {
  background: rgba(255, 170, 0, 0.2);
  color: #ffc107;
  border: 1px solid rgba(255, 170, 0, 0.4);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 700;
}

.realtime-badge {
  background: rgba(0, 255, 136, 0.2);
  color: #00ff88;
  border: 1px solid rgba(0, 255, 136, 0.4);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 700;
}

.closed-badge {
  background: rgba(255, 255, 255, 0.08);
  color: #8b949e;
  border: 1px solid rgba(255, 255, 255, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.pulse-green {
  background: #00ff88;
  box-shadow: 0 0 8px #00ff88;
  animation: pulse 1.5s infinite;
}

.pulse-gray {
  background: #8b949e;
}

@keyframes pulse {
  0% { transform: scale(0.9); opacity: 0.8; }
  50% { transform: scale(1.3); opacity: 1; }
  100% { transform: scale(0.9); opacity: 0.8; }
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  font-size: 0.82rem;
  color: var(--text-secondary);
  flex-wrap: wrap;
}

.source-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.source-tag.mx {
  background: rgba(163, 113, 247, 0.15);
  color: #bc8cff;
  border: 1px solid rgba(163, 113, 247, 0.3);
}

.source-tag.generic {
  background: rgba(0, 212, 255, 0.1);
  color: #00d2ff;
  border: 1px solid rgba(0, 212, 255, 0.25);
}

.degraded-tag {
  color: #f85149;
  font-weight: 700;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  font-size: 0.92rem;
  font-weight: 600;
}

.refresh-icon.rotating {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 各模块标题 */
.section-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.section-header.wrap-header {
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.15rem;
  font-weight: 600;
  margin: 0;
}

.section-hint {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

/* 1. 大盘指数卡片网格 */
.indices-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.index-card {
  padding: 14px;
  border-radius: 12px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.index-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.index-card.rise {
  border-top: 3px solid #f85149;
}

.index-card.fall {
  border-top: 3px solid #00ff88;
}

.index-card.flat {
  border-top: 3px solid #8b949e;
}

.index-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.index-name {
  font-weight: 600;
  font-size: 0.92rem;
}

.index-code {
  font-size: 0.72rem;
  color: var(--text-secondary);
}

.index-price-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 10px;
}

.index-current {
  font-size: 1.25rem;
  font-weight: 700;
}

.index-card.rise .index-current,
.index-card.rise .index-change {
  color: #f85149;
}

.index-card.fall .index-current,
.index-card.fall .index-change {
  color: #00ff88;
}

.index-change {
  font-weight: 600;
  font-size: 0.95rem;
}

.index-data-grid {
  display: flex;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 0.78rem;
}

.data-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.item-label {
  color: var(--text-secondary);
  font-size: 0.72rem;
}

.item-value {
  font-weight: 600;
}

/* 2. 资金流向卡片 */
.flow-summary-card {
  padding: 20px;
}

.flow-metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.metric-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-card.rise {
  background: rgba(248, 81, 73, 0.05);
  border-color: rgba(248, 81, 73, 0.3);
}

.metric-card.fall {
  background: rgba(0, 255, 136, 0.05);
  border-color: rgba(0, 255, 136, 0.3);
}

.metric-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.metric-value {
  font-size: 1.6rem;
  font-weight: 700;
}

.metric-card.rise .metric-value {
  color: #f85149;
}

.metric-card.fall .metric-value {
  color: #00ff88;
}

.metric-desc {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.unavailable-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 0.88rem;
  padding: 12px;
}

/* 3. 个股与基金面板 */
.filter-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.pill-tabs {
  display: flex;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 3px;
  gap: 4px;
}

.pill-btn {
  background: transparent;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 0.82rem;
  cursor: pointer;
  transition: all 0.2s;
}

.pill-btn.active {
  background: rgba(0, 212, 255, 0.15);
  color: #00d2ff;
  font-weight: 600;
}

.holding-select {
  padding: 7px 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #fff;
  font-size: 0.85rem;
  outline: none;
}

.holdings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.holding-card {
  padding: 16px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.holding-card.rise {
  border-left: 4px solid #f85149;
}

.holding-card.fall {
  border-left: 4px solid #00ff88;
}

.holding-card.flat {
  border-left: 4px solid #8b949e;
}

.holding-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.holding-title-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.type-badge {
  font-size: 0.7rem;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.type-badge.stock {
  background: rgba(0, 212, 255, 0.15);
  color: #00d2ff;
}

.type-badge.fund {
  background: rgba(255, 170, 0, 0.15);
  color: #ffaa00;
}

.holding-name {
  font-size: 0.95rem;
}

.holding-code {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.remove-card-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}

.remove-card-btn:hover {
  color: #f85149;
  background: rgba(248, 81, 73, 0.1);
}

.holding-price-wrap {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.main-price {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}

.price-val {
  font-size: 1.3rem;
  font-weight: 700;
}

.holding-card.rise .price-val,
.holding-card.rise .price-chg {
  color: #f85149;
}

.holding-card.fall .price-val,
.holding-card.fall .price-chg {
  color: #00ff88;
}

.price-chg {
  font-weight: 600;
  font-size: 0.95rem;
}

.nav-tag {
  font-size: 0.68rem;
  padding: 1px 5px;
  border-radius: 3px;
  background: rgba(255, 170, 0, 0.15);
  color: #ffaa00;
  border: 1px solid rgba(255, 170, 0, 0.3);
}

.volume-stat {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  font-size: 0.72rem;
  color: var(--text-secondary);
}

.calc-component-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  background: rgba(0, 212, 255, 0.08);
  border: 1px solid rgba(0, 212, 255, 0.2);
  color: #00d2ff;
  font-size: 0.72rem;
}

.holding-flow-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.flow-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
}

.flow-name {
  color: var(--text-secondary);
}

.flow-val {
  font-weight: 600;
}

.flow-val.rise { color: #f85149; }
.flow-val.fall { color: #00ff88; }
.flow-val.flat { color: var(--text-secondary); }

/* 4 & 5. 排版模式 (支持通栏大屏与双栏并排) */
.grid-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.grid-stacked {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.layout-toggle-group {
  display: flex;
  gap: 6px;
  background: rgba(255, 255, 255, 0.04);
  padding: 3px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.layout-btn {
  background: transparent;
  border: none;
  padding: 6px 14px;
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.layout-btn:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.06);
}

.layout-btn.active {
  background: rgba(0, 212, 255, 0.18);
  color: #00d2ff;
  font-weight: 600;
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.25);
}

.chart-card.is-fullwidth,
.sector-card.is-fullwidth {
  width: 100%;
}

.card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.05rem;
  font-weight: 600;
  margin: 0;
}

.chart-tab-group {
  display: flex;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 2px;
  gap: 3px;
}

.chart-tab-btn {
  background: transparent;
  border: none;
  padding: 5px 12px;
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}

.chart-tab-btn.active {
  background: rgba(0, 212, 255, 0.2);
  color: #00d2ff;
  font-weight: 600;
}

.badge-sub {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

/* 轮动表格 */
.sector-table-container {
  max-height: 480px;
  overflow-y: auto;
}

.sector-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}

.sector-table th {
  padding: 8px 10px;
  text-align: left;
  color: var(--text-secondary);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  position: sticky;
  top: 0;
  background: #161b22;
  z-index: 10;
}

.sector-table td {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.sector-table td.rise { color: #f85149; font-weight: 600; }
.sector-table td.fall { color: #00ff88; font-weight: 600; }
.sector-table td.flat { color: var(--text-secondary); }

.trend-icon {
  font-size: 0.75rem;
  font-weight: 600;
}

.trend-icon.up { color: #f85149; }
.trend-icon.down { color: #00ff88; }
.trend-icon.flat { color: #8b949e; }

/* 图表容器 */
.chart-wrapper {
  height: 440px;
  width: 100%;
  transition: height 0.3s ease;
}

.chart-wrapper.expanded-chart {
  height: 520px;
}

.main-flow-chart {
  width: 100%;
  height: 100%;
}

.hint-click {
  color: #58a6ff;
  font-weight: 500;
}

/* 动效图图例条 */
.flow-legend-bar {
  display: flex;
  justify-content: center;
  gap: 20px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
  margin-top: 6px;
  font-size: 0.75rem;
  color: var(--text-secondary);
  flex-wrap: wrap;
  align-items: center;
}

.focus-filter-pill {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: rgba(56, 139, 253, 0.16);
  border: 1px solid rgba(56, 139, 253, 0.45);
  color: #58a6ff;
  padding: 3px 12px;
  border-radius: 16px;
  font-size: 0.78rem;
  font-weight: 600;
  box-shadow: 0 0 10px rgba(56, 139, 253, 0.2);
}

.focus-icon {
  font-size: 0.9rem;
}

.reset-focus-btn {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: #e6edf3;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 0.72rem;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
}

.reset-focus-btn:hover {
  background: rgba(248, 81, 73, 0.35);
  border-color: rgba(248, 81, 73, 0.6);
  color: #ff7b72;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-dot.deep-red {
  background: #820014;
  box-shadow: 0 0 6px #cf1322;
}

.legend-dot.deep-green {
  background: #004d40;
  box-shadow: 0 0 6px #00695c;
}

.legend-arrow-anim {
  color: #ff4d4f;
  font-weight: 700;
  letter-spacing: -2px;
  animation: arrowGlow 1.5s infinite;
}

@keyframes arrowGlow {
  0% { opacity: 0.4; }
  50% { opacity: 1; }
  100% { opacity: 0.4; }
}

.sankey-summary-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.top-list {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.box-title {
  font-size: 0.78rem;
  color: var(--text-secondary);
  font-weight: 600;
  white-space: nowrap;
}

.pill-cloud {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.flow-pill {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.flow-pill.rise {
  background: rgba(248, 81, 73, 0.12);
  color: #f85149;
  border: 1px solid rgba(248, 81, 73, 0.3);
}

.flow-pill.fall {
  background: rgba(0, 255, 136, 0.12);
  color: #00ff88;
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.clickable-pill {
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
}

.clickable-pill:hover {
  transform: translateY(-1px);
  filter: brightness(1.25);
}

.clickable-pill.rise.is-selected {
  background: #f85149;
  color: #ffffff;
  border-color: #ffffff;
  box-shadow: 0 0 10px rgba(248, 81, 73, 0.85);
}

.clickable-pill.fall.is-selected {
  background: #00ff88;
  color: #0b1912;
  border-color: #ffffff;
  box-shadow: 0 0 10px rgba(0, 255, 136, 0.85);
}

.loading-box,
.empty-box {
  padding: 32px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.88rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

/* 移动端响应式 */
@media (max-width: 1024px) {
  .grid-2col {
    grid-template-columns: 1fr;
  }
  .flow-metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
