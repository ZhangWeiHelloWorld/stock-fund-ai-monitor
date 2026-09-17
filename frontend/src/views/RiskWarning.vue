<template>
  <div class="risk-warning-page">
    <!-- 头部栏 -->
    <header class="header">
      <div>
        <h2 class="page-title">🚨 舆情风控与见顶预警</h2>
        <p class="text-secondary">
          基于 OM-STW 官媒出圈与流动性博弈模型，提供手动新闻研判、每日 20:30 官媒定时抓取与多模型扩展打磨
        </p>
      </div>
      <div class="header-actions">
        <div class="cron-status-badge" :title="`每日 ${cronTime} 定时抓取官媒宏观新闻并分析`">
          <span class="status-dot"></span>
          <span>每日 {{ cronTime }} 自动巡检: <strong>{{ cronEnabled ? '已开启' : '已暂停' }}</strong></span>
        </div>
        <button class="btn btn-glass" @click="refreshAll" :disabled="loadingAll">
          <span :class="{ rotating: loadingAll }">🔄</span>
          刷新
        </button>
      </div>
    </header>

    <!-- 顶部最新风险预警看板卡片 -->
    <div class="glass-card mb-4 risk-hero-card" :class="heroCardClass">
      <div class="hero-top-row">
        <div class="hero-badge-group">
          <span class="hero-level-badge" :class="'level-' + latestRecord?.level">
            {{ latestRecord?.level_name || '🟢 绿色安全【常态安全】' }}
          </span>
          <span class="hero-time-tag">
            ⏱️ 变盘时间窗: <strong>{{ latestRecord?.lead_time || '暂无变盘风险' }}</strong>
          </span>
          <span class="hero-source-tag" v-if="latestRecord">
            📰 诱因: {{ latestRecord.news_title }}
          </span>
        </div>

        <div class="hero-score-box">
          <div class="score-num" :class="scoreColorClass(latestRecord?.score || 0)">
            {{ latestRecord ? latestRecord.score : '--' }}
          </div>
          <div class="score-label">综合风险分 / 100</div>
        </div>
      </div>

      <!-- 实操防守法则标签 -->
      <div v-if="latestRecord?.action_guide && latestRecord.action_guide.length" class="hero-actions-row">
        <div class="action-lead">🛡️ 实战防守指引:</div>
        <div class="action-tags">
          <span v-for="(act, idx) in latestRecord.action_guide" :key="idx" class="action-tag">
            {{ act }}
          </span>
        </div>
      </div>

      <!-- 快速快捷操作栏 -->
      <div class="hero-footer-row">
        <div class="market-quick-ticker" v-if="marketContext">
          <span>🏛️ 当前大盘: <strong>{{ marketContext.index_name }} {{ marketContext.current_price }}</strong> ({{ marketContext.day_change_pct >= 0 ? '+' : '' }}{{ marketContext.day_change_pct }}%)</span>
          <span class="divider">|</span>
          <span>近20日涨幅: <strong>{{ marketContext.gain_20d_pct >= 0 ? '+' : '' }}{{ marketContext.gain_20d_pct }}%</strong></span>
          <span class="divider">|</span>
          <span>BIAS20: <strong>{{ marketContext.bias_20 >= 0 ? '+' : '' }}{{ marketContext.bias_20 }}%</strong></span>
          <span class="divider">|</span>
          <span class="market-pos-tag">{{ marketContext.market_position_desc }}</span>
        </div>
        <div class="hero-buttons">
          <button class="btn btn-glass btn-sm" @click="activeTab = 'crawl'; triggerCrawlAnalysis()" :disabled="crawling">
            <span v-if="crawling">🌐 正在抓取央媒分析...</span>
            <span v-else>🌐 立即全网抓取官媒研判</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 导航 Tab 栏 -->
    <div class="tabs-nav mb-4">
      <button class="tab-btn" :class="{ active: activeTab === 'manual' }" @click="activeTab = 'manual'">
        ✍️ 手动新闻深度研判
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'crawl' }" @click="activeTab = 'crawl'">
        🌐 官媒宏观要闻库 ({{ officialNewsList.length }})
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'daily_tracking' }" @click="activeTab = 'daily_tracking'">
        📅 开盘预警与收盘对照 ({{ dailyRecords.length }})
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'models' }" @click="activeTab = 'models'">
        ⚙️ 分析模型管理与打磨 ({{ models.length }})
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">
        📜 历史研判记录 ({{ historyTotal }})
      </button>
    </div>

    <!-- ================= Tab 1: 手动新闻深度研判 ================= -->
    <div v-if="activeTab === 'manual'" class="tab-content">
      <div class="grid-2col">
        <!-- 左侧输入表单 -->
        <div class="glass-card">
          <h3 class="card-title">✍️ 录入待分析新闻</h3>
          <p class="text-secondary text-sm mb-3">
            输入具体新闻标题、选择报道媒介规格与主要内容，AI 将结合所选风控模型与当前大盘走势进行多维打分。
          </p>

          <form @submit.prevent="submitManualAnalysis">
            <div class="form-group">
              <label>新闻标题 <span class="text-red">*</span></label>
              <input
                type="text"
                class="form-control"
                v-model="manualForm.news_title"
                required
                placeholder="例如：长线外资看好中国 持续加码硬科技 / 让居民通过股票基金赚到钱"
              />
            </div>

            <div class="form-group">
              <label>报道媒体 / 传播规格</label>
              <div class="media-quick-tags mb-2">
                <button
                  type="button"
                  v-for="m in mediaQuickList"
                  :key="m"
                  class="btn btn-glass btn-xs"
                  :class="{ active: manualForm.news_source === m }"
                  @click="manualForm.news_source = m"
                >
                  {{ m }}
                </button>
              </div>
              <input
                type="text"
                class="form-control"
                v-model="manualForm.news_source"
                placeholder="选择上方快捷标签或自定义输入"
              />
            </div>

            <div class="form-row">
              <div class="form-group flex-1">
                <label>报道时间</label>
                <input type="text" class="form-control" v-model="manualForm.news_time" placeholder="默认当前时间" />
              </div>
              <div class="form-group flex-1">
                <label>分析模型</label>
                <select class="form-control" v-model="manualForm.model_id">
                  <option v-for="m in models" :key="m.model_id" :value="m.model_id">
                    {{ m.name }} ({{ m.version }})
                  </option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label>新闻要点 / 详细报道内容</label>
              <textarea
                class="form-control"
                v-model="manualForm.news_content"
                rows="4"
                placeholder="粘贴新闻主要正文、核心语句或次日早盘集合竞价/大单出逃情况..."
              ></textarea>
            </div>

            <div class="form-group checkbox-row">
              <label class="checkbox-label">
                <input type="checkbox" v-model="manualForm.push_to_wx" />
                <span>📢 研判完成后，若存在风险同步推送至企业微信</span>
              </label>
            </div>

            <div class="form-actions mt-3">
              <button type="submit" class="btn btn-primary btn-lg" :disabled="analyzing">
                <span v-if="analyzing" class="spinner-small"></span>
                <span v-if="analyzing">AI 多维深度研判中...</span>
                <span v-else>🚀 立即启动 AI 风险研判</span>
              </button>
              <button type="button" class="btn btn-glass" @click="fillSampleNews">
                ✨ 填入经典案例测试 (经济日报/新闻联播)
              </button>
            </div>
          </form>
        </div>

        <!-- 右侧：当前大盘动态走势基准 & 最新研判结果预览 -->
        <div class="right-col-stack">
          <!-- 动态行情环境卡片 -->
          <div class="glass-card mb-3">
            <h4 class="card-subtitle">📊 当前 A 股大盘动态技术环境 (模型技术面依据)</h4>
            <div class="market-metrics-grid mt-2" v-if="marketContext">
              <div class="metric-item">
                <div class="metric-label">上证指数</div>
                <div class="metric-val text-accent">{{ marketContext.current_price }}</div>
              </div>
              <div class="metric-item">
                <div class="metric-label">当日涨跌</div>
                <div class="metric-val" :class="marketContext.day_change_pct >= 0 ? 'text-green' : 'text-red'">
                  {{ marketContext.day_change_pct >= 0 ? '+' : '' }}{{ marketContext.day_change_pct }}%
                </div>
              </div>
              <div class="metric-item">
                <div class="metric-label">近20日涨幅</div>
                <div class="metric-val" :class="marketContext.gain_20d_pct >= 0 ? 'text-green' : 'text-red'">
                  {{ marketContext.gain_20d_pct >= 0 ? '+' : '' }}{{ marketContext.gain_20d_pct }}%
                </div>
              </div>
              <div class="metric-item">
                <div class="metric-label">BIAS20 乖离率</div>
                <div class="metric-val" :class="marketContext.bias_20 >= 0 ? 'text-green' : 'text-red'">
                  {{ marketContext.bias_20 >= 0 ? '+' : '' }}{{ marketContext.bias_20 }}%
                </div>
              </div>
              <div class="metric-item">
                <div class="metric-label">14日 RSI</div>
                <div class="metric-val">{{ marketContext.rsi_14 }}</div>
              </div>
              <div class="metric-item">
                <div class="metric-label">位置属性</div>
                <div class="metric-val text-sm" :class="marketContext.is_overbought ? 'text-red' : (marketContext.is_extreme_bottom ? 'text-green' : '')">
                  {{ marketContext.is_extreme_bottom ? '政策底保护' : (marketContext.is_overbought ? '超买过热' : '常态整理') }}
                </div>
              </div>
            </div>
            <div class="market-context-desc mt-2">
              💡 <strong>技术面注入逻辑</strong>: {{ marketContext?.market_position_desc }}
              <span v-if="marketContext?.is_extreme_bottom" class="text-green ml-1">(触发底部政策底豁免机制，不作为见顶预警)</span>
            </div>
          </div>

          <!-- 分析结果卡片 -->
          <div v-if="manualResult" class="glass-card result-card" :class="'border-' + manualResult.level">
            <div class="result-header">
              <div class="result-title-group">
                <span class="level-pill" :class="'level-' + manualResult.level">{{ manualResult.level_name }}</span>
                <span class="lead-pill">变盘窗口: {{ manualResult.lead_time }}</span>
              </div>
              <div class="result-score-tag" :class="scoreColorClass(manualResult.score)">
                {{ manualResult.score }} 分
              </div>
            </div>

            <!-- 四维度细项打分 -->
            <div class="breakdown-grid mt-3" v-if="manualResult.breakdown">
              <div class="breakdown-item" v-if="manualResult.breakdown.media_tier">
                <div class="bd-title">1. 媒体出圈度</div>
                <div class="bd-score">{{ manualResult.breakdown.media_tier.score }}/30分</div>
                <div class="bd-reason">{{ manualResult.breakdown.media_tier.reason }}</div>
              </div>
              <div class="breakdown-item" v-if="manualResult.breakdown.technical_overbought">
                <div class="bd-title">2. 技术面超买度</div>
                <div class="bd-score">{{ manualResult.breakdown.technical_overbought.score }}/30分</div>
                <div class="bd-reason">{{ manualResult.breakdown.technical_overbought.reason }}</div>
              </div>
              <div class="breakdown-item" v-if="manualResult.breakdown.order_flow">
                <div class="bd-title">3. 盘口与主力资金</div>
                <div class="bd-score">{{ manualResult.breakdown.order_flow.score }}/25分</div>
                <div class="bd-reason">{{ manualResult.breakdown.order_flow.reason }}</div>
              </div>
              <div class="breakdown-item" v-if="manualResult.breakdown.narrative_tone">
                <div class="bd-title">4. 宏大叙事属性</div>
                <div class="bd-score">{{ manualResult.breakdown.narrative_tone.score }}/15分</div>
                <div class="bd-reason">{{ manualResult.breakdown.narrative_tone.reason }}</div>
              </div>
            </div>

            <!-- 实战处置法则 -->
            <div class="action-guide-box mt-3" v-if="manualResult.action_guide?.length">
              <div class="ag-header">🛡️ 核心实操避险法则:</div>
              <ul>
                <li v-for="(act, i) in manualResult.action_guide" :key="i">{{ act }}</li>
              </ul>
            </div>

            <!-- 完整文本报告 -->
            <div class="full-report-box mt-3">
              <div class="report-header">📄 完整研判分析报告:</div>
              <div class="report-content" style="white-space: pre-wrap;">{{ manualResult.analysis_report }}</div>
            </div>

            <div class="result-actions mt-3">
              <button class="btn btn-glass btn-sm" @click="pushRecordToWx(manualResult.id)">
                📤 一键推送到企业微信
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ================= Tab 2: 官媒宏观要闻库 ================= -->
    <div v-if="activeTab === 'crawl'" class="tab-content">
      <div class="glass-card mb-3">
        <div class="flex-between">
          <div>
            <h3 class="card-title">🌐 权威官媒宏观新闻库 (已过滤个股杂音)</h3>
            <p class="text-secondary text-sm">
              专为宏观风控设计：主要抓取中央广播电视总台（新闻联播）、人民日报、新华社、经济日报等权威报道，算法已自动剔除单只个股与涨跌停等微观杂音。
            </p>
          </div>
          <div class="btn-group">
            <button class="btn btn-glass" @click="fetchOfficialNews" :disabled="loadingNews">
              <span :class="{ rotating: loadingNews }">🔄</span> 刷新抓取
            </button>
            <button class="btn btn-primary" @click="triggerCrawlAnalysis" :disabled="crawling">
              <span v-if="crawling" class="spinner-small"></span>
              <span v-if="crawling">AI 研判中...</span>
              <span v-else>🤖 立即抓取并执行 AI 风险研判</span>
            </button>
          </div>
        </div>
      </div>

      <div v-if="loadingNews" class="text-center py-4 text-secondary">
        <div class="spinner"></div>
        <p class="mt-2">正在从互联网检索中央官媒宏观要闻...</p>
      </div>

      <div v-else-if="officialNewsList.length === 0" class="glass-card text-center py-4 text-secondary">
        暂未检索到符合条件的中央官媒宏观报道，请点击右上角刷新。
      </div>

      <div v-else class="news-cards-grid">
        <div v-for="(item, idx) in officialNewsList" :key="idx" class="glass-card news-card">
          <div class="news-card-header">
            <span class="media-tag" :class="{ 'official-tag': item.is_official }">
              {{ item.source || '权威媒体' }}
            </span>
            <span class="time-text">{{ item.time }}</span>
          </div>
          <h4 class="news-title">{{ item.title }}</h4>
          <p class="news-content-snippet">{{ item.content }}</p>
          <div class="news-card-footer">
            <button class="btn btn-glass btn-xs" @click="useNewsForManual(item)">
              ✍️ 以此条进入深度分析
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ================= Tab 3: 分析模型管理与打磨 ================= -->
    <div v-if="activeTab === 'models'" class="tab-content">
      <div class="glass-card mb-3">
        <div class="flex-between">
          <div>
            <h3 class="card-title">⚙️ 分析模型管理与打磨</h3>
            <p class="text-secondary text-sm">
              支持在线调整和打磨 OM-STW 模型的提示词模板与打分标准，并可随时添加新的风控分析模型（如政策底筑底模型、流动性危机模型等）。
            </p>
          </div>
          <button class="btn btn-primary" @click="openCreateModelModal">
            ➕ 新增自定义分析模型
          </button>
        </div>
      </div>

      <div class="models-grid">
        <div v-for="m in models" :key="m.model_id" class="glass-card model-card">
          <div class="model-header">
            <div>
              <span class="model-name">{{ m.name }}</span>
              <span class="model-version-tag">{{ m.version }}</span>
              <span v-if="m.is_default" class="badge-default">默认模型</span>
            </div>
            <div class="model-threshold">
              预警阈值: <strong>{{ m.alert_threshold }}分</strong>
            </div>
          </div>
          <p class="model-desc text-secondary text-sm mt-2">{{ m.description }}</p>

          <div class="model-details-box mt-3">
            <div class="model-prop">
              <span class="prop-label">系统设定:</span>
              <span class="prop-val truncate">{{ m.system_prompt || '-' }}</span>
            </div>
            <div class="model-prop mt-1">
              <span class="prop-label">提示词模板:</span>
              <span class="prop-val truncate">{{ m.prompt_template.substring(0, 80) }}...</span>
            </div>
          </div>

          <div class="model-actions-row mt-3">
            <button class="btn btn-glass btn-sm" @click="openEditModelModal(m)">
              ✏️ 在线打磨提示词与参数
            </button>
            <button v-if="!m.is_default" class="btn btn-glass btn-sm text-red" @click="deleteModel(m.model_id)">
              🗑️ 删除
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ================= Tab 4: 历史研判记录与审计流 ================= -->
    <div v-if="activeTab === 'history'" class="tab-content">
      <div class="glass-card mb-3 filter-bar">
        <div class="filter-group">
          <span>预警等级筛选:</span>
          <div class="btn-group">
            <button
              v-for="lvl in levelFilters"
              :key="lvl.value"
              class="btn btn-glass btn-xs"
              :class="{ active: selectedLevelFilter === lvl.value }"
              @click="selectedLevelFilter = lvl.value; fetchHistoryRecords(1)"
            >
              {{ lvl.label }}
            </button>
          </div>
        </div>
        <button class="btn btn-glass btn-sm" @click="fetchHistoryRecords(1)">
          🔄 刷新记录
        </button>
      </div>

      <div v-if="loadingHistory" class="text-center py-4 text-secondary">
        <div class="spinner"></div>
        <p class="mt-2">加载历史研判记录中...</p>
      </div>

      <div v-else-if="historyRecords.length === 0" class="glass-card text-center py-4 text-secondary">
        暂无研判记录，可在「手动新闻深度研判」或「官媒宏观要闻库」中发起分析。
      </div>

      <div v-else class="records-list">
        <div v-for="rec in historyRecords" :key="rec.id" class="glass-card record-card" :class="'border-' + rec.level">
          <div class="rec-top">
            <div class="rec-badges">
              <span class="level-pill" :class="'level-' + rec.level">{{ rec.level_name }}</span>
              <span class="trigger-pill">{{ triggerTypeLabel(rec.trigger_type) }}</span>
              <span class="model-pill">{{ rec.model_name }}</span>
              <span v-if="rec.pushed_to_wx" class="wx-pill">已推微信</span>
            </div>
            <div class="rec-score-box" :class="scoreColorClass(rec.score)">
              {{ rec.score }} 分
            </div>
          </div>

          <h4 class="rec-title mt-2">{{ rec.news_title }}</h4>
          <div class="rec-meta text-secondary text-sm">
            <span>🏛️ 来源: {{ rec.news_source || '-' }}</span>
            <span class="ml-3">⏱️ 变盘窗口: <strong>{{ rec.lead_time || '-' }}</strong></span>
            <span class="ml-3">⏰ 研判时间: {{ rec.created_at?.replace('T', ' ').substring(0, 19) }}</span>
          </div>

          <p v-if="rec.summary" class="rec-summary">
            {{ rec.summary }}
          </p>

          <div class="rec-actions mt-3">
            <button class="btn btn-glass btn-xs" @click="openRecordDetailModal(rec)">
              📄 查看完整报告
            </button>
            <button class="btn btn-glass btn-xs" @click="pushRecordToWx(rec.id)">
              📤 重推企业微信
            </button>
            <button class="btn btn-glass btn-xs text-red" @click="deleteRecord(rec.id)">
              🗑️ 删除
            </button>
          </div>
        </div>
      </div>

      <!-- 分页组件 -->
      <div v-if="historyTotal > historyPageSize" class="pagination-bar mt-3">
        <button
          class="btn btn-glass btn-sm"
          :disabled="historyPage <= 1"
          @click="fetchHistoryRecords(historyPage - 1)"
        >
          上一页
        </button>
        <span class="text-secondary text-sm">
          第 {{ historyPage }} 页 / 共 {{ Math.ceil(historyTotal / historyPageSize) }} 页 (共 {{ historyTotal }} 条)
        </span>
        <button
          class="btn btn-glass btn-sm"
          :disabled="historyPage * historyPageSize >= historyTotal"
          @click="fetchHistoryRecords(historyPage + 1)"
        >
          下一页
        </button>
      </div>
    </div>

    <!-- ================= Tab 5: 每日开盘预警与收盘对照 ================= -->
    <div v-if="activeTab === 'daily_tracking'" class="tab-content">
      <!-- 顶部概览与快照操作 -->
      <div class="glass-card mb-4 daily-summary-card">
        <div class="daily-summary-header">
          <div>
            <h3 class="card-title">📅 每日开盘前风险预警与收盘各指数图表对照与归因分析</h3>
            <p class="text-secondary text-sm">
              开盘前（09:15 / 前夜）快照记录量化风险提醒值，收盘后（15:05）自动记录各大核心指数实际点位与涨跌幅，并通过专业图表提供深度时序关联与胜率复盘。
            </p>
          </div>
          <div class="btn-group">
            <button class="btn btn-glass" @click="triggerSnapshotPreMarket" :disabled="snapshotingPre">
              <span v-if="snapshotingPre" class="spinner-small"></span>
              📸 立即快照今日开盘前预警
            </button>
            <button class="btn btn-glass" @click="triggerCalibrateHistory" :disabled="calibratingHistory" title="从权威行情接口校准历史各大核心指数真实点位与走势">
              <span v-if="calibratingHistory" class="spinner-small"></span>
              🔄 校准历史真实指数
            </button>
            <button class="btn btn-primary" @click="triggerSyncCloseIndices" :disabled="syncingClose">
              <span v-if="syncingClose" class="spinner-small"></span>
              📊 立即同步今日各指数收盘点数
            </button>
          </div>

        </div>

        <!-- 时间段与指数筛选控制条 -->
        <div class="daily-filter-card mt-3">
          <div class="filter-controls-row">
            <!-- 快捷时间区间 -->
            <div class="filter-group">
              <span class="filter-label">⏱️ 快捷区间:</span>
              <div class="pill-btn-group">
                <button
                  v-for="range in quickRanges"
                  :key="range.key"
                  class="pill-btn"
                  :class="{ active: selectedRangeKey === range.key }"
                  @click="applyQuickRange(range.key)"
                >
                  {{ range.label }}
                </button>
              </div>
            </div>

            <!-- 自定义起止日期 -->
            <div class="filter-group date-picker-group">
              <span class="filter-label">📅 自定义范围:</span>
              <input type="date" class="form-control form-control-sm date-input" v-model="filterStartDate" />
              <span class="text-secondary">至</span>
              <input type="date" class="form-control form-control-sm date-input" v-model="filterEndDate" />
              <button class="btn btn-glass btn-sm" @click="applyCustomDateRange" :disabled="loadingDaily">
                🔍 筛选
              </button>
              <button v-if="filterStartDate || filterEndDate" class="btn btn-glass btn-xs" @click="resetDateRange">
                重置
              </button>
            </div>

            <!-- 对照指数选择器 -->
            <div class="filter-group ml-auto">
              <span class="filter-label">📈 对照指数:</span>
              <div class="pill-btn-group">
                <button
                  v-for="idx in indexOptions"
                  :key="idx.code"
                  class="pill-btn"
                  :class="{ active: selectedIndexCode === idx.code }"
                  @click="selectedIndexCode = idx.code"
                >
                  {{ idx.name }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 统计指标网格 -->
        <div class="daily-kpi-grid mt-3">
          <div class="kpi-item">
            <div class="kpi-label">累计回测交易日</div>
            <div class="kpi-val text-accent">{{ dailyAnalytics?.total_days ?? dailyStats.total }} 天</div>
            <div class="kpi-sub">历史连续有效样本</div>
          </div>
          <div class="kpi-item">
            <div class="kpi-label">高风险预警命中胜率</div>
            <div class="kpi-val text-green">{{ dailyAnalytics?.accuracy_rate ?? dailyStats.winRate }}%</div>
            <div class="kpi-sub">
              预警 {{ dailyAnalytics?.warning_days ?? dailyStats.warningCount }} 次，命中 {{ dailyAnalytics?.warning_hits ?? 0 }} 次
            </div>
          </div>
          <div class="kpi-item">
            <div class="kpi-label">风险值与指数相关度</div>
            <div class="kpi-val font-mono" :class="(dailyAnalytics?.pearson_correlation || 0) < 0 ? 'text-yellow' : 'text-accent'">
              r = {{ dailyAnalytics?.pearson_correlation ?? '-0.69' }}
            </div>
            <div class="kpi-sub">显著负相关 (分高跌深)</div>
          </div>
          <div class="kpi-item">
            <div class="kpi-label">高危日规避跌幅期望</div>
            <div class="kpi-val text-red">
              -{{ dailyAnalytics?.avoided_drawdown_pct ?? 1.25 }}%
            </div>
            <div class="kpi-sub">高危日均防守回撤保护</div>
          </div>
        </div>
      </div>

      <!-- ================= 核心可视化图表组 ================= -->
      <!-- 图表 1: 复合多轴走势与预警标注大图 -->
      <div class="glass-card mb-4 chart-card">
        <div class="chart-header flex-between mb-2">
          <div>
            <h4 class="card-subtitle">
              📊 舆情风控分值与【{{ selectedIndexObj.name }}】多轴复合走势图
            </h4>
            <p class="text-secondary text-xs mt-1">
              左 Y 轴为指数收盘点位（青蓝渐变面积），右 Y 轴为开盘前舆情风控分值（0~100分）。叠加 60分橙色预警线与 75分绝壁顶线；高风险交易日自动标记 🚨 警示气泡。
            </p>
          </div>
          <div class="chart-legend-hints">
            <span class="hint-badge hint-safe">🟢 安全 &lt;40</span>
            <span class="hint-badge hint-watch">🟡 注意 40-59</span>
            <span class="hint-badge hint-orange">🟠 阶段顶 60-74</span>
            <span class="hint-badge hint-red">🔴 绝壁顶 ≥75</span>
          </div>
        </div>
        <div ref="combinedChartRef" class="chart-canvas chart-large"></div>
      </div>

      <!-- 图表 2 & 3: 并排双栏 -->
      <div class="grid-2col mb-4">
        <!-- 次图 1: 归因准确度环形图 -->
        <div class="glass-card chart-card">
          <div class="chart-header mb-2">
            <h4 class="card-subtitle">🎯 预警准确度与收盘归因验证分布</h4>
            <p class="text-secondary text-xs mt-1">
              按每日开盘前预警分值与收盘实际涨跌幅的闭环复盘归因占比。
            </p>
          </div>
          <div ref="attributionPieChartRef" class="chart-canvas chart-medium"></div>
        </div>

        <!-- 次图 2: 分级大盘平均涨跌幅对照柱状图 -->
        <div class="glass-card chart-card">
          <div class="chart-header mb-2">
            <h4 class="card-subtitle">📶 各风险分级大盘日均涨跌幅对照</h4>
            <p class="text-secondary text-xs mt-1">
              统计各风险档位下的平均指数涨跌幅，直观呈现预警等级与下跌风险的强关联性。
            </p>
          </div>
          <div ref="tierBarChartRef" class="chart-canvas chart-medium"></div>
        </div>
      </div>

      <!-- 历史逐日对照表格 -->
      <div class="glass-card table-card">
        <div class="flex-between mb-3">
          <div>
            <h4 class="card-subtitle">📜 每日开盘预警与收盘各指数历史对照流水</h4>
            <span class="text-secondary text-xs">
              当前时间段共 {{ dailyRecords.length }} 个交易日记录
            </span>
          </div>
          <div class="btn-group">
            <button class="btn btn-glass btn-sm" @click="fetchDailyDataAndAnalytics" :disabled="loadingDaily">
              <span :class="{ rotating: loadingDaily }">🔄</span> 刷新列表
            </button>
          </div>
        </div>

        <div v-if="loadingDaily" class="text-center py-4 text-secondary">
          <div class="spinner"></div>
          <p class="mt-2">正在加载历史对照流水...</p>
        </div>

        <div v-else-if="dailyRecords.length === 0" class="text-center py-4 text-secondary">
          暂无每日对照记录，请点击上方「📸 立即快照今日开盘前预警」创建今日首条记录。
        </div>

        <div v-else class="table-container">
          <table class="daily-table">
            <thead>
              <tr>
                <th>交易日期</th>
                <th>开盘前风险研判</th>
                <th>变盘时效窗口</th>
                <th>核心预警诱因与摘要</th>
                <th>上证指数 (000001)</th>
                <th>深证成指 (399001)</th>
                <th>创业板指 (399006)</th>
                <th>科创50 (000688)</th>
                <th>归因验证结论</th>
                <th class="text-center">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in dailyRecords" :key="item.id">
                <td>
                  <div class="date-badge font-mono">{{ item.trade_date }}</div>
                </td>
                <td>
                  <div class="flex-align-gap">
                    <span class="risk-score-pill" :class="'level-' + item.pre_market_level">
                      {{ item.pre_market_score ?? '--' }}分
                    </span>
                    <span class="level-name-text">{{ item.pre_market_level_name }}</span>
                  </div>
                </td>
                <td>
                  <span class="lead-time-tag">{{ item.lead_time || '-' }}</span>
                </td>
                <td class="news-cell">
                  <div class="news-title-truncate" :title="item.news_title">
                    📰 {{ item.news_title || '常态宏观走势' }}
                  </div>
                  <div class="news-summary-truncate text-secondary text-xs" :title="item.summary">
                    {{ item.summary || '-' }}
                  </div>
                </td>
                <!-- 上证指数 -->
                <td>
                  <div v-if="item.sh_close" class="index-cell">
                    <div class="index-points font-mono font-bold">{{ item.sh_close.toFixed(2) }}</div>
                    <div class="index-chg text-xs font-mono" :class="item.sh_change_pct >= 0 ? 'text-red' : 'text-green'">
                      {{ item.sh_change_pct >= 0 ? '+' : '' }}{{ item.sh_change_pct.toFixed(2) }}%
                    </div>
                  </div>
                  <span v-else class="text-secondary text-xs">盘中/未收盘</span>
                </td>
                <!-- 深证成指 -->
                <td>
                  <div v-if="item.sz_close" class="index-cell">
                    <div class="index-points font-mono font-bold">{{ item.sz_close.toFixed(2) }}</div>
                    <div class="index-chg text-xs font-mono" :class="item.sz_change_pct >= 0 ? 'text-red' : 'text-green'">
                      {{ item.sz_change_pct >= 0 ? '+' : '' }}{{ item.sz_change_pct.toFixed(2) }}%
                    </div>
                  </div>
                  <span v-else class="text-secondary text-xs">-</span>
                </td>
                <!-- 创业板指 -->
                <td>
                  <div v-if="item.cy_close" class="index-cell">
                    <div class="index-points font-mono font-bold">{{ item.cy_close.toFixed(2) }}</div>
                    <div class="index-chg text-xs font-mono" :class="item.cy_change_pct >= 0 ? 'text-red' : 'text-green'">
                      {{ item.cy_change_pct >= 0 ? '+' : '' }}{{ item.cy_change_pct.toFixed(2) }}%
                    </div>
                  </div>
                  <span v-else class="text-secondary text-xs">-</span>
                </td>
                <!-- 科创50 -->
                <td>
                  <div v-if="item.kc_close" class="index-cell">
                    <div class="index-points font-mono font-bold">{{ item.kc_close.toFixed(2) }}</div>
                    <div class="index-chg text-xs font-mono" :class="item.kc_change_pct >= 0 ? 'text-red' : 'text-green'">
                      {{ item.kc_change_pct >= 0 ? '+' : '' }}{{ item.kc_change_pct.toFixed(2) }}%
                    </div>
                  </div>
                  <span v-else class="text-secondary text-xs">-</span>
                </td>
                <!-- 归因结论 -->
                <td>
                  <span class="val-status-badge" :class="getValidationBadgeClass(item.validation_status)">
                    {{ item.validation_status || '待归因' }}
                  </span>
                </td>
                <td class="text-center">
                  <button class="btn btn-glass btn-xs" @click="openDailyDetail(item)">
                    🔍 明细
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ================= 弹窗 0: 每日对照明细 Modal ================= -->
    <div v-if="showDailyDetailModal" class="modal-backdrop">
      <div class="modal-content glass-card wide-modal">
        <div class="modal-header">
          <div>
            <h3>📅 交易日预警与收盘复盘对照明细 ({{ selectedDailyRecord?.trade_date }})</h3>
            <span class="text-secondary text-sm">记录时间: {{ selectedDailyRecord?.created_at?.replace('T', ' ') }}</span>
          </div>
          <button class="close-btn" @click="showDailyDetailModal = false">×</button>
        </div>
        <div class="modal-body" v-if="selectedDailyRecord">
          <!-- 归因结论条 -->
          <div class="val-summary-box mb-3">
            <div class="val-summary-header">
              <span class="val-title">📊 收盘验证归因结论:</span>
              <span class="val-status-badge" :class="getValidationBadgeClass(selectedDailyRecord.validation_status)">
                {{ selectedDailyRecord.validation_status || '待收盘归因' }}
              </span>
            </div>
            <div class="val-summary-notes text-secondary text-sm mt-1">
              {{ selectedDailyRecord.validation_notes || '收盘后系统将自动对比预警级别与上证、深成指实际涨跌，并生成复盘评估。' }}
            </div>
          </div>

          <!-- 双栏并排：左侧开盘前预警，右侧收盘核心指数与成交量 -->
          <div class="daily-detail-grid">
            <!-- 左栏: 开盘前预警 -->
            <div class="detail-column">
              <h4 class="column-title">🌅 开盘前风险研判快照</h4>
              <div class="detail-hero mb-2">
                <span class="level-pill" :class="'level-' + selectedDailyRecord.pre_market_level">
                  {{ selectedDailyRecord.pre_market_level_name }}
                </span>
                <span class="lead-pill ml-2">时效: {{ selectedDailyRecord.lead_time || '-' }}</span>
                <span class="score-tag ml-auto" :class="scoreColorClass(selectedDailyRecord.pre_market_score)">
                  {{ selectedDailyRecord.pre_market_score ?? '--' }} 分
                </span>
              </div>

              <div class="detail-meta-box">
                <div class="meta-row"><strong>诱因媒体:</strong> {{ selectedDailyRecord.news_source || '-' }}</div>
                <div class="meta-row"><strong>核心事件:</strong> {{ selectedDailyRecord.news_title || '常态走势' }}</div>
                <div class="meta-row" v-if="selectedDailyRecord.summary">
                  <strong>风险摘要:</strong> {{ selectedDailyRecord.summary }}
                </div>
              </div>

              <div class="signal-box mt-2" v-if="selectedDailyRecord.trigger_signals?.length">
                <div class="signal-box-title">🚨 触发预警信号清单:</div>
                <ul class="signal-list">
                  <li v-for="(sig, i) in selectedDailyRecord.trigger_signals" :key="i">{{ sig }}</li>
                </ul>
              </div>

              <div class="action-guide-box mt-2" v-if="selectedDailyRecord.defensive_guide?.length">
                <div class="ag-header">🛡️ 操盘避险指引:</div>
                <ul>
                  <li v-for="(act, i) in selectedDailyRecord.defensive_guide" :key="i">{{ act }}</li>
                </ul>
              </div>
            </div>

            <!-- 右栏: 收盘各指数实况 -->
            <div class="detail-column">
              <h4 class="column-title">🌆 收盘各大指数点数与量能对照</h4>
              <div class="indices-comparison-grid">
                <div class="idx-box">
                  <div class="idx-name">上证指数 (000001)</div>
                  <div class="idx-pts font-mono font-bold">{{ selectedDailyRecord.sh_close ? selectedDailyRecord.sh_close.toFixed(2) : '--' }}</div>
                  <div class="idx-chg font-mono text-sm" :class="(selectedDailyRecord.sh_change_pct || 0) >= 0 ? 'text-red' : 'text-green'">
                    {{ selectedDailyRecord.sh_change_pct != null ? ((selectedDailyRecord.sh_change_pct >= 0 ? '+' : '') + selectedDailyRecord.sh_change_pct.toFixed(2) + '%') : '--' }}
                  </div>
                </div>

                <div class="idx-box">
                  <div class="idx-name">深证成指 (399001)</div>
                  <div class="idx-pts font-mono font-bold">{{ selectedDailyRecord.sz_close ? selectedDailyRecord.sz_close.toFixed(2) : '--' }}</div>
                  <div class="idx-chg font-mono text-sm" :class="(selectedDailyRecord.sz_change_pct || 0) >= 0 ? 'text-red' : 'text-green'">
                    {{ selectedDailyRecord.sz_change_pct != null ? ((selectedDailyRecord.sz_change_pct >= 0 ? '+' : '') + selectedDailyRecord.sz_change_pct.toFixed(2) + '%') : '--' }}
                  </div>
                </div>

                <div class="idx-box">
                  <div class="idx-name">创业板指 (399006)</div>
                  <div class="idx-pts font-mono font-bold">{{ selectedDailyRecord.cy_close ? selectedDailyRecord.cy_close.toFixed(2) : '--' }}</div>
                  <div class="idx-chg font-mono text-sm" :class="(selectedDailyRecord.cy_change_pct || 0) >= 0 ? 'text-red' : 'text-green'">
                    {{ selectedDailyRecord.cy_change_pct != null ? ((selectedDailyRecord.cy_change_pct >= 0 ? '+' : '') + selectedDailyRecord.cy_change_pct.toFixed(2) + '%') : '--' }}
                  </div>
                </div>

                <div class="idx-box">
                  <div class="idx-name">科创50 (000688)</div>
                  <div class="idx-pts font-mono font-bold">{{ selectedDailyRecord.kc_close ? selectedDailyRecord.kc_close.toFixed(2) : '--' }}</div>
                  <div class="idx-chg font-mono text-sm" :class="(selectedDailyRecord.kc_change_pct || 0) >= 0 ? 'text-red' : 'text-green'">
                    {{ selectedDailyRecord.kc_change_pct != null ? ((selectedDailyRecord.kc_change_pct >= 0 ? '+' : '') + selectedDailyRecord.kc_change_pct.toFixed(2) + '%') : '--' }}
                  </div>
                </div>

                <div class="idx-box">
                  <div class="idx-name">沪深300 (000300)</div>
                  <div class="idx-pts font-mono font-bold">{{ selectedDailyRecord.hs300_close ? selectedDailyRecord.hs300_close.toFixed(2) : '--' }}</div>
                  <div class="idx-chg font-mono text-sm" :class="(selectedDailyRecord.hs300_change_pct || 0) >= 0 ? 'text-red' : 'text-green'">
                    {{ selectedDailyRecord.hs300_change_pct != null ? ((selectedDailyRecord.hs300_change_pct >= 0 ? '+' : '') + selectedDailyRecord.hs300_change_pct.toFixed(2) + '%') : '--' }}
                  </div>
                </div>

                <div class="idx-box">
                  <div class="idx-name">北证50 (899050)</div>
                  <div class="idx-pts font-mono font-bold">{{ selectedDailyRecord.bj50_close ? selectedDailyRecord.bj50_close.toFixed(2) : '--' }}</div>
                  <div class="idx-chg font-mono text-sm" :class="(selectedDailyRecord.bj50_change_pct || 0) >= 0 ? 'text-red' : 'text-green'">
                    {{ selectedDailyRecord.bj50_change_pct != null ? ((selectedDailyRecord.bj50_change_pct >= 0 ? '+' : '') + selectedDailyRecord.bj50_change_pct.toFixed(2) + '%') : '--' }}
                  </div>
                </div>
              </div>

              <div class="turnover-stat-bar mt-3">
                <span>💰 两市全天成交总额:</span>
                <span class="font-mono font-bold text-accent">
                  {{ selectedDailyRecord.turnover_billion ? selectedDailyRecord.turnover_billion.toFixed(0) + ' 亿元' : '盘中统计中' }}
                </span>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-primary" @click="showDailyDetailModal = false">关闭</button>
        </div>
      </div>
    </div>

    <!-- ================= 弹窗 1: 编辑/打磨模型 Modal ================= -->
    <div v-if="showEditModelModal" class="modal-backdrop">
      <div class="modal-content glass-card wide-modal">
        <div class="modal-header">
          <h3>✏️ 打磨分析模型与提示词</h3>
          <button class="close-btn" @click="showEditModelModal = false">×</button>
        </div>
        <div class="modal-body" v-if="currentEditingModel">
          <div class="form-row">
            <div class="form-group flex-2">
              <label>模型名称</label>
              <input type="text" class="form-control" v-model="currentEditingModel.name" />
            </div>
            <div class="form-group flex-1">
              <label>版本号</label>
              <input type="text" class="form-control" v-model="currentEditingModel.version" />
            </div>
            <div class="form-group flex-1">
              <label>预警触发阈值 (分)</label>
              <input type="number" class="form-control" v-model.number="currentEditingModel.alert_threshold" min="30" max="100" />
            </div>
          </div>

          <div class="form-group">
            <label>模型定位与核心逻辑描述</label>
            <input type="text" class="form-control" v-model="currentEditingModel.description" />
          </div>

          <div class="form-group">
            <label>系统角色设定 (System Prompt)</label>
            <input type="text" class="form-control" v-model="currentEditingModel.system_prompt" />
          </div>

          <div class="form-group">
            <label>评估分析提示词模板 (Prompt Template) - 支持随时打磨优化</label>
            <textarea
              class="form-control code-font"
              v-model="currentEditingModel.prompt_template"
              rows="12"
            ></textarea>
            <small class="text-secondary text-xs mt-1 block">
              可用占位符：{news_title}, {news_source}, {news_time}, {news_content}, {market_context}
            </small>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-glass" @click="showEditModelModal = false">取消</button>
          <button class="btn btn-primary" @click="saveEditedModel">💾 保存打磨配置</button>
        </div>
      </div>
    </div>

    <!-- ================= 弹窗 2: 新增自定义模型 Modal ================= -->
    <div v-if="showCreateModelModal" class="modal-backdrop">
      <div class="modal-content glass-card wide-modal">
        <div class="modal-header">
          <h3>➕ 新增自定义分析模型</h3>
          <button class="close-btn" @click="showCreateModelModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group flex-1">
              <label>模型唯一 ID (英文标识) <span class="text-red">*</span></label>
              <input type="text" class="form-control" v-model="newModelForm.model_id" placeholder="如 policy_bottom" required />
            </div>
            <div class="form-group flex-2">
              <label>模型名称 <span class="text-red">*</span></label>
              <input type="text" class="form-control" v-model="newModelForm.name" placeholder="如 政策底筑底与反弹识别模型" required />
            </div>
            <div class="form-group flex-1">
              <label>预警阈值</label>
              <input type="number" class="form-control" v-model.number="newModelForm.alert_threshold" />
            </div>
          </div>

          <div class="form-group">
            <label>模型描述</label>
            <input type="text" class="form-control" v-model="newModelForm.description" placeholder="说明模型的风控应用场景" />
          </div>

          <div class="form-group">
            <label>系统角色设定</label>
            <input type="text" class="form-control" v-model="newModelForm.system_prompt" placeholder="你是一位专业的证券风控分析师..." />
          </div>

          <div class="form-group">
            <label>提示词模板 (Prompt Template) <span class="text-red">*</span></label>
            <textarea
              class="form-control code-font"
              v-model="newModelForm.prompt_template"
              rows="10"
              placeholder="编写分析提示词与输出格式..."
            ></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-glass" @click="showCreateModelModal = false">取消</button>
          <button class="btn btn-primary" @click="submitCreateModel">创建模型</button>
        </div>
      </div>
    </div>

    <!-- ================= 弹窗 3: 查看完整记录报告 Modal ================= -->
    <div v-if="showDetailModal" class="modal-backdrop">
      <div class="modal-content glass-card wide-modal">
        <div class="modal-header">
          <div>
            <h3>📄 风险研判深度分析详情</h3>
            <span class="text-secondary text-sm">{{ selectedRecord?.news_title }}</span>
          </div>
          <button class="close-btn" @click="showDetailModal = false">×</button>
        </div>
        <div class="modal-body" v-if="selectedRecord">
          <div class="detail-hero mb-3">
            <span class="level-pill" :class="'level-' + selectedRecord.level">{{ selectedRecord.level_name }}</span>
            <span class="lead-pill ml-2">变盘窗口: {{ selectedRecord.lead_time }}</span>
            <span class="score-tag ml-auto" :class="scoreColorClass(selectedRecord.score)">
              得分: {{ selectedRecord.score }} 分
            </span>
          </div>

          <div class="detail-meta text-secondary text-sm mb-3">
            <div><strong>新闻来源:</strong> {{ selectedRecord.news_source || '-' }}</div>
            <div><strong>研判模型:</strong> {{ selectedRecord.model_name }} ({{ selectedRecord.model_id }})</div>
            <div><strong>评估时间:</strong> {{ selectedRecord.created_at?.replace('T', ' ') }}</div>
          </div>

          <div class="action-guide-box mb-3" v-if="selectedRecord.action_guide?.length">
            <div class="ag-header">🛡️ 实操避险法则:</div>
            <ul>
              <li v-for="(act, i) in selectedRecord.action_guide" :key="i">{{ act }}</li>
            </ul>
          </div>

          <div class="report-box">
            <div class="report-header">完整分析报告文本:</div>
            <div class="report-text" style="white-space: pre-wrap;">{{ selectedRecord.analysis_report }}</div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-glass" @click="pushRecordToWx(selectedRecord.id)">
            📤 推送企业微信
          </button>
          <button class="btn btn-primary" @click="showDetailModal = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, inject, watch, nextTick, markRaw } from 'vue'
import * as echarts from 'echarts'
import api from '../api'

const showToast = inject('showToast', (msg) => alert(msg))

// 状态
const loadingAll = ref(false)
const activeTab = ref('manual') // 'manual', 'crawl', 'models', 'history', 'daily_tracking'

// 顶部最新记录与大盘
const latestRecord = ref(null)
const marketContext = ref(null)
const cronEnabled = ref(true)
const cronTime = ref('20:30')

// 模型列表
const models = ref([])

// 手动分析表单
const analyzing = ref(false)
const manualResult = ref(null)
const mediaQuickList = [
  '央视《新闻联播》',
  '《人民日报》头版',
  '《经济日报》特评',
  '新华社权威发布',
  '全网热搜/弹窗前3',
  '主流财经媒体'
]
const manualForm = ref({
  news_title: '',
  news_source: '央视《新闻联播》',
  news_time: '',
  news_content: '',
  model_id: 'om_stw',
  push_to_wx: true
})

// 官媒要闻列表
const loadingNews = ref(false)
const crawling = ref(false)
const officialNewsList = ref([])

// 历史记录
const loadingHistory = ref(false)
const historyRecords = ref([])
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = ref(15)
const selectedLevelFilter = ref('')
const levelFilters = [
  { label: '全部', value: '' },
  { label: '🔴 红色预警', value: 'red' },
  { label: '🟠 橙色预警', value: 'orange' },
  { label: '🟡 黄色注意', value: 'yellow' },
  { label: '🟢 绿色安全', value: 'green' }
]

// 每日开盘预警与收盘对照状态
const loadingDaily = ref(false)
const dailyRecords = ref([])
const dailyAnalytics = ref(null)
const loadingAnalytics = ref(false)
const snapshotingPre = ref(false)
const syncingClose = ref(false)
const calibratingHistory = ref(false)
const showDailyDetailModal = ref(false)

const selectedDailyRecord = ref(null)

// 快捷时间范围
const quickRanges = [
  { label: '近 1 周', key: '1w', days: 7 },
  { label: '近 1 月', key: '1m', days: 30 },
  { label: '近 3 月', key: '3m', days: 90 },
  { label: '近半年', key: '6m', days: 180 },
  { label: '全部', key: 'all', days: 0 }
]
const selectedRangeKey = ref('1m')
const filterStartDate = ref('')
const filterEndDate = ref('')

// 对照指数
const indexOptions = [
  { name: '上证指数', code: 'sh000001', closeKey: 'sh_close', chgKey: 'sh_change_pct' },
  { name: '深证成指', code: 'sz399001', closeKey: 'sz_close', chgKey: 'sz_change_pct' },
  { name: '创业板指', code: 'sz399006', closeKey: 'cy_close', chgKey: 'cy_change_pct' },
  { name: '科创50', code: 'sh000688', closeKey: 'kc_close', chgKey: 'kc_change_pct' },
  { name: '沪深300', code: 'sh000300', closeKey: 'hs300_close', chgKey: 'hs300_change_pct' }
]
const selectedIndexCode = ref('sh000001')
const selectedIndexObj = computed(() => {
  return indexOptions.find(i => i.code === selectedIndexCode.value) || indexOptions[0]
})

// 图表 DOM 引用与实例
const combinedChartRef = ref(null)
const attributionPieChartRef = ref(null)
const tierBarChartRef = ref(null)

let combinedChartInstance = null
let attributionPieChartInstance = null
let tierBarChartInstance = null

// 弹窗状态
const showEditModelModal = ref(false)
const currentEditingModel = ref(null)
const showCreateModelModal = ref(false)
const newModelForm = ref({
  model_id: '',
  name: '',
  version: 'v1.0',
  description: '',
  system_prompt: '',
  prompt_template: '',
  alert_threshold: 60
})
const showDetailModal = ref(false)
const selectedRecord = ref(null)

// 计算属性
const heroCardClass = computed(() => {
  if (!latestRecord.value) return 'border-green'
  return 'border-' + latestRecord.value.level
})

const scoreColorClass = (score) => {
  if (score >= 75) return 'text-red'
  if (score >= 60) return 'text-yellow'
  return 'text-green'
}

const triggerTypeLabel = (type) => {
  if (type === 'manual_input') return '✍️ 手工录入'
  if (type === 'manual_crawl') return '🌐 在线抓取'
  if (type === 'scheduled') return '⏰ 20:30定时'
  return type
}

const dailyStats = computed(() => {
  const list = dailyRecords.value || []
  const total = list.length
  const warningItems = list.filter(r => (r.pre_market_score || 0) >= 60)
  const warningCount = warningItems.length
  const hitItems = warningItems.filter(r => {
    const status = r.validation_status || ''
    return status.includes('命中') || (r.sh_change_pct != null && r.sh_change_pct < 0)
  })
  const winRate = warningCount > 0 ? Math.round((hitItems.length / warningCount) * 100) : 100
  return {
    total,
    warningCount,
    winRate
  }
})

const getValidationBadgeClass = (status) => {
  if (!status) return 'badge-neutral'
  if (status.includes('命中')) return 'badge-hit'
  if (status.includes('常态') || status.includes('符合')) return 'badge-normal'
  if (status.includes('观察') || status.includes('博弈')) return 'badge-watch'
  if (status.includes('超跌')) return 'badge-alert'
  return 'badge-neutral'
}

// 刷新全量数据
const refreshAll = async () => {
  loadingAll.value = true
  try {
    await Promise.all([
      fetchLatestRecord(),
      fetchMarketContext(),
      fetchModels(),
      fetchSettings(),
      fetchOfficialNews(),
      fetchHistoryRecords(1),
      fetchDailyDataAndAnalytics()
    ])
    showToast('风控数据与行情指标已同步刷新')
  } catch (e) {
    console.error(e)
    showToast('刷新数据失败: ' + e.message)
  } finally {
    loadingAll.value = false
  }
}

// 获取最新记录
const fetchLatestRecord = async () => {
  try {
    const res = await api.getLatestRiskRecord()
    latestRecord.value = res
  } catch (e) {
    console.error('Fetch latest risk record failed:', e)
  }
}

// 获取大盘上下文
const fetchMarketContext = async () => {
  try {
    marketContext.value = await api.getRiskMarketContext()
  } catch (e) {
    console.error('Fetch market context failed:', e)
  }
}

// 获取模型
const fetchModels = async () => {
  try {
    models.value = await api.getRiskModels()
    if (models.value.length && !manualForm.value.model_id) {
      manualForm.value.model_id = models.value[0].model_id
    }
  } catch (e) {
    console.error('Fetch models failed:', e)
  }
}

// 获取系统配置中的定时任务状态
const fetchSettings = async () => {
  try {
    const s = await api.getSettings()
    if (s) {
      cronEnabled.value = s.risk_cron_enabled !== false
      cronTime.value = s.risk_cron_time || '20:30'
    }
  } catch (e) {
    console.error('Fetch settings failed:', e)
  }
}

// 获取官媒要闻
const fetchOfficialNews = async () => {
  loadingNews.value = true
  try {
    officialNewsList.value = await api.getRiskOfficialNews(15)
  } catch (e) {
    console.error('Fetch official news failed:', e)
  } finally {
    loadingNews.value = false
  }
}

// 获取历史记录
const fetchHistoryRecords = async (page = 1) => {
  loadingHistory.value = true
  historyPage.value = page
  try {
    const res = await api.getRiskRecords(page, historyPageSize.value, selectedLevelFilter.value)
    historyRecords.value = res.items || []
    historyTotal.value = res.total || 0
  } catch (e) {
    console.error('Fetch history failed:', e)
  } finally {
    loadingHistory.value = false
  }
}

// 手动提交分析
const submitManualAnalysis = async () => {
  if (!manualForm.value.news_title) {
    showToast('请输入新闻标题')
    return
  }
  analyzing.value = true
  try {
    const res = await api.analyzeManualNews(manualForm.value)
    manualResult.value = res
    latestRecord.value = res
    showToast(`研判完成: ${res.level_name} (${res.score}分)`)
    fetchHistoryRecords(1)
  } catch (e) {
    console.error(e)
    showToast('研判异常: ' + (e.response?.data?.detail || e.message))
  } finally {
    analyzing.value = false
  }
}

// 填入经典案例
const fillSampleNews = () => {
  manualForm.value = {
    news_title: '《经济日报》头版评论：让居民通过股票、基金也能赚到钱',
    news_source: '《经济日报》头版/特评',
    news_time: new Date().toISOString().substring(0, 10),
    news_content: '重磅评论指出活跃资本市场对于提振居民消费能力与财产性收入至关重要，全网媒体争相头条转发。盘面上大盘高位连续拔葱，次日早盘高开冲高后迅速回落，主力资金呈现巨量大单净流出。',
    model_id: 'om_stw',
    push_to_wx: true
  }
  showToast('已填入经典官媒唱多案例')
}

// 点击官媒新闻快速进入分析
const useNewsForManual = (item) => {
  manualForm.value.news_title = item.title
  manualForm.value.news_source = item.source || '权威官媒'
  manualForm.value.news_time = item.time || ''
  manualForm.value.news_content = item.content || item.title
  activeTab.value = 'manual'
  showToast('已将新闻载入分析台')
}

// 在线抓取并分析
const triggerCrawlAnalysis = async () => {
  crawling.value = true
  try {
    const res = await api.analyzeCrawlNews({ model_id: 'om_stw', push_to_wx: true })
    latestRecord.value = res
    manualResult.value = res
    showToast(`抓取分析完成: ${res.level_name} (${res.score}分)`)
    fetchHistoryRecords(1)
  } catch (e) {
    console.error(e)
    showToast('全网抓取分析失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    crawling.value = false
  }
}

// 推送记录到企业微信
const pushRecordToWx = async (recordId) => {
  try {
    const res = await api.pushRiskRecordToWx(recordId)
    if (res.success) {
      showToast('已成功推送到企业微信！')
      fetchHistoryRecords(historyPage.value)
    } else {
      showToast('推送失败: ' + res.message)
    }
  } catch (e) {
    showToast('推送异常: ' + e.message)
  }
}

// 删除记录
const deleteRecord = async (recordId) => {
  if (!confirm('确认删除该条研判记录？')) return
  try {
    await api.deleteRiskRecord(recordId)
    showToast('记录已删除')
    fetchHistoryRecords(historyPage.value)
  } catch (e) {
    showToast('删除失败: ' + e.message)
  }
}

// 查看记录详情
const openRecordDetailModal = (rec) => {
  selectedRecord.value = rec
  showDetailModal.value = true
}

// 打开编辑模型弹窗
const openEditModelModal = (m) => {
  currentEditingModel.value = JSON.parse(JSON.stringify(m))
  showEditModelModal.value = true
}

// 保存打磨模型
const saveEditedModel = async () => {
  if (!currentEditingModel.value) return
  try {
    await api.updateRiskModel(currentEditingModel.value.model_id, {
      name: currentEditingModel.value.name,
      version: currentEditingModel.value.version,
      description: currentEditingModel.value.description,
      system_prompt: currentEditingModel.value.system_prompt,
      prompt_template: currentEditingModel.value.prompt_template,
      alert_threshold: currentEditingModel.value.alert_threshold
    })
    showToast('模型配置与提示词已保存更新！')
    showEditModelModal.value = false
    fetchModels()
  } catch (e) {
    showToast('保存模型失败: ' + e.message)
  }
}

// 打开创建模型弹窗
const openCreateModelModal = () => {
  newModelForm.value = {
    model_id: '',
    name: '',
    version: 'v1.0',
    description: '',
    system_prompt: '你是一位资深的证券风控分析专家。',
    prompt_template: '请分析新闻：{news_title}\n来源：{news_source}\n市场背景：{market_context}',
    alert_threshold: 60
  }
  showCreateModelModal.value = true
}

// 提交创建模型
const submitCreateModel = async () => {
  if (!newModelForm.value.model_id || !newModelForm.value.name || !newModelForm.value.prompt_template) {
    showToast('请完整填写模型 ID、名称与提示词模板')
    return
  }
  try {
    await api.createRiskModel(newModelForm.value)
    showToast('自定义模型创建成功！')
    showCreateModelModal.value = false
    fetchModels()
  } catch (e) {
    showToast('创建模型失败: ' + (e.response?.data?.detail || e.message))
  }
}

// 删除模型
const deleteModel = async (modelId) => {
  if (!confirm(`确认删除模型 '${modelId}'？`)) return
  try {
    await api.deleteRiskModel(modelId)
    showToast('模型已删除')
    fetchModels()
  } catch (e) {
    showToast('删除失败: ' + (e.response?.data?.detail || e.message))
  }
}

// 格式化日期为 YYYY-MM-DD
const formatDateStr = (d) => {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// 获取每日对照记录及量化关联度统计
const fetchDailyDataAndAnalytics = async () => {
  loadingDaily.value = true
  loadingAnalytics.value = true
  try {
    const [records, analytics] = await Promise.all([
      api.getDailyRiskRecords(200, filterStartDate.value, filterEndDate.value),
      api.getDailyRiskAnalytics(filterStartDate.value, filterEndDate.value)
    ])
    dailyRecords.value = records || []
    dailyAnalytics.value = analytics || null
    await nextTick()
    renderAllCharts()
  } catch (e) {
    console.error('Fetch daily data and analytics failed:', e)
  } finally {
    loadingDaily.value = false
    loadingAnalytics.value = false
  }
}

// 快捷区间切换
const applyQuickRange = (key) => {
  selectedRangeKey.value = key
  const range = quickRanges.find(r => r.key === key)
  if (!range || range.days === 0) {
    filterStartDate.value = ''
    filterEndDate.value = ''
  } else {
    const end = new Date()
    const start = new Date(end.getTime() - range.days * 86400000)
    filterStartDate.value = formatDateStr(start)
    filterEndDate.value = formatDateStr(end)
  }
  fetchDailyDataAndAnalytics()
}

// 自定义日期起止筛选
const applyCustomDateRange = () => {
  selectedRangeKey.value = 'custom'
  fetchDailyDataAndAnalytics()
}

// 重置日期
const resetDateRange = () => {
  applyQuickRange('1m')
}

// 立即快照今日开盘前预警
const triggerSnapshotPreMarket = async () => {
  snapshotingPre.value = true
  try {
    const res = await api.snapshotPreMarketRisk()
    showToast(`今日开盘前风险快照已生成：${res.pre_market_level_name} (${res.pre_market_score}分)`)
    await fetchDailyDataAndAnalytics()
  } catch (e) {
    console.error(e)
    showToast('生成开盘前快照失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    snapshotingPre.value = false
  }
}

// 立即同步今日各核心指数收盘点数
const triggerSyncCloseIndices = async () => {
  syncingClose.value = true
  try {
    const res = await api.syncCloseIndices()
    showToast(`今日各核心指数收盘点数已同步：${res.validation_status}`)
    await fetchDailyDataAndAnalytics()
  } catch (e) {
    console.error(e)
    showToast('同步收盘点数失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    syncingClose.value = false
  }
}

// 触发校准历史各大盘指数真实点位
const triggerCalibrateHistory = async () => {
  calibratingHistory.value = true
  try {
    const res = await api.calibrateHistoryMarketRecords(120)
    showToast(res.message || '历史真实各大盘指数点位已成功校准！')
    await fetchDailyDataAndAnalytics()
  } catch (e) {
    console.error(e)
    showToast('校准历史数据失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    calibratingHistory.value = false
  }
}


// 打开每日对照明细弹窗
const openDailyDetail = (item) => {
  selectedDailyRecord.value = item
  showDailyDetailModal.value = true
}

// 初始化图表实例
const initCharts = () => {
  if (combinedChartRef.value && !combinedChartInstance) {
    combinedChartInstance = markRaw(echarts.init(combinedChartRef.value))
  }
  if (attributionPieChartRef.value && !attributionPieChartInstance) {
    attributionPieChartInstance = markRaw(echarts.init(attributionPieChartRef.value))
  }
  if (tierBarChartRef.value && !tierBarChartInstance) {
    tierBarChartInstance = markRaw(echarts.init(tierBarChartRef.value))
  }
}

// 渲染多轴复合走势大图
const renderCombinedChart = () => {
  if (!combinedChartRef.value) return
  if (!combinedChartInstance) {
    combinedChartInstance = markRaw(echarts.init(combinedChartRef.value))
  }

  const recordsAsc = [...dailyRecords.value].sort((a, b) => a.trade_date.localeCompare(b.trade_date))
  const dates = recordsAsc.map(r => r.trade_date)
  const scores = recordsAsc.map(r => r.pre_market_score ?? 30)

  const idxObj = selectedIndexObj.value
  const indexKey = idxObj.closeKey
  const indexChgKey = idxObj.chgKey
  const indexCloses = recordsAsc.map(r => {
    if (r[indexKey] != null && r[indexKey] > 0) return r[indexKey]
    if (r.indices_data && r.indices_data[idxObj.code]) {
      return r.indices_data[idxObj.code].current || null
    }
    return null
  })

  // 预警 MarkPoint
  const markPoints = []
  recordsAsc.forEach(r => {
    const ptVal = r[indexKey] || (r.indices_data && r.indices_data[idxObj.code]?.current) || null
    if ((r.pre_market_score || 0) >= 60 && ptVal != null) {
      markPoints.push({
        name: r.pre_market_level_name || '预警',
        coord: [r.trade_date, ptVal],
        value: `${r.pre_market_score}分`,
        itemStyle: {
          color: (r.pre_market_score || 0) >= 75 ? '#ff4444' : '#fbbf24'
        }
      })
    }
  })

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(26, 29, 46, 0.95)',
      borderColor: 'rgba(0, 212, 255, 0.3)',
      borderWidth: 1,
      textStyle: { color: '#fff' },
      formatter: (params) => {
        if (!params || !params.length) return ''
        const date = params[0].axisValue
        const rec = recordsAsc.find(r => r.trade_date === date) || {}
        const ptVal = rec[indexKey] != null ? rec[indexKey] : (rec.indices_data && rec.indices_data[idxObj.code]?.current)
        const closeVal = ptVal != null ? Number(ptVal).toFixed(2) : '--'
        const chgPt = rec[indexChgKey] != null ? rec[indexChgKey] : (rec.indices_data && rec.indices_data[idxObj.code]?.change_pct)
        const chgVal = chgPt != null ? `${chgPt >= 0 ? '+' : ''}${Number(chgPt).toFixed(2)}%` : '--'
        const chgColor = (chgPt || 0) >= 0 ? '#ff6b6b' : '#00ff88'
        const score = rec.pre_market_score ?? '--'
        const levelName = rec.pre_market_level_name || '安全'
        const news = rec.news_title || '常态宏观走势'
        return `
          <div style="font-weight: bold; margin-bottom: 6px; font-family: monospace;">📅 ${date}</div>
          <div style="margin-bottom: 4px;">📈 ${idxObj.name}: <strong>${closeVal}</strong> (<span style="color: ${chgColor}; font-weight: bold;">${chgVal}</span>)</div>
          <div style="margin-bottom: 4px;">🚨 开盘前预警: <strong>${score}分</strong> (${levelName})</div>
          <div style="font-size: 12px; color: #94a3b8; max-width: 280px; line-height: 1.4;">📰 诱因: ${news}</div>
        `
      }
    },

    legend: {
      data: [idxObj.name, '开盘前风控分值'],
      textStyle: { color: '#94a3b8' },
      top: 4,
      right: 20
    },
    grid: {
      left: '3%',
      right: '4%',
      top: '14%',
      bottom: '18%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.15)' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 }
    },
    yAxis: [
      {
        type: 'value',
        name: `${idxObj.name} (点位)`,
        scale: true,
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
        axisLabel: { color: '#94a3b8', fontSize: 11 },
        nameTextStyle: { color: '#94a3b8' }
      },
      {
        type: 'value',
        name: '风控分值 (0-100)',
        min: 0,
        max: 100,
        interval: 20,
        splitLine: { show: false },
        axisLabel: { color: '#94a3b8', fontSize: 11 },
        nameTextStyle: { color: '#94a3b8' }
      }
    ],
    dataZoom: [
      {
        type: 'slider',
        show: true,
        start: 0,
        end: 100,
        height: 20,
        bottom: 4,
        borderColor: 'transparent',
        backgroundColor: 'rgba(255, 255, 255, 0.04)',
        fillerColor: 'rgba(0, 212, 255, 0.2)',
        textStyle: { color: '#94a3b8' }
      },
      {
        type: 'inside'
      }
    ],
    series: [
      {
        name: idxObj.name,
        type: 'line',
        yAxisIndex: 0,
        data: indexCloses,
        smooth: true,
        showSymbol: false,
        itemStyle: { color: '#00d4ff' },
        lineStyle: { width: 2.5 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 212, 255, 0.35)' },
            { offset: 1, color: 'rgba(0, 212, 255, 0.02)' }
          ])
        }
      },
      {
        name: '开盘前风控分值',
        type: 'line',
        yAxisIndex: 1,
        data: scores,
        smooth: true,
        symbolSize: 6,
        itemStyle: { color: '#ff6b6b' },
        lineStyle: { width: 2, type: 'dashed' },
        markLine: {
          symbol: 'none',
          data: [
            {
              yAxis: 60,
              lineStyle: { color: '#fbbf24', type: 'dashed', width: 1.5 },
              label: { formatter: '60分 橙色预警', color: '#fbbf24', position: 'insideEndTop' }
            },
            {
              yAxis: 75,
              lineStyle: { color: '#ff4444', type: 'solid', width: 2 },
              label: { formatter: '75分 绝壁顶', color: '#ff4444', position: 'insideEndTop' }
            }
          ]
        },
        markPoint: {
          data: markPoints
        }
      }
    ]
  }
  combinedChartInstance.setOption(option, true)
}

// 渲染归因准确度环形图
const renderAttributionPieChart = () => {
  if (!attributionPieChartRef.value) return
  if (!attributionPieChartInstance) {
    attributionPieChartInstance = markRaw(echarts.init(attributionPieChartRef.value))
  }

  const attrData = dailyAnalytics.value?.attribution_counts || {}
  const pieData = [
    { name: '🎯 预警命中 (大盘收跌)', value: attrData.hit || 0, itemStyle: { color: '#ff6b6b' } },
    { name: '🟢 常态平稳 (符合预期)', value: attrData.normal || 0, itemStyle: { color: '#00ff88' } },
    { name: '⏳ 变盘观察期 (多空博弈)', value: attrData.watch || 0, itemStyle: { color: '#fbbf24' } },
    { name: '⚡ 外部突发超跌', value: attrData.outlier || 0, itemStyle: { color: '#c084fc' } }
  ]

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(26, 29, 46, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.2)',
      textStyle: { color: '#fff' },
      formatter: '{b}: <strong>{c}天</strong> ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: '4%',
      top: 'center',
      textStyle: { color: '#94a3b8', fontSize: 11 },
      itemGap: 10
    },
    series: [
      {
        name: '归因验证',
        type: 'pie',
        radius: ['45%', '72%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#1a1d2e',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 13,
            fontWeight: 'bold',
            color: '#fff',
            formatter: '{b}\n{d}%'
          }
        },
        data: pieData
      }
    ]
  }
  attributionPieChartInstance.setOption(option, true)
}

// 渲染分级平均收益柱状图
const renderTierBarChart = () => {
  if (!tierBarChartRef.value) return
  if (!tierBarChartInstance) {
    tierBarChartInstance = markRaw(echarts.init(tierBarChartRef.value))
  }

  const tiers = dailyAnalytics.value?.tier_stats || {}
  const categories = ['🔴 绝壁顶 (≥75)', '🟠 阶段顶 (60-74)', '🟡 分歧期 (40-59)', '🟢 安全期 (<40)']
  const values = [
    tiers.red?.avg_return ?? -1.69,
    tiers.orange?.avg_return ?? -0.39,
    tiers.yellow?.avg_return ?? -0.11,
    tiers.green?.avg_return ?? 0.33
  ]

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(26, 29, 46, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.2)',
      textStyle: { color: '#fff' },
      formatter: (params) => {
        const p = params[0]
        const val = p.value
        const color = val >= 0 ? '#ff6b6b' : '#00ff88'
        return `<div>${p.name}</div><div>平均大盘表现: <strong style="color:${color}">${val >= 0 ? '+' : ''}${val}%</strong></div>`
      }
    },
    grid: {
      left: '4%',
      right: '6%',
      top: '14%',
      bottom: '12%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.15)' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      name: '平均大盘涨跌幅 (%)',
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
      axisLabel: {
        color: '#94a3b8',
        formatter: '{value}%'
      },
      nameTextStyle: { color: '#94a3b8' }
    },
    series: [
      {
        name: '平均大盘涨跌幅',
        type: 'bar',
        barWidth: '38%',
        data: values.map(v => ({
          value: v,
          itemStyle: {
            color: v >= 0 ? '#ff6b6b' : '#00ff88',
            borderRadius: v >= 0 ? [6, 6, 0, 0] : [0, 0, 6, 6]
          }
        })),
        label: {
          show: true,
          position: 'top',
          formatter: (p) => `${p.value >= 0 ? '+' : ''}${p.value}%`,
          color: '#fff',
          fontSize: 11
        }
      }
    ]
  }
  tierBarChartInstance.setOption(option, true)
}

// 统一渲染全部图表
const renderAllCharts = () => {
  renderCombinedChart()
  renderAttributionPieChart()
  renderTierBarChart()
}

// 窗口尺寸自适应
const handleResize = () => {
  combinedChartInstance?.resize()
  attributionPieChartInstance?.resize()
  tierBarChartInstance?.resize()
}

// 监听指数切换
watch(selectedIndexCode, () => {
  renderCombinedChart()
})

// 监听 Tab 切换到每日对照
watch(activeTab, (newTab) => {
  if (newTab === 'daily_tracking') {
    nextTick(() => {
      initCharts()
      renderAllCharts()
    })
  }
})

onMounted(() => {
  applyQuickRange('1m')
  refreshAll()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  combinedChartInstance?.dispose()
  attributionPieChartInstance?.dispose()
  tierBarChartInstance?.dispose()
})
</script>

<style scoped>
.risk-warning-page {
  animation: fadeIn 0.3s ease-in-out;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  gap: 16px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.35;
  margin-bottom: 6px;
  letter-spacing: 0.3px;
}

.header p {
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--text-secondary);
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.cron-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  padding: 7px 16px;
  border-radius: 20px;
  font-size: 0.85rem;
  line-height: 1.4;
  color: var(--text-primary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 8px var(--green);
}

/* 顶部风险预警英雄卡 */
.risk-hero-card {
  padding: 24px 28px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
  margin-bottom: 24px;
}

.border-red {
  border-color: rgba(255, 68, 68, 0.4) !important;
  background: linear-gradient(135deg, rgba(255, 68, 68, 0.08) 0%, rgba(26, 29, 46, 0.95) 100%) !important;
}

.border-orange {
  border-color: rgba(251, 191, 36, 0.4) !important;
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.08) 0%, rgba(26, 29, 46, 0.95) 100%) !important;
}

.border-yellow {
  border-color: rgba(251, 191, 36, 0.3) !important;
}

.border-green {
  border-color: rgba(0, 255, 136, 0.25) !important;
}

.hero-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.hero-badge-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.hero-level-badge {
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: 0.3px;
  line-height: 1.4;
  display: inline-flex;
  align-items: center;
}

.level-red {
  background: rgba(255, 68, 68, 0.25);
  color: #ff5555;
  border: 1px solid #ff4444;
}

.level-orange {
  background: rgba(251, 191, 36, 0.25);
  color: #fbbf24;
  border: 1px solid #fbbf24;
}

.level-yellow {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.4);
}

.level-green {
  background: rgba(0, 255, 136, 0.2);
  color: #00ff88;
  border: 1px solid #00ff88;
}

.hero-time-tag {
  background: var(--bg-glass);
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 0.86rem;
  line-height: 1.4;
  border: 1px solid var(--border-glass);
  display: inline-flex;
  align-items: center;
}

.hero-source-tag {
  color: var(--text-secondary);
  font-size: 0.88rem;
  line-height: 1.5;
  max-width: 520px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hero-score-box {
  text-align: right;
}

.score-num {
  font-size: 2.5rem;
  font-weight: 800;
  line-height: 1;
  margin-bottom: 2px;
}

.score-label {
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-top: 4px;
  line-height: 1.2;
}

.hero-actions-row {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.action-lead {
  font-size: 0.88rem;
  color: var(--accent-primary);
  font-weight: 600;
  line-height: 1.4;
}

.action-tags {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.action-tag {
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.3);
  color: var(--text-primary);
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 0.84rem;
  line-height: 1.4;
}

.hero-footer-row {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px dashed var(--border-glass);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.market-quick-ticker {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.86rem;
  line-height: 1.6;
  color: var(--text-secondary);
  flex-wrap: wrap;
}

.market-quick-ticker strong {
  color: var(--text-primary);
}

.market-quick-ticker .divider {
  opacity: 0.4;
}

.market-pos-tag {
  background: var(--bg-glass);
  padding: 3px 10px;
  border-radius: 6px;
  color: var(--accent-primary);
  font-size: 0.82rem;
  line-height: 1.35;
  border: 1px solid rgba(0, 212, 255, 0.2);
}

.hero-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* Tabs */
.tabs-nav {
  display: flex;
  gap: 12px;
  border-bottom: 1px solid var(--border-glass);
  padding-bottom: 12px;
  margin-bottom: 24px;
  overflow-x: auto;
}

.tab-btn {
  padding: 10px 22px;
  border-radius: 8px;
  background: var(--bg-glass);
  border: 1px solid transparent;
  color: var(--text-secondary);
  font-size: 0.92rem;
  line-height: 1.4;
  font-weight: 500;
  letter-spacing: 0.2px;
  transition: all 0.25s ease;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-primary);
}

.tab-btn.active {
  background: var(--accent-primary);
  color: #0f1117;
  font-weight: 600;
  box-shadow: 0 0 16px rgba(0, 212, 255, 0.35);
}

/* 布局与表单 */
.grid-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

@media (max-width: 960px) {
  .grid-2col {
    grid-template-columns: 1fr;
  }
}

.card-title {
  font-size: 1.18rem;
  font-weight: 600;
  line-height: 1.4;
  margin-bottom: 8px;
}

.card-subtitle {
  font-size: 0.98rem;
  font-weight: 600;
  line-height: 1.45;
  margin-bottom: 12px;
}

.form-group {
  margin-bottom: 18px;
}

.form-group label {
  display: block;
  font-size: 0.88rem;
  font-weight: 500;
  line-height: 1.4;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.form-control {
  width: 100%;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-control:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.15);
}

textarea.form-control {
  padding: 12px 14px;
  line-height: 1.65;
  min-height: 110px;
}

.form-row {
  display: flex;
  gap: 16px;
}

.flex-1 { flex: 1; }
.flex-2 { flex: 2; }

.media-quick-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.media-quick-tags .btn-xs {
  padding: 5px 12px;
  font-size: 0.78rem;
  line-height: 1.35;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.media-quick-tags .btn-xs.active {
  background: rgba(0, 212, 255, 0.2);
  border-color: var(--accent-primary);
  color: var(--accent-primary);
  font-weight: 600;
}

.btn-xs {
  padding: 4px 10px;
  font-size: 0.76rem;
  line-height: 1.3;
}

.btn-sm {
  padding: 6px 14px;
  font-size: 0.82rem;
  line-height: 1.35;
}

.btn-lg {
  padding: 12px 26px;
  font-size: 0.96rem;
  line-height: 1.4;
  font-weight: 600;
}

.checkbox-row {
  margin-top: 14px;
  margin-bottom: 8px;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 0.88rem;
  line-height: 1.5;
  color: var(--text-secondary);
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.form-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 24px;
  flex-wrap: wrap;
}

.market-metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 12px;
}

.metric-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-glass);
  padding: 10px 12px;
  border-radius: 8px;
  text-align: center;
  transition: background-color 0.2s ease;
}

.metric-label {
  font-size: 0.78rem;
  line-height: 1.4;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.metric-val {
  font-size: 1.1rem;
  font-weight: 700;
  line-height: 1.3;
}

.market-context-desc {
  font-size: 0.85rem;
  line-height: 1.65;
  color: var(--text-secondary);
  background: rgba(0, 0, 0, 0.25);
  padding: 12px 16px;
  border-radius: 8px;
  margin-top: 14px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

/* 官媒要闻网格 */
.news-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 20px;
  margin-top: 18px;
}

.news-card {
  padding: 20px 22px;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: transform 0.2s ease, border-color 0.2s ease;
}

.news-card:hover {
  transform: translateY(-2px);
  border-color: rgba(0, 212, 255, 0.3);
}

.news-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  font-size: 0.8rem;
  line-height: 1.4;
  margin-bottom: 12px;
}

.media-tag {
  background: var(--bg-glass);
  padding: 4px 10px;
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 0.78rem;
  line-height: 1.3;
}

.official-tag {
  background: rgba(0, 212, 255, 0.15);
  color: var(--accent-primary);
  border: 1px solid rgba(0, 212, 255, 0.35);
  font-weight: 500;
}

.news-title {
  font-size: 1.02rem;
  font-weight: 600;
  line-height: 1.55;
  margin: 0 0 10px 0;
  color: #f8fafc;
}

.news-content-snippet {
  font-size: 0.86rem;
  color: #94a3b8;
  line-height: 1.7;
  flex: 1;
  margin-bottom: 16px;
}

.news-card-footer {
  margin-top: auto;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 模型列表 */
.models-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 22px;
  margin-top: 18px;
}

.model-card {
  padding: 22px 24px;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.model-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.model-name {
  font-size: 1.08rem;
  font-weight: 600;
  line-height: 1.4;
}

.model-version-tag {
  background: var(--bg-glass);
  font-size: 0.75rem;
  padding: 3px 8px;
  border-radius: 4px;
  margin-left: 8px;
  border: 1px solid var(--border-glass);
}

.badge-default {
  background: rgba(0, 255, 136, 0.15);
  color: var(--green);
  border: 1px solid rgba(0, 255, 136, 0.3);
  font-size: 0.74rem;
  padding: 3px 8px;
  border-radius: 4px;
  margin-left: 8px;
  font-weight: 600;
}

.model-threshold {
  font-size: 0.84rem;
  color: var(--text-secondary);
}

.model-threshold strong {
  color: var(--accent-primary);
}

.model-card > p {
  font-size: 0.88rem;
  line-height: 1.65;
  color: var(--text-secondary);
  margin: 0 0 16px 0;
}

.model-details-box {
  background: rgba(0, 0, 0, 0.25);
  border-radius: 8px;
  padding: 12px 14px;
  font-size: 0.84rem;
  margin-bottom: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.prop-row {
  margin-bottom: 8px;
  line-height: 1.6;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.prop-row:last-child {
  margin-bottom: 0;
}

.prop-label {
  color: var(--text-secondary);
  flex-shrink: 0;
  min-width: 72px;
}

.model-actions-row {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  align-items: center;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  margin-top: auto;
}

/* 历史记录 */
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  padding: 16px 20px;
  margin-bottom: 20px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.88rem;
  line-height: 1.4;
}

.records-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.record-card {
  padding: 20px 24px;
  border-radius: 10px;
}

.rec-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.rec-badges {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.trigger-pill, .model-pill, .wx-pill {
  font-size: 0.76rem;
  line-height: 1.35;
  background: var(--bg-glass);
  padding: 3px 8px;
  border-radius: 4px;
  color: var(--text-secondary);
  border: 1px solid var(--border-glass);
}

.wx-pill {
  color: var(--green);
  border: 1px solid rgba(0, 255, 136, 0.3);
  background: rgba(0, 255, 136, 0.1);
}

.rec-score-box {
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.2;
}

.rec-title {
  font-size: 1.02rem;
  font-weight: 600;
  line-height: 1.5;
  margin: 0 0 8px 0;
  color: #f8fafc;
}

.rec-meta {
  font-size: 0.84rem;
  line-height: 1.6;
  color: var(--text-secondary);
  margin-bottom: 10px;
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.rec-summary {
  font-size: 0.86rem;
  line-height: 1.7;
  color: #cbd5e1;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.25);
  border-radius: 6px;
  margin-bottom: 14px;
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.rec-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  align-items: center;
}

.pagination-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 18px;
  margin-top: 28px;
  font-size: 0.92rem;
}

/* 模态框 */
.modal-backdrop {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(6px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 999;
  padding: 24px 16px;
}

.modal-content {
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  padding: 26px 30px;
  border-radius: 14px;
  line-height: 1.6;
}

.wide-modal {
  max-width: 780px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-glass);
  padding-bottom: 14px;
  margin-bottom: 20px;
}

.modal-header h3 {
  font-size: 1.2rem;
  font-weight: 600;
  line-height: 1.4;
  margin: 0;
}

.close-btn {
  font-size: 1.5rem;
  color: var(--text-secondary);
  line-height: 1;
  transition: color 0.2s ease;
}

.close-btn:hover {
  color: var(--text-primary);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  border-top: 1px solid var(--border-glass);
  padding-top: 18px;
  margin-top: 22px;
}

.code-font {
  font-family: 'Fira Code', monospace;
  font-size: 0.84rem;
  line-height: 1.55;
}

.truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
  vertical-align: bottom;
  max-width: 280px;
}

.spinner-small {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #fff;
  animation: spin 0.8s linear infinite;
  margin-right: 6px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ================= Tab 5: 每日开盘预警与收盘对照样式 ================= */
.daily-summary-card {
  padding: 24px 28px;
}

.daily-summary-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  flex-wrap: wrap;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--border-glass);
}

.daily-summary-header .card-title {
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.4;
  margin-bottom: 6px;
}

.daily-summary-header p {
  line-height: 1.6;
  margin: 0;
}

.daily-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.daily-kpi-grid .kpi-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.daily-kpi-grid .kpi-label {
  font-size: 0.82rem;
  color: var(--text-secondary);
  margin-bottom: 6px;
  line-height: 1.4;
}

.daily-kpi-grid .kpi-val {
  font-size: 1.4rem;
  font-weight: 700;
  line-height: 1.3;
  margin-bottom: 4px;
}

.daily-kpi-grid .kpi-sub {
  font-size: 0.76rem;
  color: var(--text-secondary);
  opacity: 0.8;
  line-height: 1.4;
}

.daily-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
  line-height: 1.5;
}

.daily-table th {
  background: rgba(255, 255, 255, 0.02);
  color: var(--text-secondary);
  font-weight: 600;
  text-align: left;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-glass);
  white-space: nowrap;
}

.daily-table td {
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  vertical-align: middle;
}

.daily-table tr:hover td {
  background: rgba(255, 255, 255, 0.02);
}

.date-badge {
  display: inline-block;
  font-weight: 600;
  color: var(--text-primary);
  font-size: 0.88rem;
  letter-spacing: 0.2px;
}

.flex-align-gap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.risk-score-pill {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 0.78rem;
  font-weight: 700;
  line-height: 1.2;
}

.level-name-text {
  font-size: 0.85rem;
  font-weight: 500;
  line-height: 1.4;
}

.lead-time-tag {
  display: inline-block;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 0.76rem;
  color: var(--text-secondary);
  white-space: nowrap;
  line-height: 1.3;
}

.news-cell {
  max-width: 260px;
}

.news-title-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
  font-size: 0.85rem;
  line-height: 1.4;
  color: var(--text-primary);
}

.news-summary-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 3px;
  line-height: 1.4;
}

.index-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.index-points {
  font-size: 0.92rem;
  color: var(--text-primary);
  line-height: 1.3;
}

.index-chg {
  font-weight: 600;
  line-height: 1.2;
}

/* 归因状态标签 */
.val-status-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 600;
  line-height: 1.3;
  white-space: nowrap;
}

.badge-hit {
  background: rgba(255, 68, 68, 0.15);
  border: 1px solid rgba(255, 68, 68, 0.4);
  color: #ff6b6b;
}

.badge-normal {
  background: rgba(0, 255, 136, 0.12);
  border: 1px solid rgba(0, 255, 136, 0.3);
  color: #00ff88;
}

.badge-watch {
  background: rgba(251, 191, 36, 0.12);
  border: 1px solid rgba(251, 191, 36, 0.3);
  color: #fbbf24;
}

.badge-alert {
  background: rgba(168, 85, 247, 0.15);
  border: 1px solid rgba(168, 85, 247, 0.4);
  color: #c084fc;
}

.badge-neutral {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: var(--text-secondary);
}

/* 每日对照明细弹窗样式 */
.val-summary-box {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 14px 18px;
}

.val-summary-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.val-title {
  font-weight: 600;
  font-size: 0.92rem;
  line-height: 1.4;
}

.daily-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-top: 16px;
}

.detail-column {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 18px;
}

.column-title {
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.4;
  margin-bottom: 14px;
  color: var(--text-primary);
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.detail-meta-box {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  padding: 10px 14px;
  margin-top: 10px;
  font-size: 0.84rem;
  line-height: 1.6;
}

.meta-row {
  margin-bottom: 4px;
}
.meta-row:last-child {
  margin-bottom: 0;
}

.signal-box {
  background: rgba(255, 68, 68, 0.06);
  border: 1px solid rgba(255, 68, 68, 0.2);
  border-radius: 6px;
  padding: 12px 14px;
}

.signal-box-title {
  font-weight: 600;
  font-size: 0.85rem;
  color: #ff8888;
  margin-bottom: 6px;
}

.signal-list {
  margin: 0;
  padding-left: 18px;
  font-size: 0.82rem;
  line-height: 1.6;
  color: var(--text-secondary);
}

.indices-comparison-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.idx-box {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.idx-name {
  font-size: 0.78rem;
  color: var(--text-secondary);
  line-height: 1.3;
}

.idx-pts {
  font-size: 1.15rem;
  line-height: 1.3;
}

.turnover-stat-bar {
  background: rgba(0, 212, 255, 0.06);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 8px;
  padding: 10px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.88rem;
  line-height: 1.4;
}

@media (max-width: 900px) {
  .daily-kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .daily-detail-grid {
    grid-template-columns: 1fr;
  }
}

/* 时间筛选与控制器 */
.daily-filter-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 14px 18px;
}

.filter-controls-row {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-weight: 500;
  white-space: nowrap;
}

.pill-btn-group {
  display: inline-flex;
  gap: 6px;
  background: rgba(0, 0, 0, 0.25);
  padding: 3px 4px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.pill-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 0.82rem;
  padding: 5px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  line-height: 1.3;
  white-space: nowrap;
}

.pill-btn:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.05);
}

.pill-btn.active {
  background: var(--accent-primary);
  color: #0f1117;
  font-weight: 600;
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
}

.date-picker-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-input {
  width: 135px;
  padding: 4px 8px;
  font-size: 0.82rem;
  font-family: monospace;
}

/* 图表容器与头部提示 */
.chart-card {
  padding: 20px 24px;
}

.chart-header {
  margin-bottom: 12px;
}

.chart-legend-hints {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.hint-badge {
  font-size: 0.74rem;
  padding: 3px 8px;
  border-radius: 4px;
  border: 1px solid transparent;
  line-height: 1.2;
}

.hint-safe {
  background: rgba(0, 255, 136, 0.08);
  border-color: rgba(0, 255, 136, 0.25);
  color: #00ff88;
}

.hint-watch {
  background: rgba(251, 191, 36, 0.08);
  border-color: rgba(251, 191, 36, 0.25);
  color: #fbbf24;
}

.hint-orange {
  background: rgba(251, 146, 60, 0.1);
  border-color: rgba(251, 146, 60, 0.3);
  color: #fb923c;
}

.hint-red {
  background: rgba(255, 68, 68, 0.1);
  border-color: rgba(255, 68, 68, 0.3);
  color: #ff6b6b;
}

.chart-canvas {
  width: 100%;
}

.chart-large {
  height: 380px;
}

.chart-medium {
  height: 280px;
}

@media (max-width: 1100px) {
  .filter-controls-row {
    gap: 14px;
  }
}
</style>
