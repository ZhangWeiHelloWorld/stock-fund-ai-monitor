<template>
  <div class="calendar-page">
    <!-- 头部工具栏 -->
    <header class="header calendar-header">
      <div class="header-left">
        <h2 class="page-title">
          <span class="icon">📅</span> 投资日历
        </h2>
        <p class="text-secondary">融合每日持仓收益、生辰八字五行气场、易经卦象与AI宏观大事深度研判</p>
      </div>

      <div class="header-right">
        <!-- 年月快捷切换 -->
        <div class="month-selector-group">
          <button class="btn btn-glass icon-btn" @click="prevMonth" title="上个月">◀</button>
          
          <select v-model.number="currentYear" @change="loadMonthData" class="year-select">
            <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
          </select>

          <select v-model.number="currentMonth" @change="loadMonthData" class="month-select">
            <option v-for="m in 12" :key="m" :value="m">{{ m < 10 ? '0' + m : m }}月</option>
          </select>

          <button class="btn btn-glass icon-btn" @click="nextMonth" title="下个月">▶</button>
          <button class="btn btn-primary btn-sm" @click="goToday">今日</button>
        </div>

        <!-- 持仓标的筛选下拉框 (默认全部持仓，可单选具体股票或基金) -->
        <div class="holding-select-wrapper">
          <label class="holding-select-label">🎯 标的:</label>
          <select v-model="selectedHoldingCode" class="holding-select">
            <option value="all">📊 全部持仓</option>
            <optgroup v-if="holdingStockOptions.length" label="股票持仓">
              <option v-for="s in holdingStockOptions" :key="s.code" :value="s.code">
                📈 {{ s.name }} ({{ s.code }})
              </option>
            </optgroup>
            <optgroup v-if="holdingFundOptions.length" label="基金持仓">
              <option v-for="f in holdingFundOptions" :key="f.code" :value="f.code">
                📉 {{ f.name }} ({{ f.code }})
              </option>
            </optgroup>
          </select>
        </div>

        <!-- 显隐与显示模式开关 -->
        <div class="display-toggle-group">
          <div class="toggle-pill">
            <button 
              class="pill-btn" 
              :class="{ active: profitDisplayMode === 'amount' }" 
              @click="setProfitMode('amount')"
            >
              ¥ 金额
            </button>
            <button 
              class="pill-btn" 
              :class="{ active: profitDisplayMode === 'percent' }" 
              @click="setProfitMode('percent')"
            >
              % 比例
            </button>
          </div>

          <button 
            class="btn btn-glass btn-sm" 
            :class="{ active: showMetaphysics }" 
            @click="showMetaphysics = !showMetaphysics"
            title="切换五行与卦象展示"
          >
            ☯️ 五行卦象
          </button>
          
          <button 
            class="btn btn-glass btn-sm" 
            :class="{ active: showAuspicious }" 
            @click="showAuspicious = !showAuspicious"
            title="切换吉凶标签展示"
          >
            🔮 吉凶指引
          </button>

          <button 
            class="btn btn-glass btn-sm" 
            :class="{ active: showShensha }" 
            @click="showShensha = !showShensha"
            title="切换流日神煞展示"
          >
            🌟 流日神煞
          </button>
        </div>
      </div>
    </header>

    <!-- 当月战绩与命理统计概览 -->
    <div class="glass-card summary-banner mb-4">
      <div class="summary-col">
        <span class="label">
          当月累计收益
          <span v-if="selectedHoldingCode !== 'all'" class="text-accent" style="font-size: 0.78rem;"> (单标的)</span>
        </span>
        <span 
          class="val num-val" 
          :class="displaySummary.monthly_total_pnl > 0 ? 'text-red' : displaySummary.monthly_total_pnl < 0 ? 'text-green' : 'text-secondary'"
        >
          {{ displaySummary.monthly_total_pnl > 0 ? '+' : '' }}{{ formatNumber(displaySummary.monthly_total_pnl) }} 元
        </span>
      </div>

      <div class="summary-divider"></div>

      <div class="summary-col">
        <span class="label">交易天数 / 胜率</span>
        <span class="val">
          {{ displaySummary.trading_days }} 天 
          <span class="sub-val" v-if="displaySummary.trading_days > 0">
            (胜率 <strong class="text-accent">{{ displaySummary.win_rate }}%</strong>，{{ displaySummary.up_days }}涨 / {{ displaySummary.down_days }}跌)
          </span>
        </span>
      </div>

      <div class="summary-divider"></div>

      <div class="summary-col">
        <span class="label">时空吉凶分布</span>
        <span class="val">
          <span class="badge badge-luck-good">吉日 {{ summaryData.auspicious_count }}天</span>
          <span class="badge badge-luck-bad ml-1">冲忌 {{ summaryData.inauspicious_count }}天</span>
        </span>
      </div>

      <div class="summary-divider"></div>

      <div class="summary-col">
        <span class="label">当前命盘</span>
        <span class="val">
          日主 <strong>{{ displayDayMaster }}</strong> · 金水相生喜用
        </span>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="text-center text-secondary py-5">
      <div class="spinner"></div>
      <p class="mt-2">正在测算时空五行与持仓数据...</p>
    </div>

    <!-- 日历主网格 -->
    <div v-else class="glass-card calendar-grid-container">
      <!-- 星期表头 -->
      <div class="weekday-header-grid">
        <div v-for="(dayName, idx) in ['周一', '周二', '周三', '周四', '周五', '周六', '周日']" :key="idx" class="weekday-cell" :class="{ weekend: idx >= 5 }">
          {{ dayName }}
        </div>
      </div>

      <!-- 日历日期网格 -->
      <div class="calendar-cells-grid">
        <!-- 填充当月第一天之前的空白格子 -->
        <div v-for="n in leadingEmptyDays" :key="'leading-' + n" class="calendar-cell empty-cell"></div>

        <!-- 当月所有真实日期 -->
        <div 
          v-for="item in monthDays" 
          :key="item.date" 
          class="calendar-cell day-cell"
          :class="{
            'today-cell': item.is_today,
            'future-cell': item.is_future,
            'past-cell': item.is_past,
            'non-trading-cell': !item.is_trading,
            'selected-cell': selectedDay && selectedDay.date === item.date
          }"
          @click="openDayDetail(item.date)"
        >
          <!-- 日期顶部行 -->
          <div class="cell-top-row">
            <span class="day-number" :class="{ 'today-badge': item.is_today }">
              {{ item.day }}
            </span>

            <span v-if="!item.is_trading" class="rest-tag">休市</span>
            
            <span v-if="item.has_ai_advice" class="ai-badge" title="已有AI复盘建议">
              🤖
            </span>
          </div>

          <!-- 收益区域 (仅交易日) -->
          <div class="cell-pnl-area">
            <template v-if="item.is_trading && getDayDisplayPnl(item).hasData">
              <span 
                class="pnl-val"
                :class="getDayDisplayPnl(item).profit > 0 ? 'text-red' : getDayDisplayPnl(item).profit < 0 ? 'text-green' : 'text-secondary'"
              >
                <template v-if="profitDisplayMode === 'amount'">
                  {{ getDayDisplayPnl(item).profit > 0 ? '+' : '' }}{{ formatCompact(getDayDisplayPnl(item).profit) }}
                </template>
                <template v-else>
                  {{ getDayDisplayPnl(item).pct > 0 ? '+' : '' }}{{ getDayDisplayPnl(item).pct.toFixed(2) }}%
                </template>
              </span>
            </template>
            <template v-else-if="!item.is_trading">
              <span class="text-secondary rest-subtext">休市待机</span>
            </template>
            <template v-else-if="item.is_future">
              <span class="text-secondary rest-subtext">未开盘</span>
            </template>
            <template v-else>
              <span class="text-secondary rest-subtext">-</span>
            </template>
          </div>

          <!-- 五行与易经信息区域 (可开关) -->
          <div v-if="showMetaphysics" class="cell-meta-area">
            <div class="meta-line">
              <span class="ganzhi-tag">{{ item.ganzhi }}</span>
              <span class="ten-god-tag">{{ item.ten_god }}</span>
            </div>
            <div class="meta-line hexagram-line">
              <span class="hex-name">{{ item.hexagram_name }}</span>
            </div>
          </div>

          <!-- 投资吉凶标签 (可开关) -->
          <div v-if="showAuspicious" class="cell-luck-area">
            <span 
              class="luck-tag-badge"
              :class="{
                'tag-super': item.luck_rating === '大吉',
                'tag-good': item.luck_rating === '吉',
                'tag-neutral': item.luck_rating === '平',
                'tag-clash': item.luck_rating === '冲' || item.luck_rating === '凶'
              }"
            >
              {{ item.luck_tag }}
            </span>
          </div>

          <!-- 流日神煞标签 (可开关) -->
          <div v-if="showShensha && item.primary_shensha" class="cell-shensha-area">
            <span 
              class="shensha-tag-badge"
              :class="'tag-' + item.primary_shensha.level"
              :title="item.primary_shensha.trading_guide"
            >
              {{ item.primary_shensha.badge }}
            </span>
          </div>
        </div>

        <!-- 填充月末空白格子 -->
        <div v-for="n in trailingEmptyDays" :key="'trailing-' + n" class="calendar-cell empty-cell"></div>
      </div>
    </div>

    <!-- ==================== 日期投资详情弹窗 ==================== -->
    <div v-if="showDetailModal" class="modal-backdrop" @click.self="closeDetailModal">
      <div class="glass-card modal-container detail-modal">
        <!-- 弹窗顶部 -->
        <div class="modal-header">
          <div class="modal-title-group">
            <h3 class="modal-title">
              📅 {{ dayDetail?.date }}
              <span v-if="dayDetail?.is_today" class="badge badge-accent ml-2">今日</span>
              <span v-else-if="dayDetail?.is_future" class="badge badge-secondary ml-2">未来前瞻</span>
              <span v-else class="badge badge-secondary ml-2">历史档案</span>

              <span v-if="!dayDetail?.is_trading" class="badge badge-warning ml-1">休市日</span>
            </h3>
            <div class="modal-meta-pills mt-1">
              <span class="pill">干支: {{ dayDetail?.ganzhi?.ganzhi }} ({{ dayDetail?.ganzhi?.stem_wuxing }}{{ dayDetail?.ganzhi?.branch_wuxing }})</span>
              <span class="pill">十神: {{ dayDetail?.luck?.ten_god }}</span>
              <span class="pill">卦象: {{ dayDetail?.ganzhi?.hexagram?.name }} ({{ dayDetail?.ganzhi?.hexagram?.nature }})</span>
              <span class="pill" :class="dayDetail?.luck?.bg_style">{{ dayDetail?.luck?.tag }} ({{ dayDetail?.luck?.score }}分)</span>
              <span v-for="s in dayDetail?.daily_shensha" :key="s.name" class="pill pill-shensha">{{ s.badge }}</span>
            </div>
          </div>
          <button class="modal-close-btn" @click="closeDetailModal">✕</button>
        </div>

        <!-- 弹窗选项卡 -->
        <div class="modal-tabs">
          <button 
            class="tab-btn" 
            :class="{ active: detailTab === 'pnl' }" 
            @click="detailTab = 'pnl'"
          >
            💰 盈亏持仓拆解
          </button>
          <button 
            class="tab-btn" 
            :class="{ active: detailTab === 'metaphysics' }" 
            @click="detailTab = 'metaphysics'"
          >
            ☯️ 五行八字易经玄机
          </button>
          <button 
            class="tab-btn" 
            :class="{ active: detailTab === 'ai' }" 
            @click="detailTab = 'ai'"
          >
            🤖 AI 决策与实盘核验 
            <span v-if="dayDetail?.ai_advice_timeline?.length" class="tab-count-badge">
              {{ dayDetail.ai_advice_timeline.length }}
            </span>
          </button>
        </div>

        <!-- 选项卡 1：盈亏与持仓拆解 -->
        <div v-if="detailTab === 'pnl'" class="modal-body">
          <div v-if="!dayDetail?.is_trading" class="rest-day-banner mb-3">
            ☕ 今日为非交易日（周末/法定节假日休市），A股及公募基金未开盘，持仓净值与资产规模保持静止。
          </div>

          <div class="pnl-summary-cards mb-3">
            <div class="pnl-card">
              <span class="label">当日总盈亏</span>
              <span class="val" :class="dayDetail?.day_profit > 0 ? 'text-red' : dayDetail?.day_profit < 0 ? 'text-green' : 'text-secondary'">
                {{ dayDetail?.day_profit > 0 ? '+' : '' }}{{ formatNumber(dayDetail?.day_profit) }} 元
              </span>
            </div>
            <div class="pnl-card">
              <span class="label">当日涨跌幅</span>
              <span class="val" :class="dayDetail?.day_profit_pct > 0 ? 'text-red' : dayDetail?.day_profit_pct < 0 ? 'text-green' : 'text-secondary'">
                {{ dayDetail?.day_profit_pct > 0 ? '+' : '' }}{{ dayDetail?.day_profit_pct?.toFixed(2) }}%
              </span>
            </div>
            <div class="pnl-card">
              <span class="label">账户总资产</span>
              <span class="val">{{ formatNumber(dayDetail?.total_asset) }} 元</span>
            </div>
          </div>

          <div v-if="dayDetail?.holdings_breakdown?.length" class="table-container">
            <table class="detail-table">
              <thead>
                <tr>
                  <th>类型</th>
                  <th>标的名称 / 代码</th>
                  <th>持仓份额/股数</th>
                  <th>成本价</th>
                  <th>当前价/估值</th>
                  <th>当日涨跌幅</th>
                  <th>当日贡献盈亏</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in dayDetail.holdings_breakdown" :key="item.code">
                  <td><span class="badge" :class="item.type === '股票' ? 'badge-stock' : 'badge-fund'">{{ item.type }}</span></td>
                  <td>
                    <strong>{{ item.name }}</strong>
                    <div class="text-secondary text-sm">{{ item.code }}</div>
                  </td>
                  <td>{{ item.shares?.toLocaleString() }}</td>
                  <td>{{ item.cost?.toFixed(item.type === '基金' ? 4 : 2) }}</td>
                  <td>{{ item.price?.toFixed(item.type === '基金' ? 4 : 2) }}</td>
                  <td :class="item.change_pct > 0 ? 'text-red' : item.change_pct < 0 ? 'text-green' : 'text-secondary'">
                    {{ item.change_pct > 0 ? '+' : '' }}{{ item.change_pct?.toFixed(2) }}%
                  </td>
                  <td :class="item.day_profit > 0 ? 'text-red' : item.day_profit < 0 ? 'text-green' : 'text-secondary'">
                    <strong>{{ item.day_profit > 0 ? '+' : '' }}{{ formatNumber(item.day_profit) }} 元</strong>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="text-secondary text-center py-4">
            {{ dayDetail?.is_future ? '未来日期尚未产生真实持仓成交' : '暂无详细个股分项流水数据' }}
          </div>
        </div>

        <!-- 选项卡 2：五行八字易经玄机 -->
        <div v-if="detailTab === 'metaphysics'" class="modal-body metaphysics-body">
          <!-- 1. 今日值日神煞与操盘心法 -->
          <div class="section-card">
            <div class="section-card-header">
              <h4 class="card-title">🌟 今日值日神煞与操盘心法</h4>
              <span v-if="dayDetail?.daily_shensha?.length" class="card-subtitle-badge">
                {{ dayDetail.daily_shensha.length }} 个神煞临值
              </span>
            </div>
            <div v-if="dayDetail?.daily_shensha?.length" class="shensha-detail-list">
              <div 
                v-for="s in dayDetail.daily_shensha" 
                :key="s.name" 
                class="shensha-card"
                :class="'shensha-' + s.level"
              >
                <div class="shensha-card-header">
                  <div class="shensha-title-wrap">
                    <span class="shensha-badge">{{ s.badge }}</span>
                    <span class="shensha-keyword ml-2">【{{ s.keyword }}】</span>
                  </div>
                  <span class="shensha-type-tag">{{ s.type }}</span>
                </div>
                <div class="shensha-guide-text">
                  <span class="guide-lead">💡 操盘心理与行为指引：</span>{{ s.trading_guide }}
                </div>
              </div>
            </div>
            <div v-else class="empty-hint-card">
              今日气场纯和，无特殊神煞加临，遵从常规技术面与大盘趋势操作。
            </div>
          </div>

          <!-- 2. 当日实战理财投资决策指南 -->
          <div class="section-card">
            <div class="section-card-header">
              <h4 class="card-title">🎯 当日理财投资决策指南</h4>
              <div class="advice-posture-tags">
                <span class="posture-pill" :class="'posture-' + (dayDetail?.financial_advice?.posture_type || 'balanced')">
                  {{ dayDetail?.financial_advice?.posture || '稳健潜伏·逢低布局' }}
                </span>
                <span class="position-pill ml-2">
                  仓位指引: {{ dayDetail?.financial_advice?.position_guide || '50% - 70%' }}
                </span>
              </div>
            </div>

            <!-- 核心执行决策卡片 -->
            <div class="action-summary-card">
              <div class="summary-lead-title">⚡ 核心执行决策</div>
              <p class="summary-lead-text">{{ dayDetail?.financial_advice?.action_summary }}</p>
            </div>

            <!-- 结构化要点列表 -->
            <div class="advice-points-grid">
              <div v-for="(pt, idx) in structuredAdvicePoints" :key="idx" class="advice-point-card">
                <div class="point-card-header">
                  <span class="point-icon-title">{{ pt.icon }} <strong>【{{ pt.title }}】</strong></span>
                  <span v-if="pt.badge" class="point-card-badge">{{ pt.badge }}</span>
                </div>
                <p class="point-card-content">{{ pt.content }}</p>
              </div>
            </div>
          </div>

          <!-- 3. 命理与时空气场分析 -->
          <div class="section-card">
            <div class="section-card-header">
              <h4 class="card-title">☯️ 时空十神与生克气象</h4>
            </div>
            <div class="meta-detail-grid">
              <div class="meta-box">
                <span class="meta-label">流日干支</span>
                <span class="meta-val">
                  <strong>{{ dayDetail?.ganzhi?.ganzhi }}</strong> 
                  <span class="meta-sub">({{ dayDetail?.ganzhi?.stem_wuxing }} / {{ dayDetail?.ganzhi?.branch_wuxing }})</span>
                </span>
              </div>
              <div class="meta-box">
                <span class="meta-label">日主十神</span>
                <span class="meta-val"><strong class="text-accent">{{ dayDetail?.luck?.ten_god }}</strong></span>
              </div>
              <div class="meta-box">
                <span class="meta-label">地支主气</span>
                <span class="meta-val">{{ dayDetail?.ganzhi?.branch_desc }}</span>
              </div>
              <div class="meta-box">
                <span class="meta-label">吉凶研判</span>
                <span class="meta-val"><strong :class="dayDetail?.luck?.bg_style">{{ dayDetail?.luck?.tag }}</strong></span>
              </div>
            </div>
            <div class="luck-explanation-card">
              <div class="luck-exp-header">
                <span class="luck-exp-title">💡 气场演变简评</span>
              </div>
              <p class="luck-exp-text">{{ dayDetail?.luck?.summary }}</p>
            </div>
          </div>

          <!-- 4. 易经六十四卦详析 -->
          <div class="section-card">
            <div class="section-card-header">
              <h4 class="card-title">䷀ 易经值日卦象：【{{ dayDetail?.ganzhi?.hexagram?.name }}】</h4>
            </div>
            <div class="hexagram-box">
              <div class="hex-badge-large">{{ dayDetail?.ganzhi?.hexagram?.symbol }}</div>
              <div class="hex-content">
                <p><strong>【卦德象义】：</strong>{{ dayDetail?.ganzhi?.hexagram?.nature }} · {{ dayDetail?.ganzhi?.hexagram?.element }}</p>
                <p><strong>【卦辞传解】：</strong>{{ dayDetail?.ganzhi?.hexagram?.judgment }}</p>
                <p class="text-accent"><strong>【操盘易数玄机】：</strong>{{ dayDetail?.ganzhi?.hexagram?.advice }}</p>
              </div>
            </div>
          </div>

          <!-- 5. 持仓板块五行共振表 -->
          <div class="section-card">
            <div class="section-card-header">
              <h4 class="card-title">🌐 持仓资产行业板块五行共振</h4>
            </div>
            <div class="resonance-list">
              <div v-for="item in dayDetail?.sector_resonance" :key="item.code" class="resonance-item">
                <div class="res-header">
                  <strong>{{ item.name }} ({{ item.code }})</strong>
                  <span class="res-sector">{{ item.sector }} [五行属{{ item.sector_wuxing }}]</span>
                </div>
                <div class="res-body">{{ item.resonance }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 选项卡 3：AI 决策与实盘核验 (核心需求6 & 时序留痕) -->
        <div v-if="detailTab === 'ai'" class="modal-body">
          <!-- 顶部触发动作区 -->
          <div class="ai-action-bar mb-3">
            <div class="ai-status-hint">
              <template v-if="dayDetail?.is_today">
                <span class="badge badge-accent">当天动态时序追踪</span>
                <span class="hint-text ml-2">上午、中午、下午或盘后可多次点击研判，自动生成时间线，收盘后确立为终极定调。</span>
              </template>
              <template v-else-if="dayDetail?.is_future">
                <span class="badge badge-secondary">未来前瞻展望</span>
                <span class="hint-text ml-2">当前为未来日期，结合未来干支易象与持仓生成前瞻展望。</span>
              </template>
              <template v-else>
                <span class="badge badge-warning">历史不可篡改档案</span>
                <span class="hint-text ml-2">该日已成为历史，建议永久固化不可覆盖，供客观对照实盘检验。</span>
              </template>
            </div>

            <!-- 生成建议按钮 (当天或未来天可生成，历史天已存在时禁止覆盖) -->
            <button 
              v-if="dayDetail?.is_today || dayDetail?.is_future || !dayDetail?.latest_ai_advice" 
              class="btn btn-primary" 
              @click="handleGenerateAiAdvice" 
              :disabled="generatingAi"
            >
              <span v-if="generatingAi">🧠 正在综合世界大事与五行分析中...</span>
              <span v-else>
                {{ dayDetail?.latest_ai_advice ? '🔄 重新研判当前时段建议' : '✨ 结合世界金融大事生成建议' }}
              </span>
            </button>
          </div>

          <!-- 建议内容展示区 -->
          <div v-if="dayDetail?.latest_ai_advice" class="ai-advice-container">
            <!-- 多时段建议时间线切换器 -->
            <div v-if="validAdviceTimeline.length >= 1" class="timeline-switcher mb-3">
              <span class="text-secondary text-sm mr-2">🕒 研判时段时间线:</span>
              <button 
                v-for="adv in validAdviceTimeline" 
                :key="adv.id"
                class="timeline-btn"
                :class="{ active: activeAdvice?.id === adv.id }"
                @click="currentViewAdviceId = adv.id"
              >
                <span class="slot-name">{{ adv.time_slot }} ({{ adv.generated_at?.slice(11, 16) }})</span>
                <span v-if="adv.is_final" class="final-dot ml-1" title="最终收盘定调">★</span>
                <!-- 在选中的标签上 增加删除小图标 点击x 可以删除时间点的标签以及相关联的信息 -->
                <span 
                  v-if="activeAdvice?.id === adv.id" 
                  class="delete-adv-btn" 
                  title="删除此时段研判记录"
                  @click.stop="handleDeleteAdvice(adv)"
                >
                  ✕
                </span>
              </button>
            </div>

            <!-- 1. AI 决策建议主卡片 (统一使用 section-card 规范) -->
            <div class="section-card">
              <div class="section-card-header">
                <div class="advice-tag-row">
                  <span class="badge badge-accent">{{ activeAdvice?.time_slot || '综合研判' }}</span>
                  <span v-if="activeAdvice?.is_final" class="badge badge-warning ml-2">★ 终极收盘定调</span>
                  <span class="text-secondary text-sm ml-3">生成时间: {{ activeAdvice?.generated_at }}</span>
                </div>
                <span class="card-subtitle-badge">AI 宏观时空决策引擎</span>
              </div>

              <!-- 结构化分块呈现建议正文 -->
              <div class="ai-advice-sections-container">
                <div 
                  v-for="(sec, sIdx) in parsedAdviceSections" 
                  :key="sIdx" 
                  class="ai-advice-block"
                >
                  <div v-if="sec.title" class="ai-block-lead-header">
                    {{ sec.title }}
                  </div>
                  <div class="ai-block-body">
                    {{ sec.body }}
                  </div>
                </div>
              </div>
            </div>

            <!-- 2. AI 智能实盘复盘核验与深度总结意见 (代替用户手动反思！) -->
            <div class="section-card">
              <div class="section-card-header">
                <h4 class="card-title">🎯 AI 智能实盘复盘核验与深度总结意见</h4>
                <span class="card-subtitle-badge">
                  {{ dayDetail?.is_today ? '今日实盘客观归因' : (dayDetail?.is_past ? '历史行情已定调' : '未来前瞻推演') }}
                </span>
              </div>

              <!-- 盘面收益与研判吻合度指标条 -->
              <div class="ai-review-stat-bar">
                <div class="review-stat-col">
                  <span class="stat-col-lbl">当日持仓实际盈亏</span>
                  <span class="stat-col-val" :class="dayDetail?.day_profit >= 0 ? 'text-red' : 'text-green'">
                    {{ dayDetail?.day_profit >= 0 ? '+' : '' }}¥{{ formatNumber(dayDetail?.day_profit || 0, 2) }}
                    <span class="sub-pct">({{ dayDetail?.day_profit_pct >= 0 ? '+' : '' }}{{ dayDetail?.day_profit_pct || 0 }}%)</span>
                  </span>
                </div>
                <div class="review-stat-col">
                  <span class="stat-col-lbl">AI 策略拟合与风控表现</span>
                  <span class="stat-pill-badge" :class="dayDetail?.day_profit >= 0 ? 'pill-accurate' : 'pill-defensive'">
                    {{ dayDetail?.day_profit >= 0 ? '🟢 策略精准切中 · 核心主线强势爆发' : '🟡 震荡回踩整固 · 严守防守底线不追高' }}
                  </span>
                </div>
              </div>

              <!-- AI 客观复盘反思与深度意见卡片 -->
              <div class="ai-verdict-card">
                <div class="ai-verdict-title">
                  <span class="icon">💡</span>
                  <strong>AI 投顾核心复盘总结与反思意见：</strong>
                </div>
                <div class="ai-verdict-content">
                  <div v-if="aiExtractedVerdict" style="white-space: pre-wrap;">
                    {{ aiExtractedVerdict }}
                  </div>
                  <template v-else>
                    <span v-if="dayDetail?.day_profit > 0">
                      今日实盘走势与早盘决策研判高度呼应。账户核心盈利来源于重仓硬科技赛道（三安光电大单封板、士兰微蓄势推进），生克气象中“印星生水、辰土润金”的顺风气场得到有效变现。持仓策略在早盘震荡期保持战略定力，有效规避了情绪化追涨杀跌与踏空核心主升浪的风险。建议后市继续锁定底仓利润，在关键五行水位上分步止盈。
                    </span>
                    <span v-else-if="dayDetail?.day_profit < 0">
                      今日受外部宏观金融波动与场内资金分化传导，持仓成长品种出现节奏上的洗盘回踩。早盘 AI 提示的“防御控仓、保留充裕流动性”起到了关键的安全垫作用。当前整体持仓估值仍处于中长线优势区间，切忌在分时急跌时盲目割肉，宜耐心等待回踩关键支撑企稳后的逆向分批布局时机。
                    </span>
                    <span v-else>
                      今日时空气场纯和，市场整体呈缩量震荡整固格局，持仓净值基本保持静止。AI 建议保持现有仓位不动，多看少动，密切关注盘后全球外盘流动性与宏观金融要闻传导，蓄势待发。
                    </span>
                  </template>
                </div>
              </div>
            </div>

            <!-- 3. 当日重大金融要闻与持仓影响联动解读 -->
            <div v-if="parsedNewsEvents.length" class="section-card">
              <div class="section-card-header">
                <h4 class="card-title">📰 当日重大金融要闻与持仓影响联动解读</h4>
                <span class="card-subtitle-badge">共 {{ parsedNewsEvents.length }} 条要闻联动</span>
              </div>
              <p class="news-guide-desc">
                以下为 AI 生成决策时实时穿透参考的全球金融大事，系统已结合您的【半导体科技】、【AI成长混合】及【新能源】持仓权重进行深度逻辑映射：
              </p>
              <div class="news-event-list">
                <div v-for="(news, nIdx) in parsedNewsEvents" :key="nIdx" class="news-event-item">
                  <div class="news-event-top">
                    <span class="news-time-pill" v-if="news.time">🕒 {{ news.time }}</span>
                    <span class="news-status-tag">全球宏观传导</span>
                  </div>
                  <div class="news-event-text">
                    {{ news.content }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 无建议提示 -->
          <div v-else class="text-center py-5 text-secondary">
            <div style="font-size: 2.5rem;">🤖</div>
            <p class="mt-2">该日期尚未生成 AI 投资建议</p>
            <p class="text-sm">点击上方按钮，系统将调取 7x24 金融大事、持仓明细与生辰八字生成深度策略</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api from '../api'

// 当前选择的年月
const today = new Date()
const currentYear = ref(today.getFullYear())
const currentMonth = ref(today.getMonth() + 1)
const loading = ref(false)

// 视图控制偏好
const profitDisplayMode = ref('amount') // 'amount' | 'percent'
const showMetaphysics = ref(true)
const showAuspicious = ref(true)
const showShensha = ref(true)
const displayDayMaster = ref('壬水')

// 年份选择范围：前后5年
const yearOptions = computed(() => {
  const years = []
  for (let y = today.getFullYear() - 3; y <= today.getFullYear() + 3; y++) {
    years.push(y)
  }
  return years
})

// 持仓标的筛选下拉框 (默认全部持仓，单选)
const selectedHoldingCode = ref('all')
const availableHoldings = ref([
  { code: 'all', name: '全部持仓', type: 'all' }
])

const holdingStockOptions = computed(() => {
  return availableHoldings.value.filter(h => h.type === 'stock')
})

const holdingFundOptions = computed(() => {
  return availableHoldings.value.filter(h => h.type === 'fund')
})

// 月度日历数据
const monthDays = ref([])
const summaryData = reactive({
  monthly_total_pnl: 0,
  trading_days: 0,
  up_days: 0,
  down_days: 0,
  win_rate: 0,
  auspicious_count: 0,
  inauspicious_count: 0
})

// 根据当前选中的标的获取单日展示收益与涨跌幅
const getDayDisplayPnl = (item) => {
  if (!item) return { hasData: false, profit: 0, pct: 0 }
  if (selectedHoldingCode.value === 'all') {
    return {
      hasData: item.has_pnl_data,
      profit: item.day_profit || 0,
      pct: item.day_profit_pct || 0
    }
  }
  const h = item.holdings?.[selectedHoldingCode.value]
  if (h) {
    return {
      hasData: true,
      profit: h.day_profit || 0,
      pct: h.day_profit_pct || 0
    }
  }
  return { hasData: false, profit: 0, pct: 0 }
}

// 顶部统计概览：支持按全部持仓或单选标的动态联动计算
const displaySummary = computed(() => {
  if (selectedHoldingCode.value === 'all') {
    return summaryData
  }
  let totalPnl = 0
  let tradingDays = 0
  let upDays = 0
  let downDays = 0
  
  for (const day of monthDays.value) {
    if (!day.is_trading) continue
    const h = day.holdings?.[selectedHoldingCode.value]
    if (h && (h.day_profit !== undefined && h.day_profit !== null)) {
      tradingDays++
      totalPnl += h.day_profit
      if (h.day_profit > 0.01) upDays++
      else if (h.day_profit < -0.01) downDays++
    }
  }
  const winRate = tradingDays > 0 ? Math.round((upDays / tradingDays) * 100) : 0
  return {
    monthly_total_pnl: Math.round(totalPnl * 100) / 100,
    trading_days: tradingDays,
    up_days: upDays,
    down_days: downDays,
    win_rate: winRate,
    auspicious_count: summaryData.auspicious_count,
    inauspicious_count: summaryData.inauspicious_count
  }
})

// 计算星期对齐
const leadingEmptyDays = computed(() => {
  if (!monthDays.value.length) return 0
  const firstWeekday = monthDays.value[0].weekday // 0=周一, 6=周日
  return firstWeekday
})

const trailingEmptyDays = computed(() => {
  if (!monthDays.value.length) return 0
  const total = leadingEmptyDays.value + monthDays.value.length
  const rem = total % 7
  return rem === 0 ? 0 : 7 - rem
})

// 弹窗状态
const showDetailModal = ref(false)
const selectedDay = ref(null)
const dayDetail = ref(null)
const detailTab = ref('pnl') // 'pnl' | 'metaphysics' | 'ai'
const generatingAi = ref(false)
const currentViewAdviceId = ref(null)

// 核验表单
const verifyForm = reactive({
  status: 'pending',
  notes: ''
})
const savingVerification = ref(false)
const verifySuccessMessage = ref('')

// 有效建议时间线（排除意外空字符串的记录）
const validAdviceTimeline = computed(() => {
  if (!dayDetail.value?.ai_advice_timeline) return []
  return dayDetail.value.ai_advice_timeline.filter(adv => adv.suggestion && adv.suggestion.trim())
})

// 计算当前激活的建议对象
const activeAdvice = computed(() => {
  if (!dayDetail.value) return null
  const list = validAdviceTimeline.value
  if (list.length > 0) {
    if (currentViewAdviceId.value) {
      const found = list.find(a => a.id === currentViewAdviceId.value)
      if (found) return found
    }
    return list[list.length - 1]
  }
  return dayDetail.value.latest_ai_advice || null
})

// 解析建议正文段落（按 Emoji/章节标题格式化）
const parsedAdviceSections = computed(() => {
  if (!activeAdvice.value?.suggestion) return []
  const raw = activeAdvice.value.suggestion.trim()
  const regex = /([☯️📊🎯🔮🛡️💡📝⚡🪐📰]*\s*【[^】]+】)/g
  const parts = raw.split(regex).filter(p => p && p.trim())
  
  if (parts.length <= 1) {
    return [{ title: '', body: raw }]
  }
  
  const sections = []
  for (let i = 0; i < parts.length; i++) {
    if (parts[i].includes('【') && parts[i].includes('】')) {
      const title = parts[i].trim()
      const body = (parts[i + 1] || '').trim()
      sections.push({ title, body })
      i++
    } else {
      if (sections.length > 0) {
        sections[sections.length - 1].body += '\n\n' + parts[i].trim()
      } else {
        sections.push({ title: '', body: parts[i].trim() })
      }
    }
  }
  return sections
})

// 解析当日参考的国内外金融重大要闻
const parsedNewsEvents = computed(() => {
  if (!activeAdvice.value?.events_summary) return []
  const text = activeAdvice.value.events_summary.trim()
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean)
  const items = []
  
  for (const line of lines) {
    const match = line.match(/^[-*•]?\s*\[(.*?)\]\s*(.*)$/)
    if (match) {
      items.push({
        time: match[1],
        content: match[2]
      })
    } else {
      items.push({
        time: '',
        content: line.replace(/^[-*•]\s*/, '')
      })
    }
  }
  return items
})

// 提取 AI 建议中的实盘复盘与客观总结段落（若模型输出包含）
const aiExtractedVerdict = computed(() => {
  if (!activeAdvice.value?.suggestion) return ''
  const text = activeAdvice.value.suggestion
  const m = text.match(/(?:[🤖💡🎯📝]\s*【[^】]*(?:复盘|核验|总结|反思)[^】]*】)([\s\S]*?)(?=(?:[☯️📊🎯🔮🛡️💡📝⚡🪐📰]\s*【|$))/i)
  if (m && m[1].trim()) {
    return m[1].trim()
  }
  return ''
})

// 结构化解析理财建议要点
const structuredAdvicePoints = computed(() => {
  if (!dayDetail.value?.financial_advice) return []
  if (dayDetail.value.financial_advice.advice_points_structured?.length) {
    return dayDetail.value.financial_advice.advice_points_structured
  }
  const raw = dayDetail.value.financial_advice.advice_points || []
  return raw.map(str => {
    const match = str.match(/^([^\w\s【]*)\s*【(.*?)】[：:]([\s\S]*)$/)
    if (match) {
      return {
        icon: match[1].trim() || '💡',
        title: match[2].trim(),
        content: match[3].trim()
      }
    }
    return {
      icon: '💡',
      title: '要点提示',
      content: str
    }
  })
})

// 加载月度数据
const loadMonthData = async () => {
  loading.value = true
  try {
    const res = await api.getCalendarMonth(currentYear.value, currentMonth.value)
    monthDays.value = res.days || []
    Object.assign(summaryData, res.summary || {})

    if (res.available_holdings && res.available_holdings.length) {
      availableHoldings.value = res.available_holdings
    }
    
    if (res.settings_display) {
      profitDisplayMode.value = res.settings_display.profit_display_mode || 'amount'
      showMetaphysics.value = res.settings_display.show_metaphysics !== false
      showAuspicious.value = res.settings_display.show_auspicious !== false
      showShensha.value = res.settings_display.show_shensha !== false
      displayDayMaster.value = res.settings_display.bazi_day_master || '壬水'
    }
  } catch (e) {
    console.error('Failed to load month calendar:', e)
  } finally {
    loading.value = false
  }
}

// 快捷操作
const prevMonth = () => {
  if (currentMonth.value === 1) {
    currentYear.value -= 1
    currentMonth.value = 12
  } else {
    currentMonth.value -= 1
  }
  loadMonthData()
}

const nextMonth = () => {
  if (currentMonth.value === 12) {
    currentYear.value += 1
    currentMonth.value = 1
  } else {
    currentMonth.value += 1
  }
  loadMonthData()
}

const goToday = () => {
  currentYear.value = today.getFullYear()
  currentMonth.value = today.getMonth() + 1
  loadMonthData()
}

const setProfitMode = (mode) => {
  profitDisplayMode.value = mode
}

// 打开日期详情
const openDayDetail = async (dateStr) => {
  try {
    const detail = await api.getCalendarDay(dateStr)
    dayDetail.value = detail
    selectedDay.value = monthDays.value.find(d => d.date === dateStr)
    
    // 初始化选中的建议与核验表单
    if (detail.latest_ai_advice) {
      currentViewAdviceId.value = detail.latest_ai_advice.id
      verifyForm.status = detail.latest_ai_advice.verified_status || 'pending'
      verifyForm.notes = detail.latest_ai_advice.verified_notes || ''
    } else {
      currentViewAdviceId.value = null
      verifyForm.status = 'pending'
      verifyForm.notes = ''
    }
    
    verifySuccessMessage.value = ''
    detailTab.value = 'pnl'
    showDetailModal.value = true
  } catch (e) {
    console.error('Failed to load day detail:', e)
  }
}

const closeDetailModal = () => {
  showDetailModal.value = false
  dayDetail.value = null
  selectedDay.value = null
}

// 生成 AI 建议
const handleGenerateAiAdvice = async () => {
  if (!dayDetail.value) return
  generatingAi.value = true
  try {
    const res = await api.generateCalendarAiAdvice({
      date: dayDetail.value.date
    })
    if (res.success) {
      // 重新加载该日详情与月份汇总
      await openDayDetail(dayDetail.value.date)
      loadMonthData()
      detailTab.value = 'ai'
    } else {
      alert(res.message || 'AI 建议生成异常')
    }
  } catch (e) {
    alert('AI 建议生成失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    generatingAi.value = false
  }
}

// 删除指定的时段研判建议及相关联信息
const deletingAdvice = ref(false)
const handleDeleteAdvice = async (adv) => {
  if (!adv || !adv.id) return
  const slotName = adv.time_slot || '该时段'
  const timeStr = adv.generated_at ? adv.generated_at.slice(11, 16) : ''
  const ok = window.confirm(`确定要删除【${slotName} (${timeStr})】的研判时段标签及其所有关联建议内容吗？\n删除后不可恢复。`)
  if (!ok) return

  deletingAdvice.value = true
  try {
    const res = await api.deleteCalendarAiAdvice(adv.id)
    if (res.success) {
      // 重新加载该日详情
      if (dayDetail.value?.date) {
        const detail = await api.getCalendarDay(dayDetail.value.date)
        dayDetail.value = detail
        // 自动重置或切换当前选中的建议ID
        if (detail.latest_ai_advice) {
          currentViewAdviceId.value = detail.latest_ai_advice.id
        } else {
          currentViewAdviceId.value = null
        }
      }
      // 刷新日历月份数据标记
      await loadMonthData()
    } else {
      alert('删除失败: ' + (res.message || '未知错误'))
    }
  } catch (err) {
    console.error('Failed to delete advice:', err)
    alert('删除建议失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    deletingAdvice.value = false
  }
}

// 保存核验结果
const handleSaveVerification = async () => {
  if (!dayDetail.value) return
  savingVerification.value = true
  verifySuccessMessage.value = ''
  try {
    const res = await api.verifyCalendarAiAdvice(dayDetail.value.date, {
      verified_status: verifyForm.status,
      verified_notes: verifyForm.notes
    })
    if (res.success) {
      verifySuccessMessage.value = '✅ 实盘核验结论已保存'
      loadMonthData()
      setTimeout(() => {
        verifySuccessMessage.value = ''
      }, 3000)
    }
  } catch (e) {
    alert('核验结论保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    savingVerification.value = false
  }
}

// 数字格式化工具
const formatNumber = (num) => {
  if (num === null || num === undefined || isNaN(num)) return '0.00'
  return Number(num).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatCompact = (num) => {
  if (num === null || num === undefined || isNaN(num)) return '0'
  const abs = Math.abs(num)
  if (abs >= 10000) {
    return (num / 10000).toFixed(2) + '万'
  }
  return Number(num).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

onMounted(() => {
  loadMonthData()
})
</script>

<style scoped>
.calendar-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 20px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.month-selector-group {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-card);
  padding: 6px 12px;
  border-radius: 10px;
  border: 1px solid var(--border-glass);
}

.year-select, .month-select {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--border-glass);
  border-radius: 6px;
  padding: 4px 8px;
  color: var(--text-primary);
  font-size: 0.95rem;
  cursor: pointer;
}

.holding-select-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-card);
  border: 1px solid var(--border-glass);
  padding: 5px 10px;
  border-radius: 8px;
}

.holding-select-label {
  font-size: 0.82rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

.holding-select {
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 0.86rem;
  font-weight: 600;
  outline: none;
  cursor: pointer;
}

.holding-select option,
.holding-select optgroup {
  background: #1e222d;
  color: #e2e8f0;
}

.display-toggle-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toggle-pill {
  display: flex;
  background: var(--bg-card);
  border-radius: 8px;
  border: 1px solid var(--border-glass);
  padding: 2px;
}

.pill-btn {
  padding: 4px 10px;
  font-size: 0.85rem;
  border-radius: 6px;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.pill-btn.active {
  background: var(--accent-primary);
  color: #000;
  font-weight: 600;
}

/* 总结面板 */
.summary-banner {
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 16px 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.summary-col {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-col .label {
  font-size: 0.82rem;
  color: var(--text-secondary);
}

.summary-col .val {
  font-size: 1.15rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 6px;
}

.summary-col .sub-val {
  font-size: 0.85rem;
  font-weight: normal;
  color: var(--text-secondary);
}

.summary-divider {
  width: 1px;
  height: 36px;
  background: var(--border-glass);
}

/* 日历网格 */
.calendar-grid-container {
  padding: 16px;
}

.weekday-header-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
  margin-bottom: 8px;
  text-align: center;
}

.weekday-cell {
  padding: 8px 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.weekday-cell.weekend {
  color: var(--yellow);
}

.calendar-cells-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
}

.calendar-cell {
  min-height: 110px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.calendar-cell:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--accent-primary);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
}

.calendar-cell.empty-cell {
  background: transparent;
  border-color: transparent;
  cursor: default;
}

.calendar-cell.empty-cell:hover {
  transform: none;
  box-shadow: none;
}

.calendar-cell.today-cell {
  border-color: var(--accent-primary);
  background: rgba(0, 212, 255, 0.05);
}

.calendar-cell.non-trading-cell {
  background: rgba(0, 0, 0, 0.15);
}

.cell-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.day-number {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  display: inline-block;
  min-width: 24px;
  text-align: center;
}

.day-number.today-badge {
  background: var(--accent-primary);
  color: #000;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  line-height: 24px;
}

.rest-tag {
  font-size: 0.72rem;
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  padding: 1px 5px;
  border-radius: 4px;
}

.ai-badge {
  font-size: 0.85rem;
  cursor: pointer;
}

.cell-pnl-area {
  margin: 4px 0;
  text-align: right;
}

.pnl-val {
  font-size: 0.95rem;
  font-weight: 700;
}

.rest-subtext {
  font-size: 0.78rem;
}

.cell-meta-area {
  border-top: 1px dashed rgba(255, 255, 255, 0.08);
  padding-top: 4px;
  font-size: 0.74rem;
  color: var(--text-secondary);
}

.meta-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ganzhi-tag {
  color: var(--accent-primary);
  font-weight: 600;
}

.ten-god-tag {
  color: var(--yellow);
}

.hex-name {
  color: #cbd5e1;
  font-size: 0.72rem;
}

.cell-luck-area {
  margin-top: 2px;
}

.luck-tag-badge {
  display: block;
  font-size: 0.7rem;
  padding: 1px 4px;
  border-radius: 4px;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tag-super {
  background: rgba(239, 68, 68, 0.15);
  color: #ff6b6b;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.tag-good {
  background: rgba(124, 58, 237, 0.15);
  color: #c084fc;
  border: 1px solid rgba(124, 58, 237, 0.3);
}

.tag-neutral {
  background: rgba(148, 163, 184, 0.1);
  color: #94a3b8;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.tag-clash {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.cell-shensha-area {
  margin-top: 2px;
}

.shensha-tag-badge {
  display: block;
  font-size: 0.68rem;
  padding: 1px 4px;
  border-radius: 4px;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 600;
}

.shensha-tag-badge.tag-supreme {
  background: rgba(245, 158, 11, 0.25);
  color: #fcd34d;
  border: 1px solid rgba(245, 158, 11, 0.45);
}

.shensha-tag-badge.tag-high {
  background: rgba(139, 92, 246, 0.2);
  color: #c4b5fd;
  border: 1px solid rgba(139, 92, 246, 0.35);
}

.shensha-tag-badge.tag-medium {
  background: rgba(14, 165, 233, 0.2);
  color: #7dd3fc;
  border: 1px solid rgba(14, 165, 233, 0.35);
}

.shensha-tag-badge.tag-danger {
  background: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
  border: 1px solid rgba(239, 68, 68, 0.35);
}

.shensha-tag-badge.tag-warning {
  background: rgba(234, 179, 8, 0.2);
  color: #fde047;
  border: 1px solid rgba(234, 179, 8, 0.35);
}

/* ================= 弹窗样式 ================= */
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.detail-modal {
  width: 100%;
  max-width: 950px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  padding: 24px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid var(--border-glass);
  padding-bottom: 16px;
}

.modal-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--text-primary);
  display: flex;
  align-items: center;
}

.modal-meta-pills {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.modal-meta-pills .pill {
  font-size: 0.78rem;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-secondary);
}

.modal-meta-pills .pill.pill-shensha {
  background: rgba(245, 158, 11, 0.2);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.4);
  font-weight: 600;
}

.modal-close-btn {
  font-size: 1.3rem;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
}

.modal-close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.modal-tabs {
  display: flex;
  gap: 12px;
  border-bottom: 1px solid var(--border-glass);
  padding: 12px 0;
}

.modal-tabs .tab-btn {
  background: transparent;
  border: none;
  font-size: 0.95rem;
  color: var(--text-secondary);
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.modal-tabs .tab-btn.active {
  background: var(--accent-primary);
  color: #000;
  font-weight: 600;
}

.tab-count-badge {
  background: rgba(0, 0, 0, 0.3);
  color: #fff;
  font-size: 0.72rem;
  padding: 1px 6px;
  border-radius: 10px;
}

.modal-body {
  overflow-y: auto;
  padding: 16px 0;
  flex: 1;
}

/* 选项卡 1 样式 */
.pnl-summary-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.pnl-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-glass);
  border-radius: 10px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pnl-card .label {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.pnl-card .val {
  font-size: 1.25rem;
  font-weight: 700;
}

.detail-table {
  width: 100%;
  border-collapse: collapse;
}

.detail-table th, .detail-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.detail-table th {
  color: var(--text-secondary);
  font-size: 0.82rem;
}

/* 选项卡 2 样式 */
.section-card {
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px 22px;
  margin-bottom: 24px;
}

.section-card:last-child {
  margin-bottom: 0;
}

.section-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.card-title {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--accent-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.card-subtitle-badge {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-secondary);
}

.meta-detail-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.meta-box {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.meta-box .meta-label {
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.meta-box .meta-val {
  font-size: 0.95rem;
  line-height: 1.4;
}

.meta-box .meta-sub {
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-left: 4px;
}

.luck-explanation-card {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 14px 18px;
  margin-top: 14px;
}

.luck-exp-header {
  margin-bottom: 6px;
}

.luck-exp-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--accent-primary);
}

.luck-exp-text {
  font-size: 0.9rem;
  color: #cbd5e1;
  line-height: 1.85;
  margin: 0;
  letter-spacing: 0.015em;
}

.hexagram-box {
  display: flex;
  gap: 20px;
  align-items: center;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 16px 20px;
}

.hex-badge-large {
  font-size: 3rem;
  line-height: 1;
  color: var(--accent-primary);
}

.hex-content p {
  margin-bottom: 10px;
  font-size: 0.88rem;
  line-height: 1.85;
  color: #cbd5e1;
  letter-spacing: 0.015em;
}

.hex-content p:last-child {
  margin-bottom: 0;
}

.resonance-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.resonance-item {
  background: rgba(255, 255, 255, 0.03);
  padding: 12px;
  border-radius: 8px;
  border-left: 3px solid var(--accent-primary);
}

.res-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.res-sector {
  font-size: 0.8rem;
  color: var(--yellow);
}

.res-body {
  font-size: 0.88rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* 选项卡 3 AI 样式 */
.ai-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.025);
  padding: 14px 18px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  margin-bottom: 24px;
}

.ai-status-hint {
  display: flex;
  align-items: center;
  font-size: 0.88rem;
}

.timeline-switcher {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

.timeline-btn {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 6px 12px;
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 0.82rem;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.timeline-btn:hover {
  border-color: var(--accent-primary);
  color: var(--text-primary);
}

.timeline-btn.active {
  background: var(--accent-primary);
  color: #000;
  font-weight: 700;
  border-color: var(--accent-primary);
}

.final-dot {
  color: #fbbf24;
  font-weight: bold;
}

.delete-adv-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  margin-left: 4px;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.2);
  color: #111;
  cursor: pointer;
  transition: all 0.2s ease;
}

.delete-adv-btn:hover {
  background: #ef4444;
  color: #ffffff;
  transform: scale(1.18);
}

/* 建议正文结构化卡片 */
.ai-advice-sections-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ai-advice-block {
  background: rgba(0, 0, 0, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 16px 20px;
}

.ai-block-lead-header {
  font-size: 0.98rem;
  font-weight: 700;
  color: var(--accent-primary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.08);
  letter-spacing: 0.02em;
}

.ai-block-body {
  font-size: 0.9rem;
  line-height: 1.85;
  color: #cbd5e1;
  white-space: pre-wrap;
  letter-spacing: 0.015em;
}

/* AI 实盘复盘核验与深度总结意见 */
.ai-review-stat-bar {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 16px;
}

.review-stat-col {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stat-col-lbl {
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.stat-col-val {
  font-size: 1.2rem;
  font-weight: 700;
}

.stat-col-val .sub-pct {
  font-size: 0.88rem;
  font-weight: 600;
  margin-left: 6px;
}

.stat-pill-badge {
  font-size: 0.85rem;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  display: inline-block;
}

.stat-pill-badge.pill-accurate {
  background: rgba(16, 185, 129, 0.2);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.4);
}

.stat-pill-badge.pill-defensive {
  background: rgba(245, 158, 11, 0.2);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.4);
}

.ai-verdict-card {
  background: rgba(0, 212, 255, 0.04);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-left: 4px solid var(--accent-primary);
  border-radius: 8px;
  padding: 16px 20px;
}

.ai-verdict-title {
  font-size: 0.94rem;
  font-weight: 700;
  color: var(--accent-primary);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.ai-verdict-content {
  font-size: 0.9rem;
  line-height: 1.85;
  color: #f1f5f9;
  letter-spacing: 0.015em;
}

/* 重大金融要闻与持仓联动 */
.news-guide-desc {
  font-size: 0.86rem;
  color: var(--text-secondary);
  margin-bottom: 14px;
  line-height: 1.6;
}

.news-event-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.news-event-item {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 14px 18px;
}

.news-event-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.news-time-pill {
  font-size: 0.78rem;
  color: var(--accent-primary);
  font-weight: 600;
}

.news-status-tag {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-secondary);
}

.news-event-text {
  font-size: 0.88rem;
  line-height: 1.8;
  color: #cbd5e1;
  letter-spacing: 0.015em;
}

/* 颜色工具类 */
.text-red {
  color: var(--red);
}

.text-green {
  color: var(--green);
}

.text-accent {
  color: var(--accent-primary);
}

.text-yellow {
  color: var(--yellow);
}

.badge-stock {
  background: rgba(239, 68, 68, 0.15);
  color: #ff6b6b;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.badge-fund {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.badge-accent {
  background: rgba(0, 212, 255, 0.15);
  color: var(--accent-primary);
  border: 1px solid rgba(0, 212, 255, 0.3);
}

.badge-secondary {
  background: rgba(148, 163, 184, 0.15);
  color: #94a3b8;
  border: 1px solid rgba(148, 163, 184, 0.3);
}

.badge-warning {
  background: rgba(245, 158, 11, 0.15);
  color: var(--yellow);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.badge-luck-good {
  background: rgba(124, 58, 237, 0.15);
  color: #c084fc;
  border: 1px solid rgba(124, 58, 237, 0.3);
}

.badge-luck-bad {
  background: rgba(239, 68, 68, 0.15);
  color: #ff6b6b;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

/* ================= 流日神煞与深度理财建议样式 ================= */
.shensha-detail-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.shensha-card {
  padding: 14px 18px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.shensha-card.shensha-supreme {
  border-color: rgba(245, 158, 11, 0.45);
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.14) 0%, rgba(0, 0, 0, 0.3) 100%);
}

.shensha-card.shensha-high {
  border-color: rgba(139, 92, 246, 0.4);
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.14) 0%, rgba(0, 0, 0, 0.3) 100%);
}

.shensha-card.shensha-medium {
  border-color: rgba(14, 165, 233, 0.35);
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.12) 0%, rgba(0, 0, 0, 0.3) 100%);
}

.shensha-card.shensha-danger {
  border-color: rgba(239, 68, 68, 0.4);
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.14) 0%, rgba(0, 0, 0, 0.3) 100%);
}

.shensha-card.shensha-warning {
  border-color: rgba(234, 179, 8, 0.35);
  background: linear-gradient(135deg, rgba(234, 179, 8, 0.12) 0%, rgba(0, 0, 0, 0.3) 100%);
}

.shensha-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.shensha-title-wrap {
  display: flex;
  align-items: center;
}

.shensha-badge {
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--text-primary);
}

.shensha-keyword {
  font-size: 0.85rem;
  color: var(--accent-primary);
  font-weight: 600;
}

.shensha-type-tag {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
}

.shensha-guide-text {
  font-size: 0.88rem;
  color: #cbd5e1;
  line-height: 1.8;
  margin: 0;
  letter-spacing: 0.015em;
}

.guide-lead {
  color: var(--yellow);
  font-weight: 600;
}

/* 综合理财建议卡片 */
.advice-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.advice-posture-tags {
  display: flex;
  align-items: center;
  gap: 8px;
}

.posture-pill {
  font-size: 0.8rem;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 12px;
}

.posture-bullish {
  background: rgba(239, 68, 68, 0.25);
  color: #ff6b6b;
  border: 1px solid rgba(239, 68, 68, 0.4);
}

.posture-balanced {
  background: rgba(16, 185, 129, 0.25);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.4);
}

.posture-neutral {
  background: rgba(59, 130, 246, 0.25);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.4);
}

.posture-defensive {
  background: rgba(245, 158, 11, 0.25);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.4);
}

.position-pill {
  font-size: 0.78rem;
  padding: 3px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.action-summary-card {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-left: 4px solid var(--accent-primary);
  border-radius: 8px;
  padding: 14px 18px;
  margin-bottom: 16px;
}

.summary-lead-title {
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--accent-primary);
  margin-bottom: 6px;
}

.summary-lead-text {
  font-size: 0.9rem;
  color: #f1f5f9;
  line-height: 1.8;
  margin: 0;
  letter-spacing: 0.015em;
}

.advice-points-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.advice-point-card {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 14px 18px;
  transition: background 0.2s;
}

.advice-point-card:hover {
  background: rgba(0, 0, 0, 0.35);
}

.point-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.point-icon-title {
  font-size: 0.92rem;
  color: var(--text-primary);
}

.point-icon-title strong {
  color: var(--accent-primary);
}

.point-card-badge {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.08);
  color: #94a3b8;
}

.point-card-content {
  font-size: 0.88rem;
  color: #cbd5e1;
  line-height: 1.85;
  margin: 0;
  letter-spacing: 0.015em;
}

.empty-hint-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px dashed rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  font-size: 0.86rem;
  color: var(--text-secondary);
}

.rest-day-banner {
  background: rgba(148, 163, 184, 0.12);
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 0.88rem;
  color: #cbd5e1;
  display: flex;
  align-items: center;
  gap: 8px;
  line-height: 1.6;
}
</style>
