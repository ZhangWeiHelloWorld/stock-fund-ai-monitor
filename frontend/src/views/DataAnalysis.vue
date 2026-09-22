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

    <!-- 一级核心模块页签切换 -->
    <nav class="main-page-tabs-bar">
      <button 
        class="main-tab-btn" 
        :class="{ active: activeMainTab === 'overview' }" 
        @click="switchMainTab('overview')"
      >
        <span class="tab-icon">📊</span>
        <div class="tab-text-wrap">
          <span class="tab-title">今日概况</span>
          <span class="tab-subtitle">宏观大盘 · 全市场资金 · 板块轮动全景</span>
        </div>
      </button>
      <button 
        class="main-tab-btn" 
        :class="{ active: activeMainTab === 'stock_analysis' }" 
        @click="switchMainTab('stock_analysis')"
      >
        <span class="tab-icon">🎯</span>
        <div class="tab-text-wrap">
          <span class="tab-title">个股数据分析</span>
          <span class="tab-subtitle">技术指标 · 顶底背离 · 重仓穿透 · AI智能买卖</span>
        </div>
      </button>
    </nav>

    <!-- TAB 1: 今日概况 (宏观大盘与板块全景) -->
    <div v-show="activeMainTab === 'overview'" class="tab-pane-content">
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
          <div class="metric-card" :class="getFlowClass(overview.fund_flow.main_net_inflow)"
               :title="overview.fund_flow.large_net_inflow_formatted ? `超大单: ${overview.fund_flow.institution_net_inflow_formatted} | 大单: ${overview.fund_flow.large_net_inflow_formatted}` : ''">
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
          <div class="metric-card" :class="getFlowClass(overview.fund_flow.retail_net_inflow)"
               :title="overview.fund_flow.medium_net_inflow_formatted ? `中单: ${overview.fund_flow.medium_net_inflow_formatted} | 小单: ${overview.fund_flow.small_net_inflow_formatted}` : ''">
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

    <!-- 3. A股板块轮动时间事件图与交易量全景看板 -->
    <section class="section-block rotation-timeline-section">
      <!-- Section Header -->
      <div class="section-header wrap-header">
        <div>
          <div class="title-with-badge">
            <h3 class="section-title">
              <span class="title-icon">📊</span>
              <span>A股板块轮动时间事件图与交易量全景</span>
            </h3>
            <span class="source-tag" :class="rotationTimelineData.provider_type || 'mx'">
              {{ rotationTimelineData.source_label || '💎 东方财富妙想权威数据' }}
            </span>
          </div>
          <span class="section-hint">
            融合每日催化事件、两市2万亿级成交量波动、行业涨跌幅热力矩阵及主力资金腾挪路径的全流程复盘分析
          </span>
        </div>

        <!-- Metric badges summary -->
        <div class="rotation-stat-badges" v-if="rotationTimelineData.stat_cards && rotationTimelineData.stat_cards.length">
          <div 
            v-for="(stat, sIdx) in rotationTimelineData.stat_cards" 
            :key="sIdx"
            class="stat-pill-badge"
          >
            <div class="stat-pill-label">{{ stat.label }}</div>
            <div class="stat-pill-val" :style="{ color: stat.color || '#ff4444' }">{{ stat.value }}</div>
            <div class="stat-pill-sub">{{ stat.sub }}</div>
          </div>
        </div>
      </div>

      <!-- Navigation Sub-Tabs -->
      <div class="rotation-tabs-bar">
        <div class="rotation-tabs-group">
          <button 
            class="rotation-tab-btn" 
            :class="{ active: activeRotationTab === 'timeline' }"
            @click="switchRotationTab('timeline')"
          >
            🗓️ 时间事件轴与轮动演进
          </button>
          <button 
            class="rotation-tab-btn" 
            :class="{ active: activeRotationTab === 'volume' }"
            @click="switchRotationTab('volume')"
          >
            📊 轮动交易量双维对比
          </button>
          <button 
            class="rotation-tab-btn" 
            :class="{ active: activeRotationTab === 'matrix' }"
            @click="switchRotationTab('matrix')"
          >
            🔥 板块涨跌幅热力矩阵
          </button>
        </div>
        <div class="rotation-tab-hint">
          💡 提示：点击时间轴节点可切换每日复盘与成交量下钻
        </div>
      </div>

      <!-- Generic Interface Notice -->
      <div v-if="!rotationTimelineData.is_rich" class="generic-notice-banner">
        <span class="notice-icon">🌐</span>
        <div class="notice-content">
          <strong>当前为通用接口实际行情模式：</strong>
          已实时呈现当日实际成交量与申万行业涨跌数据。切换至【东方财富妙想】接口可解锁完整的 5 日深度演进时序、核心产业驱动催化及异动标杆个股下钻。
        </div>
        <router-link to="/settings" class="btn btn-sm btn-outline-primary">前往设置切换</router-link>
      </div>

      <!-- VIEW 1: TIMELINE & EVENT DEEP DIVE -->
      <div v-show="activeRotationTab === 'timeline'" class="rotation-view-content">
        <!-- 5-day Stepper Buttons -->
        <div class="timeline-stepper-grid">
          <button 
            v-for="(day, idx) in (rotationTimelineData.timeline || [])" 
            :key="idx"
            class="stepper-node-btn"
            :class="[
              activeTimelineDayIndex === idx ? 'is-active ' + day.phaseClass : '',
              day.phaseClass
            ]"
            @click="selectTimelineDay(idx)"
          >
            <div class="node-header">
              <span class="node-date">{{ day.date }}</span>
              <span class="node-phase-tag">{{ day.phase }}</span>
            </div>
            <div class="node-title">{{ day.shortTitle }}</div>
            <div class="node-vol">{{ day.marketVol }}</div>
          </button>
        </div>

        <!-- Current Day Deep Dive Card -->
        <div v-if="currentTimelineDay" class="glass-card day-detail-card">
          <div class="day-detail-grid">
            <!-- Left 7 cols: Story, Catalysts, Leaders/Laggers, Capital flow -->
            <div class="day-detail-main">
              <div class="day-detail-header">
                <div class="day-badge-title">
                  <span class="day-badge">{{ currentTimelineDay.dateStr }}</span>
                  <h4 class="day-title">{{ currentTimelineDay.title }}</h4>
                </div>
                <div class="day-breadth font-mono">{{ currentTimelineDay.breadth }}</div>
              </div>

              <!-- Catalysts Box -->
              <div class="detail-catalyst-box">
                <h5 class="catalyst-header">
                  <span>⚡</span>
                  <span>核心催化驱动事件与消息面</span>
                </h5>
                <ul class="catalyst-list">
                  <li v-for="(cat, cIdx) in currentTimelineDay.catalysts" :key="cIdx" v-html="cat"></li>
                </ul>
              </div>

              <!-- Leaders and Laggers Flow -->
              <div class="leaders-laggers-grid">
                <!-- Leaders -->
                <div class="sector-group-card leaders-card">
                  <div class="group-header text-red">
                    <span>🔥 强势领涨板块与核心驱动</span>
                    <span class="group-sub">涨跌幅</span>
                  </div>
                  <div class="group-list">
                    <div v-for="(item, lIdx) in currentTimelineDay.leaders" :key="lIdx" class="group-item">
                      <div class="item-name-wrap">
                        <strong class="item-name">{{ item.name }}</strong>
                        <span class="item-desc">{{ item.desc }}</span>
                      </div>
                      <span class="item-val rise">{{ item.val }}</span>
                    </div>
                  </div>
                </div>

                <!-- Laggers -->
                <div class="sector-group-card laggers-card">
                  <div class="group-header text-green">
                    <span>❄️ 失血回踩板块 (资金提款机)</span>
                    <span class="group-sub">涨跌幅</span>
                  </div>
                  <div class="group-list">
                    <div v-for="(item, lgIdx) in currentTimelineDay.laggers" :key="lgIdx" class="group-item">
                      <div class="item-name-wrap">
                        <strong class="item-name">{{ item.name }}</strong>
                        <span class="item-desc">{{ item.desc }}</span>
                      </div>
                      <span class="item-val fall">{{ item.val }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Capital Flow Description -->
              <div class="capital-flow-card">
                <span class="capital-label">💡 资金腾挪逻辑：</span>
                <span class="capital-text">{{ currentTimelineDay.capital }}</span>
              </div>
            </div>

            <!-- Right 5 cols: Sector Volumes & Focus Stocks -->
            <div class="day-detail-side">
              <!-- Key Sectors Volume on that day -->
              <div class="side-vol-section">
                <div class="side-vol-header">
                  <span class="side-vol-title">当日重点赛道成交额分布</span>
                  <span class="side-vol-total font-mono">{{ currentTimelineDay.volTotal }}</span>
                </div>
                <div class="side-vol-bars">
                  <div v-for="(bar, bIdx) in currentTimelineDay.volBars" :key="bIdx" class="vol-bar-item">
                    <div class="bar-info-row">
                      <span class="bar-name">{{ bar.name }}</span>
                      <span class="bar-vol font-mono">{{ bar.vol }}</span>
                    </div>
                    <div class="bar-track">
                      <div 
                        class="bar-fill" 
                        :style="{ width: bar.pct + '%', backgroundColor: bar.color || '#3b82f6' }"
                      ></div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Focus Stocks -->
              <div class="side-stocks-section" v-if="currentTimelineDay.stocks && currentTimelineDay.stocks.length">
                <div class="side-stocks-header">
                  <span>🎯 核心异动 / 标杆个股</span>
                  <span class="stocks-sub">日成交额与表现</span>
                </div>
                <div class="side-stocks-list">
                  <div v-for="(stock, sIdx) in currentTimelineDay.stocks" :key="sIdx" class="stock-item-pill">
                    <strong class="stock-name">{{ stock.name }}</strong>
                    <span class="stock-desc">{{ stock.desc }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- VIEW 2: VOLUME COMPARISON VIEW -->
      <div v-show="activeRotationTab === 'volume'" class="rotation-view-content">
        <div class="volume-comparison-grid">
          <!-- Left: Turnover Trend Chart -->
          <div class="glass-card vol-chart-card">
            <div class="card-header-row">
              <div>
                <h4 class="card-title">两市大盘成交额波动与转折点 (亿元)</h4>
                <p class="card-desc">{{ rotationTimelineData.volume_trend?.sub_title || '呈现缩量探底到巨量爆发的量能放大过程' }}</p>
              </div>
              <span class="turning-badge">{{ rotationTimelineData.volume_trend?.turning_point || '+2564亿 放量拐点' }}</span>
            </div>
            
            <div class="vol-chart-wrapper">
              <div ref="volumeChartRef" class="volume-trend-chart"></div>
            </div>
          </div>

          <!-- Right: Multi-Day Sector Turnover Table -->
          <div class="glass-card vol-table-card">
            <div class="card-header-row">
              <div>
                <h4 class="card-title">核心赛道日成交金额对比 (亿元)</h4>
                <p class="card-desc">数据直采自东方财富 Choice：半导体/通信放量翻倍，银行/煤炭缩水</p>
              </div>
            </div>

            <div class="table-container mini-scroll-table">
              <table class="vol-table">
                <thead>
                  <tr>
                    <th>核心赛道</th>
                    <th v-for="col in (rotationTimelineData.sector_multi_day_volumes?.columns || [])" :key="col" class="text-right font-mono">
                      {{ col }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr 
                    v-for="(row, rIdx) in (rotationTimelineData.sector_multi_day_volumes?.rows || [])" 
                    :key="rIdx"
                    :class="{ 'row-highlight': row.highlight }"
                  >
                    <td class="font-bold" :style="{ color: row.color }">{{ row.sector }}</td>
                    <td 
                      v-for="(val, vIdx) in row.values" 
                      :key="vIdx" 
                      class="text-right font-mono"
                      :class="vIdx === row.values.length - 1 && row.highlight ? 'text-red font-bold' : ''"
                    >
                      {{ val }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Insight Callout -->
            <div class="insight-callout" v-if="rotationTimelineData.sector_multi_day_volumes?.insight">
              📌 <strong>成交量演进洞见：</strong>
              <span>{{ rotationTimelineData.sector_multi_day_volumes.insight }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- VIEW 3: SECTOR HEATMAP & RETURN MATRIX -->
      <div v-show="activeRotationTab === 'matrix'" class="rotation-view-content">
        <div class="glass-card matrix-card">
          <div class="card-header-row">
            <div>
              <h4 class="card-title">核心板块日度涨跌幅热力矩阵 (流通市值加权)</h4>
              <p class="card-desc">直观展现资金在“科技成长 vs 周期防御 vs 消费服务”之间的轮动时序</p>
            </div>
            <div class="matrix-legend">
              <span class="legend-chip"><span class="chip-color deep-red"></span> &gt;+2.0% 强势</span>
              <span class="legend-chip"><span class="chip-color light-red"></span> 0~+2% 小涨</span>
              <span class="legend-chip"><span class="chip-color deep-green"></span> &lt;0% 走弱</span>
            </div>
          </div>

          <div class="table-container">
            <table class="matrix-table">
              <thead>
                <tr>
                  <th>板块名称</th>
                  <th>产业大类</th>
                  <th 
                    v-for="dHeader in (rotationTimelineData.heatmap_matrix?.dates || [])" 
                    :key="dHeader"
                    class="text-center"
                  >
                    {{ dHeader }}
                  </th>
                  <th class="text-center font-bold text-red">区间表现</th>
                  <th>阶段特征</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, mIdx) in (rotationTimelineData.heatmap_matrix?.rows || [])" :key="mIdx">
                  <td class="font-bold" :style="{ color: row.color }">{{ row.name }}</td>
                  <td class="text-secondary">{{ row.category }}</td>
                  <td 
                    v-for="(chg, cIdx) in row.chgs" 
                    :key="cIdx"
                    class="text-center font-bold heat-cell"
                    :class="getHeatmapCellClass(chg)"
                  >
                    {{ chg }}
                  </td>
                  <td class="text-center font-black text-red heat-cell" :class="getHeatmapCellClass(row.range_chg)">
                    {{ row.range_chg }}
                  </td>
                  <td class="text-secondary text-sm">{{ row.feature }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Core Takeaways / Summary (Always Visible in Section Footer) -->
      <div class="glass-card takeaways-card" v-if="rotationTimelineData.strategy_takeaways && rotationTimelineData.strategy_takeaways.length">
        <div class="takeaways-header">
          <span>🧭</span>
          <strong>核心复盘结论与板块轮动策略要点</strong>
        </div>
        <div class="takeaways-grid">
          <div 
            v-for="(item, tIdx) in rotationTimelineData.strategy_takeaways" 
            :key="tIdx"
            class="takeaway-item"
          >
            <div class="takeaway-title" :style="{ color: item.color }">{{ item.title }}</div>
            <p class="takeaway-desc">{{ item.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 5. 板块资金流动拓扑与动效全景图 & 6. 申万行业板块轮动方向 -->
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
    </div> <!-- end of TAB 1 overview -->

    <!-- TAB 2: 个股数据分析 -->
    <div v-show="activeMainTab === 'stock_analysis'" class="tab-pane-content">
      <div class="tech-analysis-view">
        <!-- 1. 标的选择与检索工具条 -->
        <div class="glass-card tech-toolbar-card">
          <div class="tech-toolbar-row">
            <div class="toolbar-left">
              <!-- 分类过滤 -->
              <div class="pill-tabs mini-pills">
                <button 
                  class="pill-btn" 
                  :class="{ active: selectedTechFilter === 'all' }" 
                  @click="selectedTechFilter = 'all'"
                >
                  全部 ({{ allTechAvailableHoldings.length }})
                </button>
                <button 
                  class="pill-btn" 
                  :class="{ active: selectedTechFilter === 'stock' }" 
                  @click="selectedTechFilter = 'stock'"
                >
                  📈 股票 ({{ allTechStockCount }})
                </button>
                <button 
                  class="pill-btn" 
                  :class="{ active: selectedTechFilter === 'fund' }" 
                  @click="selectedTechFilter = 'fund'"
                >
                  💰 基金 ({{ allTechFundCount }})
                </button>
              </div>

              <!-- 标的下拉选择 -->
              <div class="tech-select-wrapper">
                <select v-model="selectedTechCode" @change="handleSelectTechHolding" class="tech-dropdown">
                  <option value="" disabled>🎯 选择关注/持仓标的进行深度分析...</option>
                  <option 
                    v-for="h in filteredTechHoldingsForSelect" 
                    :key="h.code" 
                    :value="h.code"
                  >
                    {{ h.type === 'stock' ? '📈' : '💰' }} {{ h.name }} ({{ h.code }})
                  </option>
                </select>
              </div>
            </div>

            <!-- 自定义代码输入与快捷分析 -->
            <div class="toolbar-right">
              <div class="code-search-box">
                <input 
                  type="text" 
                  v-model="techSearchInput" 
                  placeholder="输入股票或基金代码 (如 600519 / 017811)..." 
                  class="code-input"
                  @keyup.enter="handleSearchCustomCode"
                />
                <button class="btn btn-primary btn-sm search-btn" @click="handleSearchCustomCode" :disabled="loadingTechData">
                  <span>{{ loadingTechData ? '分析中...' : '🔍 深度分析' }}</span>
                </button>
              </div>
              <button class="btn btn-outline-secondary btn-sm refresh-tech-btn" @click="loadTechAnalysis(selectedTechCode, true)" :disabled="loadingTechData" title="强制刷新最新技术指标数据">
                <span>🔄 刷新行情</span>
              </button>
            </div>
          </div>

          <!-- 快捷标的标签条 -->
          <div class="quick-tags-row" v-if="displayedHoldingsAnalysis.length">
            <span class="quick-label">⚡ 快速切换:</span>
            <div class="quick-tags-list">
              <button 
                v-for="h in displayedHoldingsAnalysis" 
                :key="h.code"
                class="quick-tag-btn"
                :class="{ active: selectedTechCode === h.code }"
                @click="selectQuickTarget(h)"
              >
                <span class="tag-icon">{{ h.type === 'stock' ? '📈' : '💰' }}</span>
                <span class="tag-name">{{ h.name }}</span>
                <span class="tag-pct" :class="h.change_pct > 0 ? 'rise' : (h.change_pct < 0 ? 'fall' : 'flat')">
                  {{ h.change_pct > 0 ? '+' : '' }}{{ h.change_pct?.toFixed(2) }}%
                </span>
              </button>
            </div>
          </div>
        </div>

        <!-- 加载中与空状态 -->
        <div v-if="loadingTechData && !techData" class="glass-card loading-box tech-loading-state">
          <span class="spinner">⏳</span>
          <span>正在精密运算 MACD、RSI、顶底背离及重仓穿透量化指标...</span>
        </div>

        <div v-else-if="!techData" class="glass-card empty-box">
          <span>请在上方选择或输入股票/基金代码以开启深度技术分析与AI研判。</span>
        </div>

        <div v-else class="tech-main-layout">
          <!-- 标的即时行情与资金流动摘要横幅 -->
          <div class="glass-card target-snapshot-banner" :class="techData.quote?.change_pct > 0 ? 'rise' : (techData.quote?.change_pct < 0 ? 'fall' : 'flat')">
            <div class="snapshot-left">
              <div class="snapshot-title-row">
                <span class="type-pill" :class="techData.asset_type">
                  {{ techData.asset_type === 'fund' ? '公募基金' : (techData.asset_type === 'etf' ? '场内ETF' : 'A股股票') }}
                </span>
                <h3 class="target-title-name">{{ techData.name }}</h3>
                <span class="target-title-code font-mono">{{ techData.code }}</span>
                <span class="source-tag" :class="overview.provider_type">
                  {{ overview.provider_type === 'mx' ? '💎 东方财富妙想' : '🌐 通用公开接口' }}
                </span>
              </div>
              <div class="snapshot-price-row">
                <span class="live-price font-mono">
                  {{ techData.quote?.current ? techData.quote.current.toFixed(techData.is_fund ? 4 : 2) : '-' }}
                </span>
                <span class="live-chg font-mono">
                  {{ techData.quote?.change_pct > 0 ? '+' : '' }}{{ techData.quote?.change_pct?.toFixed(2) }}%
                </span>
                <span v-if="techData.is_fund" class="nav-badge">
                  {{ techData.quote?.nav_type || '官方净值' }}
                </span>
              </div>
            </div>

            <div class="snapshot-stats-grid">
              <div class="snap-stat">
                <span class="snap-label">成交量</span>
                <span class="snap-val">{{ techData.quote?.volume_formatted || '-' }}</span>
              </div>
              <div class="snap-stat">
                <span class="snap-label">成交额/结算</span>
                <span class="snap-val">{{ techData.quote?.amount_formatted || '-' }}</span>
              </div>
              <div class="snap-stat">
                <span class="snap-label">{{ techData.is_fund ? '穿透主力流向' : '主力净流入' }}</span>
                <span class="snap-val" :class="getFlowClass(techData.quote?.main_net_inflow)">
                  {{ techData.quote?.main_net_inflow_formatted || '-' }}
                </span>
              </div>
              <div class="snap-stat">
                <span class="snap-label">{{ techData.is_fund ? '穿透机构流向' : '机构净流入' }}</span>
                <span class="snap-val" :class="getFlowClass(techData.quote?.institution_net_inflow)">
                  {{ techData.quote?.institution_net_inflow_formatted || '-' }}
                </span>
              </div>
              <div class="snap-stat">
                <span class="snap-label">{{ techData.is_fund ? '穿透散户流向' : '散户净流入' }}</span>
                <span class="snap-val" :class="getFlowClass(techData.quote?.retail_net_inflow)">
                  {{ techData.quote?.retail_net_inflow_formatted || '-' }}
                </span>
              </div>
            </div>
          </div>

          <!-- 顶背离 / 底背离 智能雷达诊断告警条 (如果检测到背离，显著置顶呈现) -->
          <div v-if="techData.divergence?.has_divergence" class="divergence-alert-box" :class="techData.divergence.bottom_divergence ? 'bottom-alert' : 'top-alert'">
            <div class="alert-icon-wrap">
              <span>{{ techData.divergence.bottom_divergence ? '🔥' : '⚠️' }}</span>
            </div>
            <div class="alert-content-wrap">
              <div class="alert-title-row">
                <strong class="alert-title">
                  {{ techData.divergence.bottom_divergence ? '【强烈做多】检出日线底背离 · 底部反转买入契机' : '【风险预警】检出日线顶背离 · 动能衰退回落风险' }}
                </strong>
                <span class="alert-type-badge">
                  {{ (techData.divergence.bottom_divergence || techData.divergence.top_divergence)?.indicator_type }}
                </span>
              </div>
              <p class="alert-desc">
                {{ (techData.divergence.bottom_divergence || techData.divergence.top_divergence)?.desc }}
              </p>
              <div class="alert-action">
                <span class="action-tag">操盘指引:</span>
                <span>{{ (techData.divergence.bottom_divergence || techData.divergence.top_divergence)?.action_advice }}</span>
              </div>
            </div>
          </div>

          <!-- 核心两栏交互结构: 左侧图表与指标，右侧综合评分与指标诊断 -->
          <div class="tech-content-grid">
            <!-- 左栏: ECharts K线/净值走势 + 成交量 + 副图指标(MACD/RSI/KDJ) -->
            <div class="tech-chart-column">
              <div class="glass-card chart-main-card">
                <div class="chart-header-row">
                  <div class="chart-title-group">
                    <span class="chart-icon">📈</span>
                    <h4 class="chart-title">{{ techData.name }} 日K线与多维技术指标</h4>
                    <span class="chart-timeframe-tag">日线走势 (近200交易日)</span>
                  </div>

                  <!-- 副图指标选择器 -->
                  <div class="sub-indicator-tabs">
                    <button 
                      class="sub-ind-btn" 
                      :class="{ active: techChartSubTab === 'macd' }"
                      @click="switchTechSubTab('macd')"
                    >
                      MACD (12, 26, 9)
                    </button>
                    <button 
                      class="sub-ind-btn" 
                      :class="{ active: techChartSubTab === 'rsi' }"
                      @click="switchTechSubTab('rsi')"
                    >
                      RSI (6, 12, 24)
                    </button>
                    <button 
                      class="sub-ind-btn" 
                      :class="{ active: techChartSubTab === 'kdj' }"
                      @click="switchTechSubTab('kdj')"
                    >
                      KDJ (9, 3, 3)
                    </button>
                  </div>
                </div>

                <!-- 图表渲染容器 (高度 540px) -->
                <div class="tech-echart-wrapper">
                  <div ref="techChartRef" class="tech-echart-canvas"></div>
                </div>

                <div class="chart-footer-legend">
                  <span class="legend-item"><span class="dot-ma5"></span> MA5</span>
                  <span class="legend-item"><span class="dot-ma10"></span> MA10</span>
                  <span class="legend-item"><span class="dot-ma20"></span> MA20 (生命线)</span>
                  <span class="legend-item"><span class="dot-ma60"></span> MA60 (决策线)</span>
                  <span class="legend-tip">💡 提示：按住鼠标可水平缩放平移，悬浮查看精密点位</span>
                </div>
              </div>

              <!-- 基金专属: 重仓股穿透技术面看板 (仅基金展示) -->
              <div v-if="techData.is_fund && techData.components && techData.components.length" class="glass-card fund-components-card">
                <div class="components-card-header">
                  <div class="header-left-title">
                    <span class="icon">🔬</span>
                    <h4 class="title">公开前十大重仓股技术面穿透测算</h4>
                    <span class="badge-weight">合计持仓权重: {{ techData.components_weight_total }}%</span>
                  </div>
                  <div class="header-right-score">
                    <span class="score-label">重仓加权穿透评分:</span>
                    <span class="score-val font-mono">{{ techData.weighted_penetration_score }} 分</span>
                  </div>
                </div>

                <p class="penetration-summary-p">
                  {{ techData.penetration_desc }}
                </p>

                <div class="table-container mini-scroll-table">
                  <table class="vol-table components-table">
                    <thead>
                      <tr>
                        <th>重仓代码</th>
                        <th>股票名称</th>
                        <th>持仓权重</th>
                        <th>最新价格</th>
                        <th>今日涨跌幅</th>
                        <th>MACD状态</th>
                        <th>RSI(6)</th>
                        <th>技术评分</th>
                        <th>多空定性</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="comp in techData.components" :key="comp.code">
                        <td class="font-mono">{{ comp.code }}</td>
                        <td><strong>{{ comp.name }}</strong></td>
                        <td class="font-mono text-cyan">{{ comp.weight?.toFixed(2) }}%</td>
                        <td class="font-mono">{{ comp.current ? comp.current.toFixed(2) : '-' }}</td>
                        <td class="font-mono" :class="comp.change_pct > 0 ? 'rise' : (comp.change_pct < 0 ? 'fall' : 'flat')">
                          {{ comp.change_pct > 0 ? '+' : '' }}{{ comp.change_pct?.toFixed(2) }}%
                        </td>
                        <td>
                          <span class="badge-status-sm" :class="comp.macd_status.includes('金叉') || comp.macd_status.includes('多头') ? 'status-green' : (comp.macd_status.includes('死叉') || comp.macd_status.includes('空头') ? 'status-red' : 'status-gray')">
                            {{ comp.macd_status }}
                          </span>
                        </td>
                        <td class="font-mono" :class="comp.rsi_val >= 75 ? 'rise' : (comp.rsi_val <= 25 ? 'fall' : '')">
                          {{ comp.rsi_val?.toFixed(1) }}
                        </td>
                        <td class="font-mono font-bold">{{ comp.score }}</td>
                        <td>
                          <span class="bias-pill" :class="comp.bias">
                            {{ comp.bias === 'bullish' ? '🟢 做多' : (comp.bias === 'bearish' ? '🔴 偏弱' : '🟡 观望') }}
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <!-- 右栏: 综合技术研判卡片 + 4维诊断矩阵 + AI买卖提示面板 -->
            <div class="tech-eval-column">
              <!-- 1. 综合技术研判与评分卡片 -->
              <div class="glass-card eval-summary-card">
                <div class="eval-header">
                  <h4 class="eval-title">🎯 量化技术综合研判</h4>
                  <span class="eval-grade-badge" :style="{ borderColor: techData.evaluation?.grade_color, color: techData.evaluation?.grade_color }">
                    {{ techData.evaluation?.grade }}
                  </span>
                </div>

                <!-- 得分与核心动作 -->
                <div class="score-display-row">
                  <div class="score-circle-box">
                    <span class="score-num font-mono" :style="{ color: techData.evaluation?.grade_color }">
                      {{ techData.evaluation?.score }}
                    </span>
                    <span class="score-max">/100分</span>
                  </div>
                  <div class="advice-box">
                    <span class="advice-title">💡 操盘策略建言</span>
                    <p class="advice-text">{{ techData.evaluation?.action_advice }}</p>
                  </div>
                </div>

                <!-- 支撑与阻力点位 -->
                <div class="support-resistance-grid">
                  <div class="level-card support-card">
                    <span class="level-label">🛡️ 关键支撑防守位</span>
                    <span class="level-val font-mono">{{ techData.evaluation?.support_price }} 元</span>
                    <span class="level-desc">跌破需防范破位风险</span>
                  </div>
                  <div class="level-card resistance-card">
                    <span class="level-label">🎯 关键压力突破位</span>
                    <span class="level-val font-mono">{{ techData.evaluation?.resistance_price }} 元</span>
                    <span class="level-desc">突破将打开上行空间</span>
                  </div>
                </div>

                <!-- 触发信号标签 -->
                <div class="triggered-signals-row" v-if="techData.evaluation?.signals?.length">
                  <span class="signals-label">⚡ 当前共振信号:</span>
                  <div class="signals-tags-wrap">
                    <span 
                      v-for="(sig, sIdx) in techData.evaluation.signals" 
                      :key="sIdx"
                      class="signal-badge"
                    >
                      {{ sig }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- 2. 核心指标 4 维诊断矩阵 -->
              <div class="indicators-matrix-grid">
                <!-- MACD -->
                <div class="glass-card ind-matrix-card">
                  <div class="matrix-card-top">
                    <span class="ind-icon">📊</span>
                    <strong class="ind-name">MACD 指标</strong>
                  </div>
                  <div class="ind-status-val text-cyan">{{ techData.evaluation?.macd_status }}</div>
                  <div class="ind-sub-info font-mono">
                    DIF: {{ techData.indicators?.macd?.dif?.slice(-1)[0]?.toFixed(3) }} | DEA: {{ techData.indicators?.macd?.dea?.slice(-1)[0]?.toFixed(3) }}
                  </div>
                </div>

                <!-- RSI -->
                <div class="glass-card ind-matrix-card">
                  <div class="matrix-card-top">
                    <span class="ind-icon">🌊</span>
                    <strong class="ind-name">RSI 强弱度</strong>
                  </div>
                  <div class="ind-status-val" :class="techData.indicators?.rsi?.RSI6?.slice(-1)[0] >= 80 ? 'rise' : (techData.indicators?.rsi?.RSI6?.slice(-1)[0] <= 20 ? 'fall' : '')">
                    {{ techData.evaluation?.rsi_status }}
                  </div>
                  <div class="ind-sub-info font-mono">
                    RSI(6): {{ techData.indicators?.rsi?.RSI6?.slice(-1)[0]?.toFixed(1) || '-' }} | RSI(12): {{ techData.indicators?.rsi?.RSI12?.slice(-1)[0]?.toFixed(1) || '-' }}
                  </div>
                </div>

                <!-- 量价形态 -->
                <div class="glass-card ind-matrix-card">
                  <div class="matrix-card-top">
                    <span class="ind-icon">⚡</span>
                    <strong class="ind-name">量价形态</strong>
                  </div>
                  <div class="ind-status-val text-yellow">{{ techData.indicators?.volume?.pattern }}</div>
                  <div class="ind-sub-info font-mono">
                    量比: {{ techData.indicators?.volume?.volume_ratio }} | {{ techData.indicators?.volume?.pattern_desc }}
                  </div>
                </div>

                <!-- 均线趋势 -->
                <div class="glass-card ind-matrix-card">
                  <div class="matrix-card-top">
                    <span class="ind-icon">📐</span>
                    <strong class="ind-name">均线趋势</strong>
                  </div>
                  <div class="ind-status-val text-green">{{ techData.evaluation?.ma_status }}</div>
                  <div class="ind-sub-info font-mono">
                    MA20: {{ techData.indicators?.ma?.MA20?.slice(-1)[0]?.toFixed(2) || '-' }} | MA60: {{ techData.indicators?.ma?.MA60?.slice(-1)[0]?.toFixed(2) || '-' }}
                  </div>
                </div>
              </div>

              <!-- 3. AI 智能操盘与买卖研判面板 (手动触发 + 双引擎 + 频次保护) -->
              <div class="glass-card ai-trading-card">
                <div class="ai-card-header">
                  <div class="header-left">
                    <span class="ai-icon">🤖</span>
                    <h4 class="ai-title">AI 智能操盘研判与买卖决策指引</h4>
                  </div>
                  <div class="engine-toggle-group">
                    <button 
                      class="engine-btn" 
                      :class="{ active: aiEngine === 'generic' }"
                      @click="aiEngine = 'generic'"
                      title="调用通用大模型 (DeepSeek/OpenAI规范)，进行结构化操盘点位深度推演"
                    >
                      🤖 通用大模型
                    </button>
                    <button 
                      class="engine-btn" 
                      :class="{ active: aiEngine === 'mx' }"
                      @click="aiEngine = 'mx'"
                      title="调用东方财富妙想金融AI权威数据知识库"
                    >
                      💎 东方财富妙想
                    </button>
                  </div>
                </div>

                <div class="ai-control-row">
                  <button 
                    class="btn btn-primary ai-trigger-btn" 
                    @click="handleTriggerAiAdvice(false)"
                    :disabled="loadingAi || aiCooldown > 0"
                  >
                    <span class="ai-spark" :class="{ rotating: loadingAi }">⚡</span>
                    <span>
                      {{ loadingAi ? 'AI 正在推演操盘点位...' : (aiCooldown > 0 ? `冷却中 (${aiCooldown}s)` : '生成 AI 智能买卖研判') }}
                    </span>
                  </button>
                  <span class="ai-quota-hint">
                    🔒 手动触发防扣费 · 15分钟自动缓存 · 30秒冷却
                  </span>
                </div>

                <!-- AI Loading State -->
                <div v-if="loadingAi" class="ai-loading-box">
                  <span class="spinner">⏳</span>
                  <span>正在综合 MACD 金叉/死叉、日线背离形态、量价突破及支撑压力位进行 AI 操盘推理...</span>
                </div>

                <!-- AI Result Presentation -->
                <div v-else-if="aiAdviceResult && aiAdviceResult.content" class="ai-result-content">
                  <div class="ai-meta-bar">
                    <span class="meta-tag">引擎: {{ aiAdviceResult.engine }}</span>
                    <span class="meta-time">🕒 生成时间: {{ aiAdviceResult.generated_at }}</span>
                    <span v-if="aiAdviceResult.cached" class="cached-pill">⚡ 缓存结果</span>
                    <button class="re-analyze-btn" @click="handleTriggerAiAdvice(true)" :disabled="loadingAi || aiCooldown > 0" title="忽略缓存，重新分析">
                      🔄 重新生成
                    </button>
                  </div>
                  <div class="ai-markdown-body" v-html="renderedAiMarkdown"></div>
                </div>

                <div v-else class="ai-placeholder-box">
                  <span class="placeholder-icon">💡</span>
                  <span>点击上方【生成 AI 智能买卖研判】按钮，大模型将为您输出包含操作定级、仓位控制、买入区间与防守止损线的专业操盘策略。</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick, inject } from 'vue'
import * as echarts from 'echarts'
import { marked } from 'marked'
import api from '../api'

const showToast = inject('showToast')

// 页面主要响应式数据
const refreshing = ref(false)
const loadingHoldings = ref(false)
const activeHoldingFilter = ref('all')
const activeFlowChartTab = ref('inflow') // 'inflow' (流入Top8动效飞线图), 'outflow' (流出Top8动效飞线图), 'sankey' (桑基图)
const chartLayoutMode = ref('stacked') // 'stacked' (通栏全景大屏模式，推荐), 'split' (左右双栏并排)
const selectedCodeToAdd = ref('')
let autoRefreshTimer = null

// 一级主页签与个股子面板切换
const activeMainTab = ref('overview') // 'overview' (今日概况) | 'stock_analysis' (个股数据分析)
const activeStockSubView = ref('technical') // 'technical' (深度技术分析与AI研判) | 'monitoring' (标的监控面板)

// 个股深度技术分析专属响应式状态
const selectedTechFilter = ref('all') // 'all' | 'stock' | 'fund'
const selectedTechCode = ref('')
const techSearchInput = ref('')
const loadingTechData = ref(false)
const techData = ref(null)
const techChartSubTab = ref('macd') // 'macd' | 'rsi' | 'kdj'
const techChartRef = ref(null)
let techChart = null
let techChartResizeObserver = null

// AI 操盘智能买卖研判状态
const aiEngine = ref('generic') // 'generic' (通用大模型) | 'mx' (东方财富妙想)
const loadingAi = ref(false)
const aiAdviceResult = ref(null)
const aiCooldown = ref(0)
let aiCooldownTimer = null

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

// 板块轮动全景看板状态
const activeRotationTab = ref('timeline') // 'timeline' | 'volume' | 'matrix'
const activeTimelineDayIndex = ref(4) // 默认选中最新一个交易日 (09-18 周五 主升)
const volumeChartRef = ref(null)
let volumeChart = null

const rotationTimelineData = reactive({
  stat_cards: [],
  timeline: [],
  volume_trend: null,
  sector_multi_day_volumes: null,
  heatmap_matrix: null,
  strategy_takeaways: [],
  provider_type: 'mx',
  source_label: '💎 东方财富妙想权威数据',
  is_rich: true
})

const currentTimelineDay = computed(() => {
  const list = rotationTimelineData.timeline || []
  if (!list.length) return null
  return list[activeTimelineDayIndex.value] || list[list.length - 1]
})

const getHeatmapCellClass = (val) => {
  if (!val) return ''
  const num = parseFloat(String(val).replace('%', '').replace('+', ''))
  if (isNaN(num)) return ''
  if (num >= 3.0) return 'heat-red-strong'
  if (num >= 1.5) return 'heat-red-medium'
  if (num > 0) return 'heat-red-light'
  if (num === 0) return 'heat-flat'
  if (num <= -1.5) return 'heat-green-strong'
  return 'heat-green-light'
}

const selectTimelineDay = (idx) => {
  activeTimelineDayIndex.value = idx
}

const switchRotationTab = (tab) => {
  activeRotationTab.value = tab
  if (tab === 'volume') {
    renderVolumeChart()
  }
}

// 本地持久化缓存键与交易时间判定
const STORAGE_KEY_HOLDINGS = 'lh_data_analysis_holdings_v2'
const STORAGE_KEY_OVERVIEW = 'lh_data_analysis_overview_v2'
const STORAGE_KEY_ROTATION_TIMELINE = 'lh_data_analysis_rotation_timeline_v2'

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
    const cachedTimeline = localStorage.getItem(STORAGE_KEY_ROTATION_TIMELINE)
    if (cachedTimeline) {
      const parsedTl = JSON.parse(cachedTimeline)
      if (parsedTl && typeof parsedTl === 'object') {
        Object.assign(rotationTimelineData, parsedTl)
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
    localStorage.setItem(STORAGE_KEY_ROTATION_TIMELINE, JSON.stringify(rotationTimelineData))
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

// ==========================================
// 个股深度技术分析与AI研判状态与方法
// ==========================================

const allTechAvailableHoldings = computed(() => {
  const map = new Map()
  for (const h of displayedHoldingsAnalysis.value) {
    if (h && h.code) map.set(h.code, h)
  }
  for (const h of holdingsList.value) {
    if (h && h.code && !map.has(h.code)) map.set(h.code, h)
  }
  return Array.from(map.values())
})

const allTechStockCount = computed(() => {
  return allTechAvailableHoldings.value.filter(h => h.type === 'stock').length
})

const allTechFundCount = computed(() => {
  return allTechAvailableHoldings.value.filter(h => h.type === 'fund').length
})

const filteredTechHoldingsForSelect = computed(() => {
  if (selectedTechFilter.value === 'stock') {
    return allTechAvailableHoldings.value.filter(h => h.type === 'stock')
  }
  if (selectedTechFilter.value === 'fund') {
    return allTechAvailableHoldings.value.filter(h => h.type === 'fund')
  }
  return allTechAvailableHoldings.value
})

const renderedAiMarkdown = computed(() => {
  if (!aiAdviceResult.value || !aiAdviceResult.value.content) return ''
  try {
    return marked.parse(aiAdviceResult.value.content)
  } catch (e) {
    return aiAdviceResult.value.content
  }
})

const switchMainTab = (tab) => {
  activeMainTab.value = tab
  if (tab === 'overview') {
    nextTick(() => {
      if (flowChart) flowChart.resize()
      if (volumeChart && activeRotationTab.value === 'volume') volumeChart.resize()
    })
  } else if (tab === 'stock_analysis') {
    nextTick(() => {
      if (!techData.value && allTechAvailableHoldings.value.length > 0) {
        const first = allTechAvailableHoldings.value[0]
        selectedTechCode.value = first.code
        loadTechAnalysis(first.code, false, first.type === 'fund')
      } else if (techData.value) {
        renderTechChart()
        if (techChart) techChart.resize()
      }
      setTimeout(() => {
        if (techChart) techChart.resize()
      }, 60)
    })
  }
}

const selectQuickTarget = (h) => {
  if (!h || !h.code) return
  selectedTechCode.value = h.code
  loadTechAnalysis(h.code, false, h.type === 'fund')
}

const handleSelectTechHolding = () => {
  if (!selectedTechCode.value) return
  const item = allTechAvailableHoldings.value.find(h => h.code === selectedTechCode.value)
  loadTechAnalysis(selectedTechCode.value, false, item ? item.type === 'fund' : null)
}

const handleSearchCustomCode = () => {
  const raw = (techSearchInput.value || '').trim()
  if (!raw) {
    showToast('请输入股票或基金代码')
    return
  }
  const cleanCode = raw.replace(/^[a-zA-Z]+/, '')
  if (cleanCode.length !== 6) {
    showToast('请输入正确的 6 位股票或基金代码')
    return
  }
  // Determine if it looks like a fund
  const isFund = cleanCode.startsWith('00') || cleanCode.startsWith('01') || cleanCode.startsWith('16') || cleanCode.startsWith('02') || cleanCode.startsWith('519')
  loadTechAnalysis(cleanCode, true, isFund)
}

const switchTechSubTab = (tab) => {
  techChartSubTab.value = tab
  nextTick(() => {
    renderTechChart()
    if (techChart) techChart.resize()
  })
}

const loadTechAnalysis = async (code, force = false, isFundHint = null) => {
  if (!code) return
  loadingTechData.value = true

  let isFund = false
  if (isFundHint !== null) {
    isFund = isFundHint
  } else {
    const found = allTechAvailableHoldings.value.find(h => h.code === code)
    if (found) {
      isFund = found.type === 'fund'
    } else {
      isFund = code.startsWith('00') || code.startsWith('01') || code.startsWith('16') || code.startsWith('02') || code.startsWith('519')
    }
  }

  try {
    const data = await api.getDataAnalysisTechnical(code, isFund, force)
    techData.value = data
    selectedTechCode.value = data.code
    aiAdviceResult.value = null

    nextTick(() => {
      renderTechChart()
      setTimeout(() => {
        if (techChart) techChart.resize()
      }, 60)
    })
  } catch (e) {
    console.error('获取技术分析失败:', e)
    showToast('获取标的技术分析失败: ' + (e.message || '网络异常'))
  } finally {
    loadingTechData.value = false
  }
}

const renderTechChart = () => {
  if (!techChartRef.value || !techData.value) return
  if (!techChart) {
    techChart = echarts.init(techChartRef.value)
  }

  const dates = techData.value.dates || []
  const klineRaw = techData.value.kline_data || []
  const isFund = techData.value.is_fund
  const ind = techData.value.indicators || {}
  const ma = ind.ma || {}
  const macd = ind.macd || {}
  const rsi = ind.rsi || {}
  const kdj = ind.kdj || {}
  const volMetrics = ind.volume || {}
  const divergence = techData.value.divergence || {}

  // Candlestick format: [open, close, lowest, highest]
  const klineValues = klineRaw.map(item => [item[0], item[1], item[2], item[3]])
  const volumes = klineRaw.map(item => {
    const isUp = item[1] >= item[0]
    return {
      value: item[4],
      itemStyle: {
        color: isUp ? '#f85149' : '#00ff88'
      }
    }
  })

  // Mark points for Divergence on Candlestick
  const markPointsCandle = []
  if (divergence.top_divergence) {
    markPointsCandle.push({
      name: '顶背离',
      coord: [divergence.top_divergence.date2, divergence.top_divergence.price2],
      value: '⚠️ 顶背离',
      itemStyle: { color: '#f85149' },
      symbol: 'pin',
      symbolSize: 42
    })
  }
  if (divergence.bottom_divergence) {
    markPointsCandle.push({
      name: '底背离',
      coord: [divergence.bottom_divergence.date2, divergence.bottom_divergence.price2],
      value: '🔥 底背离',
      itemStyle: { color: '#00ff88' },
      symbol: 'pin',
      symbolSize: 42
    })
  }

  // Tooltip
  const tooltip = {
    trigger: 'axis',
    axisPointer: { type: 'cross', lineStyle: { color: '#388bfd', width: 1, type: 'dashed' } },
    backgroundColor: 'rgba(15, 23, 42, 0.95)',
    borderColor: '#30363d',
    borderWidth: 1,
    textStyle: { color: '#e6edf3', fontSize: 12 },
    formatter: function (params) {
      if (!params || !params.length) return ''
      const d = params[0].axisValue
      let res = `<div style="font-weight:bold;margin-bottom:4px;color:#58a6ff;">📅 ${d}</div>`
      for (const p of params) {
        if (p.seriesName === 'K线' || p.seriesName === '单位净值') {
          const val = p.value
          if (Array.isArray(val)) {
            const o = val[1], c = val[2], l = val[3], h = val[4]
            const chg = o > 0 ? ((c - o) / o * 100).toFixed(2) : '0.00'
            const col = c >= o ? '#f85149' : '#00ff88'
            res += `<div style="color:${col};">开: ${o} | 收: ${c} (${chg}%)<br/>低: ${l} | 高: ${h}</div>`
          } else if (val !== undefined && val !== null) {
            res += `<div>净值: <strong>${val}</strong></div>`
          }
        } else if (p.seriesName === '成交量') {
          const v = p.value
          res += `<div>成交量: ${v ? (v >= 10000 ? (v / 10000).toFixed(1) + '万手' : v + '手') : '0'}</div>`
        } else if (p.seriesName === 'MACD柱') {
          const v = p.value
          const col = v >= 0 ? '#f85149' : '#00ff88'
          res += `<div style="color:${col};">MACD柱: ${v}</div>`
        } else if (typeof p.value === 'number') {
          res += `<div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:5px;"></span>${p.seriesName}: ${p.value.toFixed(2)}</div>`
        }
      }
      return res
    }
  }

  // 3-tier vertical grid layout
  const grids = [
    { left: 52, right: 20, top: 32, height: '48%' },
    { left: 52, right: 20, top: '60%', height: '14%' },
    { left: 52, right: 20, top: '78%', height: '16%' }
  ]

  const xAxes = [
    {
      type: 'category',
      data: dates,
      gridIndex: 0,
      boundaryGap: true,
      axisLine: { lineStyle: { color: '#30363d' } },
      axisLabel: { show: false },
      splitLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.04)' } }
    },
    {
      type: 'category',
      data: dates,
      gridIndex: 1,
      boundaryGap: true,
      axisLine: { lineStyle: { color: '#30363d' } },
      axisLabel: { show: false },
      splitLine: { show: false }
    },
    {
      type: 'category',
      data: dates,
      gridIndex: 2,
      boundaryGap: true,
      axisLine: { lineStyle: { color: '#30363d' } },
      axisLabel: { color: '#8b949e', fontSize: 11 },
      splitLine: { show: false }
    }
  ]

  const yAxes = [
    {
      type: 'value',
      scale: true,
      gridIndex: 0,
      axisLine: { show: false },
      axisLabel: { color: '#8b949e' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } }
    },
    {
      type: 'value',
      scale: true,
      gridIndex: 1,
      splitNumber: 2,
      axisLine: { show: false },
      axisLabel: { show: false },
      splitLine: { show: false }
    },
    {
      type: 'value',
      scale: true,
      gridIndex: 2,
      splitNumber: 3,
      axisLine: { show: false },
      axisLabel: { color: '#8b949e', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } }
    }
  ]

  const series = []

  // Main Candlestick or NAV line
  if (!isFund) {
    series.push({
      name: 'K线',
      type: 'candlestick',
      data: klineValues,
      xAxisIndex: 0,
      yAxisIndex: 0,
      itemStyle: {
        color: '#f85149',
        color0: '#00ff88',
        borderColor: '#f85149',
        borderColor0: '#00ff88'
      },
      markPoint: {
        data: markPointsCandle
      }
    })
  } else {
    series.push({
      name: '单位净值',
      type: 'line',
      data: klineRaw.map(r => r[1]),
      xAxisIndex: 0,
      yAxisIndex: 0,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#58a6ff', width: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(88, 166, 255, 0.3)' },
          { offset: 1, color: 'rgba(88, 166, 255, 0.0)' }
        ])
      },
      markPoint: {
        data: markPointsCandle
      }
    })
  }

  // MA Lines
  const maList = [
    { key: 'MA5', name: 'MA5', color: '#58a6ff' },
    { key: 'MA10', name: 'MA10', color: '#e3b341' },
    { key: 'MA20', name: 'MA20', color: '#bc8cff' },
    { key: 'MA60', name: 'MA60', color: '#f0883e' }
  ]
  for (const m of maList) {
    if (ma[m.key]) {
      series.push({
        name: m.name,
        type: 'line',
        data: ma[m.key],
        xAxisIndex: 0,
        yAxisIndex: 0,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: m.color, width: 1.2 }
      })
    }
  }

  // Volume Bar
  series.push({
    name: '成交量',
    type: 'bar',
    data: volumes,
    xAxisIndex: 1,
    yAxisIndex: 1,
    barWidth: '60%'
  })

  // Volume MAs
  if (volMetrics.vol_ma5) {
    series.push({
      name: 'VOL5',
      type: 'line',
      data: volMetrics.vol_ma5,
      xAxisIndex: 1,
      yAxisIndex: 1,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#e3b341', width: 1 }
    })
  }
  if (volMetrics.vol_ma10) {
    series.push({
      name: 'VOL10',
      type: 'line',
      data: volMetrics.vol_ma10,
      xAxisIndex: 1,
      yAxisIndex: 1,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#58a6ff', width: 1 }
    })
  }

  // Sub-indicators (MACD / RSI / KDJ)
  if (techChartSubTab.value === 'macd' && macd.dif) {
    series.push({
      name: 'DIF',
      type: 'line',
      data: macd.dif,
      xAxisIndex: 2,
      yAxisIndex: 2,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#58a6ff', width: 1.5 }
    })
    series.push({
      name: 'DEA',
      type: 'line',
      data: macd.dea,
      xAxisIndex: 2,
      yAxisIndex: 2,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#e3b341', width: 1.5 }
    })
    series.push({
      name: 'MACD柱',
      type: 'bar',
      data: (macd.bar || []).map(b => ({
        value: b,
        itemStyle: { color: b >= 0 ? '#f85149' : '#00ff88' }
      })),
      xAxisIndex: 2,
      yAxisIndex: 2,
      barWidth: '50%'
    })
  } else if (techChartSubTab.value === 'rsi' && rsi.RSI6) {
    series.push({
      name: 'RSI(6)',
      type: 'line',
      data: rsi.RSI6,
      xAxisIndex: 2,
      yAxisIndex: 2,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#e3b341', width: 1.5 },
      markLine: {
        data: [
          { yAxis: 80, lineStyle: { color: 'rgba(248, 81, 73, 0.6)', type: 'dashed' }, label: { formatter: '超买80' } },
          { yAxis: 20, lineStyle: { color: 'rgba(0, 255, 136, 0.6)', type: 'dashed' }, label: { formatter: '超卖20' } }
        ]
      }
    })
    if (rsi.RSI12) {
      series.push({
        name: 'RSI(12)',
        type: 'line',
        data: rsi.RSI12,
        xAxisIndex: 2,
        yAxisIndex: 2,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#58a6ff', width: 1.2 }
      })
    }
    if (rsi.RSI24) {
      series.push({
        name: 'RSI(24)',
        type: 'line',
        data: rsi.RSI24,
        xAxisIndex: 2,
        yAxisIndex: 2,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#bc8cff', width: 1.2 }
      })
    }
  } else if (techChartSubTab.value === 'kdj' && kdj.k) {
    series.push({
      name: 'K',
      type: 'line',
      data: kdj.k,
      xAxisIndex: 2,
      yAxisIndex: 2,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#58a6ff', width: 1.5 }
    })
    series.push({
      name: 'D',
      type: 'line',
      data: kdj.d,
      xAxisIndex: 2,
      yAxisIndex: 2,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#e3b341', width: 1.5 }
    })
    series.push({
      name: 'J',
      type: 'line',
      data: kdj.j,
      xAxisIndex: 2,
      yAxisIndex: 2,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#bc8cff', width: 1.5 },
      markLine: {
        data: [
          { yAxis: 100, lineStyle: { color: 'rgba(248, 81, 73, 0.6)', type: 'dashed' }, label: { formatter: '超买100' } },
          { yAxis: 0, lineStyle: { color: 'rgba(0, 255, 136, 0.6)', type: 'dashed' }, label: { formatter: '超卖0' } }
        ]
      }
    })
  }

  const dataZoom = [
    {
      type: 'inside',
      xAxisIndex: [0, 1, 2],
      start: Math.max(0, 100 - (60 / (dates.length || 1)) * 100),
      end: 100
    },
    {
      type: 'slider',
      xAxisIndex: [0, 1, 2],
      bottom: 4,
      height: 14,
      borderColor: 'transparent',
      backgroundColor: 'rgba(255,255,255,0.05)',
      fillerColor: 'rgba(88, 166, 255, 0.2)',
      textStyle: { color: 'transparent' },
      handleStyle: { color: '#58a6ff' },
      start: Math.max(0, 100 - (60 / (dates.length || 1)) * 100),
      end: 100
    }
  ]

  const option = {
    animation: false,
    tooltip: tooltip,
    axisPointer: { link: [{ xAxisIndex: 'all' }] },
    grid: grids,
    xAxis: xAxes,
    yAxis: yAxes,
    dataZoom: dataZoom,
    series: series
  }

  techChart.setOption(option, true)
  techChart.resize()
  requestAnimationFrame(() => {
    if (techChart) techChart.resize()
  })
}

const handleTriggerAiAdvice = async (force = false) => {
  if (!techData.value || loadingAi.value || aiCooldown.value > 0) return
  loadingAi.value = true

  try {
    const payload = {
      code: techData.value.code,
      name: techData.value.name,
      is_fund: Boolean(techData.value.is_fund),
      engine: aiEngine.value,
      force_refresh: force
    }
    const res = await api.generateDataAnalysisTechnicalAi(payload)
    if (res.success) {
      aiAdviceResult.value = res
      if (!res.cached) {
        showToast('AI 操盘智能研判生成成功')
      } else {
        showToast('已载入最近 15 分钟内的智能研判分析')
      }
      startAiCooldown(30)
    } else {
      showToast(res.error || 'AI 分析生成异常，请稍后重试')
    }
  } catch (err) {
    console.error('AI 研判生成失败:', err)
    showToast('AI 接口调用失败: ' + (err.message || '网络超时'))
  } finally {
    loadingAi.value = false
  }
}

const startAiCooldown = (seconds = 30) => {
  aiCooldown.value = seconds
  if (aiCooldownTimer) clearInterval(aiCooldownTimer)
  aiCooldownTimer = setInterval(() => {
    if (aiCooldown.value > 0) {
      aiCooldown.value--
    } else {
      clearInterval(aiCooldownTimer)
      aiCooldownTimer = null
    }
  }, 1000)
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

const renderVolumeChart = () => {
  nextTick(() => {
    if (!volumeChartRef.value) return
    if (!volumeChart) {
      volumeChart = echarts.init(volumeChartRef.value)
    }
    const trend = rotationTimelineData.volume_trend || {
      dates: ["09-14", "09-15", "09-16", "09-17", "09-18"],
      volumes: [16430, 16252, 18525, 18365, 20929],
      labels: ["1.64万亿", "1.61万亿(地量)", "1.85万亿", "1.84万亿", "2.09万亿(放量)"]
    }
    const dates = trend.dates || []
    const rawVols = trend.volumes || []
    const validVols = rawVols.filter(v => typeof v === 'number' && v > 0)

    // 动态计算真实的地量与放量拐点，杜绝固定坐标错位
    let minVol = Infinity, minIdx = -1
    let maxVol = -Infinity, maxIdx = -1
    rawVols.forEach((v, idx) => {
      if (typeof v === 'number' && v > 0) {
        if (v < minVol) {
          minVol = v
          minIdx = idx
        }
        if (v > maxVol) {
          maxVol = v
          maxIdx = idx
        }
      }
    })

    const markPointData = []
    if (minIdx >= 0) {
      markPointData.push({
        name: '地量探底',
        coord: [minIdx, minVol],
        value: '地量',
        itemStyle: { color: '#f59e0b' }
      })
    }
    if (maxIdx >= 0 && maxIdx !== minIdx) {
      markPointData.push({
        name: '巨量主升',
        coord: [maxIdx, maxVol],
        value: '放量',
        itemStyle: { color: '#ef4444' }
      })
    }

    const minVal = validVols.length ? Math.min(...validVols) * 0.90 : 10000
    const maxVal = validVols.length ? Math.max(...validVols) * 1.08 : 25000

    const option = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(22, 27, 34, 0.95)',
        borderColor: 'rgba(255, 255, 255, 0.15)',
        textStyle: { color: '#e6edf3' },
        formatter: (params) => {
          if (!params || !params.length) return ''
          const item = params[0]
          const idx = item.dataIndex
          const label = trend.labels && trend.labels[idx] ? trend.labels[idx] : `${item.value} 亿元`
          return `<b>2026-${item.name}</b><br/>
                  全市场成交额: <span style="color:#ef4444;font-weight:bold;">${item.value} 亿元 (${label})</span>`
        }
      },
      grid: {
        top: 36,
        right: 25,
        bottom: 30,
        left: 58
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.15)' } },
        axisLabel: { color: '#94a3b8', fontSize: 11 }
      },
      yAxis: {
        type: 'value',
        min: Math.floor(minVal / 1000) * 1000,
        max: Math.ceil(maxVal / 1000) * 1000,
        axisLabel: {
          color: '#94a3b8',
          fontSize: 10,
          formatter: (val) => `${(val / 10000).toFixed(1)}万亿`
        },
        splitLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.06)',
            type: 'dashed'
          }
        }
      },
      series: [
        {
          name: '全市场成交额',
          type: 'line',
          smooth: 0.3,
          symbol: 'circle',
          symbolSize: 8,
          itemStyle: { color: '#ef4444' },
          lineStyle: { width: 3, color: '#ef4444' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(239, 68, 68, 0.4)' },
              { offset: 1, color: 'rgba(239, 68, 68, 0.0)' }
            ])
          },
          markPoint: {
            symbol: 'pin',
            symbolSize: 42,
            data: markPointData
          },
          data: rawVols
        }
      ]
    }
    // notMerge: true 确保每次刷新均能完全重绘，不残留旧 markPoint
    volumeChart.setOption(option, true)
    volumeChart.resize()
  })
}

// 监听成交量数据与激活Tab变化，确保图表实时跟随重绘
watch(
  () => [rotationTimelineData.volume_trend, activeRotationTab.value],
  ([newTrend, newTab]) => {
    if (newTab === 'volume' && newTrend) {
      renderVolumeChart()
    }
  },
  { deep: true }
)

const loadRotationTimeline = async (force = false) => {
  try {
    const res = await api.getDataAnalysisSectorRotationTimeline(force)
    if (res) {
      Object.assign(rotationTimelineData, res)
      if (rotationTimelineData.timeline && rotationTimelineData.timeline.length) {
        if (activeTimelineDayIndex.value >= rotationTimelineData.timeline.length) {
          activeTimelineDayIndex.value = rotationTimelineData.timeline.length - 1
        }
      }
      saveCacheToStorage()
      if (activeRotationTab.value === 'volume') {
        renderVolumeChart()
      }
    }
  } catch (e) {
    console.error('加载板块轮动全景失败:', e)
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
      loadRotationTimeline(true),
      loadSectorFlow(),
      loadHoldingsAndAnalysis(false),
      loadStatusConfig()
    ])
    saveCacheToStorage()
    if (activeRotationTab.value === 'volume') {
      renderVolumeChart()
    }
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
  if (volumeChart) {
    volumeChart.resize()
  }
  if (techChart) {
    techChart.resize()
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
  // 随后均在后台拉取全量最新数据（包括概览、板块轮动全景以及个股/基金监控面板），静默平滑替换
  await Promise.all([
    loadOverview(),
    loadSectorRotation(),
    loadRotationTimeline(),
    loadSectorFlow(),
    loadHoldingsAndAnalysis(hasCache)
  ])

  // 3. 初始化默认个股技术分析标的
  if (allTechAvailableHoldings.value.length > 0 && !techData.value) {
    const defaultTarget = allTechAvailableHoldings.value[0]
    selectedTechCode.value = defaultTarget.code
    loadTechAnalysis(defaultTarget.code, false, defaultTarget.type === 'fund')
  }

  // 4. 交易时间内跟随刷新机制：每 30 秒自动在后台静默获取最新实盘分笔资金流并平滑更新看板
  autoRefreshTimer = setInterval(async () => {
    if (isMarketTradingTime() && !refreshing.value) {
      try {
        await Promise.all([
          loadOverview(),
          loadSectorRotation(),
          loadRotationTimeline(),
          loadSectorFlow(),
          loadHoldingsAndAnalysis(true)
        ])
        saveCacheToStorage()
      } catch (err) {
        console.debug('自动静默刷新错误:', err)
      }
    }
  }, 30000)

  // 5. 监听图表容器尺寸动态变化 (彻底解决Tab切换或容器初次展开时宽高为0导致的图表塌缩)
  if (techChartRef.value && typeof ResizeObserver !== 'undefined') {
    techChartResizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 50 && entry.contentRect.height > 50) {
          if (techChart) {
            techChart.resize()
          } else if (techData.value) {
            renderTechChart()
          }
        }
      }
    })
    techChartResizeObserver.observe(techChartRef.value)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (techChartResizeObserver) {
    techChartResizeObserver.disconnect()
    techChartResizeObserver = null
  }
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
  if (flowChart) {
    flowChart.dispose()
    flowChart = null
  }
  if (volumeChart) {
    volumeChart.dispose()
    volumeChart = null
  }
  if (techChart) {
    techChart.dispose()
    techChart = null
  }
  if (aiCooldownTimer) {
    clearInterval(aiCooldownTimer)
    aiCooldownTimer = null
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

/* ============================================================
   A股板块轮动时间事件图与交易量全景看板 专属样式
   ============================================================ */
.rotation-timeline-section {
  display: flex;
  flex-direction: column;
}

.title-with-badge {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.rotation-stat-badges {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.stat-pill-badge {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-glass);
  border-radius: 10px;
  padding: 6px 14px;
  text-align: center;
  min-width: 110px;
  backdrop-filter: blur(8px);
}

.stat-pill-label {
  font-size: 0.72rem;
  color: var(--text-secondary);
  margin-bottom: 2px;
}

.stat-pill-val {
  font-size: 1.05rem;
  font-weight: 800;
  font-family: monospace;
}

.stat-pill-sub {
  font-size: 0.68rem;
  color: var(--text-secondary);
}

.rotation-tabs-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.rotation-tabs-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.rotation-tab-btn {
  padding: 8px 16px;
  border-radius: 10px;
  font-size: 0.84rem;
  font-weight: 600;
  border: 1px solid var(--border-glass);
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-secondary);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.rotation-tab-btn:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.2);
}

.rotation-tab-btn.active {
  color: #ff4444;
  border-color: rgba(255, 68, 68, 0.5);
  background: rgba(255, 68, 68, 0.12);
  box-shadow: 0 0 12px rgba(255, 68, 68, 0.2);
}

.rotation-tab-hint {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.generic-notice-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(0, 212, 255, 0.08);
  border: 1px solid rgba(0, 212, 255, 0.25);
  border-radius: 10px;
  padding: 10px 16px;
  font-size: 0.82rem;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.generic-notice-banner .notice-icon {
  font-size: 1.2rem;
}

.generic-notice-banner .notice-content {
  flex: 1;
}

.generic-notice-banner .btn {
  white-space: nowrap;
}

/* 时间轴步进器节点按钮 */
.timeline-stepper-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}

.stepper-node-btn {
  background: var(--bg-card);
  border: 1px solid var(--border-glass);
  border-radius: 12px;
  padding: 12px;
  text-align: left;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.stepper-node-btn:hover {
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.05);
}

.stepper-node-btn.is-active {
  border-color: #ff4444;
  background: rgba(255, 68, 68, 0.12);
  box-shadow: 0 4px 20px rgba(255, 68, 68, 0.2);
}

.node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.node-date {
  font-size: 0.72rem;
  color: var(--text-secondary);
  font-family: monospace;
}

.node-phase-tag {
  font-size: 0.65rem;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: bold;
}

.phase-defense .node-phase-tag {
  background: rgba(148, 163, 184, 0.2);
  color: #94a3b8;
}

.phase-bottom .node-phase-tag {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.phase-breakout .node-phase-tag {
  background: rgba(239, 68, 68, 0.2);
  color: #ff4444;
}

.phase-diverge .node-phase-tag {
  background: rgba(168, 85, 247, 0.2);
  color: #c084fc;
}

.phase-surge .node-phase-tag {
  background: #ef4444;
  color: #ffffff;
}

.node-title {
  font-size: 0.88rem;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 2px;
}

.node-vol {
  font-size: 0.72rem;
  color: var(--text-secondary);
  font-family: monospace;
}

.stepper-node-btn.is-active .node-vol {
  color: #ff8888;
  font-weight: 600;
}

/* 每日深挖复盘看板 */
.day-detail-card {
  padding: 20px;
  border-radius: 16px;
  margin-bottom: 16px;
}

.day-detail-grid {
  display: grid;
  grid-template-columns: 7fr 5fr;
  gap: 20px;
}

.day-detail-header {
  border-bottom: 1px solid var(--border-glass);
  padding-bottom: 12px;
  margin-bottom: 14px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 8px;
}

.day-badge-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.day-badge {
  background: #ff4444;
  color: #ffffff;
  font-size: 0.74rem;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
}

.day-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
}

.day-breadth {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

/* 催化剂 */
.detail-catalyst-box {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-glass);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 14px;
}

.catalyst-header {
  font-size: 0.8rem;
  font-weight: 700;
  color: #f59e0b;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.catalyst-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.catalyst-list li {
  font-size: 0.78rem;
  color: var(--text-primary);
  line-height: 1.55;
  position: relative;
  padding-left: 14px;
}

.catalyst-list li::before {
  content: "•";
  position: absolute;
  left: 0;
  color: #f59e0b;
  font-weight: bold;
}

/* 领跑 / 失血卡片 */
.leaders-laggers-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
}

.sector-group-card {
  border-radius: 10px;
  padding: 12px;
}

.leaders-card {
  background: rgba(239, 68, 68, 0.05);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.laggers-card {
  background: rgba(0, 255, 136, 0.05);
  border: 1px solid rgba(0, 255, 136, 0.2);
}

.group-header {
  font-size: 0.78rem;
  font-weight: 700;
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.group-header.text-red {
  color: #ff4444;
}

.group-header.text-green {
  color: #00ff88;
}

.group-sub {
  font-weight: normal;
  font-size: 0.68rem;
  color: var(--text-secondary);
}

.group-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.group-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.75rem;
}

.item-name-wrap {
  display: flex;
  flex-direction: column;
}

.item-name {
  color: #ffffff;
  font-size: 0.78rem;
}

.item-desc {
  color: var(--text-secondary);
  font-size: 0.68rem;
  margin-top: 1px;
}

.item-val.rise {
  color: #ff4444;
  font-weight: 700;
  font-family: monospace;
}

.item-val.fall {
  color: #00ff88;
  font-weight: 700;
  font-family: monospace;
}

.capital-flow-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 0.76rem;
  line-height: 1.55;
}

.capital-label {
  font-weight: 700;
  color: #ffffff;
}

.capital-text {
  color: var(--text-secondary);
}

/* 侧边成交额与标杆股 */
.day-detail-side {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-glass);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.side-vol-header,
.side-stocks-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-glass);
  padding-bottom: 6px;
  margin-bottom: 10px;
  font-size: 0.8rem;
  font-weight: 700;
  color: #ffffff;
}

.side-vol-total {
  font-size: 0.75rem;
  color: #ff4444;
}

.stocks-sub {
  font-size: 0.68rem;
  font-weight: normal;
  color: var(--text-secondary);
}

.side-vol-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.vol-bar-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.bar-info-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.74rem;
}

.bar-name {
  color: var(--text-primary);
}

.bar-vol {
  color: var(--text-secondary);
}

.bar-track {
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}

.side-stocks-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stock-item-pill {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-glass);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 0.74rem;
  display: flex;
  flex-direction: column;
}

.stock-name {
  color: #ffffff;
  font-weight: 600;
}

.stock-desc {
  color: var(--text-secondary);
  font-size: 0.68rem;
  margin-top: 1px;
}

/* 成交量对比视图 */
.volume-comparison-grid {
  display: grid;
  grid-template-columns: 7fr 5fr;
  gap: 16px;
  margin-bottom: 16px;
}

.vol-chart-card,
.vol-table-card {
  padding: 20px;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  gap: 10px;
  flex-wrap: wrap;
}

.card-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 2px 0;
}

.card-desc {
  font-size: 0.72rem;
  color: var(--text-secondary);
  margin: 0;
}

.turning-badge {
  font-size: 0.72rem;
  font-weight: bold;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(239, 68, 68, 0.15);
  color: #ff4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
  white-space: nowrap;
}

.vol-chart-wrapper {
  height: 280px;
  width: 100%;
}

.volume-trend-chart {
  height: 100%;
  width: 100%;
}

.mini-scroll-table {
  max-height: 220px;
  overflow-y: auto;
  border: 1px solid var(--border-glass);
  border-radius: 8px;
}

.vol-table {
  font-size: 0.76rem;
}

.vol-table th,
.vol-table td {
  padding: 8px 10px;
}

.row-highlight {
  background: rgba(255, 68, 68, 0.04);
}

.insight-callout {
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 0.75rem;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #ff8888;
  line-height: 1.55;
}

/* 热力矩阵视图 */
.matrix-card {
  padding: 20px;
  border-radius: 16px;
  margin-bottom: 16px;
}

.matrix-legend {
  display: flex;
  gap: 12px;
  font-size: 0.74rem;
  align-items: center;
}

.legend-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-secondary);
}

.chip-color {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}

.chip-color.deep-red {
  background: rgba(239, 68, 68, 0.85);
}

.chip-color.light-red {
  background: rgba(239, 68, 68, 0.4);
}

.chip-color.deep-green {
  background: rgba(0, 255, 136, 0.85);
}

.matrix-table {
  font-size: 0.78rem;
}

.matrix-table th,
.matrix-table td {
  padding: 10px 12px;
}

.heat-cell {
  border-radius: 4px;
  transition: background 0.2s;
  font-family: monospace;
}

.heat-red-strong {
  background: rgba(239, 68, 68, 0.32);
  color: #ff5252;
}

.heat-red-medium {
  background: rgba(239, 68, 68, 0.18);
  color: #ff7575;
}

.heat-red-light {
  background: rgba(239, 68, 68, 0.08);
  color: #ffa0a0;
}

.heat-flat {
  color: var(--text-secondary);
}

.heat-green-strong {
  background: rgba(0, 255, 136, 0.25);
  color: #00ff88;
}

.heat-green-light {
  background: rgba(0, 255, 136, 0.12);
  color: #4ade80;
}

/* 核心复盘策略要点卡片 */
.takeaways-card {
  padding: 16px 20px;
  border-radius: 14px;
  margin-top: 16px;
}

.takeaways-header {
  font-size: 0.88rem;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.takeaways-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.takeaway-item {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-glass);
  border-radius: 10px;
  padding: 12px 14px;
}

.takeaway-title {
  font-size: 0.82rem;
  font-weight: 700;
  margin-bottom: 6px;
}

.takeaway-desc {
  font-size: 0.74rem;
  color: var(--text-secondary);
  line-height: 1.55;
  margin: 0;
}

@media (max-width: 1024px) {
  .day-detail-grid {
    grid-template-columns: 1fr;
  }
  .volume-comparison-grid {
    grid-template-columns: 1fr;
  }
  .takeaways-grid {
    grid-template-columns: 1fr;
  }
  .timeline-stepper-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .timeline-stepper-grid {
    grid-template-columns: 1fr;
  }
  .leaders-laggers-grid {
    grid-template-columns: 1fr;
  }
}
/* ===================================================
   TOP-LEVEL PAGE TABS & STOCK ANALYSIS STYLES
   =================================================== */
.main-page-tabs-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.main-tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  background: rgba(22, 27, 34, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
  backdrop-filter: blur(12px);
  text-align: left;
}

.main-tab-btn:hover {
  background: rgba(30, 41, 59, 0.85);
  border-color: rgba(88, 166, 255, 0.35);
  transform: translateY(-2px);
}

.main-tab-btn.active {
  background: linear-gradient(135deg, rgba(30, 58, 138, 0.45) 0%, rgba(15, 23, 42, 0.85) 100%);
  border-color: #388bfd;
  box-shadow: 0 0 20px rgba(56, 139, 253, 0.25);
}

.main-tab-btn .tab-icon {
  font-size: 1.8rem;
}

.main-tab-btn .tab-text-wrap {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.main-tab-btn .tab-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-primary);
}

.main-tab-btn.active .tab-title {
  color: #58a6ff;
}

.main-tab-btn .tab-subtitle {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

/* SUB TABS BAR */
.stock-subtabs-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.subtabs-group {
  display: flex;
  background: rgba(13, 17, 23, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 4px;
  gap: 4px;
}

.subtab-btn {
  padding: 8px 18px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.subtab-btn:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.04);
}

.subtab-btn.active {
  background: #238636;
  color: #ffffff;
  box-shadow: 0 0 10px rgba(35, 134, 54, 0.4);
}

.subtab-hint {
  font-size: 0.82rem;
  color: var(--text-secondary);
}

/* TECH TOOLBAR */
.tech-toolbar-card {
  padding: 16px 20px;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.tech-toolbar-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
}

.toolbar-left, .toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.mini-pills .pill-btn {
  padding: 5px 12px;
  font-size: 0.82rem;
}

.tech-dropdown {
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  color: var(--text-primary);
  padding: 7px 14px;
  font-size: 0.88rem;
  min-width: 260px;
  cursor: pointer;
  outline: none;
}

.code-search-box {
  display: flex;
  align-items: center;
  gap: 6px;
}

.code-input {
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  color: var(--text-primary);
  padding: 7px 12px;
  font-size: 0.88rem;
  width: 210px;
  outline: none;
}

.code-input:focus {
  border-color: #58a6ff;
}

.quick-tags-row {
  display: flex;
  align-items: center;
  gap: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 10px;
}

.quick-label {
  font-size: 0.8rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

.quick-tags-list {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.quick-tag-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.8rem;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}

.quick-tag-btn:hover, .quick-tag-btn.active {
  background: rgba(56, 139, 253, 0.2);
  border-color: #388bfd;
}

/* SNAPSHOT BANNER */
.target-snapshot-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  margin-bottom: 20px;
  border-left: 5px solid #388bfd;
  flex-wrap: wrap;
  gap: 20px;
}

.target-snapshot-banner.rise {
  border-left-color: #f85149;
}

.target-snapshot-banner.fall {
  border-left-color: #00ff88;
}

.snapshot-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.snapshot-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.type-pill {
  padding: 3px 8px;
  font-size: 0.75rem;
  border-radius: 4px;
  font-weight: 600;
  background: rgba(88, 166, 255, 0.15);
  color: #58a6ff;
  border: 1px solid rgba(88, 166, 255, 0.3);
}

.type-pill.fund {
  background: rgba(210, 153, 34, 0.15);
  color: #e3b341;
  border-color: rgba(210, 153, 34, 0.3);
}

.target-title-name {
  font-size: 1.4rem;
  font-weight: 800;
  margin: 0;
  color: var(--text-primary);
}

.target-title-code {
  font-size: 1rem;
  color: var(--text-secondary);
}

.snapshot-price-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.live-price {
  font-size: 2rem;
  font-weight: 800;
}

.live-chg {
  font-size: 1.25rem;
  font-weight: 700;
}

.snapshot-stats-grid {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.snap-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.snap-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.snap-val {
  font-size: 0.98rem;
  font-weight: 700;
  font-family: var(--font-mono, monospace);
}

/* DIVERGENCE ALERT BOX */
.divergence-alert-box {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px 20px;
  border-radius: 12px;
  margin-bottom: 20px;
  backdrop-filter: blur(10px);
}

.divergence-alert-box.bottom-alert {
  background: linear-gradient(135deg, rgba(0, 255, 136, 0.1) 0%, rgba(13, 17, 23, 0.8) 100%);
  border: 1px solid #00ff88;
  box-shadow: 0 0 16px rgba(0, 255, 136, 0.2);
}

.divergence-alert-box.top-alert {
  background: linear-gradient(135deg, rgba(248, 81, 73, 0.12) 0%, rgba(13, 17, 23, 0.8) 100%);
  border: 1px solid #f85149;
  box-shadow: 0 0 16px rgba(248, 81, 73, 0.2);
}

.alert-icon-wrap {
  font-size: 2rem;
}

.alert-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.alert-title {
  font-size: 1.05rem;
  color: var(--text-primary);
}

.alert-type-badge {
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  font-size: 0.78rem;
  color: var(--text-primary);
}

.alert-desc {
  font-size: 0.88rem;
  color: var(--text-secondary);
  margin: 0 0 8px 0;
  line-height: 1.5;
}

.alert-action {
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 6px;
}

.action-tag {
  font-weight: 700;
  color: #e3b341;
}

/* TECH CONTENT GRID */
.tech-content-grid {
  display: grid;
  grid-template-columns: 7fr 5fr;
  gap: 20px;
  min-width: 0;
}

.tech-chart-column, .tech-eval-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
  width: 100%;
}

/* CHART CARD */
.chart-main-card {
  padding: 16px 20px;
  min-width: 0;
  width: 100%;
  box-sizing: border-box;
}

.chart-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 12px;
}

.chart-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chart-title {
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0;
}

.chart-timeframe-tag {
  font-size: 0.76rem;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
}

.sub-indicator-tabs {
  display: flex;
  gap: 6px;
  background: rgba(0, 0, 0, 0.25);
  padding: 3px;
  border-radius: 8px;
}

.sub-ind-btn {
  padding: 4px 10px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.sub-ind-btn.active {
  background: #388bfd;
  color: #ffffff;
}

.tech-echart-wrapper {
  height: 540px;
  min-height: 540px;
  width: 100%;
  min-width: 0;
  position: relative;
}

.tech-echart-canvas {
  width: 100% !important;
  height: 100% !important;
  min-height: 540px;
  display: block;
}

.chart-footer-legend {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-top: 8px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.dot-ma5 { width: 8px; height: 8px; border-radius: 50%; background: #58a6ff; }
.dot-ma10 { width: 8px; height: 8px; border-radius: 50%; background: #e3b341; }
.dot-ma20 { width: 8px; height: 8px; border-radius: 50%; background: #bc8cff; }
.dot-ma60 { width: 8px; height: 8px; border-radius: 50%; background: #f0883e; }
.legend-tip { margin-left: auto; font-size: 0.74rem; color: rgba(255,255,255,0.4); }

/* FUND COMPONENTS CARD */
.fund-components-card {
  padding: 16px 20px;
}

.components-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  flex-wrap: wrap;
  gap: 10px;
}

.header-left-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-left-title .title {
  font-size: 1rem;
  font-weight: 700;
  margin: 0;
}

.badge-weight {
  font-size: 0.76rem;
  background: rgba(88, 166, 255, 0.15);
  color: #58a6ff;
  padding: 2px 8px;
  border-radius: 4px;
}

.header-right-score {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.score-label {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.score-val {
  font-size: 1.2rem;
  font-weight: 800;
  color: #f85149;
}

.penetration-summary-p {
  font-size: 0.84rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0 0 12px 0;
}

.components-table th, .components-table td {
  padding: 8px 10px;
  font-size: 0.8rem;
}

.bias-pill {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 600;
}

.bias-pill.bullish { background: rgba(0, 255, 136, 0.15); color: #00ff88; }
.bias-pill.bearish { background: rgba(248, 81, 73, 0.15); color: #f85149; }
.bias-pill.neutral { background: rgba(255, 255, 255, 0.08); color: var(--text-secondary); }

/* EVALUATION SUMMARY CARD */
.eval-summary-card {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.eval-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.eval-title {
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0;
}

.eval-grade-badge {
  padding: 4px 12px;
  border: 1.5px solid;
  border-radius: 20px;
  font-size: 0.86rem;
  font-weight: 800;
  letter-spacing: 0.5px;
}

.score-display-row {
  display: flex;
  align-items: center;
  gap: 20px;
}

.score-circle-box {
  display: flex;
  align-items: baseline;
  gap: 2px;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.score-num {
  font-size: 2.2rem;
  font-weight: 900;
}

.score-max {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.advice-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.advice-title {
  font-size: 0.78rem;
  color: #e3b341;
  font-weight: 700;
}

.advice-text {
  font-size: 0.86rem;
  color: var(--text-primary);
  line-height: 1.45;
  margin: 0;
}

.support-resistance-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.level-card {
  padding: 10px 14px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.support-card {
  background: rgba(0, 255, 136, 0.05);
  border: 1px solid rgba(0, 255, 136, 0.2);
}

.resistance-card {
  background: rgba(248, 81, 73, 0.05);
  border: 1px solid rgba(248, 81, 73, 0.2);
}

.level-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.level-val {
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--text-primary);
}

.level-desc {
  font-size: 0.72rem;
  color: var(--text-secondary);
}

.triggered-signals-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.signals-label {
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.signals-tags-wrap {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.signal-badge {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(88, 166, 255, 0.15);
  color: #58a6ff;
  border: 1px solid rgba(88, 166, 255, 0.25);
}

/* 4-DIM INDICATOR MATRIX */
.indicators-matrix-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.ind-matrix-card {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.matrix-card-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ind-name {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.ind-status-val {
  font-size: 0.95rem;
  font-weight: 700;
}

.ind-sub-info {
  font-size: 0.75rem;
  color: var(--text-secondary);
  line-height: 1.35;
}

/* AI TRADING CARD */
.ai-trading-card {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  border: 1px solid rgba(138, 43, 226, 0.35);
  box-shadow: 0 0 20px rgba(138, 43, 226, 0.15);
}

.ai-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.ai-card-header .header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ai-title {
  font-size: 1rem;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(90deg, #c084fc, #60a5fa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.engine-toggle-group {
  display: flex;
  gap: 4px;
  background: rgba(0, 0, 0, 0.3);
  padding: 3px;
  border-radius: 8px;
}

.engine-btn {
  padding: 4px 10px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.engine-btn.active {
  background: rgba(138, 43, 226, 0.4);
  color: #ffffff;
  border: 1px solid rgba(138, 43, 226, 0.6);
}

.ai-control-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.ai-trigger-btn {
  background: linear-gradient(135deg, #7c3aed 0%, #2563eb 100%);
  border: none;
  padding: 8px 18px;
  font-size: 0.88rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}

.ai-trigger-btn:hover:not(:disabled) {
  box-shadow: 0 0 15px rgba(124, 58, 237, 0.5);
  transform: translateY(-1px);
}

.ai-quota-hint {
  font-size: 0.74rem;
  color: var(--text-secondary);
}

.ai-loading-box {
  padding: 24px 16px;
  text-align: center;
  color: #c084fc;
  font-size: 0.88rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.ai-result-content {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 16px;
}

.ai-meta-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 10px;
  margin-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 0.76rem;
  color: var(--text-secondary);
}

.cached-pill {
  padding: 1px 6px;
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
  border-radius: 4px;
  font-size: 0.7rem;
}

.re-analyze-btn {
  margin-left: auto;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: var(--text-secondary);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 0.72rem;
  cursor: pointer;
}

.re-analyze-btn:hover {
  color: var(--text-primary);
  border-color: #58a6ff;
}

.ai-markdown-body {
  font-size: 0.86rem;
  line-height: 1.65;
  color: #e6edf3;
}

.ai-markdown-body h1, .ai-markdown-body h2, .ai-markdown-body h3, .ai-markdown-body h4, .ai-markdown-body h5 {
  color: #58a6ff;
  margin-top: 12px;
  margin-bottom: 6px;
  font-size: 0.95rem;
}

.ai-markdown-body ul, .ai-markdown-body ol {
  padding-left: 18px;
  margin: 6px 0;
}

.ai-markdown-body p {
  margin: 6px 0;
}

.ai-placeholder-box {
  padding: 18px 16px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  border: 1px dashed rgba(255, 255, 255, 0.1);
  font-size: 0.82rem;
  color: var(--text-secondary);
  line-height: 1.5;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* HOLDING CARD ACTION BUTTON IN MONITORING */
.holding-card-action {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.btn-jump-tech {
  width: 100%;
  padding: 7px 0;
  background: linear-gradient(135deg, rgba(56, 139, 253, 0.15) 0%, rgba(35, 134, 54, 0.15) 100%);
  border: 1px solid rgba(56, 139, 253, 0.3);
  border-radius: 6px;
  color: #58a6ff;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.2s ease;
}

.btn-jump-tech:hover {
  background: linear-gradient(135deg, rgba(56, 139, 253, 0.3) 0%, rgba(35, 134, 54, 0.3) 100%);
  border-color: #388bfd;
  color: #ffffff;
  transform: translateY(-1px);
}

@media (max-width: 1100px) {
  .tech-content-grid {
    grid-template-columns: 1fr;
  }
  .snapshot-stats-grid {
    gap: 16px;
  }
}
</style>
