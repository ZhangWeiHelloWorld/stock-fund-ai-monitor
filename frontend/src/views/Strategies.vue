<template>
  <div class="strategies-page">
    <!-- Header & Tabs -->
    <header class="header">
      <div>
        <h2 class="page-title">买卖策略管理</h2>
        <p class="text-secondary">量化交易策略配置、历史全周期回测与实盘信号监控</p>
      </div>

      <div class="header-actions">
        <button class="btn btn-glass" @click="scanSignals" :disabled="scanning">
          <span>{{ scanning ? '扫描中...' : '🔄 扫描实时信号' }}</span>
        </button>
        <button class="btn btn-accent" @click="openBacktestModal()">
          <span>📊 策略回测台</span>
        </button>
        <button class="btn btn-primary" @click="openCreateModal()">
          <span>➕ 新建策略</span>
        </button>
      </div>
    </header>

    <!-- Top Tab Navigation -->
    <div class="strategy-tabs">
      <button
        class="tab-item"
        :class="{ active: currentTab === 'fund' }"
        @click="currentTab = 'fund'"
      >
        <span class="tab-icon">💰</span>
        <span>基金买卖策略</span>
        <span class="tab-badge">{{ fundStrategies.length }}</span>
      </button>

      <button
        class="tab-item"
        :class="{ active: currentTab === 'stock' }"
        @click="currentTab = 'stock'"
      >
        <span class="tab-icon">📈</span>
        <span>股票买卖策略</span>
        <span class="tab-badge">{{ stockStrategies.length }}</span>
      </button>
    </div>

    <!-- TAB 1: FUND STRATEGIES -->
    <div v-if="currentTab === 'fund'" class="tab-content">
      <!-- Strategy Stats Bar -->
      <div class="stats-grid">
        <div class="glass-card stat-card">
          <div class="stat-icon">🎯</div>
          <div class="stat-info">
            <div class="stat-label">运行中策略</div>
            <div class="stat-value">{{ runningCount }} <span class="stat-sub">/ {{ fundStrategies.length }} 个</span></div>
          </div>
        </div>

        <div class="glass-card stat-card">
          <div class="stat-icon">💵</div>
          <div class="stat-info">
            <div class="stat-label">初始本金总额</div>
            <div class="stat-value">¥{{ formatNumber(totalInitialCapital, 2) }}</div>
          </div>
        </div>

        <div class="glass-card stat-card">
          <div class="stat-icon">🏦</div>
          <div class="stat-info">
            <div class="stat-label">策略总资产估值</div>
            <div class="stat-value">¥{{ formatNumber(totalAssetsVal, 2) }}</div>
          </div>
        </div>

        <div class="glass-card stat-card">
          <div class="stat-icon">📈</div>
          <div class="stat-info">
            <div class="stat-label">策略累计总盈亏</div>
            <div class="stat-value" :class="totalPnlVal >= 0 ? 'text-red' : 'text-green'">
              {{ totalPnlVal >= 0 ? '+' : '' }}¥{{ formatNumber(totalPnlVal, 2) }}
              <span class="stat-sub" :class="totalPnlVal >= 0 ? 'text-red' : 'text-green'">
                ({{ totalPnlVal >= 0 ? '+' : '' }}{{ formatNumber(totalPnlPctVal, 2) }}%)
              </span>
            </div>
          </div>
        </div>

        <div class="glass-card stat-card" :class="{ 'highlight-signal': pendingSignalsCount > 0 }">
          <div class="stat-icon">⚡</div>
          <div class="stat-info">
            <div class="stat-label">今日待执行信号</div>
            <div class="stat-value" :class="pendingSignalsCount > 0 ? 'text-yellow' : ''">
              {{ pendingSignalsCount }} <span class="stat-sub">条提醒</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Pending Signals Alert Banner -->
      <div v-if="pendingSignals.length > 0" class="signals-banner glass-card">
        <div class="banner-header">
          <div class="banner-title">
            <span class="pulse-dot"></span>
            <strong>今日触发策略买卖信号 ({{ pendingSignals.length }})</strong>
          </div>
          <span class="banner-tip">遵循基金15:00交易界限规则，建议在 14:30~14:50 确认在支付宝或相关平台操作</span>
        </div>

        <div class="signal-items">
          <div v-for="sig in pendingSignals" :key="sig.id" class="signal-item">
            <div class="signal-badge" :class="sig.action === 'BUY' ? 'buy' : 'sell'">
              {{ sig.action === 'BUY' ? '🟢 建议加仓' : '🔴 建议止盈' }}
            </div>
            <div class="signal-details">
              <div class="sig-target">
                <strong>{{ sig.target_name }}</strong> ({{ sig.target_code }}) · {{ sig.strategy_name }}
              </div>
              <div class="sig-reason">{{ sig.reason }}</div>
            </div>
            <div class="sig-actions">
              <button class="btn btn-sm btn-primary" @click="openExecuteModal(sig)">
                ✅ 确认已在平台操作
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Strategy Cards Grid -->
      <div v-if="fundStrategies.length > 0" class="strategies-grid">
        <div
          v-for="strat in fundStrategies"
          :key="strat.id"
          class="glass-card strategy-card"
          :class="{ paused: strat.status === 'paused' }"
        >
          <!-- Card Header -->
          <div class="card-header">
            <div class="card-title-area">
              <div class="target-title">
                <span class="target-name">{{ strat.target_name }}</span>
                <span class="target-code">{{ strat.target_code }}</span>
                <span class="settle-badge">{{ strat.settlement_type || 'T+1' }}</span>
              </div>
              <div class="strat-name-sub">{{ strat.name }}</div>
            </div>

            <div class="card-status-area">
              <span class="strat-type-badge">{{ getStrategyTypeName(strat.strategy_type) }}</span>
              <button
                class="status-toggle"
                :class="strat.status === 'running' ? 'status-running' : 'status-paused'"
                @click="toggleStrategyStatus(strat)"
                :title="strat.status === 'running' ? '点击暂停策略' : '点击启动策略'"
              >
                {{ strat.status === 'running' ? '● 运行中' : '○ 已暂停' }}
              </button>
            </div>
          </div>

          <!-- Market & Performance Metrics -->
          <div class="card-metrics-grid">
            <div class="metric-box">
              <span class="label">最新净值 ({{ strat.nav_type || '估值' }})</span>
              <span class="val">{{ strat.market_nav ? strat.market_nav.toFixed(4) : '-' }}</span>
              <span class="sub" :class="strat.day_change_pct >= 0 ? 'text-red' : 'text-green'">
                {{ strat.day_change_pct >= 0 ? '+' : '' }}{{ formatNumber(strat.day_change_pct, 2) }}%
              </span>
            </div>

            <div class="metric-box">
              <span class="label">当前持仓份额</span>
              <span class="val">{{ formatNumber(strat.current_shares, 2) }} 份</span>
              <span class="sub text-secondary">市值 ¥{{ formatNumber(strat.market_value, 2) }}</span>
            </div>

            <div class="metric-box">
              <span class="label">可用现金储备</span>
              <span class="val">¥{{ formatNumber(strat.current_cash, 2) }}</span>
              <span class="sub text-secondary">初始本金 ¥{{ formatNumber(strat.initial_capital, 0) }}</span>
            </div>

            <div class="metric-box">
              <span class="label">持仓浮动盈亏</span>
              <span class="val" :class="strat.floating_pnl >= 0 ? 'text-red' : 'text-green'">
                {{ strat.floating_pnl >= 0 ? '+' : '' }}¥{{ formatNumber(strat.floating_pnl, 2) }}
              </span>
              <span class="sub" :class="strat.floating_pnl >= 0 ? 'text-red' : 'text-green'">
                {{ strat.floating_pnl >= 0 ? '+' : '' }}{{ formatNumber(strat.floating_pnl_pct, 2) }}%
              </span>
            </div>
          </div>

          <!-- Current Stage Target Profit Point Section -->
          <div v-if="strat.target_profit_info && strat.target_profit_info.target_pct > 0" class="card-target-profit-box">
            <div class="tp-header">
              <div class="tp-title">
                <span class="tp-icon">🎯</span>
                <strong>当前阶段目标止盈点</strong>
                <span class="tp-target-badge">+{{ strat.target_profit_info.target_pct }}%</span>
              </div>
              <div class="tp-status" :class="{ reached: strat.target_profit_info.is_reached }">
                <span v-if="strat.target_profit_info.is_reached" class="status-reached-tag">
                  🎉 已达标 (+{{ formatNumber(strat.floating_pnl_pct, 2) }}% ≥ +{{ strat.target_profit_info.target_pct }}%)
                </span>
                <span v-else-if="strat.target_profit_info.has_holding" class="status-gap-tag">
                  距目标还需 <strong class="text-accent">+{{ formatNumber(strat.target_profit_info.gap_pct, 2) }}%</strong>
                </span>
                <span v-else class="status-empty-tag text-secondary">
                  空仓待建仓 (首笔建仓后起算)
                </span>
              </div>
            </div>

            <!-- Target Price and Gap Details -->
            <div v-if="strat.target_profit_info.has_holding" class="tp-details-row">
              <div class="tp-detail-item">
                <span class="tp-d-label">持仓基准成本</span>
                <span class="tp-d-val">¥{{ formatPrice(strat.target_profit_info.cost_price, 'fund') }}</span>
              </div>
              <div class="tp-detail-item">
                <span class="tp-d-label">目标止盈净值</span>
                <span class="tp-d-val highlight-gold">¥{{ formatPrice(strat.target_profit_info.target_price, 'fund') }}</span>
              </div>
              <div class="tp-detail-item">
                <span class="tp-d-label">阶段浮盈进度</span>
                <span class="tp-d-val">{{ formatNumber(strat.target_profit_info.progress_pct, 1) }}%</span>
              </div>
            </div>

            <!-- Progress Bar -->
            <div v-if="strat.target_profit_info.has_holding" class="tp-progress-bar-bg">
              <div
                class="tp-progress-bar-fill"
                :class="{ reached: strat.target_profit_info.is_reached }"
                :style="{ width: `${strat.target_profit_info.progress_pct}%` }"
              ></div>
            </div>
          </div>

          <!-- Strategy Rule Summary Tags -->
          <div class="rule-summary-box">
            <span class="rule-title">核心规则：</span>
            <div class="rule-tags">
              <span v-for="(tag, tIdx) in getStrategyRuleTags(strat)" :key="tIdx" class="rule-tag">
                {{ tag }}
              </span>
            </div>
          </div>

          <!-- Card Footer Actions -->
          <div class="card-footer">
            <div class="left-actions">
              <button class="btn btn-sm btn-glass" @click="openQuickBacktest(strat)">
                📊 快速回测
              </button>
              <button class="btn btn-sm btn-glass" @click="openTradesModal(strat)">
                📋 流水记录
              </button>
            </div>
            <div class="right-actions">
              <button class="action-icon-btn edit" @click="openEditModal(strat)" title="修改策略参数">
                ✎
              </button>
              <button class="action-icon-btn delete" @click="confirmDelete(strat)" title="删除策略">
                🗑
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="glass-card empty-card">
        <div class="empty-icon">🎯</div>
        <h3>暂未创建任何基金买卖策略</h3>
        <p class="text-secondary">
          点击上方「➕ 新建策略」配置您的第一个基金自动化交易策略，或打开「📊 策略回测台」验证历史收益率！
        </p>
        <div class="empty-actions">
          <button class="btn btn-primary" @click="openCreateModal()">
            <span>➕ 立即新建策略</span>
          </button>
          <button class="btn btn-glass" @click="openBacktestModal('000001')">
            <span>📊 体验华夏成长回测</span>
          </button>
        </div>
      </div>
    </div>

    <!-- TAB 2: STOCK STRATEGIES -->
    <div v-else-if="currentTab === 'stock'" class="tab-content">
      <!-- Strategy Stats Bar for Stocks -->
      <div class="stats-grid">
        <div class="glass-card stat-card">
          <div class="stat-icon">🎯</div>
          <div class="stat-info">
            <div class="stat-label">运行中股票策略</div>
            <div class="stat-value">{{ stockRunningCount }} <span class="stat-sub">/ {{ stockStrategies.length }} 个</span></div>
          </div>
        </div>

        <div class="glass-card stat-card">
          <div class="stat-icon">💵</div>
          <div class="stat-info">
            <div class="stat-label">初始本金总额</div>
            <div class="stat-value">¥{{ formatNumber(stockTotalInitialCapital, 2) }}</div>
          </div>
        </div>

        <div class="glass-card stat-card">
          <div class="stat-icon">🏦</div>
          <div class="stat-info">
            <div class="stat-label">股票策略总资产</div>
            <div class="stat-value">¥{{ formatNumber(stockTotalAssetsVal, 2) }}</div>
          </div>
        </div>

        <div class="glass-card stat-card">
          <div class="stat-icon">📈</div>
          <div class="stat-info">
            <div class="stat-label">策略累计总盈亏</div>
            <div class="stat-value" :class="stockTotalPnlVal >= 0 ? 'text-red' : 'text-green'">
              {{ stockTotalPnlVal >= 0 ? '+' : '' }}¥{{ formatNumber(stockTotalPnlVal, 2) }}
              <span class="stat-sub" :class="stockTotalPnlVal >= 0 ? 'text-red' : 'text-green'">
                ({{ stockTotalPnlVal >= 0 ? '+' : '' }}{{ formatNumber(stockTotalPnlPctVal, 2) }}%)
              </span>
            </div>
          </div>
        </div>

        <div class="glass-card stat-card" :class="{ 'highlight-signal': stockPendingSignalsCount > 0 }">
          <div class="stat-icon">⚡</div>
          <div class="stat-info">
            <div class="stat-label">今日待执行信号</div>
            <div class="stat-value" :class="stockPendingSignalsCount > 0 ? 'text-yellow' : ''">
              {{ stockPendingSignalsCount }} <span class="stat-sub">条提醒</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Stock Pending Signals Alert Banner -->
      <div v-if="stockPendingSignals.length > 0" class="signals-banner glass-card">
        <div class="banner-header">
          <span class="pulse-icon">⚡</span>
          <strong>A股策略买卖信号提醒 (共 {{ stockPendingSignals.length }} 条待确认)</strong>
        </div>
        <div class="signals-list">
          <div
            v-for="sig in stockPendingSignals"
            :key="sig.id"
            class="signal-item"
            :class="sig.action === 'BUY' ? 'sig-buy' : 'sig-sell'"
          >
            <div class="sig-left">
              <span class="sig-badge" :class="sig.action === 'BUY' ? 'buy' : 'sell'">
                {{ sig.action === 'BUY' ? '🟢 加仓买入' : '🔴 止盈卖出' }}
              </span>
              <span class="sig-fund">{{ sig.target_name }} ({{ sig.target_code }})</span>
              <span class="sig-strat">「{{ sig.strategy_name }}」</span>
              <span class="sig-reason">{{ sig.reason }}</span>
            </div>
            <div class="sig-right">
              <div class="sig-nums">
                <span>参考现价: <strong>¥{{ sig.current_nav?.toFixed(2) }}</strong></span>
                <span>建议金额: <strong>¥{{ formatNumber(sig.suggested_amount, 2) }}</strong> (约 {{ sig.suggested_shares }} 股/{{ Math.round(sig.suggested_shares/100) }}手)</span>
              </div>
              <button class="btn btn-sm btn-primary" @click="openExecuteModal(sig)">
                ⚡ 确认执行并记账
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Stock Strategy Cards Grid -->
      <div v-if="stockStrategies.length > 0" class="strategy-cards-grid">
        <div
          v-for="strat in stockStrategies"
          :key="strat.id"
          class="glass-card strategy-card"
          :class="{ paused: strat.status === 'paused' }"
        >
          <div class="card-header">
            <div class="strat-title-wrap">
              <div class="title-with-code">
                <span class="fund-icon">📈</span>
                <span class="strat-title" :title="strat.name">{{ strat.name }}</span>
              </div>
              <div class="fund-sub-code">
                {{ strat.target_name }} <span class="code-badge">{{ strat.target_code }}</span>
                <span class="tag-type">{{ getStrategyTypeName(strat.strategy_type) }}</span>
              </div>
            </div>

            <div class="status-toggle-wrap">
              <span class="status-badge" :class="strat.status">
                {{ strat.status === 'running' ? '● 运行中' : '○ 已暂停' }}
              </span>
              <button
                class="btn-icon-switch"
                @click="toggleStrategyStatus(strat)"
                :title="strat.status === 'running' ? '暂停监控' : '恢复运行'"
              >
                {{ strat.status === 'running' ? '⏸️' : '▶️' }}
              </button>
            </div>
          </div>

          <div class="card-pnl-overview">
            <div class="pnl-main-col">
              <span class="label">当前市值 / 现价</span>
              <div class="val">
                ¥{{ formatNumber(strat.market_value, 2) }}
                <span class="sub-price" :class="(strat.day_change_pct || 0) >= 0 ? 'text-red' : 'text-green'">
                  (¥{{ (strat.market_nav || 0).toFixed(2) }} · {{ (strat.day_change_pct || 0) >= 0 ? '+' : '' }}{{ formatNumber(strat.day_change_pct, 2) }}%)
                </span>
              </div>
            </div>
            <div class="pnl-main-col text-right">
              <span class="label">持仓浮动盈亏</span>
              <div class="val" :class="(strat.floating_pnl || 0) >= 0 ? 'text-red' : 'text-green'">
                {{ (strat.floating_pnl || 0) >= 0 ? '+' : '' }}¥{{ formatNumber(strat.floating_pnl, 2) }}
                <span class="sub-pct">
                  ({{ (strat.floating_pnl_pct || 0) >= 0 ? '+' : '' }}{{ formatNumber(strat.floating_pnl_pct, 2) }}%)
                </span>
              </div>
            </div>
          </div>

          <div class="card-details-grid">
            <div class="detail-cell">
              <span class="d-label">初始本金</span>
              <span class="d-val">¥{{ formatNumber(strat.initial_capital, 2) }}</span>
            </div>
            <div class="detail-cell">
              <span class="d-label">现金结余</span>
              <span class="d-val">¥{{ formatNumber(strat.current_cash, 2) }}</span>
            </div>
            <div class="detail-cell">
              <span class="d-label">持仓股数</span>
              <span class="d-val">{{ strat.current_shares }} 股 <small style="color:var(--text-secondary); font-size:0.75rem;">({{ Math.round(strat.current_shares / 100) }}手)</small></span>
            </div>
            <div class="detail-cell">
              <span class="d-label">持仓均价</span>
              <span class="d-val">¥{{ strat.current_shares > 0 ? (strat.total_cost / strat.current_shares).toFixed(2) : '0.00' }}</span>
            </div>
          </div>

          <!-- Current Stage Target Profit Point Section for Stocks -->
          <div v-if="strat.target_profit_info && strat.target_profit_info.target_pct > 0" class="card-target-profit-box">
            <div class="tp-header">
              <div class="tp-title">
                <span class="tp-icon">🎯</span>
                <strong>当前阶段目标止盈点</strong>
                <span class="tp-target-badge">+{{ strat.target_profit_info.target_pct }}%</span>
              </div>
              <div class="tp-status" :class="{ reached: strat.target_profit_info.is_reached }">
                <span v-if="strat.target_profit_info.is_reached" class="status-reached-tag">
                  🎉 已达标 (+{{ formatNumber(strat.floating_pnl_pct, 2) }}% ≥ +{{ strat.target_profit_info.target_pct }}%)
                </span>
                <span v-else-if="strat.target_profit_info.has_holding" class="status-gap-tag">
                  距目标还需 <strong class="text-accent">+{{ formatNumber(strat.target_profit_info.gap_pct, 2) }}%</strong>
                </span>
                <span v-else class="status-empty-tag text-secondary">
                  空仓待建仓 (首笔建仓后起算)
                </span>
              </div>
            </div>

            <!-- Target Price and Gap Details -->
            <div v-if="strat.target_profit_info.has_holding" class="tp-details-row">
              <div class="tp-detail-item">
                <span class="tp-d-label">持仓均价</span>
                <span class="tp-d-val">¥{{ formatPrice(strat.target_profit_info.cost_price, 'stock') }}</span>
              </div>
              <div class="tp-detail-item">
                <span class="tp-d-label">目标止盈股价</span>
                <span class="tp-d-val highlight-gold">¥{{ formatPrice(strat.target_profit_info.target_price, 'stock') }}</span>
              </div>
              <div class="tp-detail-item">
                <span class="tp-d-label">阶段浮盈进度</span>
                <span class="tp-d-val">{{ formatNumber(strat.target_profit_info.progress_pct, 1) }}%</span>
              </div>
            </div>

            <!-- Progress Bar -->
            <div v-if="strat.target_profit_info.has_holding" class="tp-progress-bar-bg">
              <div
                class="tp-progress-bar-fill"
                :class="{ reached: strat.target_profit_info.is_reached }"
                :style="{ width: `${strat.target_profit_info.progress_pct}%` }"
              ></div>
            </div>
          </div>

          <div class="card-rules-tags">
            <span
              v-for="(ruleTag, rIdx) in getStrategyRuleTags(strat)"
              :key="rIdx"
              class="rule-tag"
            >
              {{ ruleTag }}
            </span>
          </div>

          <div v-if="strat.pending_signal" class="card-pending-signal">
            <span class="blink-dot">●</span>
            <span class="sig-text">{{ strat.pending_signal.reason }}</span>
            <button class="btn btn-xs btn-accent" @click="openExecuteModal(strat.pending_signal)">
              记账
            </button>
          </div>

          <div class="card-actions">
            <button class="btn btn-sm btn-glass" @click="openBacktestFromCard(strat)">
              📊 回测
            </button>
            <button class="btn btn-sm btn-glass" @click="openEditModal(strat)">
              📝 编辑
            </button>
            <button class="btn btn-sm btn-glass" @click="openTradesModal(strat)">
              📋 流水
            </button>
            <button class="btn btn-sm btn-danger-ghost" @click="deleteStrategyItem(strat)">
              🗑️ 删除
            </button>
          </div>
        </div>
      </div>

      <!-- Empty State for Stocks -->
      <div v-else class="glass-card empty-state">
        <div class="empty-icon">📈</div>
        <h3>暂无运行中的股票交易策略</h3>
        <p class="text-secondary">
          创建属于您的第一个A股股票量化策略（支持整手交易、印花税/佣金模型、均线跟踪、智能网格与阶梯止盈），实现自动化纪律执行。
        </p>
        <button class="btn btn-primary mt-3" @click="openCreateModal('stock')">
          <span>➕ 新建第一个股票买卖策略</span>
        </button>
      </div>
    </div>

    <!-- ============================================================== -->
    <!-- MODAL 1: CREATE / EDIT STRATEGY MODAL                          -->
    <!-- ============================================================== -->
    <div class="modal-overlay" :class="{ active: showFormModal }">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h3>{{ editingStrategy ? (form.asset_type === 'stock' ? '编辑股票交易策略' : '编辑基金交易策略') : (form.asset_type === 'stock' ? '新建股票交易策略' : '新建基金交易策略') }}</h3>
          <button class="close-btn" @click="closeFormModal">×</button>
        </div>

        <form @submit.prevent="saveStrategy">
          <div class="form-scrollable">
            <!-- 1. Basic Info & Target Asset Selection -->
            <div class="form-section">
              <h4 class="section-title">1. 标的资产与策略基础信息</h4>

              <div class="form-group mb-3">
                <label>策略标的资产类别</label>
                <div class="asset-type-radios">
                  <button
                    type="button"
                    class="asset-type-btn"
                    :class="{ active: form.asset_type === 'fund' }"
                    @click="setFormAssetType('fund')"
                  >
                    💰 场外公募基金
                  </button>
                  <button
                    type="button"
                    class="asset-type-btn"
                    :class="{ active: form.asset_type === 'stock' }"
                    @click="setFormAssetType('stock')"
                  >
                    📈 A股股票
                  </button>
                </div>
              </div>

              <div class="form-row grid-2">
                <div class="form-group">
                  <label>{{ form.asset_type === 'stock' ? '股票代码' : '基金代码' }} <span class="required">*</span></label>
                  <input
                    type="text"
                    class="form-control"
                    v-model="form.target_code"
                    @blur="fetchTargetInfoAndFees"
                    required
                    :placeholder="form.asset_type === 'stock' ? '如：600519、000001、300750' : '如：000001、005827'"
                  />
                </div>

                <div class="form-group">
                  <label style="display:flex; justify-content:space-between;">
                    <span>{{ form.asset_type === 'stock' ? '股票名称' : '基金名称' }}</span>
                    <span v-if="fetchingInfo" style="color:var(--accent-primary); font-size:0.75rem;">正在查询信息与费率...</span>
                  </label>
                  <input
                    type="text"
                    class="form-control"
                    v-model="form.target_name"
                    placeholder="留空自动联想"
                  />
                </div>
              </div>

              <div class="form-row grid-3">
                <div class="form-group">
                  <label>策略自定义名称</label>
                  <input
                    type="text"
                    class="form-control"
                    v-model="form.name"
                    :placeholder="form.asset_type === 'stock' ? '如：贵州茅台网格做T' : '如：华夏成长大跌倍投'"
                  />
                </div>

                <div class="form-group">
                  <label>初始投入本金 (元)</label>
                  <input
                    type="number"
                    step="100"
                    class="form-control"
                    v-model="form.initial_capital"
                    required
                  />
                </div>

                <div class="form-group">
                  <label>确认规则 (结算模式)</label>
                  <select class="form-control" v-model="form.settlement_type">
                    <option value="T+1">T+1 确认 (A股标准/国内公募基金)</option>
                    <option v-if="form.asset_type === 'fund'" value="T+2">T+2 确认 (QDII/海外互认基金)</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- 2. Strategy Template Selection -->
            <div class="form-section">
              <h4 class="section-title">2. 选择策略模型与规则模板</h4>
              <div class="templates-picker">
                <div
                  v-for="tpl in currentTemplates"
                  :key="tpl.id"
                  class="template-card-option"
                  :class="{ selected: form.strategy_type === tpl.id }"
                  @click="selectPresetTemplate(tpl)"
                >
                  <div class="tpl-head">
                    <span class="tpl-badge">{{ tpl.badge }}</span>
                    <strong>{{ tpl.name }}</strong>
                  </div>
                  <p class="tpl-desc">{{ tpl.description }}</p>
                </div>
              </div>
            </div>

            <!-- 3. Dynamic Strategy Parameters -->
            <div class="form-section">
              <h4 class="section-title">3. 策略详细参数配置</h4>

              <!-- Case A: 跌幅加仓与阶梯止盈 -->
              <div v-if="form.strategy_type === 'dip_buying_profit_take' || form.strategy_type === 'stock_dip_profit_take'" class="param-group-box">
                <div class="alert alert-info">
                  💡 <strong>多阶梯买卖与收益重置规则说明：</strong>
                  支持配置多个下跌跌幅对应的加仓金额与多个大涨止盈档位；卖出后剩余持仓以当日净值重置为新一轮基准。
                </div>

                <div class="tier-section-block">
                  <div class="tier-header">
                    <strong>📊 多档位动态加仓规则</strong>
                    <div class="btn-group-sm">
                      <button type="button" class="btn btn-sm btn-glass" @click="addDropTier">+ 下跌加仓</button>
                      <button type="button" class="btn btn-sm btn-glass" @click="addRiseTier">+ 上涨加仓</button>
                      <button type="button" class="btn btn-sm btn-glass" @click="addRoutineTier">+ 日常加仓</button>
                    </div>
                  </div>
                  <table class="tiers-table">
                    <thead>
                      <tr>
                        <th style="width:130px;">类型</th>
                        <th style="width:205px;">涨跌阈值</th>
                        <th style="width:140px;">金额</th>
                        <th>说明</th>
                        <th style="width:50px;">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(tier, dIdx) in (form.config.buy_tiers || form.config.dip_buy_tiers)" :key="dIdx">
                        <td>
                          <select class="mini-input" v-model="tier.type" @change="onTierTypeChange(tier)">
                            <option value="drop">📉 下跌</option>
                            <option value="rise">📈 上涨</option>
                            <option value="routine">☕ 日常</option>
                          </select>
                        </td>
                        <td>
                          <div v-if="tier.type === 'drop'" style="display:flex; align-items:center; gap:4px;">
                            <span>下跌</span>
                            <select class="mini-input op-select" v-model="tier.operator" @change="updateTierLabel(tier)">
                              <option value=">=">≥</option>
                              <option value=">">&gt;</option>
                            </select>
                            <input type="number" step="0.1" class="mini-input val-input" style="width:50px;" v-model.number="tier.drop_pct" @input="updateTierLabel(tier)" />
                            <span>%</span>
                          </div>
                          <div v-else-if="tier.type === 'rise'" style="display:flex; align-items:center; gap:4px;">
                            <span>上涨</span>
                            <select class="mini-input op-select" v-model="tier.operator" @change="updateTierLabel(tier)">
                              <option value="<=">≤</option>
                              <option value="<">&lt;</option>
                            </select>
                            <input type="number" step="0.1" class="mini-input val-input" style="width:50px;" v-model.number="tier.rise_pct" @input="updateTierLabel(tier)" />
                            <span>%</span>
                          </div>
                          <div v-else style="color:var(--text-secondary); font-size:0.8rem;">
                            <span>不满足特定涨跌时执行</span>
                          </div>
                        </td>
                        <td>
                          <div style="display:flex; align-items:center; gap:2px;">
                            <span>¥</span>
                            <input type="number" step="500" class="mini-input" style="width:85px;" v-model.number="tier.amount" @input="updateTierLabel(tier)" />
                          </div>
                        </td>
                        <td>
                          <input type="text" class="mini-input label-in" v-model="tier.label" />
                        </td>
                        <td>
                          <button type="button" class="action-icon-btn delete" @click="removeBuyTier(dIdx)">×</button>
                        </td>
                      </tr>
                      <tr v-if="!(form.config.buy_tiers || form.config.dip_buy_tiers)?.length">
                        <td colspan="5" class="text-center text-secondary" style="padding:15px;">暂未添加档位</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div class="tier-section-block mt-3">
                  <div class="tier-header">
                    <strong>📈 单日暴涨阶梯止盈</strong>
                    <button type="button" class="btn btn-sm btn-glass" @click="addSurgeTier">+ 增加止盈档位</button>
                  </div>
                  <table class="tiers-table">
                    <thead>
                      <tr>
                        <th>大涨阈值 (%)</th>
                        <th>卖出比例</th>
                        <th>重置基准</th>
                        <th>说明</th>
                        <th style="width:50px;">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(sTier, sIdx) in form.config.surge_profit_tiers" :key="sIdx">
                        <td>
                          <span>≥ </span>
                          <input type="number" step="0.5" class="mini-input" style="width:60px;" v-model.number="sTier.surge_pct" /> %
                        </td>
                        <td>
                          <select class="mini-input" v-model="sTier.sell_ratio">
                            <option :value="0.2">20%</option>
                            <option :value="0.5">50%</option>
                            <option :value="1.0">100%</option>
                          </select>
                        </td>
                        <td>
                          <input type="checkbox" v-model="sTier.reset_on_sell" />
                        </td>
                        <td><input type="text" class="mini-input label-in" v-model="sTier.label" /></td>
                        <td><button type="button" class="action-icon-btn delete" @click="removeSurgeTier(sIdx)">×</button></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div class="tier-section-block mt-3">
                  <div class="tier-header">
                    <strong>🎯 当前阶段目标止盈点与重置基准规则</strong>
                  </div>
                  <div class="form-row grid-3 mt-2">
                    <div class="form-group">
                      <label>🎯 当前阶段目标止盈点 (%)</label>
                      <input
                        type="number"
                        step="0.5"
                        class="form-control"
                        v-model.number="form.config.cumulative_profit_target_pct"
                        placeholder="如: 10.0"
                      />
                      <span class="help-text">当前持仓累计浮盈达标后自动触发阶段止盈</span>
                    </div>

                    <div class="form-group">
                      <label>达标止盈卖出比例</label>
                      <select class="form-control" v-model="form.config.cumulative_profit_sell_ratio">
                        <option :value="0.20">卖出 1/5 (20%)</option>
                        <option :value="0.25">卖出 1/4 (25%)</option>
                        <option :value="0.3333">卖出 1/3 (33.33%)</option>
                        <option :value="0.50">卖出 1/2 (50%)</option>
                        <option :value="1.0">全部清仓 (100%)</option>
                      </select>
                    </div>

                    <div class="form-group">
                      <label>达标卖出后重置基准</label>
                      <select class="form-control" v-model="form.config.cumulative_reset_on_sell">
                        <option :value="true">是 (以成交日现价作为新一轮0%基准)</option>
                        <option :value="false">否 (维持历史原始加权成本)</option>
                      </select>
                    </div>
                  </div>

                  <div class="form-row grid-3 mt-2">
                    <div class="form-group">
                      <label>加仓冷却间隔 (交易日数)</label>
                      <input type="number" class="form-control" v-model.number="form.config.buy_cooldown_days" />
                      <span class="help-text">加仓后的冷却天数，默认 1 天</span>
                    </div>

                    <div class="form-group">
                      <label>止盈冷却间隔 (交易日数)</label>
                      <input type="number" class="form-control" v-model.number="form.config.sell_cooldown_days" />
                      <span class="help-text">止盈后的冷却天数，默认 1 天</span>
                    </div>

                    <div class="form-group">
                      <label>持仓金额上限 (元)</label>
                      <input type="number" step="1000" class="form-control" v-model.number="form.config.max_position_limit" placeholder="0 表示不限" />
                    </div>
                  </div>
                </div>
              </div>

              <!-- Case A2: 分时做T与底仓波段策略 (T+1 Intraday Doing-T Strategy) -->
              <div v-else-if="form.strategy_type === 'intraday_t' || form.strategy_type === 'stock_intraday_t'" class="param-group-box">
                <div class="alert alert-info">
                  ⚡ <strong>A股严格 T+1 底仓做T规则：</strong>
                  以持有的<strong>初始底仓</strong>为依托，盘中分时冲高时高抛卖出，回踩时低吸接回（<strong>买回手数严格限制 ≤ 当日已卖出量</strong>，不放大持仓敞口）。做T价差收益自动用于<strong>持续摊薄剩余持仓成本</strong>，同时受<strong>底仓锁定保护</strong>防守。
                </div>

                <!-- 1. 底仓与做T基础风控 -->
                <div class="tier-section-block">
                  <div class="tier-header">
                    <strong>🛡️ 1. 底仓配置与做T风控保护</strong>
                  </div>
                  <div class="form-row grid-3 mt-2">
                    <div class="form-group">
                      <label>初始底仓股数 (股)</label>
                      <input type="number" step="100" class="form-control" v-model.number="form.config.initial_base_shares" placeholder="如: 1000" />
                      <span class="help-text">盘前已具备的可用股数，T+1起可卖出做T</span>
                    </div>
                    <div class="form-group">
                      <label>底仓锁定保护 (股)</label>
                      <input type="number" step="100" class="form-control" v-model.number="form.config.base_protect_shares" placeholder="如: 300" />
                      <span class="help-text">不可卖出的核心底仓，防止单边大涨卖飞</span>
                    </div>
                    <div class="form-group">
                      <label>单日最多做T轮次</label>
                      <input type="number" class="form-control" v-model.number="form.config.max_daily_t_rounds" placeholder="如: 2" />
                      <span class="help-text">限制每日做T频次，避免税费过度磨损</span>
                    </div>
                  </div>
                </div>

                <!-- 2. 分时高抛与回踩接回规则 -->
                <div class="tier-section-block mt-3">
                  <div class="tier-header">
                    <strong>⚡ 2. 分时冲高高抛与回踩低吸接回规则</strong>
                  </div>
                  <div class="form-row grid-2 mt-2">
                    <div class="form-group">
                      <label>冲高高抛涨幅 (%)</label>
                      <input type="number" step="0.1" class="form-control" v-model.number="form.config.t_surge_sell_pct" placeholder="如: 1.8" />
                      <span class="help-text">分时价格较持仓成本/开盘涨幅达到此阈值高抛</span>
                    </div>
                    <div class="form-group">
                      <label>单次高抛股数 (股)</label>
                      <input type="number" step="100" class="form-control" v-model.number="form.config.t_sell_shares" placeholder="如: 300" />
                      <span class="help-text">单次高抛卖出量（自动按100股整手取整）</span>
                    </div>
                  </div>

                  <div class="form-row grid-3 mt-2">
                    <div class="form-group">
                      <label>卖出后是否低吸接回</label>
                      <select class="form-control" v-model="form.config.enable_pullback_buyback">
                        <option :value="true">✅ 开启高抛后低吸接回 (滚动做T)</option>
                        <option :value="false">🚫 关闭 (仅高抛减仓，不自动买回)</option>
                      </select>
                      <span class="help-text">买回手数严格限制 ≤ 当天已卖出量</span>
                    </div>

                    <div class="form-group" v-if="form.config.enable_pullback_buyback !== false">
                      <label>回调跌幅参考基准</label>
                      <select class="form-control" v-model="form.config.pullback_ref_type">
                        <option value="from_sell_price">📉 较卖出点价格跌幅 (高抛后回踩)</option>
                        <option value="from_daily_change">📊 当天整体跌幅 (按全天累计跌幅)</option>
                      </select>
                      <span class="help-text">选择触发接回所比对的价格基准</span>
                    </div>

                    <div class="form-group" v-if="form.config.enable_pullback_buyback !== false && form.config.pullback_ref_type === 'from_daily_change'">
                      <label>当天总跌幅接回阈值 (%)</label>
                      <input type="number" step="0.1" class="form-control" v-model.number="form.config.daily_drop_buyback_pct" placeholder="如: 2.0" />
                      <span class="help-text">当天累计跌幅达到该比例时接回已卖手数</span>
                    </div>

                    <div class="form-group" v-if="form.config.enable_pullback_buyback !== false && form.config.pullback_ref_type !== 'from_daily_change'">
                      <label>较高抛点跌幅接回阈值 (%)</label>
                      <input type="number" step="0.1" class="form-control" v-model.number="form.config.t_pullback_buy_pct" placeholder="如: 1.5" />
                      <span class="help-text">从高抛成交价回落达到该比例时接回已卖手数</span>
                    </div>
                  </div>
                </div>

                <!-- 3. 逐批次买入独立止盈做T -->
                <div class="tier-section-block mt-3">
                  <div class="tier-header">
                    <strong>📦 3. 逐批次独立止盈做T (比前次买入价涨幅达标即卖出对应数量)</strong>
                  </div>
                  <div class="form-row grid-3 mt-2">
                    <div class="form-group">
                      <label>是否开启逐批次独立止盈</label>
                      <select class="form-control" v-model="form.config.enable_lot_profit_take">
                        <option :value="true">✅ 开启 (严格T+1，达标即卖出该批次)</option>
                        <option :value="false">🚫 关闭 (仅按总持仓成本做T)</option>
                      </select>
                      <span class="help-text">遵循A股T+1，低吸批次独立核算止盈</span>
                    </div>
                    <div class="form-group" v-if="form.config.enable_lot_profit_take !== false">
                      <label>较买入价涨幅达标阈值 (%)</label>
                      <input type="number" step="0.1" class="form-control" v-model.number="form.config.lot_profit_take_pct" placeholder="如: 3.0" />
                      <span class="help-text">股价较历史加仓买入价涨幅达到该比例触发止盈</span>
                    </div>
                    <div class="form-group" v-if="form.config.enable_lot_profit_take !== false">
                      <label>达标批次卖出比例</label>
                      <select class="form-control" v-model="form.config.lot_profit_sell_ratio">
                        <option :value="1.0">卖出该批次全部股数 (100%)</option>
                        <option :value="0.5">卖出该批次半数 (50%)</option>
                        <option :value="0.3333">卖出该批次 1/3 (33%)</option>
                      </select>
                      <span class="help-text">自动按 100 股整手向下取整卖出</span>
                    </div>
                  </div>
                </div>

                <!-- 4. 大跌/大涨多档阶梯加减仓 -->
                <div class="tier-section-block mt-3">
                  <div class="tier-header">
                    <strong>📊 4. 多档位大跌加仓与极端暴涨减仓</strong>
                    <div class="btn-group-sm">
                      <button type="button" class="btn btn-sm btn-glass" @click="addDropTier">+ 下跌加仓档</button>
                      <button type="button" class="btn btn-sm btn-glass" @click="addSurgeTier">+ 暴涨减仓档</button>
                    </div>
                  </div>
                  
                  <!-- 下跌加仓表格 -->
                  <div v-if="(form.config.buy_tiers || form.config.dip_buy_tiers)?.length" class="mt-2">
                    <div style="font-size: 0.85rem; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">📉 大跌阶梯加仓档位：</div>
                    <table class="tiers-table">
                      <thead>
                        <tr>
                          <th style="width:130px;">加仓类型</th>
                          <th style="width:205px;">跌幅阈值</th>
                          <th style="width:140px;">金额 (元)</th>
                          <th>说明</th>
                          <th style="width:50px;">操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(tier, dIdx) in (form.config.buy_tiers || form.config.dip_buy_tiers)" :key="'buy-'+dIdx">
                          <td>📉 下跌加仓</td>
                          <td>
                            <div style="display:flex; align-items:center; gap:4px;">
                              <span>下跌</span>
                              <select class="mini-input op-select" v-model="tier.operator" @change="updateTierLabel(tier)">
                                <option value=">=">≥</option>
                                <option value=">">&gt;</option>
                              </select>
                              <input type="number" step="0.1" class="mini-input val-input" style="width:50px;" v-model.number="tier.drop_pct" @input="updateTierLabel(tier)" />
                              <span>%</span>
                            </div>
                          </td>
                          <td>
                            <input type="number" step="500" class="mini-input" style="width:90px;" v-model.number="tier.amount" @input="updateTierLabel(tier)" />
                          </td>
                          <td style="color:var(--text-secondary); font-size:0.8rem;">{{ tier.label }}</td>
                          <td>
                            <button type="button" class="action-icon-btn delete" title="删除此加仓档" @click="removeBuyTier(dIdx)">×</button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <!-- 暴涨减仓表格 -->
                  <div v-if="form.config.surge_profit_tiers?.length" class="mt-3">
                    <div style="font-size: 0.85rem; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">📈 暴涨阶梯减仓档位：</div>
                    <table class="tiers-table">
                      <thead>
                        <tr>
                          <th style="width:130px;">涨幅阈值</th>
                          <th style="width:180px;">卖出比例</th>
                          <th style="width:120px;">成本摊薄</th>
                          <th>说明</th>
                          <th style="width:50px;">操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(sTier, sIdx) in form.config.surge_profit_tiers" :key="'surge-'+sIdx">
                          <td>
                            <div style="display:flex; align-items:center; gap:4px;">
                              <span>涨 ≥</span>
                              <input type="number" step="0.5" class="mini-input" style="width:50px;" v-model.number="sTier.surge_pct" />
                              <span>%</span>
                            </div>
                          </td>
                          <td>
                            <select class="mini-input" v-model="sTier.sell_ratio">
                              <option :value="0.20">卖出 1/5 (20%)</option>
                              <option :value="0.25">卖出 1/4 (25%)</option>
                              <option :value="0.3333">卖出 1/3 (33%)</option>
                              <option :value="0.50">卖出 1/2 (50%)</option>
                            </select>
                          </td>
                          <td>
                            <label style="font-size:0.8rem; display:flex; align-items:center; gap:4px; cursor:pointer;">
                              <input type="checkbox" v-model="sTier.reset_on_sell" /> 摊薄成本
                            </label>
                          </td>
                          <td style="color:var(--text-secondary); font-size:0.8rem;">{{ sTier.label }}</td>
                          <td>
                            <button type="button" class="action-icon-btn delete" title="删除此减仓档" @click="removeSurgeTier(sIdx)">×</button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <!-- 5. 阶段目标止盈与成本摊薄重置 -->
                <div class="tier-section-block mt-3">
                  <div class="tier-header">
                    <strong>🎯 5. 全局目标止盈与做T成本摊薄重置</strong>
                  </div>
                  <div class="form-row grid-3 mt-2">
                    <div class="form-group">
                      <label>🎯 全局目标止盈点 (%)</label>
                      <input type="number" step="0.5" class="form-control" v-model.number="form.config.cumulative_profit_target_pct" placeholder="如: 15.0" />
                      <span class="help-text">总持仓累计浮盈达标后执行阶段大额止盈</span>
                    </div>
                    <div class="form-group">
                      <label>达标止盈卖出比例</label>
                      <select class="form-control" v-model="form.config.cumulative_profit_sell_ratio">
                        <option :value="0.3333">卖出 1/3 (33%)</option>
                        <option :value="0.50">卖出 1/2 (50%)</option>
                        <option :value="1.0">全部清仓 (100%)</option>
                      </select>
                    </div>
                    <div class="form-group">
                      <label>减仓收益摊薄持仓成本</label>
                      <select class="form-control" v-model="form.config.cumulative_reset_on_sell">
                        <option :value="true">是 (做T收益持续扣减剩余成本线)</option>
                        <option :value="false">否 (维持原始买入成本)</option>
                      </select>
                    </div>
                  </div>
                  <div class="form-row grid-2 mt-2">
                    <div class="form-group">
                      <label>极限单边破位硬止损 (%)</label>
                      <input type="number" step="0.5" class="form-control" v-model.number="form.config.stop_loss_pct" placeholder="如: 10.0" />
                      <span class="help-text">深度破位时清仓防守（0 表示不设硬止损）</span>
                    </div>
                    <div class="form-group">
                      <label>做T冷却间隔</label>
                      <input type="text" class="form-control" value="0 (分时盘中实时极速监控)" disabled />
                    </div>
                  </div>
                </div>
              </div>

              <!-- Case B: 目标止盈定投 -->
              <div v-else-if="form.strategy_type === 'target_profit_dca'" class="param-group-box">
                <div class="form-row grid-2">
                  <div class="form-group">
                    <label>定投周期 (交易日)</label>
                    <input type="number" class="form-control" v-model="form.config.dca_interval_days" />
                  </div>
                  <div class="form-group">
                    <label>金额 (元)</label>
                    <input type="number" class="form-control" v-model="form.config.dca_amount" />
                  </div>
                </div>
              </div>

              <!-- Case C: 智能网格震荡 -->
              <div v-else-if="form.strategy_type === 'smart_grid' || form.strategy_type === 'stock_smart_grid'" class="param-group-box">
                <div class="form-row grid-3">
                  <div class="form-group">
                    <label>网格下跌步长 (%)</label>
                    <input type="number" step="0.1" class="form-control" v-model="form.config.grid_step_down_pct" />
                  </div>
                  <div class="form-group">
                    <label>网格反弹步长 (%)</label>
                    <input type="number" step="0.1" class="form-control" v-model="form.config.grid_step_up_pct" />
                  </div>
                  <div class="form-group">
                    <label>单格金额 (元)</label>
                    <input type="number" class="form-control" v-model="form.config.grid_trade_amount" />
                  </div>
                </div>
              </div>

              <!-- Case D: 均线趋势跟踪 -->
              <div v-else-if="form.strategy_type === 'ma_trend' || form.strategy_type === 'stock_ma_trend'" class="param-group-box">
                <div class="form-row grid-2">
                  <div class="form-group">
                    <label>短期均线周期 (日)</label>
                    <input type="number" class="form-control" v-model="form.config.ma_fast" required />
                  </div>
                  <div class="form-group">
                    <label>长期均线周期 (日)</label>
                    <input type="number" class="form-control" v-model="form.config.ma_slow" required />
                  </div>
                </div>
                <div class="form-row grid-2">
                  <div class="form-group">
                    <label>金叉突破买入金额 (元)</label>
                    <input type="number" class="form-control" v-model="form.config.buy_amount" required />
                  </div>
                  <div class="form-group">
                    <label>死叉跌破卖出比例</label>
                    <select class="form-control" v-model="form.config.sell_ratio">
                      <option :value="0.5">减仓 50%</option>
                      <option :value="1.0">全部清仓 100%</option>
                    </select>
                  </div>
                </div>
              </div>

              <!-- Case E: 天机时空策略 -->
              <div v-else-if="form.strategy_type === 'tianjit' || form.strategy_type === 'stock_tianjit'" class="param-group-box tianjit-box">
                <div class="tianjit-header">
                  <span class="tianjit-icon">🏮</span>
                  <div>
                    <div class="tianjit-title">天机时空策略 · 四层信号过滤</div>
                    <div class="tianjit-subtitle">月度大势滤网 → 流日评分(35~98) → T+1次日前瞻 → 价格触发</div>
                  </div>
                </div>
                <!-- 评分阈值 & 月度大势 -->
                <div class="tianjit-section">
                  <div class="tianjit-section-title">📊 评分阈值 &amp; 月度大势滤网</div>
                  <div class="form-row grid-3">
                    <div class="form-group">
                      <label>大吉阈值 S级 (≥分)</label>
                      <input type="number" class="form-control" v-model.number="form.config.score_threshold_s" min="60" max="98" />
                    </div>
                    <div class="form-group">
                      <label>吉日阈值 A级 (≥分)</label>
                      <input type="number" class="form-control" v-model.number="form.config.score_threshold_a" min="50" max="90" />
                    </div>
                    <div class="form-group">
                      <label>平日阈值 B级 (≥分)</label>
                      <input type="number" class="form-control" v-model.number="form.config.score_threshold_b" min="40" max="80" />
                    </div>
                  </div>
                  <div class="form-row grid-2">
                    <div class="form-group">
                      <label>逆境月最大仓位 (%)</label>
                      <input type="number" class="form-control" v-model.number="form.config.pressure_max_position_pct" min="0" max="100" />
                      <div class="form-hint">逆境五行月强制限仓，默认 30%</div>
                    </div>
                    <div class="form-group">
                      <label>月度大势滤网</label>
                      <select class="form-control" v-model="form.config.monthly_regime_enabled">
                        <option :value="true">✅ 启用（推荐）</option>
                        <option :value="false">❌ 关闭</option>
                      </select>
                    </div>
                  </div>
                </div>
                <!-- 四级信号 -->
                <div class="tianjit-section">
                  <div class="tianjit-section-title">🎯 四级信号配置</div>
                  <div class="signal-tier-block signal-s">
                    <div class="signal-tier-head">
                      <span class="signal-badge s">S级 · 大吉进攻</span>
                      <label class="toggle-inline"><input type="checkbox" v-model="form.config.signal_s.enabled" /> 启用</label>
                    </div>
                    <div class="form-row grid-3" v-if="form.config.signal_s && form.config.signal_s.enabled">
                      <div class="form-group">
                        <label>买入金额 (元)</label>
                        <input type="number" class="form-control" v-model.number="form.config.signal_s.amount" />
                      </div>
                      <div class="form-group">
                        <label>叠加跌幅要求 (%, 0=无)</label>
                        <input type="number" step="0.1" class="form-control" v-model.number="form.config.signal_s.price_drop_required" />
                        <div class="form-hint">0=大吉日无需等跌直接买</div>
                      </div>
                      <div class="form-group">
                        <label>大吉日涨幅止盈 (%)</label>
                        <input type="number" step="0.1" class="form-control" v-model.number="form.config.signal_s.price_rise_sell" />
                      </div>
                    </div>
                  </div>
                  <div class="signal-tier-block signal-a">
                    <div class="signal-tier-head">
                      <span class="signal-badge a">A级 · 吉日逢低</span>
                      <label class="toggle-inline"><input type="checkbox" v-model="form.config.signal_a.enabled" /> 启用</label>
                    </div>
                    <div class="form-row grid-2" v-if="form.config.signal_a && form.config.signal_a.enabled">
                      <div class="form-group">
                        <label>逢低买入金额 (元)</label>
                        <input type="number" class="form-control" v-model.number="form.config.signal_a.amount" />
                      </div>
                      <div class="form-group">
                        <label>须跌幅 ≥ (%) 才触发</label>
                        <input type="number" step="0.1" class="form-control" v-model.number="form.config.signal_a.price_drop_required" />
                        <div class="form-hint">吉日须等跌才买</div>
                      </div>
                    </div>
                  </div>
                  <div class="signal-tier-block signal-c">
                    <div class="signal-tier-head">
                      <span class="signal-badge c">C级 · 冲凶防守</span>
                      <label class="toggle-inline"><input type="checkbox" v-model="form.config.signal_c.enabled" /> 启用</label>
                    </div>
                    <div class="form-row grid-3" v-if="form.config.signal_c && form.config.signal_c.enabled">
                      <div class="form-group">
                        <label>基础减仓比例</label>
                        <select class="form-control" v-model.number="form.config.signal_c.sell_ratio">
                          <option :value="0.20">减仓 20%</option>
                          <option :value="0.30">减仓 30%</option>
                          <option :value="0.40">减仓 40%</option>
                          <option :value="0.50">减仓 50%</option>
                        </select>
                      </div>
                      <div class="form-group">
                        <label>叠加跌幅追加减仓 (%)</label>
                        <input type="number" step="0.1" class="form-control" v-model.number="form.config.signal_c.price_drop_sell_trigger" />
                      </div>
                      <div class="form-group">
                        <label>强制清仓跌幅 (%)</label>
                        <input type="number" step="0.1" class="form-control" v-model.number="form.config.signal_c.force_clear_on_drop" />
                        <div class="form-hint">凶日跌超此值直接清仓</div>
                      </div>
                    </div>
                  </div>
                  <div class="signal-tier-block signal-sha">
                    <div class="signal-tier-head">
                      <span class="signal-badge sha">⚡ 伤官/七杀日专项抄底</span>
                      <label class="toggle-inline"><input type="checkbox" v-model="form.config.sha_enhanced_rules.enabled" /> 启用</label>
                    </div>
                    <div class="form-row grid-2" v-if="form.config.sha_enhanced_rules && form.config.sha_enhanced_rules.enabled">
                      <div class="form-group">
                        <label>须跌 ≥ (%) 才抄底</label>
                        <input type="number" step="0.1" class="form-control" v-model.number="form.config.sha_enhanced_rules.buy_drop_pct" />
                      </div>
                      <div class="form-group">
                        <label>抄底金额 (元)</label>
                        <input type="number" class="form-control" v-model.number="form.config.sha_enhanced_rules.buy_amount" />
                      </div>
                    </div>
                  </div>
                </div>
                <!-- T+1 前瞻 -->
                <div class="tianjit-section tianjit-t1">
                  <div class="tianjit-section-title">🔮 T+1 下一交易日前瞻信号 <span class="t1-badge">严格跳过周末/休市日</span></div>
                  <div class="t1-scenarios">
                    <div class="t1-scenario-item">📈 场景A：今跌+下个交易日大吉 → 增强买入×{{ form.config.t1_lookahead ? form.config.t1_lookahead.tomorrow_boost_multiplier : 1.5 }}</div>
                    <div class="t1-scenario-item">📉 场景B：今有浮盈+下个交易日凶 → 今日提前减仓</div>
                    <div class="t1-scenario-item">🌅 场景C：今平淡+下个交易日大吉 → 预建仓 ¥{{ form.config.t1_lookahead ? form.config.t1_lookahead.preview_amount : 1500 }}</div>
                    <div class="t1-scenario-item">🚀 场景D：连续大吉交易日 → 额外放大×{{ form.config.t1_lookahead ? form.config.t1_lookahead.consecutive_good_boost : 1.2 }}</div>
                  </div>
                  <div class="form-row grid-2">
                    <div class="form-group">
                      <label>下一交易日前瞻开关</label>
                      <select class="form-control" v-model="form.config.t1_lookahead.enabled">
                        <option :value="true">✅ 启用（推荐）</option>
                        <option :value="false">❌ 关闭</option>
                      </select>
                    </div>
                    <div class="form-group">
                      <label>场景A 今日跌幅触发 (%)</label>
                      <input type="number" step="0.1" class="form-control" v-model.number="form.config.t1_lookahead.today_drop_required_pct" />
                    </div>
                  </div>
                  <div v-if="form.config.t1_lookahead && form.config.t1_lookahead.enabled">
                    <div class="form-row grid-3">
                      <div class="form-group">
                        <label>下一交易日大吉阈值 (分)</label>
                        <input type="number" class="form-control" v-model.number="form.config.t1_lookahead.tomorrow_good_threshold" />
                        <div class="form-hint">≥此分触发场景A/C/D（周五自动推演周一）</div>
                      </div>
                      <div class="form-group">
                        <label>下一交易日凶日阈值 (分)</label>
                        <input type="number" class="form-control" v-model.number="form.config.t1_lookahead.tomorrow_bad_threshold" />
                        <div class="form-hint">&lt;此分触发场景B减仓</div>
                      </div>
                      <div class="form-group">
                        <label>下一交易日极凶阈值 (分)</label>
                        <input type="number" class="form-control" v-model.number="form.config.t1_lookahead.tomorrow_danger_threshold" />
                        <div class="form-hint">&lt;此分升级危险减仓</div>
                      </div>
                    </div>
                    <div class="form-row grid-3">
                      <div class="form-group">
                        <label>场景A 买入放大系数</label>
                        <input type="number" step="0.1" class="form-control" v-model.number="form.config.t1_lookahead.tomorrow_boost_multiplier" min="1.0" max="3.0" />
                      </div>
                      <div class="form-group">
                        <label>场景B 提前减仓比例</label>
                        <select class="form-control" v-model.number="form.config.t1_lookahead.tomorrow_reduce_ratio">
                          <option :value="0.20">减仓 20%</option>
                          <option :value="0.25">减仓 25%</option>
                          <option :value="0.30">减仓 30%</option>
                          <option :value="0.40">减仓 40%</option>
                        </select>
                      </div>
                      <div class="form-group">
                        <label>场景C 预建仓金额 (元)</label>
                        <input type="number" class="form-control" v-model.number="form.config.t1_lookahead.preview_amount" />
                      </div>
                    </div>
                    <div class="form-row grid-2">
                      <div class="form-group">
                        <label>场景D 连续大吉系数</label>
                        <input type="number" step="0.1" class="form-control" v-model.number="form.config.t1_lookahead.consecutive_good_boost" min="1.0" max="2.0" />
                      </div>
                      <div class="form-group">
                        <label>放大系数最高上限</label>
                        <input type="number" step="0.1" class="form-control" v-model.number="form.config.t1_lookahead.max_boost_cap_multiplier" min="1.0" max="3.0" />
                      </div>
                    </div>
                  </div>
                </div>
                <!-- 神煞 & 十神权重 -->
                <div class="tianjit-section">
                  <div class="tianjit-section-title">⚖️ 神煞权重（正=吉神加分，负=凶煞扣分）</div>
                  <div class="shensha-grid" v-if="form.config.shensha_weights">
                    <div class="shensha-item" v-for="(val, key) in form.config.shensha_weights" :key="key">
                      <label>{{ key }}</label>
                      <input type="number" class="form-control sm" v-model.number="form.config.shensha_weights[key]" min="-20" max="20" />
                    </div>
                  </div>
                </div>
                <div class="tianjit-section">
                  <div class="tianjit-section-title">🔰 十神权重</div>
                  <div class="shensha-grid" v-if="form.config.ten_god_weights">
                    <div class="shensha-item" v-for="(val, key) in form.config.ten_god_weights" :key="key">
                      <label>{{ key }}</label>
                      <input type="number" class="form-control sm" v-model.number="form.config.ten_god_weights[key]" min="-15" max="15" />
                    </div>
                  </div>
                </div>
                <!-- 全局止盈止损 -->
                <div class="tianjit-section">
                  <div class="tianjit-section-title">🛡️ 全局止盈止损 &amp; 冷却规则</div>
                  <div class="form-row grid-3">
                    <div class="form-group">
                      <label>全局止损线 (%)</label>
                      <input type="number" step="0.1" class="form-control" v-model.number="form.config.global_stop_loss_pct" />
                    </div>
                    <div class="form-group">
                      <label>累计止盈目标 (%)</label>
                      <input type="number" step="0.1" class="form-control" v-model.number="form.config.global_profit_target_pct" />
                    </div>
                    <div class="form-group">
                      <label>止盈卖出比例</label>
                      <select class="form-control" v-model.number="form.config.global_profit_sell_ratio">
                        <option :value="0.25">卖出 25%</option>
                        <option :value="0.40">卖出 40%</option>
                        <option :value="0.50">卖出 50%</option>
                        <option :value="1.00">全部清仓</option>
                      </select>
                    </div>
                  </div>
                  <div class="form-row grid-3">
                    <div class="form-group">
                      <label>卖出后重置利润基准</label>
                      <select class="form-control" v-model="form.config.reset_profit_on_sell" @change="form.config.global_profit_reset = form.config.reset_profit_on_sell">
                        <option :value="true">✅ 开启重置 (推荐)</option>
                        <option :value="false">❌ 关闭重置 (维持原成本)</option>
                      </select>
                      <div class="form-hint">开启后止盈或减仓将重置持仓浮盈基准，避免连续每天卖出</div>
                    </div>
                    <div class="form-group">
                      <label>买入冷却交易日数</label>
                      <input type="number" class="form-control" v-model.number="form.config.buy_cooldown_days" min="0" max="10" />
                    </div>
                    <div class="form-group">
                      <label>卖出冷却交易日数</label>
                      <input type="number" class="form-control" v-model.number="form.config.sell_cooldown_days" min="0" max="10" />
                    </div>
                  </div>
                </div>
              </div>

              <!-- Case F: 自定义多因子 -->
              <div v-else class="param-group-box">
                <div class="form-group">
                  <label>单日跌幅加仓阈值 (%)</label>
                  <input type="number" step="0.1" class="form-control" v-model="form.config.dip_buy_drop_pct" />
                </div>
                <div class="form-group">
                  <label>加仓买入金额 (元)</label>
                  <input type="number" class="form-control" v-model="form.config.dip_buy_amount" />
                </div>
                <div class="form-group">
                  <label>目标止盈阈值 (%)</label>
                  <input type="number" step="0.1" class="form-control" v-model="form.config.cumulative_profit_target_pct" />
                </div>
              </div>
            </div>

            <!-- 4. Fee Configuration Section -->
            <div class="form-section">
              <div class="section-head-flex">
                <h4 class="section-title">4. 交易手续费率与税费规则</h4>
                <button type="button" class="btn-text-action" @click="fetchTargetInfoAndFees">
                  🔄 重新从接口获取费率
                </button>
              </div>

              <!-- Stock Fee Configuration -->
              <div v-if="form.asset_type === 'stock'">
                <div class="form-row grid-2">
                  <div class="form-group">
                    <label>券商佣金费率 (%)</label>
                    <input
                      type="number"
                      step="0.001"
                      class="form-control"
                      :value="(form.fee_config.commission_rate * 100).toFixed(3)"
                      @input="form.fee_config.commission_rate = parseFloat($event.target.value) / 100.0"
                    />
                    <span class="help-text">标准A股佣金通常为万 2.5 (0.025%) ~ 万 1.5 (0.015%)</span>
                  </div>

                  <div class="form-group">
                    <label>单笔最低佣金 (元)</label>
                    <input
                      type="number"
                      step="1"
                      class="form-control"
                      v-model.number="form.fee_config.min_commission"
                    />
                    <span class="help-text">A股默认单笔佣金不足 5 元按 5 元收取</span>
                  </div>
                </div>

                <div class="form-row grid-2 mt-2">
                  <div class="form-group">
                    <label>证券交易印花税 (%)</label>
                    <input
                      type="number"
                      step="0.01"
                      class="form-control"
                      :value="(form.fee_config.stamp_duty_rate * 100).toFixed(2)"
                      @input="form.fee_config.stamp_duty_rate = parseFloat($event.target.value) / 100.0"
                    />
                    <span class="help-text">国家税法规定：仅在卖出股票时单边征收 0.05%</span>
                  </div>

                  <div class="form-group">
                    <label>证券交易过户费 (%)</label>
                    <input
                      type="number"
                      step="0.0001"
                      class="form-control"
                      :value="(form.fee_config.transfer_fee_rate * 100).toFixed(4)"
                      @input="form.fee_config.transfer_fee_rate = parseFloat($event.target.value) / 100.0"
                    />
                    <span class="help-text">双向征收万 0.1 (0.001%)</span>
                  </div>
                </div>
              </div>

              <!-- Fund Fee Configuration -->
              <div v-else>
                <div class="form-row grid-2">
                  <div class="form-group">
                    <label>申购费率 (%)</label>
                    <input
                      type="number"
                      step="0.01"
                      class="form-control"
                      :value="(form.fee_config.subscription_rate * 100).toFixed(2)"
                      @input="form.fee_config.subscription_rate = parseFloat($event.target.value) / 100.0"
                    />
                    <span class="help-text">支付宝一折通常为 0.10% ~ 0.15%，C类基金为 0.00%</span>
                  </div>

                  <div class="form-group">
                    <label>基金份额属性</label>
                    <div class="fee-badge-info">
                      {{ form.fee_config.is_c_share ? '🏷️ C 类份额（免申购费，7天以上免赎回费）' : '🏷️ A 类份额（前端申购费率）' }}
                    </div>
                  </div>
                </div>

                <!-- Tiered Redemption Fee Table -->
                <div class="tiers-table-wrap">
                  <label>赎回费率阶梯定义（按自然日持有天数精确计算）：</label>
                  <table class="tiers-table">
                    <thead>
                      <tr>
                        <th>起始天数</th>
                        <th>截止天数</th>
                        <th>赎回费率 (%)</th>
                        <th>规则标签</th>
                        <th style="width:60px;">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(tier, tIdx) in form.fee_config.redemption_tiers" :key="tIdx">
                        <td><input type="number" class="mini-input" v-model.number="tier.min_days" /> 天</td>
                        <td><input type="number" class="mini-input" v-model.number="tier.max_days" /> 天</td>
                        <td>
                          <input
                            type="number"
                            step="0.01"
                            class="mini-input"
                            :value="(tier.rate * 100).toFixed(2)"
                            @input="tier.rate = parseFloat($event.target.value) / 100.0"
                          /> %
                        </td>
                        <td><input type="text" class="mini-input label-in" v-model="tier.label" /></td>
                        <td>
                          <button
                            type="button"
                            class="action-icon-btn delete"
                            @click="removeFeeTier(tIdx)"
                            title="删除该阶梯"
                          >×</button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                  <button type="button" class="btn btn-sm btn-glass mt-2" @click="addFeeTier">
                    + 增加费率阶梯档位
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Modal Actions -->
          <div class="modal-actions">
            <button type="button" class="btn btn-glass" @click="closeFormModal">取消</button>
            <button type="button" class="btn btn-accent" @click="runDirectBacktestFromModal">
              📊 立即测试此策略
            </button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              {{ saving ? '保存中...' : '💾 保存策略' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- ============================================================== -->
    <!-- MODAL 2: BACKTEST LABORATORY MODAL                             -->
    <!-- ============================================================== -->
    <div class="modal-overlay" :class="{ active: showBacktestModal }">
      <div class="modal-content modal-xl">
        <div class="modal-header">
          <div class="header-with-tag">
            <h3>{{ btForm.asset_type === 'stock' ? '📈 股票量化策略回测工作台' : '💰 基金量化策略回测工作台' }}</h3>
            <span v-if="btResult && (btResult.fund_code || btResult.target_code)" class="bt-summary-tag">
              标的：{{ (btResult.fund_name && btResult.fund_name !== (btResult.fund_code || btResult.target_code)) ? (btResult.fund_name + ' (' + (btResult.fund_code || btResult.target_code) + ')') : (btResult.fund_code || btResult.target_code) }} · {{ btResult.total_days }} 交易日
            </span>
          </div>
          <button class="close-btn" @click="closeBacktestModal">×</button>
        </div>

        <div class="backtest-body">
          <!-- Backtest Control Bar -->
          <div class="bt-controls glass-card">
            <div class="ctrl-group">
              <label>资产类别</label>
              <div class="bt-asset-toggle">
                <button
                  type="button"
                  class="btn-tag"
                  :class="{ active: btForm.asset_type === 'fund' }"
                  @click="setBtAssetType('fund')"
                >💰 基金</button>
                <button
                  type="button"
                  class="btn-tag"
                  :class="{ active: btForm.asset_type === 'stock' }"
                  @click="setBtAssetType('stock')"
                >📈 股票</button>
              </div>
            </div>

            <div class="ctrl-group">
              <label>{{ btForm.asset_type === 'stock' ? '股票代码' : '基金代码' }}</label>
              <input
                type="text"
                class="form-control sm"
                v-model="btForm.fund_code"
                :placeholder="btForm.asset_type === 'stock' ? '如：600519、000001' : '如：000001、005827'"
              />
            </div>

            <div class="ctrl-group">
              <label>策略模型</label>
              <select class="form-control sm" v-model="btForm.strategy_type" @change="onBtStrategyTypeChange">
                <option
                  v-for="tpl in currentBtTemplates"
                  :key="tpl.id"
                  :value="tpl.id"
                >
                  {{ tpl.name }}
                </option>
              </select>
            </div>

            <div class="ctrl-group date-picker-group">
              <label>回测时间跨度</label>
              <div class="quick-dates">
                <button
                  type="button"
                  class="btn-tag"
                  :class="{ active: btDateRangeTag === '1m' }"
                  @click="setQuickDateRange('1m')"
                >近1月</button>
                <button
                  type="button"
                  class="btn-tag"
                  :class="{ active: btDateRangeTag === '3m' }"
                  @click="setQuickDateRange('3m')"
                >近3月</button>
                <button
                  type="button"
                  class="btn-tag"
                  :class="{ active: btDateRangeTag === '6m' }"
                  @click="setQuickDateRange('6m')"
                >近半年</button>
                <button
                  type="button"
                  class="btn-tag"
                  :class="{ active: btDateRangeTag === '1y' }"
                  @click="setQuickDateRange('1y')"
                >近1年</button>
                <button
                  type="button"
                  class="btn-tag"
                  :class="{ active: btDateRangeTag === '3y' }"
                  @click="setQuickDateRange('3y')"
                >近3年</button>
                <button
                  type="button"
                  class="btn-tag"
                  :class="{ active: btDateRangeTag === '5y' }"
                  @click="setQuickDateRange('5y')"
                >近5年</button>
                <button
                  type="button"
                  class="btn-tag"
                  :class="{ active: btDateRangeTag === 'all' }"
                  @click="setQuickDateRange('all')"
                >{{ btForm.asset_type === 'stock' ? '上市以来' : '成立以来' }}</button>
                <button
                  type="button"
                  class="btn-tag"
                  :class="{ active: btDateRangeTag === 'custom' }"
                  @click="setQuickDateRange('custom')"
                >自定义</button>
              </div>

              <!-- Custom Date Range Inputs -->
              <div v-if="btDateRangeTag === 'custom'" class="custom-date-picker-wrap">
                <div class="custom-date-box">
                  <span class="custom-date-label">开始:</span>
                  <input
                    type="date"
                    class="form-control sm date-input"
                    v-model="btForm.start_date"
                  />
                </div>
                <div class="custom-date-box">
                  <span class="custom-date-label">结束:</span>
                  <input
                    type="date"
                    class="form-control sm date-input"
                    v-model="btForm.end_date"
                  />
                </div>
              </div>
            </div>

            <div class="ctrl-group">
              <button class="btn btn-primary" @click="executeBacktest" :disabled="btLoading">
                <span>{{ btLoading ? '回测中...' : '▶️ 运行回测' }}</span>
              </button>
            </div>
          </div>

          <!-- Loading State -->
          <div v-if="btLoading" class="bt-loading-card glass-card">
            <div class="spinner"></div>
            <p>正在拉取全量历史行情并逐日演算交易指令与扣除手续费...</p>
          </div>

          <!-- Backtest Results Presentation -->
          <div v-else-if="btResult && btResult.success" class="bt-results">
            <!-- Metrics Summary Cards Grid -->
            <div class="metrics-dashboard">
              <div class="metric-card main">
                <div class="card-caption">策略累计总收益率</div>
                <div class="card-val" :class="btResult.metrics.strategy_return_pct >= 0 ? 'text-red' : 'text-green'">
                  {{ btResult.metrics.strategy_return_pct >= 0 ? '+' : '' }}{{ btResult.metrics.strategy_return_pct }}%
                </div>
                <div class="card-footnote">
                  基准买入持有：{{ btResult.metrics.benchmark_return_pct >= 0 ? '+' : '' }}{{ btResult.metrics.benchmark_return_pct }}%
                  (超额: {{ btResult.metrics.excess_return_pct >= 0 ? '+' : '' }}{{ btResult.metrics.excess_return_pct }}%)
                </div>
              </div>

              <div class="metric-card">
                <div class="card-caption">年化收益率 (CAGR)</div>
                <div class="card-val" :class="btResult.metrics.annualized_return_pct >= 0 ? 'text-red' : 'text-green'">
                  {{ btResult.metrics.annualized_return_pct >= 0 ? '+' : '' }}{{ btResult.metrics.annualized_return_pct }}%
                </div>
                <div class="card-footnote">复合年化增长</div>
              </div>

              <div class="metric-card">
                <div class="card-caption">最大回撤率</div>
                <div class="card-val text-yellow">
                  {{ btResult.metrics.max_drawdown_pct }}%
                </div>
                <div class="card-footnote">风险控制表现</div>
              </div>

              <div class="metric-card">
                <div class="card-caption">夏普比率 (Sharpe)</div>
                <div class="card-val">
                  {{ btResult.metrics.sharpe_ratio }}
                </div>
                <div class="card-footnote">无风险利率 2.0%</div>
              </div>

              <div class="metric-card">
                <div class="card-caption">交易胜率 / 交易次数</div>
                <div class="card-val">
                  {{ btResult.metrics.win_rate }}%
                </div>
                <div class="card-footnote">
                  买 {{ btResult.metrics.buy_trades }} 次 / 卖 {{ btResult.metrics.sell_trades }} 次 (赢 {{ btResult.metrics.winning_sells }})
                </div>
              </div>

              <div class="metric-card">
                <div class="card-caption">产生手续费总计</div>
                <div class="card-val text-secondary">
                  ¥{{ btResult.metrics.total_fees_paid }}
                </div>
                <div class="card-footnote">
                  {{ (btResult.asset_type === 'stock' || btForm.asset_type === 'stock') ? '买入佣金' : '申购' }} ¥{{ btResult.metrics.subscription_fees }} / {{ (btResult.asset_type === 'stock' || btForm.asset_type === 'stock') ? '卖出税费' : '赎回' }} ¥{{ btResult.metrics.redemption_fees }}
                </div>
              </div>

              <div class="metric-card">
                <div class="card-caption">期末总资产</div>
                <div class="card-val">
                  ¥{{ formatNumber(btResult.metrics.final_assets, 2) }}
                </div>
                <div class="card-footnote">
                  总投入: ¥{{ formatNumber(btResult.metrics.total_invested, 2) }}
                </div>
              </div>
            </div>

            <!-- ECharts Timeseries Chart -->
            <div class="glass-card chart-card">
              <div class="chart-header">
                <h4>📈 策略{{ (btResult.asset_type === 'stock' || btForm.asset_type === 'stock') ? '收益率曲线 vs 股票' : '净值收益曲线 vs 基金' }}基准对比 (带买卖触发点)</h4>
                <div class="chart-legend">
                  <span class="legend-item"><span class="dot line-strat"></span>策略累计收益率</span>
                  <span class="legend-item"><span class="dot line-bm"></span>{{ (btResult.asset_type === 'stock' || btForm.asset_type === 'stock') ? '股票买入持有基准' : '基金买入持有基准' }}</span>
                  <span class="legend-item"><span class="badge-dot buy"></span>加仓买入点</span>
                  <span class="legend-item"><span class="badge-dot sell"></span>{{ (btResult.asset_type === 'stock' || btForm.asset_type === 'stock') ? '做T/止盈卖出点' : '止盈卖出点' }}</span>
                </div>
              </div>
              <div ref="chartContainer" class="chart-container"></div>
            </div>

            <!-- Trade History Logs Table -->
            <div class="glass-card trades-table-card">
              <div class="trades-head">
                <h4>📋 策略逐笔交易流水明细 ({{ btResult.trades.length }} 笔)</h4>
                <button
                  type="button"
                  class="btn btn-sm btn-primary"
                  @click="applyBacktestAsLiveStrategy"
                >
                  💾 保存此回测为实盘监控策略
                </button>
              </div>

              <div class="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>序号</th>
                      <th>交易日期</th>
                      <th>操作方向</th>
                      <th>触发规则</th>
                      <th>{{ (btResult.asset_type === 'stock' || btForm.asset_type === 'stock') ? '成交价格' : '成交净值' }}</th>
                      <th>当日涨跌幅</th>
                      <th>成交金额 (元)</th>
                      <th>{{ (btResult.asset_type === 'stock' || btForm.asset_type === 'stock') ? '成交股数' : '成交份额' }}</th>
                      <th>扣除手续费</th>
                      <th>持有天数</th>
                      <th>本次盈亏</th>
                      <th>剩余现金</th>
                      <th>持仓市值</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="t in btResult.trades"
                      :key="t.id"
                      class="clickable-trade-row"
                      @click="openBtTradeDetail(t)"
                      title="点击查看本笔交易深度分析详情"
                    >
                      <td>{{ t.id }}</td>
                      <td>{{ t.date }}</td>
                      <td>
                        <span class="action-tag" :class="t.action === 'BUY' ? 'buy' : 'sell'">
                          {{ t.action_label || t.action }}
                        </span>
                      </td>
                      <td class="rule-cell" :title="t.rule_trigger">{{ t.rule_trigger }}</td>
                      <td>{{ t.nav.toFixed(btResult.asset_type === 'stock' ? 2 : 4) }}</td>
                      <td>
                        <span
                          :class="t.change_pct > 0 ? 'text-red' : (t.change_pct < 0 ? 'text-green' : 'text-secondary')"
                          style="font-weight: 600;"
                        >
                          {{ t.change_pct !== undefined && t.change_pct !== null ? (t.change_pct > 0 ? '+' : '') + t.change_pct.toFixed(2) + '%' : '-' }}
                        </span>
                      </td>
                      <td>¥{{ formatNumber(t.gross_amount, 2) }}</td>
                      <td>{{ formatNumber(t.shares, 2) }}</td>
                      <td class="text-secondary">¥{{ formatNumber(t.fee, 2) }}</td>
                      <td>{{ t.action === 'SELL' ? t.holding_days + ' 天' : '-' }}</td>
                      <td :class="t.realized_pnl > 0 ? 'text-red' : (t.realized_pnl < 0 ? 'text-green' : 'text-secondary')">
                        {{ t.action === 'SELL' ? (t.realized_pnl > 0 ? '+' : '') + '¥' + formatNumber(t.realized_pnl, 2) : '-' }}
                      </td>
                      <td>¥{{ formatNumber(t.cash_balance, 2) }}</td>
                      <td>¥{{ formatNumber(t.market_value, 2) }}</td>
                      <td>
                        <button type="button" class="btn btn-xs btn-glass text-info" @click.stop="openBtTradeDetail(t)">
                          🔍 详情
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ============================================================== -->
    <!-- MODAL 3: TRADE HISTORY MODAL FOR LIVE STRATEGY                -->
    <!-- ============================================================== -->
    <div class="modal-overlay" :class="{ active: showTradesModal }">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h3>📋 {{ activeStrategyForTrades?.name }} · 实盘交易流水记录</h3>
          <button class="close-btn" @click="showTradesModal = false">×</button>
        </div>

        <div class="table-container" style="max-height: 500px; overflow-y: auto;">
          <table>
            <thead>
              <tr>
                <th>交易时间</th>
                <th>操作类型</th>
                <th>{{ activeStrategyForTrades?.asset_type === 'stock' ? '成交价格' : '成交净值' }}</th>
                <th>交易金额</th>
                <th>{{ activeStrategyForTrades?.asset_type === 'stock' ? '成交股数' : '成交份额' }}</th>
                <th>手续费</th>
                <th>持有天数</th>
                <th>触发原因</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tr in liveTradesList" :key="tr.id">
                <td>{{ tr.trade_date }}</td>
                <td>
                  <span class="action-tag" :class="tr.action === 'BUY' ? 'buy' : 'sell'">
                    {{ tr.action_label || tr.action }}
                  </span>
                </td>
                <td>¥{{ tr.nav_or_price.toFixed(activeStrategyForTrades?.asset_type === 'stock' ? 2 : 4) }}</td>
                <td>¥{{ formatNumber(tr.gross_amount, 2) }}</td>
                <td>{{ formatNumber(tr.shares, activeStrategyForTrades?.asset_type === 'stock' ? 0 : 2) }} {{ activeStrategyForTrades?.asset_type === 'stock' ? '股' : '份' }}</td>
                <td>¥{{ formatNumber(tr.fee, 2) }}</td>
                <td>{{ tr.holding_days ? tr.holding_days + '天' : '-' }}</td>
                <td>{{ tr.trigger_reason }}</td>
              </tr>
              <tr v-if="!liveTradesList.length">
                <td colspan="8" class="text-center text-secondary" style="padding: 30px;">
                  暂无实盘交易记录。当盘中或收盘触发买卖信号并确认执行后，将自动记录在此处。
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ============================================================== -->
    <!-- MODAL 4: CONFIRM SIGNAL EXECUTION DIALOG                      -->
    <!-- ============================================================== -->
    <div class="modal-overlay" :class="{ active: showExecuteModal }">
      <div class="modal-content">
        <div class="modal-header">
          <h3>✅ 确认执行策略买卖操作</h3>
          <button class="close-btn" @click="showExecuteModal = false">×</button>
        </div>

        <div v-if="executingSignal" class="execute-form">
          <div class="alert alert-info">
            <strong>{{ executingSignal.target_name }}</strong> ({{ executingSignal.target_code }})<br />
            {{ executingSignal.reason }}
          </div>

          <div class="form-group">
            <label>操作方向</label>
            <div class="badge-direction" :class="executingSignal.action === 'BUY' ? 'buy' : 'sell'">
              {{ executingSignal.action === 'BUY' ? (executingSignal.asset_type === 'stock' ? '🟢 加仓买入' : '🟢 加仓申购') : (executingSignal.asset_type === 'stock' ? '🔴 减仓卖出' : '🔴 止盈赎回') }}
            </div>
          </div>

          <div v-if="executingSignal.action === 'BUY'" class="form-group">
            <label>{{ executingSignal.asset_type === 'stock' ? '实际买入金额 (元)' : '实际申购金额 (元)' }}</label>
            <input
              type="number"
              class="form-control"
              v-model="executeForm.amount"
              required
            />
          </div>

          <div v-else class="form-group">
            <label>{{ executingSignal.asset_type === 'stock' ? '实际卖出股数 (股)' : '实际赎回份额 (份)' }}</label>
            <input
              type="number"
              class="form-control"
              v-model="executeForm.shares"
              required
            />
          </div>

          <div class="form-group">
            <label>{{ executingSignal.asset_type === 'stock' ? '成交价格参考' : '成交净值参考' }}</label>
            <input
              type="number"
              :step="executingSignal.asset_type === 'stock' ? '0.01' : '0.0001'"
              class="form-control"
              v-model="executeForm.nav"
              required
            />
            <span class="help-text">{{ executingSignal.asset_type === 'stock' ? 'A股按即时撮合成交价或限价单成交记账' : '15:00 前操作将按今日官方公布净值最终确认' }}</span>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn btn-glass" @click="showExecuteModal = false">取消</button>
            <button type="button" class="btn btn-primary" @click="confirmExecuteSignal">
              确认记账并更新持仓
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ============================================================== -->
    <!-- MODAL 4: BACKTEST TRADE DETAIL MODAL                          -->
    <!-- ============================================================== -->
    <div class="modal-overlay" :class="{ active: showBtTradeDetailModal }" @click.self="showBtTradeDetailModal = false">
      <div class="modal-content modal-lg trade-detail-modal" v-if="selectedBtTrade">
        <div class="modal-header">
          <div class="trade-detail-title-wrap" style="display: flex; align-items: center; gap: 10px;">
            <span class="action-tag" :class="selectedBtTrade.action === 'BUY' ? 'buy' : 'sell'" style="font-size: 0.9rem; padding: 4px 10px;">
              {{ selectedBtTrade.action_label || selectedBtTrade.action }}
            </span>
            <h3 style="margin: 0;">第 {{ selectedBtTrade.id }} 笔 · 交易决策深度分析详情</h3>
          </div>
          <button class="close-btn" @click="showBtTradeDetailModal = false">×</button>
        </div>

        <div class="trade-detail-body" style="max-height: 580px; overflow-y: auto; padding: 10px 4px;">
          <!-- 1. 触发规则与决策判定 -->
          <div class="detail-card rule-card">
            <div class="detail-card-head" style="margin-bottom: 8px; font-weight: 600; color: var(--text-primary);">
              <span class="icon">🎯</span>
              <strong>触发规则与决策逻辑</strong>
            </div>
            <div class="rule-box-highlight" style="background: rgba(59, 130, 246, 0.1); border-left: 3px solid #3b82f6; padding: 10px 14px; border-radius: 6px; font-size: 0.95rem; line-height: 1.5;">
              {{ selectedBtTrade.rule_trigger }}
            </div>
          </div>

          <!-- 1.5 天机时空八字与次日前瞻信号剖析 (仅天机时空策略有) -->
          <div class="detail-card mt-3 tianjit-signal-card" v-if="selectedBtTrade.bazi_signal">
            <div class="detail-card-head" style="margin-bottom: 8px; font-weight: 600; color: #a78bfa;">
              <span class="icon">🏮</span>
              <strong>天机时空流日八字与前瞻剖析</strong>
            </div>
            <div class="grid-metrics-box">
              <div class="metric-cell">
                <span class="m-lbl">流日干支</span>
                <span class="m-val highlight">{{ selectedBtTrade.bazi_signal.ganzhi }}</span>
              </div>
              <div class="metric-cell">
                <span class="m-lbl">天机综合评分</span>
                <span class="m-val" :class="selectedBtTrade.bazi_signal.score >= 88 ? 'text-red' : (selectedBtTrade.bazi_signal.score < 60 ? 'text-green' : 'text-warning')">
                  {{ selectedBtTrade.bazi_signal.score }} 分 ({{ selectedBtTrade.bazi_signal.rating }})
                </span>
              </div>
              <div class="metric-cell">
                <span class="m-lbl">十神 / 信号标签</span>
                <span class="m-val">{{ selectedBtTrade.bazi_signal.ten_god }} · {{ selectedBtTrade.bazi_signal.tag }}</span>
              </div>
              <div class="metric-cell" v-if="selectedBtTrade.bazi_signal.shenshas && selectedBtTrade.bazi_signal.shenshas.length">
                <span class="m-lbl">当日临值神煞</span>
                <span class="m-val text-info">{{ selectedBtTrade.bazi_signal.shenshas.join('、') }}</span>
              </div>
              <div class="metric-cell">
                <span class="m-lbl">月度大势滤网</span>
                <span class="m-val">{{ selectedBtTrade.bazi_signal.monthly_regime === 'SUPPORT' ? '喜用顺境 (仓位充裕)' : (selectedBtTrade.bazi_signal.monthly_regime === 'PRESSURE' ? '逆境承压 (严控仓位)' : '中性平衡') }}</span>
              </div>
            </div>
            <div class="t1-analysis-box mt-2" v-if="selectedBtTrade.t1_signal && selectedBtTrade.t1_signal.scenario" style="background: rgba(139, 92, 246, 0.12); border-left: 3px solid #8b5cf6; padding: 8px 12px; border-radius: 6px; font-size: 0.88rem; line-height: 1.5; color: var(--text-primary);">
              <strong>🔮 T+1 下一交易日前瞻：</strong>
              <span>{{ selectedBtTrade.t1_signal.reason }}</span>
              <span v-if="selectedBtTrade.t1_signal.next_trading_label || selectedBtTrade.t1_signal.tomorrow_ganzhi" class="ml-1 text-secondary" style="font-size: 0.82rem;">
                （{{ selectedBtTrade.t1_signal.next_trading_label || '下一交易日' }}预告：{{ selectedBtTrade.t1_signal.next_trading_ganzhi || selectedBtTrade.t1_signal.tomorrow_ganzhi }}，评分 {{ selectedBtTrade.t1_signal.next_trading_score || selectedBtTrade.t1_signal.tomorrow_score }} 分 / {{ selectedBtTrade.t1_signal.next_trading_signal_level || selectedBtTrade.t1_signal.tomorrow_signal_level }}级<span v-if="selectedBtTrade.t1_signal.is_weekend_skipped" style="margin-left: 4px; color: #eab308; font-weight: 600;">[跳过休市]</span>）
              </span>
            </div>
          </div>

          <!-- 2. 当日行情与分时价位比对 -->
          <div class="detail-card mt-3">
            <div class="detail-card-head" style="margin-bottom: 8px; font-weight: 600; color: var(--text-primary);">
              <span class="icon">📊</span>
              <strong>成交点与当日盘面行情</strong>
            </div>
            <div class="grid-metrics-box">
              <div class="metric-cell">
                <span class="m-lbl">交易日期</span>
                <span class="m-val">{{ selectedBtTrade.date }}</span>
              </div>
              <div class="metric-cell">
                <span class="m-lbl">成交价格 / 净值</span>
                <span class="m-val highlight">¥{{ selectedBtTrade.nav ? Number(selectedBtTrade.nav).toFixed(btResult?.asset_type === 'stock' ? 2 : 4) : '-' }}</span>
              </div>
              <div class="metric-cell">
                <span class="m-lbl">当日全天涨跌幅</span>
                <span class="m-val" :class="selectedBtTrade.change_pct > 0 ? 'text-red' : (selectedBtTrade.change_pct < 0 ? 'text-green' : '')">
                  {{ selectedBtTrade.change_pct !== undefined && selectedBtTrade.change_pct !== null ? (selectedBtTrade.change_pct > 0 ? '+' : '') + Number(selectedBtTrade.change_pct).toFixed(2) + '%' : '-' }}
                </span>
              </div>
              <div class="metric-cell" v-if="selectedBtTrade.open">
                <span class="m-lbl">当日开盘价</span>
                <span class="m-val">¥{{ Number(selectedBtTrade.open).toFixed(2) }}</span>
              </div>
              <div class="metric-cell" v-if="selectedBtTrade.high">
                <span class="m-lbl">当日最高价 (冲高点)</span>
                <span class="m-val text-red">¥{{ Number(selectedBtTrade.high).toFixed(2) }}</span>
              </div>
              <div class="metric-cell" v-if="selectedBtTrade.low">
                <span class="m-lbl">当日最低价 (回踩点)</span>
                <span class="m-val text-green">¥{{ Number(selectedBtTrade.low).toFixed(2) }}</span>
              </div>
              <div class="metric-cell" v-if="selectedBtTrade.close">
                <span class="m-lbl">当日收盘价</span>
                <span class="m-val">¥{{ Number(selectedBtTrade.close).toFixed(2) }}</span>
              </div>
              <div class="metric-cell" v-if="selectedBtTrade.high && selectedBtTrade.low">
                <span class="m-lbl">日内振幅</span>
                <span class="m-val text-warning">{{ (((selectedBtTrade.high - selectedBtTrade.low) / (selectedBtTrade.open || selectedBtTrade.nav)) * 100).toFixed(2) }}%</span>
              </div>
            </div>
          </div>

          <!-- 3. 做T价差与成本摊薄剖析 -->
          <div class="detail-card mt-3">
            <div class="detail-card-head" style="margin-bottom: 8px; font-weight: 600; color: var(--text-primary);">
              <span class="icon">⚡</span>
              <strong>做T价差与持仓成本变动</strong>
            </div>
            <div class="grid-metrics-box">
              <div class="metric-cell" v-if="selectedBtTrade.cost_nav_before">
                <span class="m-lbl">交易前持仓成本</span>
                <span class="m-val">¥{{ Number(selectedBtTrade.cost_nav_before).toFixed(btResult?.asset_type === 'stock' ? 2 : 4) }}</span>
              </div>
              <div class="metric-cell" v-if="selectedBtTrade.cost_nav_after">
                <span class="m-lbl">交易后成本基准</span>
                <span class="m-val text-info">¥{{ Number(selectedBtTrade.cost_nav_after).toFixed(btResult?.asset_type === 'stock' ? 2 : 4) }}</span>
              </div>
              <div class="metric-cell" v-if="selectedBtTrade.cost_nav_before && selectedBtTrade.cost_nav_after">
                <span class="m-lbl">成本摊薄效果</span>
                <span class="m-val text-green">
                  {{ (selectedBtTrade.cost_nav_after - selectedBtTrade.cost_nav_before < -1e-5) ? '⬇ 成本下降 ¥' + (selectedBtTrade.cost_nav_before - selectedBtTrade.cost_nav_after).toFixed(3) : '持平 / 加权建仓' }}
                </span>
              </div>
              <div class="metric-cell" v-if="selectedBtTrade.action === 'SELL'">
                <span class="m-lbl">平均持有时长</span>
                <span class="m-val">{{ selectedBtTrade.holding_days }} 天</span>
              </div>
              <div class="metric-cell" v-if="selectedBtTrade.action === 'SELL'">
                <span class="m-lbl">本次实现盈亏</span>
                <span class="m-val" :class="selectedBtTrade.realized_pnl >= 0 ? 'text-red' : 'text-green'">
                  {{ selectedBtTrade.realized_pnl >= 0 ? '+' : '' }}¥{{ formatNumber(selectedBtTrade.realized_pnl, 2) }}
                </span>
              </div>
            </div>
          </div>

          <!-- 4. 交易财务与手续费清单 -->
          <div class="detail-card mt-3">
            <div class="detail-card-head" style="margin-bottom: 8px; font-weight: 600; color: var(--text-primary);">
              <span class="icon">{{ (btResult?.asset_type === 'stock' || btForm.asset_type === 'stock') ? '📈' : '💰' }}</span>
              <strong>交易财务与税费明细</strong>
            </div>
            <div class="grid-metrics-box">
              <div class="metric-cell">
                <span class="m-lbl">{{ (btResult?.asset_type === 'stock' || btForm.asset_type === 'stock') ? '成交股数' : '成交份额' }}</span>
                <span class="m-val">{{ formatNumber(selectedBtTrade.shares, (btResult?.asset_type === 'stock' || btForm.asset_type === 'stock') ? 0 : 2) }} {{ (btResult?.asset_type === 'stock' || btForm.asset_type === 'stock') ? '股' : '份' }}</span>
              </div>
              <div class="metric-cell">
                <span class="m-lbl">成交发生总额</span>
                <span class="m-val">¥{{ formatNumber(selectedBtTrade.gross_amount, 2) }}</span>
              </div>
              <div class="metric-cell">
                <span class="m-lbl">实际发生净额</span>
                <span class="m-val highlight">¥{{ formatNumber(selectedBtTrade.net_amount, 2) }}</span>
              </div>
              <div class="metric-cell">
                <span class="m-lbl">扣除总手续费</span>
                <span class="m-val text-secondary">¥{{ formatNumber(selectedBtTrade.fee, 2) }}</span>
              </div>
              <div class="metric-cell" v-if="selectedBtTrade.fee_breakdown?.commission !== undefined">
                <span class="m-lbl">券商佣金 (万2.5/保底5元)</span>
                <span class="m-val text-secondary">¥{{ formatNumber(selectedBtTrade.fee_breakdown.commission, 2) }}</span>
              </div>
              <div class="metric-cell" v-if="selectedBtTrade.fee_breakdown?.stamp_duty !== undefined">
                <span class="m-lbl">印花税 (卖出千0.5)</span>
                <span class="m-val text-secondary">¥{{ formatNumber(selectedBtTrade.fee_breakdown.stamp_duty, 2) }}</span>
              </div>
              <div class="metric-cell" v-if="selectedBtTrade.fee_breakdown?.transfer_fee !== undefined">
                <span class="m-lbl">证券过户费 (双向万0.1)</span>
                <span class="m-val text-secondary">¥{{ formatNumber(selectedBtTrade.fee_breakdown.transfer_fee, 2) }}</span>
              </div>
            </div>
          </div>

          <!-- 5. 交易后账户资金与持仓概况 -->
          <div class="detail-card mt-3">
            <div class="detail-card-head" style="margin-bottom: 8px; font-weight: 600; color: var(--text-primary);">
              <span class="icon">💼</span>
              <strong>交易后账户资产状态</strong>
            </div>
            <div class="grid-metrics-box">
              <div class="metric-cell">
                <span class="m-lbl">{{ (btResult?.asset_type === 'stock' || btForm.asset_type === 'stock') ? '成交后持仓股数' : '成交后持仓份额' }}</span>
                <span class="m-val">{{ formatNumber(selectedBtTrade.holding_shares, (btResult?.asset_type === 'stock' || btForm.asset_type === 'stock') ? 0 : 2) }} {{ (btResult?.asset_type === 'stock' || btForm.asset_type === 'stock') ? '股' : '份' }}</span>
              </div>
              <div class="metric-cell">
                <span class="m-lbl">成交后持仓市值</span>
                <span class="m-val">¥{{ formatNumber(selectedBtTrade.market_value, 2) }}</span>
              </div>
              <div class="metric-cell">
                <span class="m-lbl">成交后现金余额</span>
                <span class="m-val">¥{{ formatNumber(selectedBtTrade.cash_balance, 2) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer" style="padding: 14px 20px; display: flex; justify-content: flex-end;">
          <button type="button" class="btn btn-secondary" @click="showBtTradeDetailModal = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick, inject } from 'vue'
import * as echarts from 'echarts'
import api from '../api'

const showToast = inject('showToast', (msg) => alert(msg))

// Navigation tab: 'fund' | 'stock'
const currentTab = ref('fund')

// State variables
const fundStrategies = ref([])
const stockStrategies = ref([])
const presetTemplates = ref([])
const pendingSignals = ref([])
const scanning = ref(false)
const saving = ref(false)
const fetchingInfo = ref(false)

// Modals state
const showFormModal = ref(false)
const editingStrategy = ref(null)
const showBacktestModal = ref(false)
const showTradesModal = ref(false)
const activeStrategyForTrades = ref(null)
const liveTradesList = ref([])
const showExecuteModal = ref(false)
const executingSignal = ref(null)
const executeForm = reactive({ nav: 1.0, amount: 5000, shares: 0 })
const showBtTradeDetailModal = ref(false)
const selectedBtTrade = ref(null)

const openBtTradeDetail = (trade) => {
  selectedBtTrade.value = trade
  showBtTradeDetailModal.value = true
}

// Chart
const chartContainer = ref(null)
let chartInstance = null

// Fee Default Configs
const defaultFeeConfig = {
  subscription_rate: 0.001,
  original_subscription_rate: 0.015,
  is_c_share: false,
  redemption_tiers: [
    { min_days: 0, max_days: 6, rate: 0.015, label: '小于7天 (1.50%)' },
    { min_days: 7, max_days: 29, rate: 0.005, label: '7天至29天 (0.50%)' },
    { min_days: 30, max_days: 364, rate: 0.0025, label: '30天至364天 (0.25%)' },
    { min_days: 365, max_days: 999999, rate: 0.0, label: '1年及以上 (0.00% 免赎回费)' }
  ]
}

const defaultStockFeeConfig = {
  commission_rate: 0.00025,
  min_commission: 5.0,
  stamp_duty_rate: 0.0005,
  transfer_fee_rate: 0.00001
}

// Form State
const form = reactive({
  asset_type: 'fund',
  target_code: '',
  target_name: '',
  name: '',
  strategy_type: 'dip_buying_profit_take',
  initial_capital: 10000,
  settlement_type: 'T+1',
  config: {
    buy_tiers: [
      { type: 'drop', operator: '>=', drop_pct: 2.0, amount: 5000.0, label: '单日下跌 ≥ 2.0% 加仓 ¥5000' },
      { type: 'drop', operator: '>=', drop_pct: 5.0, amount: 8000.0, label: '单日下跌 ≥ 5.0% 加仓 ¥8000' },
      { type: 'drop', operator: '>=', drop_pct: 10.0, amount: 10000.0, label: '单日下跌 ≥ 10.0% 加仓 ¥10000' }
    ],
    dip_buy_tiers: [
      { type: 'drop', operator: '>=', drop_pct: 2.0, amount: 5000.0, label: '单日下跌 ≥ 2.0% 加仓 ¥5000' },
      { type: 'drop', operator: '>=', drop_pct: 5.0, amount: 8000.0, label: '单日下跌 ≥ 5.0% 加仓 ¥8000' },
      { type: 'drop', operator: '>=', drop_pct: 10.0, amount: 10000.0, label: '单日下跌 ≥ 10.0% 加仓 ¥10000' }
    ],
    surge_profit_tiers: [
      { surge_pct: 3.0, sell_ratio: 0.20, reset_on_sell: false, label: '单日上涨 ≥ 3.0% 卖出 1/5 (20%)' },
      { surge_pct: 5.0, sell_ratio: 0.25, reset_on_sell: false, label: '单日上涨 ≥ 5.0% 卖出 1/4 (25%)' },
      { surge_pct: 7.0, sell_ratio: 0.3333, reset_on_sell: false, label: '单日上涨 ≥ 7.0% 卖出 1/3 (33.33%)' }
    ],
    cumulative_profit_target_pct: 10.0,
    cumulative_profit_sell_ratio: 0.3333,
    cumulative_reset_on_sell: true,
    buy_cooldown_days: 1,
    sell_cooldown_days: 1,
    max_position_limit: 0,
    avoid_7day_penalty: true
  },
  fee_config: JSON.parse(JSON.stringify(defaultFeeConfig))
})

// Filtered Templates by Asset Type
const currentTemplates = computed(() => {
  const at = form.asset_type || 'fund'
  const filtered = presetTemplates.value.filter(t => t.category === at)
  return filtered.length > 0 ? filtered : presetTemplates.value
})

// Backtest Form State
const btDateRangeTag = ref('1y')
const btForm = reactive({
  asset_type: 'fund',
  fund_code: '000001',
  strategy_type: 'dip_buying_profit_take',
  strategy_config: {},
  fee_config: null,
  start_date: null,
  end_date: null
})
const btLoading = ref(false)
const btResult = ref(null)

const currentBtTemplates = computed(() => {
  const at = btForm.asset_type || 'fund'
  const filtered = presetTemplates.value.filter(t => t.category === at)
  return filtered.length > 0 ? filtered : presetTemplates.value
})

// Computed Stats for Funds
const runningCount = computed(() => fundStrategies.value.filter(s => s.status === 'running').length)
const totalInitialCapital = computed(() => fundStrategies.value.reduce((acc, s) => acc + (s.initial_capital || 0), 0))
const totalAssetsVal = computed(() => fundStrategies.value.reduce((acc, s) => acc + (s.total_assets || 0), 0))
const totalPnlVal = computed(() => fundStrategies.value.reduce((acc, s) => acc + (s.total_pnl || 0), 0))
const totalPnlPctVal = computed(() => totalInitialCapital.value > 0 ? (totalPnlVal.value / totalInitialCapital.value * 100) : 0)
const fundPendingSignals = computed(() => pendingSignals.value.filter(sig => !sig.asset_type || sig.asset_type === 'fund'))
const pendingSignalsCount = computed(() => fundPendingSignals.value.length)

// Computed Stats for Stocks
const stockRunningCount = computed(() => stockStrategies.value.filter(s => s.status === 'running').length)
const stockTotalInitialCapital = computed(() => stockStrategies.value.reduce((acc, s) => acc + (s.initial_capital || 0), 0))
const stockTotalAssetsVal = computed(() => stockStrategies.value.reduce((acc, s) => acc + (s.total_assets || 0), 0))
const stockTotalPnlVal = computed(() => stockStrategies.value.reduce((acc, s) => acc + (s.total_pnl || 0), 0))
const stockTotalPnlPctVal = computed(() => stockTotalInitialCapital.value > 0 ? (stockTotalPnlVal.value / stockTotalInitialCapital.value * 100) : 0)
const stockPendingSignals = computed(() => pendingSignals.value.filter(sig => sig.asset_type === 'stock'))
const stockPendingSignalsCount = computed(() => stockPendingSignals.value.length)

// Format number utility
const formatNumber = (val, decimals = 2) => {
  if (val === null || val === undefined || isNaN(val)) return '0.00'
  return Number(val).toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

// Format price utility (4 decimals for funds, 2 decimals for stocks)
const formatPrice = (val, assetType = 'fund') => {
  if (val === null || val === undefined || isNaN(val)) return '-'
  return Number(val).toFixed(assetType === 'stock' ? 2 : 4)
}

// Strategy Type Name Helper
const getStrategyTypeName = (stype) => {
  const map = {
    intraday_t: '分时做T与底仓波段',
    stock_intraday_t: '分时做T与底仓波段',
    dip_buying_profit_take: '跌幅加仓与阶梯止盈',
    target_profit_dca: '目标止盈定投',
    smart_grid: '智能网格震荡',
    ma_trend: '均线趋势跟踪',
    custom: '自定义多因子',
    stock_dip_profit_take: '跌幅加仓与阶梯止盈',
    stock_smart_grid: '智能网格震荡',
    stock_ma_trend: '均线趋势跟踪',
    stock_custom: '自定义多因子',
    tianjit: '天机时空策略',
    stock_tianjit: '天机时空策略'
  }
  return map[stype] || stype
}

// Rule Tags for Card Helper
const getStrategyRuleTags = (strat) => {
  const cfg = strat.config || {}
  const stype = strat.strategy_type
  const tags = []

  if (stype === 'tianjit' || stype === 'stock_tianjit') {
    tags.push('时空择时·四层信号')
    if (cfg.score_threshold_s) tags.push(`S级大吉 ≥${cfg.score_threshold_s}分`)
    if (cfg.t1_lookahead?.enabled) tags.push('T+1次日前瞻联动')
    if (cfg.monthly_regime_enabled) tags.push('月度大势滤网')
  } else if (stype === 'intraday_t' || stype === 'stock_intraday_t') {
    if (cfg.initial_base_shares) tags.push(`底仓 ${cfg.initial_base_shares}股`)
    if (cfg.t_surge_sell_pct) tags.push(`冲高 ≥ +${cfg.t_surge_sell_pct}% 高抛 ${cfg.t_sell_shares || 300}股`)
    if (cfg.enable_pullback_buyback === false) {
      tags.push('仅高抛不接回')
    } else if (cfg.pullback_ref_type === 'from_daily_change') {
      tags.push(`当天跌 ≥ ${cfg.daily_drop_buyback_pct || 2.0}% 接回`)
    } else {
      tags.push(`回踩 ≥ -${cfg.t_pullback_buy_pct || 1.5}% 接回`)
    }
    if (cfg.base_protect_shares) tags.push(`锁定保护 ${cfg.base_protect_shares}股`)
    if (cfg.enable_lot_profit_take !== false && cfg.lot_profit_take_pct) tags.push(`批次涨 ≥ +${cfg.lot_profit_take_pct}% 独立止盈`)
    if (cfg.cumulative_profit_target_pct) tags.push(`总目标止盈 ≥ ${cfg.cumulative_profit_target_pct}%`)
  } else if (stype === 'dip_buying_profit_take' || stype === 'stock_dip_profit_take') {
    const rawBuy = cfg.buy_tiers || cfg.dip_buy_tiers || []
    if (rawBuy && rawBuy.length) {
      rawBuy.forEach(t => {
        const type = t.type || (t.rise_pct ? 'rise' : (t.is_routine || (!t.drop_pct && !t.threshold_pct) ? 'routine' : 'drop'))
        if (type === 'drop') {
          const op = t.operator || '>='
          tags.push(`跌 ${op} ${t.drop_pct || t.threshold_pct}% 加 ¥${t.amount}`)
        } else if (type === 'rise') {
          const op = t.operator || '<='
          tags.push(`涨 ${op} ${t.rise_pct || t.threshold_pct}% 加 ¥${t.amount}`)
        } else if (type === 'routine') {
          tags.push(`日常加 ¥${t.amount}`)
        }
      })
    } else if (cfg.dip_buy_drop_pct) {
      tags.push(`跌 ≥ ${cfg.dip_buy_drop_pct}% 加 ¥${cfg.dip_buy_amount}`)
    }

    if (cfg.surge_profit_tiers && cfg.surge_profit_tiers.length) {
      cfg.surge_profit_tiers.forEach(st => {
        tags.push(`涨 ≥ ${st.surge_pct}% 卖 ${(st.sell_ratio*100).toFixed(0)}%`)
      })
    } else if (cfg.surge_profit_pct) {
      tags.push(`暴涨 ≥ ${cfg.surge_profit_pct}% 卖 ${(cfg.surge_profit_sell_ratio*100).toFixed(0)}%`)
    }

    if (cfg.cumulative_profit_target_pct) {
      tags.push(`轮次浮盈 ≥ ${cfg.cumulative_profit_target_pct}% 卖 ${(cfg.cumulative_profit_sell_ratio*100).toFixed(0)}%`)
    }
  } else if (stype === 'target_profit_dca') {
    tags.push(`每 ${cfg.dca_interval_days || 5} 日定投 ¥${cfg.dca_amount || 1000}`)
    tags.push(`目标浮盈 ≥ ${cfg.target_profit_pct || 15}% 止盈`)
  } else if (stype === 'smart_grid' || stype === 'stock_smart_grid') {
    tags.push(`跌 ${cfg.grid_step_down_pct}% 加仓`)
    tags.push(`涨 ${cfg.grid_step_up_pct}% 卖出一格`)
  } else if (stype === 'ma_trend' || stype === 'stock_ma_trend') {
    tags.push(`MA${cfg.ma_fast}/MA${cfg.ma_slow} 均线跟踪`)
  } else {
    tags.push('多因子自定义规则')
  }

  tags.push(`${strat.settlement_type || 'T+1'} 结算`)
  return tags
}

// -------------------------------------------------------------
// Load Initial Data
// -------------------------------------------------------------
const loadStrategies = async () => {
  try {
    const [funds, stocks] = await Promise.all([
      api.getStrategies('fund'),
      api.getStrategies('stock')
    ])
    fundStrategies.value = funds || []
    stockStrategies.value = stocks || []
  } catch (e) {
    showToast('加载策略列表失败: ' + (e.response?.data?.detail || e.message))
  }
}

const loadTemplates = async () => {
  try {
    const tpls = await api.getStrategyTemplates()
    presetTemplates.value = tpls || []
  } catch (e) {
    // Ignore
  }
}

const loadSignals = async () => {
  try {
    const sigs = await api.getStrategySignals('pending')
    pendingSignals.value = sigs || []
  } catch (e) {
    // Ignore
  }
}

const scanSignals = async () => {
  scanning.value = true
  try {
    const res = await api.scanStrategySignals()
    await loadSignals()
    await loadStrategies()
    showToast(`信号扫描完成，发现 ${res.count || 0} 条触发信号`)
  } catch (e) {
    showToast('扫描信号失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    scanning.value = false
  }
}

// -------------------------------------------------------------
// Form Operations
// -------------------------------------------------------------
const setFormAssetType = (type) => {
  form.asset_type = type
  if (type === 'stock') {
    form.fee_config = JSON.parse(JSON.stringify(defaultStockFeeConfig))
    const firstStockTpl = presetTemplates.value.find(t => t.category === 'stock')
    if (firstStockTpl) selectPresetTemplate(firstStockTpl)
  } else {
    form.fee_config = JSON.parse(JSON.stringify(defaultFeeConfig))
    const firstFundTpl = presetTemplates.value.find(t => t.category === 'fund')
    if (firstFundTpl) selectPresetTemplate(firstFundTpl)
  }
}

const setBtAssetType = (type) => {
  btForm.asset_type = type
  if (type === 'stock') {
    btForm.fund_code = stockStrategies.value[0]?.target_code || '600519'
    const firstStockTpl = presetTemplates.value.find(t => t.category === 'stock')
    if (firstStockTpl) {
      btForm.strategy_type = firstStockTpl.id
      btForm.strategy_config = JSON.parse(JSON.stringify(firstStockTpl.default_config || {}))
    }
  } else {
    btForm.fund_code = fundStrategies.value[0]?.target_code || '000001'
    const firstFundTpl = presetTemplates.value.find(t => t.category === 'fund')
    if (firstFundTpl) {
      btForm.strategy_type = firstFundTpl.id
      btForm.strategy_config = JSON.parse(JSON.stringify(firstFundTpl.default_config || {}))
    }
  }
  executeBacktest()
}

const ensureBuyTiers = () => {
  if (!form.config.buy_tiers) {
    form.config.buy_tiers = form.config.dip_buy_tiers || []
  }
  form.config.dip_buy_tiers = form.config.buy_tiers
  return form.config.buy_tiers
}

const onTierTypeChange = (tier) => {
  if (tier.type === 'drop') {
    if (!tier.drop_pct) tier.drop_pct = tier.rise_pct || 2.0
    if (!tier.operator) tier.operator = '>='
    delete tier.rise_pct
  } else if (tier.type === 'rise') {
    if (!tier.rise_pct) tier.rise_pct = tier.drop_pct || 1.5
    if (!tier.operator) tier.operator = '<='
    delete tier.drop_pct
  } else if (tier.type === 'routine') {
    delete tier.drop_pct
    delete tier.rise_pct
    delete tier.operator
  }
  updateTierLabel(tier)
}

const updateTierLabel = (tier) => {
  const amt = tier.amount || 0
  const op = tier.operator || (tier.type === 'rise' ? '<=' : '>=')
  if (tier.type === 'drop') {
    tier.label = `单日下跌 ${op} ${tier.drop_pct || 2.0}% 加仓 ¥${amt}`
  } else if (tier.type === 'rise') {
    tier.label = `单日上涨 ${op} ${tier.rise_pct || 1.5}% 加仓 ¥${amt}`
  } else if (tier.type === 'routine') {
    tier.label = `日常打底加仓 (未触发特殊涨跌时) ¥${amt}`
  }
}

const addDropTier = () => {
  const list = ensureBuyTiers()
  const dropTiers = list.filter(t => t.type === 'drop' || (!t.type && !t.rise_pct))
  const last = dropTiers[dropTiers.length - 1]
  const nextDrop = last ? Number(((last.drop_pct || 2.0) + 2.0).toFixed(1)) : 2.0
  const nextAmt = last ? (last.amount || 5000) + 2000 : 5000
  const item = {
    type: 'drop',
    operator: '>=',
    drop_pct: nextDrop,
    amount: nextAmt,
    label: `单日下跌 ≥ ${nextDrop}% 加仓 ¥${nextAmt}`
  }
  list.push(item)
}

const addRiseTier = () => {
  const list = ensureBuyTiers()
  const riseTiers = list.filter(t => t.type === 'rise')
  const last = riseTiers[riseTiers.length - 1]
  const nextRise = last ? Number(((last.rise_pct || 1.5) + 1.0).toFixed(1)) : 1.5
  const nextAmt = last ? (last.amount || 3000) + 2000 : 3000
  const item = {
    type: 'rise',
    operator: '<=',
    rise_pct: nextRise,
    amount: nextAmt,
    label: `单日上涨 ≤ ${nextRise}% 加仓 ¥${nextAmt}`
  }
  list.push(item)
}

const addRoutineTier = () => {
  const list = ensureBuyTiers()
  const existingRoutine = list.find(t => t.type === 'routine')
  if (existingRoutine) {
    showToast('已存在日常加仓档位，可直接在列表中调整金额')
    return
  }
  const item = {
    type: 'routine',
    amount: 1000,
    label: '日常打底加仓 (未满足涨跌加仓条件时)'
  }
  list.push(item)
}

const removeBuyTier = (idx) => {
  const list = ensureBuyTiers()
  list.splice(idx, 1)
}

const addDipTier = addDropTier
const removeDipTier = removeBuyTier
const removeDropTier = removeBuyTier

const addSurgeTier = () => {
  if (!form.config.surge_profit_tiers) form.config.surge_profit_tiers = []
  const last = form.config.surge_profit_tiers[form.config.surge_profit_tiers.length - 1]
  const nextSurge = last ? Number((last.surge_pct + 2.0).toFixed(1)) : 5.0
  form.config.surge_profit_tiers.push({
    surge_pct: nextSurge,
    sell_ratio: 0.25,
    reset_on_sell: false,
    label: `单日上涨 ≥ ${nextSurge}% 卖出 1/4`
  })
}

const removeSurgeTier = (idx) => {
  if (form.config.surge_profit_tiers) {
    form.config.surge_profit_tiers.splice(idx, 1)
  }
}

const openCreateModal = (targetAssetType = null) => {
  editingStrategy.value = null
  const at = targetAssetType || currentTab.value || 'fund'
  form.asset_type = at
  form.target_code = ''
  form.target_name = ''
  form.name = ''
  form.initial_capital = at === 'stock' ? 20000 : 10000
  form.settlement_type = 'T+1'

  if (at === 'stock') {
    form.strategy_type = 'dip_buying_profit_take'
    form.fee_config = JSON.parse(JSON.stringify(defaultStockFeeConfig))
  } else {
    form.strategy_type = 'dip_buying_profit_take'
    form.fee_config = JSON.parse(JSON.stringify(defaultFeeConfig))
  }

  form.config = {
    buy_tiers: [
      { type: 'drop', operator: '>=', drop_pct: 2.0, amount: 5000.0, label: '单日下跌 ≥ 2.0% 加仓 ¥5000' },
      { type: 'drop', operator: '>=', drop_pct: 5.0, amount: 8000.0, label: '单日下跌 ≥ 5.0% 加仓 ¥8000' },
      { type: 'drop', operator: '>=', drop_pct: 10.0, amount: 10000.0, label: '单日下跌 ≥ 10.0% 加仓 ¥10000' }
    ],
    dip_buy_tiers: [
      { type: 'drop', operator: '>=', drop_pct: 2.0, amount: 5000.0, label: '单日下跌 ≥ 2.0% 加仓 ¥5000' },
      { type: 'drop', operator: '>=', drop_pct: 5.0, amount: 8000.0, label: '单日下跌 ≥ 5.0% 加仓 ¥8000' },
      { type: 'drop', operator: '>=', drop_pct: 10.0, amount: 10000.0, label: '单日下跌 ≥ 10.0% 加仓 ¥10000' }
    ],
    surge_profit_tiers: [
      { surge_pct: 3.0, sell_ratio: 0.20, reset_on_sell: false, label: '单日上涨 ≥ 3.0% 卖出 1/5 (20%)' },
      { surge_pct: 5.0, sell_ratio: 0.25, reset_on_sell: false, label: '单日上涨 ≥ 5.0% 卖出 1/4 (25%)' },
      { surge_pct: 7.0, sell_ratio: 0.3333, reset_on_sell: false, label: '单日上涨 ≥ 7.0% 卖出 1/3 (33.33%)' }
    ],
    cumulative_profit_target_pct: 10.0,
    cumulative_profit_sell_ratio: 0.3333,
    cumulative_reset_on_sell: true,
    buy_cooldown_days: 1,
    sell_cooldown_days: 1,
    max_position_limit: 0,
    avoid_7day_penalty: true
  }

  showFormModal.value = true
}

const openEditModal = (strat) => {
  editingStrategy.value = strat
  form.asset_type = strat.asset_type || 'fund'
  form.target_code = strat.target_code
  form.target_name = strat.target_name
  form.name = strat.name
  form.strategy_type = strat.strategy_type
  form.initial_capital = strat.initial_capital
  form.settlement_type = strat.settlement_type || 'T+1'
  form.config = JSON.parse(JSON.stringify(strat.config || {}))

  // Normalize multi-tier and cooldown configs if editing older records
  if (form.strategy_type === 'dip_buying_profit_take' || form.strategy_type === 'stock_dip_profit_take') {
    let buyTiers = form.config.buy_tiers || form.config.dip_buy_tiers
    if (!buyTiers || !Array.isArray(buyTiers)) {
      buyTiers = [
        { type: 'drop', operator: '>=', drop_pct: form.config.dip_buy_drop_pct || 2.0, amount: form.config.dip_buy_amount || 5000.0, label: '单日下跌加仓' }
      ]
    } else {
      buyTiers.forEach(t => {
        if (!t.type) {
          if (t.rise_pct || t.is_rise) t.type = 'rise'
          else if (t.is_routine || (!t.drop_pct && !t.threshold_pct)) t.type = 'routine'
          else t.type = 'drop'
        }
        if (!t.operator && t.type !== 'routine') {
          t.operator = t.type === 'rise' ? '<=' : '>='
        }
      })
    }
    form.config.buy_tiers = buyTiers
    form.config.dip_buy_tiers = buyTiers

    if (!form.config.surge_profit_tiers || !Array.isArray(form.config.surge_profit_tiers)) {
      form.config.surge_profit_tiers = [
        { surge_pct: form.config.surge_profit_pct || 7.0, sell_ratio: form.config.surge_profit_sell_ratio || 0.25, reset_on_sell: false, label: '单日大涨止盈' }
      ]
    } else {
      form.config.surge_profit_tiers.forEach(st => {
        if (st.reset_on_sell === undefined) st.reset_on_sell = false
      })
    }
    if (form.config.cumulative_reset_on_sell === undefined) {
      form.config.cumulative_reset_on_sell = form.config.reset_profit_on_sell !== undefined ? form.config.reset_profit_on_sell : true
    }
    if (form.config.buy_cooldown_days === undefined) {
      form.config.buy_cooldown_days = form.config.cooldown_trading_days || 1
    }
    if (form.config.sell_cooldown_days === undefined) {
      form.config.sell_cooldown_days = form.config.cooldown_trading_days || 1
    }
  }

  if (strat.fee_config) {
    form.fee_config = JSON.parse(JSON.stringify(strat.fee_config))
  } else {
    form.fee_config = form.asset_type === 'stock'
      ? JSON.parse(JSON.stringify(defaultStockFeeConfig))
      : JSON.parse(JSON.stringify(defaultFeeConfig))
  }
  showFormModal.value = true
}

const closeFormModal = () => {
  showFormModal.value = false
}

const selectPresetTemplate = (tpl) => {
  form.strategy_type = tpl.id
  form.config = JSON.parse(JSON.stringify(tpl.default_config || {}))
}

const fetchTargetInfoAndFees = async () => {
  const code = form.target_code.trim()
  if (!code) return
  fetchingInfo.value = true
  try {
    if (form.asset_type === 'stock') {
      const stockInfo = await api.lookupStock(code)
      if (stockInfo && stockInfo.name) {
        form.target_name = stockInfo.name
        if (!form.name || form.name.includes('策略') || form.name.includes('网格') || form.name.includes('倍投')) {
          form.name = `${stockInfo.name} - ${getStrategyTypeName(form.strategy_type)}`
        }
      }
      const feeInfo = await api.getStockFeeStructure(code)
      if (feeInfo) form.fee_config = feeInfo
    } else {
      const fundInfo = await api.lookupFund(code)
      if (fundInfo && fundInfo.name) {
        form.target_name = fundInfo.name
        if (!form.name || form.name.includes('大跌倍投') || form.name.includes('策略')) {
          form.name = `${fundInfo.name} - ${getStrategyTypeName(form.strategy_type)}`
        }
      }
      const feeInfo = await api.getFundFeeStructure(code)
      if (feeInfo) form.fee_config = feeInfo
    }
  } catch (e) {
    // Ignore
  } finally {
    fetchingInfo.value = false
  }
}

const addFeeTier = () => {
  if (!form.fee_config.redemption_tiers) form.fee_config.redemption_tiers = []
  form.fee_config.redemption_tiers.push({
    min_days: 30,
    max_days: 364,
    rate: 0.0025,
    label: '自定义阶梯 (0.25%)'
  })
}

const removeFeeTier = (idx) => {
  if (form.fee_config.redemption_tiers) {
    form.fee_config.redemption_tiers.splice(idx, 1)
  }
}

const saveStrategy = async () => {
  if (!form.target_code) {
    showToast(form.asset_type === 'stock' ? '请输入股票代码' : '请输入基金代码')
    return
  }
  saving.value = true
  try {
    const payload = {
      asset_type: form.asset_type || 'fund',
      target_code: form.target_code.trim(),
      target_name: form.target_name || form.target_code,
      strategy_type: form.strategy_type,
      name: form.name || `${form.target_name || form.target_code} - ${getStrategyTypeName(form.strategy_type)}`,
      initial_capital: Number(form.initial_capital) || 10000,
      settlement_type: form.settlement_type || 'T+1',
      config: form.config,
      fee_config: form.fee_config,
      status: 'running'
    }

    if (editingStrategy.value) {
      await api.updateStrategy(editingStrategy.value.id, payload)
      showToast('策略修改成功')
    } else {
      await api.createStrategy(payload)
      showToast('策略创建成功并已加入实盘监控')
    }

    closeFormModal()
    await loadStrategies()
    await loadSignals()
  } catch (e) {
    showToast('保存策略失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

const toggleStrategyStatus = async (strat) => {
  const newStatus = strat.status === 'running' ? 'paused' : 'running'
  try {
    await api.updateStrategy(strat.id, { status: newStatus })
    strat.status = newStatus
    showToast(newStatus === 'running' ? '策略已恢复监控' : '策略已暂停')
  } catch (e) {
    showToast('更新状态失败')
  }
}

const deleteStrategyItem = async (strat) => {
  if (!confirm(`确定要删除策略「${strat.name}」吗？`)) return
  try {
    await api.deleteStrategy(strat.id)
    showToast('策略已删除')
    await loadStrategies()
    await loadSignals()
  } catch (e) {
    showToast('删除失败')
  }
}

// -------------------------------------------------------------
// Backtesting Laboratory
// -------------------------------------------------------------
const onBtStrategyTypeChange = () => {
  const at = btForm.asset_type || 'fund'
  const tpl = presetTemplates.value.find(t => t.id === btForm.strategy_type && t.category === at) ||
              presetTemplates.value.find(t => t.id === btForm.strategy_type)
  if (tpl) {
    btForm.strategy_config = JSON.parse(JSON.stringify(tpl.default_config || {}))
  }
  executeBacktest()
}

const openBacktestModal = (prefillCode, assetType = 'fund') => {
  btForm.asset_type = assetType
  if (prefillCode) {
    btForm.fund_code = prefillCode
  } else {
    btForm.fund_code = assetType === 'stock'
      ? (stockStrategies.value[0]?.target_code || '600519')
      : (fundStrategies.value[0]?.target_code || '000001')
  }
  setQuickDateRange('1y')
  showBacktestModal.value = true
  executeBacktest()
}

const openBacktestFromCard = (strat) => {
  btForm.asset_type = strat.asset_type || 'fund'
  btForm.fund_code = strat.target_code
  btForm.strategy_type = strat.strategy_type
  btForm.strategy_config = JSON.parse(JSON.stringify(strat.config || {}))
  btForm.fee_config = strat.fee_config ? JSON.parse(JSON.stringify(strat.fee_config)) : null
  setQuickDateRange('1y')
  showBacktestModal.value = true
  executeBacktest()
}

const openQuickBacktest = openBacktestFromCard

const runDirectBacktestFromModal = () => {
  btForm.asset_type = form.asset_type || 'fund'
  btForm.fund_code = form.target_code || (form.asset_type === 'stock' ? '600519' : '000001')
  btForm.strategy_type = form.strategy_type
  btForm.strategy_config = JSON.parse(JSON.stringify(form.config || {}))
  btForm.fee_config = JSON.parse(JSON.stringify(form.fee_config || {}))
  setQuickDateRange('1y')
  showBacktestModal.value = true
  setTimeout(() => {
    executeBacktest()
  }, 60)
}

const closeBacktestModal = () => {
  showBacktestModal.value = false
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

const setQuickDateRange = (tag) => {
  btDateRangeTag.value = tag
  const now = new Date()
  const endStr = now.toISOString().split('T')[0]
  let startStr = null

  if (tag === '1m') {
    const d = new Date()
    d.setMonth(d.getMonth() - 1)
    startStr = d.toISOString().split('T')[0]
  } else if (tag === '3m') {
    const d = new Date()
    d.setMonth(d.getMonth() - 3)
    startStr = d.toISOString().split('T')[0]
  } else if (tag === '6m') {
    const d = new Date()
    d.setMonth(d.getMonth() - 6)
    startStr = d.toISOString().split('T')[0]
  } else if (tag === '1y') {
    const d = new Date()
    d.setFullYear(d.getFullYear() - 1)
    startStr = d.toISOString().split('T')[0]
  } else if (tag === '3y') {
    const d = new Date()
    d.setFullYear(d.getFullYear() - 3)
    startStr = d.toISOString().split('T')[0]
  } else if (tag === '5y') {
    const d = new Date()
    d.setFullYear(d.getFullYear() - 5)
    startStr = d.toISOString().split('T')[0]
  } else if (tag === 'all') {
    startStr = null
  } else if (tag === 'custom') {
    if (!btForm.start_date) {
      const d = new Date()
      d.setMonth(d.getMonth() - 1)
      btForm.start_date = d.toISOString().split('T')[0]
    }
    if (!btForm.end_date) {
      btForm.end_date = endStr
    }
    return
  }

  btForm.start_date = startStr
  btForm.end_date = endStr
}

const executeBacktest = async () => {
  if (!btForm.fund_code) {
    showToast(btForm.asset_type === 'stock' ? '请输入回测股票代码' : '请输入回测基金代码')
    return
  }
  btLoading.value = true
  try {
    const payload = {
      asset_type: btForm.asset_type || 'fund',
      fund_code: btForm.fund_code.trim(),
      target_code: btForm.fund_code.trim(),
      strategy_type: btForm.strategy_type,
      strategy_config: btForm.strategy_config && Object.keys(btForm.strategy_config).length > 0 
        ? btForm.strategy_config 
        : form.config,
      fee_config: btForm.fee_config || form.fee_config,
      start_date: btForm.start_date,
      end_date: btForm.end_date
    }

    const res = await api.runStrategyBacktest(payload)
    if (!res || !res.success) {
      showToast(res?.message || '回测执行失败')
      return
    }
    btResult.value = res

    await nextTick()
    setTimeout(() => {
      renderBacktestChart()
    }, 60)
  } catch (e) {
    showToast('回测失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    btLoading.value = false
  }
}

const renderBacktestChart = () => {
  if (!chartContainer.value || !btResult.value || !btResult.value.equity_curve) return

  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  chartInstance = echarts.init(chartContainer.value)

  const curve = btResult.value.equity_curve
  const dates = curve.map(c => c.date)
  const stratReturns = curve.map(c => c.strategy_return_pct)
  const bmReturns = curve.map(c => c.benchmark_return_pct)

  // Collect MarkPoints safely
  const markPointData = []
  if (btResult.value.trades && Array.isArray(btResult.value.trades)) {
    btResult.value.trades.forEach(t => {
      if (t.id === 1) return // skip day0 initial buy mark
      const dateIdx = dates.indexOf(t.date)
      if (dateIdx < 0) return // Skip if date not found in curve dates
      const pointVal = stratReturns[dateIdx] !== undefined ? stratReturns[dateIdx] : 0

      if (t.action === 'BUY') {
        markPointData.push({
          name: '加仓',
          coord: [t.date, pointVal],
          value: '加',
          itemStyle: { color: '#00ff88' },
          symbol: 'pin',
          symbolSize: 30
        })
      } else if (t.action === 'SELL') {
        markPointData.push({
          name: '止盈',
          coord: [t.date, pointVal],
          value: '盈',
          itemStyle: { color: '#ff4444' },
          symbol: 'pin',
          symbolSize: 30
        })
      }
    })
  }

  const isStock = btResult.value.asset_type === 'stock' || btForm.asset_type === 'stock' || btResult.value.strategy_type?.startsWith('stock_')
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(26, 29, 46, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.15)',
      textStyle: { color: '#e2e8f0', fontSize: 12 },
      formatter: (params) => {
        if (!params || !params.length) return ''
        const idx = params[0].dataIndex
        const item = curve[idx]
        if (!item) return ''
        return `
          <div style="font-weight:600; margin-bottom:4px;">📅 日期: ${item.date}</div>
          <div style="color:#00d4ff;">🎯 策略收益率: <b>${item.strategy_return_pct > 0 ? '+' : ''}${item.strategy_return_pct}%</b></div>
          <div style="color:#fbbf24;">📈 ${isStock ? '股票买入持有' : '基金基准收益'}: <b>${item.benchmark_return_pct > 0 ? '+' : ''}${item.benchmark_return_pct}%</b></div>
          <div style="color:#94a3b8; font-size:11px; margin-top:4px;">
            ${isStock ? '股价' : '净值'}: ¥${item.nav.toFixed(isStock ? 2 : 4)} | 资产: ¥${formatNumber(item.total_assets, 0)} | 现金: ¥${formatNumber(item.cash, 0)}
          </div>
        `
      }
    },
    grid: {
      top: 30,
      left: 55,
      right: 25,
      bottom: 30
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.15)' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#94a3b8',
        fontSize: 11,
        formatter: '{value}%'
      },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)' } }
    },
    series: [
      {
        name: '策略累计收益率',
        type: 'line',
        data: stratReturns,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#00d4ff', width: 2.5 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 212, 255, 0.25)' },
            { offset: 1, color: 'rgba(0, 212, 255, 0.0)' }
          ])
        },
        markPoint: {
          data: markPointData,
          label: { fontSize: 10, color: '#fff' }
        }
      },
      {
        name: isStock ? '股票买入持有基准' : '基金买入持有基准',
        type: 'line',
        data: bmReturns,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#fbbf24', width: 1.8, type: 'dashed' }
      }
    ]
  }

  chartInstance.setOption(option, true)
  chartInstance.resize()

  setTimeout(() => {
    chartInstance?.resize()
  }, 100)
  setTimeout(() => {
    chartInstance?.resize()
  }, 300)
}

const applyBacktestAsLiveStrategy = async () => {
  if (!btResult.value) return
  try {
    const isStock = btResult.value.asset_type === 'stock' || btForm.asset_type === 'stock' || btResult.value.strategy_type?.startsWith('stock_')
    const targetName = btResult.value.target_name || btResult.value.fund_name
    const targetCode = btResult.value.target_code || btResult.value.fund_code
    const payload = {
      asset_type: isStock ? 'stock' : 'fund',
      target_code: targetCode,
      target_name: targetName,
      strategy_type: btResult.value.strategy_type,
      name: `${targetName} - ${isStock ? '股票' : '基金'}实盘策略`,
      initial_capital: btResult.value.metrics.initial_capital || 10000,
      current_cash: btResult.value.metrics.initial_capital || 10000,
      current_shares: 0,
      total_cost: 0,
      settlement_type: 'T+1',
      config: btForm.strategy_config || form.config,
      fee_config: btForm.fee_config || form.fee_config,
      status: 'running'
    }

    await api.createStrategy(payload)
    showToast('已成功将此策略配置创建为实盘监控策略！')
    closeBacktestModal()
    await loadStrategies()
  } catch (e) {
    showToast('保存实盘策略失败: ' + (e.response?.data?.detail || e.message))
  }
}

// -------------------------------------------------------------
// Live Trades Log & Signal Execution
// -------------------------------------------------------------
const openTradesModal = async (strat) => {
  activeStrategyForTrades.value = strat
  showTradesModal.value = true
  try {
    const data = await api.getStrategyTrades(strat.id)
    liveTradesList.value = data || []
  } catch (e) {
    showToast('加载流水记录失败')
  }
}

const openExecuteModal = (sig) => {
  executingSignal.value = sig
  executeForm.nav = sig.current_nav || 1.0
  executeForm.amount = sig.suggested_amount || 5000
  executeForm.shares = sig.suggested_shares || 100
  showExecuteModal.value = true
}

const confirmExecuteSignal = async () => {
  if (!executingSignal.value) return
  try {
    await api.executeStrategySignal(executingSignal.value.id, {
      nav: Number(executeForm.nav),
      amount: Number(executeForm.amount),
      shares: Number(executeForm.shares)
    })
    showToast('操作确认成功，持仓与资金状态已更新！')
    showExecuteModal.value = false
    await loadSignals()
    await loadStrategies()
  } catch (e) {
    showToast('执行失败: ' + (e.response?.data?.detail || e.message))
  }
}

// -------------------------------------------------------------
// Lifecycle Hooks
// -------------------------------------------------------------
onMounted(async () => {
  window.addEventListener('resize', () => {
    if (chartInstance) {
      chartInstance.resize()
    }
  })
  await loadStrategies()
  await loadTemplates()
  await loadSignals()
})
</script>

<style scoped>
.strategies-page {
  padding: 24px;
  max-width: 1600px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.strategy-tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--border-glass);
  padding-bottom: 12px;
}

.tab-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 8px;
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 0.98rem;
  background: var(--bg-glass);
  transition: all 0.2s;
  border: 1px solid transparent;
}

.tab-item:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.08);
}

.tab-item.active {
  background: rgba(0, 212, 255, 0.15);
  color: var(--accent-primary);
  border-color: rgba(0, 212, 255, 0.3);
}

.tab-badge {
  font-size: 0.75rem;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
}

.tab-badge.reserved {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.3);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px;
}

.stat-card.highlight-signal {
  border-color: rgba(251, 191, 36, 0.4);
  background: rgba(251, 191, 36, 0.05);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
}

.stat-label {
  font-size: 0.82rem;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
}

.stat-sub {
  font-size: 0.8rem;
  font-weight: 400;
  color: var(--text-secondary);
}

/* Signals Banner */
.signals-banner {
  margin-bottom: 24px;
  border-left: 4px solid #fbbf24;
  padding: 18px 20px;
  background: rgba(251, 191, 36, 0.06);
}

.banner-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.banner-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fbbf24;
  font-size: 1.05rem;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #fbbf24;
  box-shadow: 0 0 8px #fbbf24;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.3); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}

.banner-tip {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.signal-items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.signal-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(0, 0, 0, 0.2);
  padding: 12px 16px;
  border-radius: 8px;
  gap: 12px;
  flex-wrap: wrap;
}

.signal-badge {
  font-size: 0.85rem;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 6px;
}

.signal-badge.buy {
  background: rgba(0, 255, 136, 0.15);
  color: #00ff88;
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.signal-badge.sell {
  background: rgba(255, 68, 68, 0.15);
  color: #ff4444;
  border: 1px solid rgba(255, 68, 68, 0.3);
}

.signal-details {
  flex: 1;
}

.sig-target {
  font-size: 0.95rem;
  margin-bottom: 2px;
}

.sig-reason {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

/* Strategy Grid & Cards */
.strategies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 20px;
}

.strategy-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 22px;
  border-radius: 14px;
  transition: transform 0.2s, border-color 0.2s;
}

.strategy-card:hover {
  transform: translateY(-2px);
  border-color: rgba(0, 212, 255, 0.3);
}

.strategy-card.paused {
  opacity: 0.7;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  gap: 10px;
}

.target-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.target-name {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-primary);
}

.target-code {
  font-size: 0.85rem;
  color: var(--accent-primary);
  background: rgba(0, 212, 255, 0.1);
  padding: 1px 6px;
  border-radius: 4px;
}

.settle-badge {
  font-size: 0.72rem;
  background: rgba(255, 255, 255, 0.08);
  padding: 1px 5px;
  border-radius: 4px;
  color: var(--text-secondary);
}

.strat-name-sub {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.card-status-area {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.strat-type-badge {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(124, 58, 237, 0.15);
  color: #c084fc;
  border: 1px solid rgba(124, 58, 237, 0.3);
}

.status-toggle {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 10px;
  transition: all 0.2s;
}

.status-running {
  background: rgba(0, 255, 136, 0.15);
  color: #00ff88;
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.status-paused {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.card-metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  background: rgba(0, 0, 0, 0.2);
  padding: 14px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.metric-box {
  display: flex;
  flex-direction: column;
}

.metric-box .label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: 2px;
}

.metric-box .val {
  font-size: 1.05rem;
  font-weight: 700;
}

.metric-box .sub {
  font-size: 0.75rem;
}

.rule-summary-box {
  margin-bottom: 16px;
}

.rule-title {
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-bottom: 6px;
  display: block;
}

.rule-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.rule-tag {
  font-size: 0.72rem;
  padding: 3px 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  color: var(--text-secondary);
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 14px;
  border-top: 1px solid var(--border-glass);
}

.left-actions, .right-actions {
  display: flex;
  gap: 8px;
}

.action-icon-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.action-icon-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: var(--text-primary);
}

.action-icon-btn.delete:hover {
  background: rgba(255, 68, 68, 0.2);
  color: #ff4444;
}

/* Empty Card */
.empty-card {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 16px;
}

.empty-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
}

/* Reserved Stock Tab Card */
.reserved-card {
  max-width: 800px;
  margin: 30px auto;
  padding: 40px;
  text-align: center;
  border-radius: 16px;
}

.reserved-badge {
  display: inline-block;
  font-size: 0.8rem;
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.3);
  padding: 4px 12px;
  border-radius: 20px;
  margin-bottom: 16px;
}

.reserved-icon {
  font-size: 3.5rem;
  margin-bottom: 16px;
}

.reserved-desc {
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 30px;
}

.reserved-feature-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  text-align: left;
  background: rgba(0, 0, 0, 0.2);
  padding: 20px;
  border-radius: 10px;
  margin-bottom: 30px;
}

.feature-item {
  display: flex;
  gap: 14px;
}

.feature-item .feat-icon {
  font-size: 1.4rem;
}

.feature-item p {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-top: 2px;
}

/* Modal Form Styles */
.modal-lg {
  max-width: 860px;
  width: 90%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-xl {
  max-width: 1240px;
  width: 95%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.backtest-body {
  flex: 1;
  overflow-y: auto;
  padding-right: 6px;
}

.form-scrollable {
  flex: 1;
  max-height: calc(90vh - 160px);
  overflow-y: auto;
  padding-right: 8px;
}

.modal-actions {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border-glass);
}

.form-section {
  background: rgba(0, 0, 0, 0.15);
  border: 1px solid var(--border-glass);
  border-radius: 10px;
  padding: 18px;
  margin-bottom: 18px;
}

.section-title {
  font-size: 0.98rem;
  color: var(--accent-primary);
  margin-bottom: 14px;
}

.section-head-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.btn-text-action {
  font-size: 0.8rem;
  color: var(--accent-primary);
}

.form-row {
  display: grid;
  gap: 14px;
  margin-bottom: 14px;
}

.grid-2 { grid-template-columns: 1fr 1fr; }
.grid-3 { grid-template-columns: 1fr 1fr 1fr; }

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 0.82rem;
  color: var(--text-secondary);
}

.required { color: #ff4444; }

.form-control {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-glass);
  border-radius: 6px;
  padding: 8px 12px;
  color: var(--text-primary);
  font-size: 0.9rem;
}

.form-control:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.form-control.sm {
  padding: 6px 10px;
  font-size: 0.85rem;
}

.help-text {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

/* Template Picker */
.templates-picker {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}

.template-card-option {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.template-card-option:hover {
  background: rgba(255, 255, 255, 0.08);
}

.template-card-option.selected {
  background: rgba(0, 212, 255, 0.12);
  border-color: var(--accent-primary);
}

.tpl-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.tpl-badge {
  font-size: 0.68rem;
  background: rgba(124, 58, 237, 0.2);
  color: #c084fc;
  padding: 1px 6px;
  border-radius: 4px;
}

.tpl-desc {
  font-size: 0.75rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.param-group-box {
  background: rgba(255, 255, 255, 0.02);
  padding: 12px;
  border-radius: 8px;
}

.alert {
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 0.82rem;
  margin-bottom: 14px;
}

.alert-info {
  background: rgba(0, 212, 255, 0.08);
  border: 1px solid rgba(0, 212, 255, 0.2);
  color: #e2e8f0;
}

.fee-badge-info {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-glass);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 0.85rem;
}

.tier-section-block {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  padding: 12px;
}

.tier-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 0.85rem;
}

.tier-sub-tip {
  font-size: 0.78rem;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.03);
  padding: 6px 10px;
  border-radius: 6px;
  margin-bottom: 8px;
  line-height: 1.4;
}

.btn-group-sm {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mt-3 { margin-top: 14px; }

.tiers-table-wrap {
  margin-top: 14px;
}

.tiers-table {
  width: 100%;
  margin-top: 8px;
  border-collapse: collapse;
}

.tiers-table th {
  padding: 8px;
  font-size: 0.8rem;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-glass);
  text-align: left;
}

.tiers-table td {
  padding: 6px 8px;
  vertical-align: middle;
}

.mini-input {
  width: 70px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--border-glass);
  border-radius: 4px;
  padding: 4px 6px;
  color: #fff;
  font-size: 0.85rem;
}

.mini-input.op-select {
  width: 48px !important;
  padding: 4px 2px !important;
  text-align: center;
  font-weight: 600;
  color: var(--accent-primary) !important;
  cursor: pointer;
}

.mini-input.val-input {
  width: 52px !important;
}

.mini-input.label-in {
  width: 180px;
}

/* Backtest Laboratory Styles */
.bt-controls {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  padding: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.ctrl-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ctrl-group label {
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.quick-dates {
  display: flex;
  gap: 6px;
}

.btn-tag {
  font-size: 0.75rem;
  padding: 4px 10px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-secondary);
  border: 1px solid transparent;
  transition: all 0.2s;
}

.btn-tag:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

.btn-tag.active {
  background: rgba(0, 212, 255, 0.2);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.custom-date-picker-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  background: rgba(255, 255, 255, 0.03);
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px dashed rgba(0, 212, 255, 0.3);
}

.custom-date-box {
  display: flex;
  align-items: center;
  gap: 6px;
}

.custom-date-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.date-input {
  width: 135px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--border-glass);
  border-radius: 4px;
  padding: 3px 6px;
  color: #fff;
  font-size: 0.8rem;
  color-scheme: dark;
}

.bt-loading-card {
  padding: 40px;
  text-align: center;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 1s infinite linear;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.metrics-dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.metric-card {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  padding: 12px;
}

.metric-card.main {
  border-color: rgba(0, 212, 255, 0.4);
  background: rgba(0, 212, 255, 0.05);
}

.card-caption {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.card-val {
  font-size: 1.35rem;
  font-weight: 700;
  margin-bottom: 2px;
}

.card-footnote {
  font-size: 0.72rem;
  color: var(--text-secondary);
}

.chart-card {
  padding: 18px;
  margin-bottom: 20px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.chart-legend {
  display: flex;
  gap: 14px;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 12px;
  height: 3px;
  border-radius: 2px;
}

.dot.line-strat { background: #00d4ff; }
.dot.line-bm { background: #fbbf24; }

.badge-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.badge-dot.buy { background: #00ff88; }
.badge-dot.sell { background: #ff4444; }

.chart-container {
  width: 100%;
  height: 380px;
}

.trades-table-card {
  padding: 18px;
}

.trades-table-card .table-container {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--border-glass);
  border-radius: 8px;
}

.trades-table-card table th {
  position: sticky;
  top: 0;
  background: #1a1d2e;
  z-index: 2;
  box-shadow: 0 1px 0 var(--border-glass);
}

.trades-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.action-tag {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
}

.action-tag.buy {
  background: rgba(0, 255, 136, 0.15);
  color: #00ff88;
}

.action-tag.sell {
  background: rgba(255, 68, 68, 0.15);
  color: #ff4444;
}

.rule-cell {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Modal Headers and Buttons */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border-glass);
  padding-bottom: 12px;
}

.header-with-tag {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bt-summary-tag {
  font-size: 0.8rem;
  color: var(--accent-primary);
  background: rgba(0, 212, 255, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.close-btn {
  font-size: 1.5rem;
  line-height: 1;
  color: var(--text-secondary);
}

.close-btn:hover { color: #fff; }

.btn-accent {
  background: linear-gradient(135deg, #7c3aed, #00d4ff);
  color: #fff;
  font-weight: 600;
}

.btn-accent:hover {
  opacity: 0.9;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 0.82rem;
}

.btn-glass {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--border-glass);
  color: var(--text-primary);
}

.btn-glass:hover {
  background: rgba(255, 255, 255, 0.15);
}

.badge-direction {
  font-size: 0.9rem;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: 6px;
  display: inline-block;
}

.badge-direction.buy {
  background: rgba(0, 255, 136, 0.15);
  color: #00ff88;
}

.badge-direction.sell {
  background: rgba(255, 68, 68, 0.15);
  color: #ff4444;
}

.asset-type-radios {
  display: flex;
  gap: 12px;
}

.asset-type-btn {
  flex: 1;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 0.92rem;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.asset-type-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.asset-type-btn.active {
  background: rgba(0, 212, 255, 0.15);
  color: var(--accent-primary);
  border-color: rgba(0, 212, 255, 0.5);
  box-shadow: 0 0 12px rgba(0, 212, 255, 0.2);
}

.bt-asset-toggle {
  display: flex;
  gap: 6px;
}

/* Target Profit Point Card Box */
.card-target-profit-box {
  background: rgba(0, 212, 255, 0.04);
  border: 1px solid rgba(0, 212, 255, 0.18);
  border-radius: 10px;
  padding: 10px 14px;
  margin-top: 10px;
  margin-bottom: 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.2s;
}

.card-target-profit-box:hover {
  background: rgba(0, 212, 255, 0.07);
  border-color: rgba(0, 212, 255, 0.35);
}

.tp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.tp-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.84rem;
  color: var(--text-primary);
}

.tp-icon {
  font-size: 0.95rem;
}

.tp-target-badge {
  background: linear-gradient(135deg, rgba(255, 170, 0, 0.2), rgba(255, 85, 0, 0.2));
  color: #ffaa00;
  border: 1px solid rgba(255, 170, 0, 0.4);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 0.78rem;
  font-weight: 700;
}

.tp-status {
  font-size: 0.82rem;
}

.status-reached-tag {
  color: #00ff88;
  font-weight: 700;
  background: rgba(0, 255, 136, 0.12);
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.status-gap-tag {
  color: var(--text-secondary);
}

.tp-details-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  background: rgba(0, 0, 0, 0.2);
  padding: 6px 10px;
  border-radius: 6px;
}

.tp-detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tp-d-label {
  font-size: 0.72rem;
  color: var(--text-secondary);
}

.tp-d-val {
  font-size: 0.84rem;
  font-weight: 600;
  color: var(--text-primary);
}

.highlight-gold {
  color: #ffaa00;
  font-weight: 700;
}

.tp-progress-bar-bg {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
}

.tp-progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #00d4ff, #00ff88);
  border-radius: 3px;
  transition: width 0.4s ease;
}

.tp-progress-bar-fill.reached {
  background: linear-gradient(90deg, #00ff88, #ffaa00);
  box-shadow: 0 0 8px rgba(0, 255, 136, 0.6);
}

.clickable-trade-row {
  cursor: pointer;
  transition: background 0.15s ease;
}

.clickable-trade-row:hover {
  background: rgba(59, 130, 246, 0.12) !important;
}

.trade-detail-modal {
  max-width: 720px;
  width: 95%;
}

.detail-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 12px 14px;
}

.detail-card-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.grid-metrics-box {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 10px;
}

.metric-cell {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.m-lbl {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.m-val {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
}

.m-val.highlight {
  color: #00d4ff;
}

.btn-xs {
  padding: 2px 8px;
  font-size: 0.78rem;
  border-radius: 4px;
}

.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 12px; }

/* ── TianJi Timing Strategy Config Styles ── */
.tianjit-box {
  border-left: 3px solid #8b5cf6 !important;
  background: rgba(139, 92, 246, 0.03);
}

.tianjit-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.15) 0%, rgba(59, 130, 246, 0.08) 100%);
  border-radius: 8px;
  margin-bottom: 16px;
  border: 1px solid rgba(139, 92, 246, 0.25);
}

.tianjit-icon {
  font-size: 1.8rem;
  line-height: 1;
}

.tianjit-title {
  font-weight: 700;
  font-size: 1.05rem;
  color: #c4b5fd;
}

.tianjit-subtitle {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-top: 2px;
}

.tianjit-section {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 14px;
}

.tianjit-section-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.t1-badge {
  font-size: 0.72rem;
  background: rgba(16, 185, 129, 0.2);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.3);
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: normal;
}

.t1-scenarios {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.t1-scenario-item {
  background: rgba(139, 92, 246, 0.08);
  border: 1px dashed rgba(139, 92, 246, 0.3);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 0.8rem;
  color: #d8b4fe;
}

.signal-tier-block {
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 10px;
  background: rgba(255, 255, 255, 0.015);
}

.signal-tier-block.signal-s { border-left: 3px solid #ef4444; }
.signal-tier-block.signal-a { border-left: 3px solid #10b981; }
.signal-tier-block.signal-c { border-left: 3px solid #f59e0b; }
.signal-tier-block.signal-sha { border-left: 3px solid #ec4899; }

.signal-tier-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.signal-badge {
  font-size: 0.78rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.signal-badge.s { background: rgba(239, 68, 68, 0.2); color: #f87171; }
.signal-badge.a { background: rgba(16, 185, 129, 0.2); color: #34d399; }
.signal-badge.c { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
.signal-badge.sha { background: rgba(236, 72, 153, 0.2); color: #f472b6; }

.toggle-inline {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: var(--text-secondary);
  cursor: pointer;
}

.shensha-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 8px;
}

.shensha-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: rgba(255, 255, 255, 0.03);
  padding: 6px 8px;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.shensha-item label {
  font-size: 0.72rem;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tianjit-signal-card {
  border-left: 3px solid #8b5cf6;
}
</style>
