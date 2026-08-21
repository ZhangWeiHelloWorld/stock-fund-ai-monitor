<template>
  <div class="settings-page">
    <header class="header">
      <div>
        <h2 class="page-title">系统设置</h2>
        <p class="text-secondary">配置推送通知、企业微信参数及用户账号</p>
      </div>
    </header>

    <div v-if="loading" class="text-center text-secondary" style="padding: 40px;">
      <div class="spinner"></div>
      <p style="margin-top:12px">加载配置中...</p>
    </div>

    <div v-else class="settings-grid">

      <!-- 企业微信配置 -->
      <div class="glass-card settings-section">
        <h3 class="section-title">🔔 企业微信配置</h3>

        <div class="form-group">
          <label>企业 CorpID</label>
          <input type="text" class="form-control" v-model="settings.wxwork_corpid"
                 placeholder="在企业微信管理后台「我的企业」中查看" />
        </div>
        <div class="form-group">
          <label>应用 AgentID</label>
          <input type="text" class="form-control" v-model="settings.wxwork_agentid"
                 placeholder="1000002" />
        </div>
        <div class="form-group">
          <label>应用 Secret</label>
          <div class="input-row">
            <input :type="showSecret ? 'text' : 'password'" class="form-control"
                   v-model="settings.wxwork_agentsecret"
                   placeholder="在应用管理中点击「查看」获取" />
            <button class="btn btn-glass icon-btn" @click="showSecret = !showSecret">
              {{ showSecret ? '🙈' : '👁' }}
            </button>
          </div>
        </div>
        <div class="form-group">
          <label>推送接收人</label>
          <input type="text" class="form-control" v-model="settings.wxwork_touser"
                 placeholder="@all 发送给所有人，或填写成员 UserID" />
          <small class="text-secondary">多人用 | 分隔，例如：user1|user2</small>
        </div>

        <!-- 接收消息服务器信息 -->
        <div class="server-info">
          <h4>📡 接收消息服务器配置（只读）</h4>
          <p class="text-secondary" style="font-size:0.82rem;margin-bottom:12px">
            将以下信息填入企业微信管理后台 → 应用管理 → 接收消息设置
          </p>
          <div class="info-row">
            <span class="label">URL:</span>
            <span class="value">http://&lt;服务器IP&gt;:8888/swx/receive</span>
          </div>
          <div class="info-row">
            <span class="label">Token:</span>
            <span class="value">{{ settings.token || '-' }}</span>
            <button class="copy-btn" @click="copyText(settings.token)">复制</button>
          </div>
          <div class="info-row">
            <span class="label">AESKey:</span>
            <span class="value truncate">{{ settings.encoding_aes_key || '-' }}</span>
            <button class="copy-btn" @click="copyText(settings.encoding_aes_key)">复制</button>
          </div>
        </div>

        <div class="actions-row">
          <button class="btn btn-primary" @click="saveSettings">💾 保存配置</button>
          <button class="btn btn-glass" @click="testPush" :disabled="testing">
            <span v-if="testing">发送中...</span>
            <span v-else>📤 测试推送</span>
          </button>
        </div>
        <div v-if="testResult" class="test-result" :class="testResult.success ? 'success' : 'error'">
          {{ testResult.message }}
        </div>
      </div>

      <!-- 推送设置 -->
      <div class="glass-card settings-section">
        <h3 class="section-title">⏰ 推送设置</h3>

        <div class="toggle-group">
          <label class="toggle-label">
            <span>启用推送通知</span>
            <div class="switch">
              <input type="checkbox" v-model="settings.push_enabled" />
              <span class="slider"></span>
            </div>
          </label>
        </div>

        <div class="form-group mt-3" :class="{ 'disabled-group': !settings.push_enabled }">
          <label>推送频率</label>
          <div class="push-schedule-container">
            <select class="form-control" v-model="selectedSchedulePreset" @change="onSchedulePresetChange">
              <option value="3min">每 3 分钟</option>
              <option value="5min">每 5 分钟</option>
              <option value="10min">每 10 分钟</option>
              <option value="15min">每 15 分钟</option>
              <option value="30min">每 30 分钟</option>
              <option value="60min">每 1 小时</option>
              <option value="120min">每 2 小时</option>
              <option value="custom">⚙️ 自定义 (分钟)</option>
            </select>

            <div v-if="selectedSchedulePreset === 'custom'" class="custom-minutes-input mt-2">
              <div class="input-group">
                <span class="input-prefix">每</span>
                <input type="number" min="3" step="1" class="form-control" v-model.number="customMinutes" @input="onCustomMinutesInput" placeholder="最低 3 分钟" />
                <span class="input-suffix">分钟</span>
              </div>
              <small class="text-secondary" style="margin-top: 4px; display: block;">请输入自定义推送间隔（最低 3 分钟）</small>
            </div>
          </div>
        </div>

        <div class="checkbox-group mt-3" :class="{ 'disabled-group': !settings.push_enabled }">
          <label class="checkbox-label">
            <input type="checkbox" v-model="settings.push_at_open" />
            🔔 开盘时推送（09:30）
          </label>
          <label class="checkbox-label">
            <input type="checkbox" v-model="settings.push_at_close" />
            🔔 收盘时推送（15:00）
          </label>
        </div>

        <h4 class="mt-4 mb-2">推送内容设置</h4>
        <div class="checkbox-group" :class="{ 'disabled-group': !settings.push_enabled }">
          
          <!-- 股票推送设置 -->
          <div class="checkbox-item-block">
            <label class="checkbox-label">
              <input type="checkbox" v-model="settings.push_stocks" />
              📈 股票行情（代码、价格、涨跌幅、盈亏）
            </label>

            <div v-if="settings.push_stocks" class="item-selection-box mt-2">
              <div class="selection-header">
                <span>指定推送的股票:</span>
                <span class="selection-tip">
                  {{ selectedStockCodes.length === 0 ? '（未勾选时默认推送全部持有的股票）' : `（已指定 ${selectedStockCodes.length} 只股票）` }}
                </span>
              </div>
              <div v-if="stocksList.length" class="chip-group mt-1">
                <label 
                  v-for="s in stocksList" 
                  :key="s.id" 
                  class="chip-label"
                  :class="{ active: selectedStockCodes.includes(s.code) }"
                >
                  <input 
                    type="checkbox" 
                    :value="s.code" 
                    v-model="selectedStockCodes"
                    @change="syncSelectionToSettings"
                  />
                  <span>{{ s.name }} ({{ s.code }})</span>
                </label>
              </div>
              <div v-else class="text-secondary text-sm mt-1">暂无股票数据，请先在股票管理中添加</div>
            </div>
          </div>

          <!-- 基金推送设置 -->
          <div class="checkbox-item-block mt-3">
            <label class="checkbox-label">
              <input type="checkbox" v-model="settings.push_funds" />
              💰 基金行情（代码、估值净值、涨跌幅、盈亏）
            </label>

            <div v-if="settings.push_funds" class="item-selection-box mt-2">
              <div class="selection-header">
                <span>指定推送的基金:</span>
                <span class="selection-tip">
                  {{ selectedFundCodes.length === 0 ? '（未勾选时默认推送全部持有的基金）' : `（已指定 ${selectedFundCodes.length} 只基金）` }}
                </span>
              </div>
              <div v-if="fundsList.length" class="chip-group mt-1">
                <label 
                  v-for="f in fundsList" 
                  :key="f.id" 
                  class="chip-label"
                  :class="{ active: selectedFundCodes.includes(f.code) }"
                >
                  <input 
                    type="checkbox" 
                    :value="f.code" 
                    v-model="selectedFundCodes"
                    @change="syncSelectionToSettings"
                  />
                  <span>{{ f.name }} ({{ f.code }})</span>
                </label>
              </div>
              <div v-else class="text-secondary text-sm mt-1">暂无基金数据，请先在基金管理中添加</div>
            </div>
          </div>

          <label class="checkbox-label mt-3">
            <input type="checkbox" v-model="settings.push_pnl" />
            💰 盈亏汇总（今日总盈亏、累计总盈亏）
          </label>
        </div>

        <div class="actions-row mt-4">
          <button class="btn btn-primary" @click="saveSettings">💾 保存配置</button>
          <button class="btn btn-glass" @click="testFormatPush" :disabled="testingFormat">
            <span v-if="testingFormat">生成推送中...</span>
            <span v-else>🧪 测试推送快报效果</span>
          </button>
        </div>
        <div v-if="formatTestResult" class="test-result mt-2" :class="formatTestResult.success ? 'success' : 'error'">
          {{ formatTestResult.message }}
        </div>
      </div>

      <!-- ⚡ 股票与基金涨跌幅/估值异动预警 -->
      <div class="glass-card settings-section">
        <h3 class="section-title">⚡ 股票与基金异动波动预警</h3>

        <!-- ================= 股票预警子模块 ================= -->
        <div class="toggle-group">
          <label class="toggle-label">
            <span>📈 启用股票异动预警</span>
            <div class="switch">
              <input type="checkbox" v-model="settings.alert_enabled" />
              <span class="slider"></span>
            </div>
          </label>
        </div>
        <small class="text-secondary" style="margin-top: 4px; display: block; font-size: 0.8rem;">
          在交易时段实时监测股票价格，触发涨跌幅阈值、触及日内新高/新低或短时间剧烈振幅时推送企微提醒。
        </small>

        <div :class="{ 'disabled-group': !settings.alert_enabled }" class="mt-2 mb-4">
          <!-- 监控股票范围 -->
          <div class="form-group mt-2">
            <div class="item-selection-box" style="margin-left: 0;">
              <div class="selection-header">
                <span>指定监控的股票:</span>
                <span class="selection-tip">
                  {{ alertMonitoredStockCodes.length === 0 ? '（未勾选时默认监控全部持仓股票）' : `（已指定 ${alertMonitoredStockCodes.length} 只股票）` }}
                </span>
              </div>
              <div v-if="stocksList.length" class="chip-group mt-1">
                <label 
                  v-for="s in stocksList" 
                  :key="s.id" 
                  class="chip-label"
                  :class="{ active: alertMonitoredStockCodes.includes(s.code) }"
                >
                  <input 
                    type="checkbox" 
                    :value="s.code" 
                    v-model="alertMonitoredStockCodes"
                    @change="syncSelectionToSettings"
                  />
                  <span>{{ s.name }} ({{ s.code }})</span>
                </label>
              </div>
              <div v-else class="text-secondary text-sm mt-1">暂无股票数据，请先在股票管理中添加</div>
            </div>
          </div>

          <!-- 股票涨跌幅阈值预警 -->
          <div class="threshold-grid mt-3">
            <div class="form-group">
              <label class="checkbox-label mb-2">
                <input type="checkbox" v-model="settings.alert_rise_enabled" />
                <span>股价上涨预警 (当日 ≥)</span>
              </label>
              <div class="input-group">
                <span class="input-prefix">+</span>
                <input type="number" step="0.1" class="form-control" v-model.number="settings.alert_rise_pct" placeholder="如 5.0" :disabled="!settings.alert_rise_enabled" />
                <span class="input-suffix">%</span>
              </div>
            </div>

            <div class="form-group">
              <label class="checkbox-label mb-2">
                <input type="checkbox" v-model="settings.alert_fall_enabled" />
                <span>股价下跌预警 (当日 ≤)</span>
              </label>
              <div class="input-group">
                <span class="input-prefix">-</span>
                <input type="number" step="0.1" class="form-control" :value="Math.abs(settings.alert_fall_pct)" @input="settings.alert_fall_pct = -Math.abs(parseFloat($event.target.value) || 0)" placeholder="如 5.0" :disabled="!settings.alert_fall_enabled" />
                <span class="input-suffix">%</span>
              </div>
            </div>
          </div>

          <!-- 股票日内极值触及提醒 -->
          <div class="checkbox-group mt-2">
            <label class="checkbox-label">
              <input type="checkbox" v-model="settings.alert_reach_high_enabled" />
              <span>🚀 触及 / 突破日内最高价提醒</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="settings.alert_reach_low_enabled" />
              <span>⚠️ 触及 / 跌破日内最低价提醒</span>
            </label>
          </div>

          <!-- 股票短时间剧烈波动/振幅预警 -->
          <div class="checkbox-item-block mt-3">
            <label class="checkbox-label">
              <input type="checkbox" v-model="settings.alert_swing_enabled" />
              <span>⚡ 启用股票短时间拉升、跳水与振幅预警</span>
            </label>

            <div v-if="settings.alert_swing_enabled" class="threshold-grid mt-2">
              <div class="form-group">
                <label>统计时间窗口</label>
                <select class="form-control" v-model.number="settings.alert_swing_minutes">
                  <option :value="3">3 分钟内</option>
                  <option :value="5">5 分钟内 (推荐)</option>
                  <option :value="10">10 分钟内</option>
                  <option :value="15">15 分钟内</option>
                  <option :value="30">30 分钟内</option>
                </select>
              </div>
              <div class="form-group">
                <label>波动 / 振幅阈值</label>
                <div class="input-group">
                  <span class="input-prefix">≥</span>
                  <input type="number" step="0.1" min="0.5" class="form-control" v-model.number="settings.alert_swing_pct" placeholder="如 3.0" />
                  <span class="input-suffix">%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <hr style="border:none; border-top:1px dashed var(--border-glass); margin: 20px 0;" />

        <!-- ================= 基金估值预警子模块 ================= -->
        <div class="toggle-group">
          <label class="toggle-label">
            <span>📦 启用基金实时估值预警</span>
            <div class="switch">
              <input type="checkbox" v-model="settings.alert_funds_enabled" />
              <span class="slider"></span>
            </div>
          </label>
        </div>
        <small class="text-secondary" style="margin-top: 4px; display: block; font-size: 0.8rem;">
          在交易时段实时监测天天基金/新浪基金估值变动，触发估值涨跌阈值或短时间异动时推送预警。
        </small>

        <div :class="{ 'disabled-group': !settings.alert_funds_enabled }" class="mt-2 mb-3">
          <!-- 监控基金范围 -->
          <div class="form-group mt-2">
            <div class="item-selection-box" style="margin-left: 0;">
              <div class="selection-header">
                <span>指定监控的基金:</span>
                <span class="selection-tip">
                  {{ alertMonitoredFundCodes.length === 0 ? '（未勾选时默认监控全部持仓基金）' : `（已指定 ${alertMonitoredFundCodes.length} 只基金）` }}
                </span>
              </div>
              <div v-if="fundsList.length" class="chip-group mt-1">
                <label 
                  v-for="f in fundsList" 
                  :key="f.id" 
                  class="chip-label"
                  :class="{ active: alertMonitoredFundCodes.includes(f.code) }"
                >
                  <input 
                    type="checkbox" 
                    :value="f.code" 
                    v-model="alertMonitoredFundCodes"
                    @change="syncSelectionToSettings"
                  />
                  <span>{{ f.name }} ({{ f.code }})</span>
                </label>
              </div>
              <div v-else class="text-secondary text-sm mt-1">暂无基金数据，请先在基金管理中添加</div>
            </div>
          </div>

          <!-- 基金估值涨跌幅阈值 -->
          <div class="threshold-grid mt-3">
            <div class="form-group">
              <label class="checkbox-label mb-2">
                <input type="checkbox" v-model="settings.alert_fund_rise_enabled" />
                <span>估值上涨预警 (今日 ≥)</span>
              </label>
              <div class="input-group">
                <span class="input-prefix">+</span>
                <input type="number" step="0.1" class="form-control" v-model.number="settings.alert_fund_rise_pct" placeholder="如 2.0" :disabled="!settings.alert_fund_rise_enabled" />
                <span class="input-suffix">%</span>
              </div>
            </div>

            <div class="form-group">
              <label class="checkbox-label mb-2">
                <input type="checkbox" v-model="settings.alert_fund_fall_enabled" />
                <span>估值下跌预警 (今日 ≤)</span>
              </label>
              <div class="input-group">
                <span class="input-prefix">-</span>
                <input type="number" step="0.1" class="form-control" :value="Math.abs(settings.alert_fund_fall_pct)" @input="settings.alert_fund_fall_pct = -Math.abs(parseFloat($event.target.value) || 0)" placeholder="如 2.0" :disabled="!settings.alert_fund_fall_enabled" />
                <span class="input-suffix">%</span>
              </div>
            </div>
          </div>

          <!-- 基金短时间估值剧烈波动预警 -->
          <div class="checkbox-item-block mt-3">
            <label class="checkbox-label">
              <input type="checkbox" v-model="settings.alert_fund_swing_enabled" />
              <span>⚡ 启用基金估值短时间异动波动预警</span>
            </label>

            <div v-if="settings.alert_fund_swing_enabled" class="threshold-grid mt-2">
              <div class="form-group">
                <label>统计时间窗口</label>
                <select class="form-control" v-model.number="settings.alert_fund_swing_minutes">
                  <option :value="5">5 分钟内</option>
                  <option :value="10">10 分钟内</option>
                  <option :value="15">15 分钟内 (推荐)</option>
                  <option :value="30">30 分钟内</option>
                  <option :value="60">60 分钟内</option>
                </select>
              </div>
              <div class="form-group">
                <label>估值波动阈值</label>
                <div class="input-group">
                  <span class="input-prefix">≥</span>
                  <input type="number" step="0.1" min="0.3" class="form-control" v-model.number="settings.alert_fund_swing_pct" placeholder="如 1.5" />
                  <span class="input-suffix">%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <hr style="border:none; border-top:1px dashed var(--border-glass); margin: 20px 0;" />

        <!-- 共同冷却时间 -->
        <div class="form-group mt-3" :class="{ 'disabled-group': !settings.alert_enabled && !settings.alert_funds_enabled }">
          <label>预警防刷屏冷却间隔</label>
          <select class="form-control" v-model.number="settings.alert_cooldown_minutes">
            <option :value="5">⏱️ 5 分钟内同一标的同类型不重复提醒</option>
            <option :value="10">⏱️ 10 分钟内同一标的同类型不重复提醒</option>
            <option :value="15">⏱️ 15 分钟内同一标的同类型不重复提醒 (默认)</option>
            <option :value="30">⏱️ 30 分钟内同一标的同类型不重复提醒</option>
            <option :value="60">⏱️ 1 小时内同一标的同类型不重复提醒</option>
          </select>
        </div>

        <div class="actions-row mt-4">
          <button class="btn btn-primary" @click="saveSettings">💾 保存预警配置</button>
          <button class="btn btn-glass" @click="testAlertPush" :disabled="testingAlert">
            <span v-if="testingAlert">⚡ 预警测试发送中...</span>
            <span v-else>🧪 测试股票与基金预警推送</span>
          </button>
        </div>
        <div v-if="alertTestResult" class="test-result mt-2" :class="alertTestResult.success ? 'success' : 'error'" style="white-space: pre-wrap; font-size:0.85rem;">
          {{ alertTestResult.message }}
        </div>
      </div>

      <!-- 🤖 AI 基础大模型配置 (独立抽出，供所有 AI 新功能共用) -->
      <div class="glass-card settings-section">
        <h3 class="section-title">🤖 AI 大模型通用配置</h3>
        <p class="text-secondary mb-3" style="font-size:0.82rem;">
          在此统一配置 DeepSeek 或任意 OpenAI 兼容大模型的 API Key 与 Endpoint，供系统各类 AI 智能分析功能通用。
        </p>

        <div class="form-group">
          <label>API Key</label>
          <div class="input-row">
            <input :type="showDeepseekKey ? 'text' : 'password'" class="form-control"
                   v-model="settings.deepseek_api_key"
                   placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxx" />
            <button class="btn btn-glass icon-btn" @click="showDeepseekKey = !showDeepseekKey">
              {{ showDeepseekKey ? '🙈' : '👁' }}
            </button>
          </div>
          <small class="text-secondary">可从 DeepSeek 开放平台 (platform.deepseek.com) 或各模型平台获取</small>
        </div>

        <div class="form-group">
          <label>API 接口地址 (Base URL)</label>
          <input type="text" class="form-control" v-model="settings.deepseek_api_url"
                 placeholder="https://api.deepseek.com" />
        </div>

        <div class="form-group">
          <label>模型选择 (Model)</label>
          <input type="text" class="form-control" v-model="settings.deepseek_model"
                 placeholder="deepseek-chat" />
        </div>

        <div class="actions-row">
          <button class="btn btn-primary" @click="saveSettings">💾 保存模型配置</button>
        </div>
      </div>

      <!-- 📰 AI 实时新闻持仓影响分析 (新增功能) -->
      <div class="glass-card settings-section">
        <h3 class="section-title">📰 AI 实时新闻持仓影响分析</h3>

        <div class="toggle-group">
          <label class="toggle-label">
            <span>启用 AI 实时新闻持仓影响分析</span>
            <div class="switch">
              <input type="checkbox" v-model="settings.ai_news_analysis_enabled" />
              <span class="slider"></span>
            </div>
          </label>
        </div>
        <small class="text-secondary" style="margin-top: 4px; display: block; font-size: 0.8rem;">
          自动从全网大盘快讯与东方财富、新浪等平台抓取最新新闻，结合持仓评估利好利空并推送至微信。
        </small>

        <div class="form-group mt-3" :class="{ 'disabled-group': !settings.ai_news_analysis_enabled }">
          <label>分析与推送频率 (默认每 1 小时)</label>
          <select class="form-control" v-model="settings.ai_news_schedule">
            <option value="30min">⏱️ 每 0.5 小时 (30分钟)</option>
            <option value="60min">⏱️ 每 1 小时 (默认)</option>
            <option value="120min">⏱️ 每 2 小时</option>
            <option value="180min">⏱️ 每 3 小时</option>
            <option value="240min">⏱️ 每 4 小时</option>
            <option value="300min">⏱️ 每 5 小时</option>
            <option value="360min">⏱️ 每 6 小时</option>
            <option value="420min">⏱️ 每 7 小时</option>
            <option value="480min">⏱️ 每 8 小时</option>
            <option value="540min">⏱️ 每 9 小时</option>
            <option value="600min">⏱️ 每 10 小时</option>
            <option value="660min">⏱️ 每 11 小时</option>
            <option value="720min">⏱️ 每 12 小时</option>
          </select>
        </div>

        <div class="form-group" :class="{ 'disabled-group': !settings.ai_news_analysis_enabled }">
          <div class="label-row" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <label style="margin-bottom:0">新闻分析提示词模板 (Prompt Template)</label>
            <button class="btn-text" @click="resetDefaultNewsPrompt" style="font-size:0.8rem; color:var(--accent-primary);">
              ↺ 恢复默认模板
            </button>
          </div>
          <textarea class="form-control" rows="6" v-model="settings.ai_news_prompt_template"
                    placeholder="输入新闻分析提示词模板..." style="font-family: inherit; font-size:0.85rem; line-height:1.4;"></textarea>
          <small class="text-secondary" style="margin-top: 4px; display: block; font-size: 0.78rem;">
            💡 可用占位符：<code style="color:var(--accent-primary)">{holdings_summary}</code> (持仓行情), 
            <code style="color:var(--accent-primary)">{news_summary}</code> (互联网抓取新闻), 
            <code style="color:var(--accent-primary)">{date_str}</code> (日期时间)
          </small>
        </div>

        <div class="actions-row">
          <button class="btn btn-primary" @click="saveSettings">💾 保存配置</button>
          <button class="btn btn-glass" @click="testAiNewsAnalysis" :disabled="testingAiNews">
            <span v-if="testingAiNews">🤖 AI 抓取新闻分析中...</span>
            <span v-else>🧪 测试新闻分析并推送</span>
          </button>
        </div>
        <div v-if="aiNewsTestResult" class="test-result mt-2" :class="aiNewsTestResult.success ? 'success' : 'error'" style="white-space: pre-wrap; font-size:0.85rem;">
          {{ aiNewsTestResult.message }}
        </div>
      </div>

      <!-- 📊 DeepSeek 交易日自动复盘 -->
      <div class="glass-card settings-section">
        <h3 class="section-title">📊 DeepSeek 交易日自动复盘</h3>

        <div class="toggle-group">
          <label class="toggle-label">
            <span>启用交易日 AI 自动复盘</span>
            <div class="switch">
              <input type="checkbox" v-model="settings.deepseek_review_enabled" />
              <span class="slider"></span>
            </div>
          </label>
        </div>
        <small class="text-secondary" style="margin-top: 4px; display: block; font-size: 0.8rem;">
          开启后，系统将在每个交易日 11:35（午盘）和 15:05（收盘）自动调用 DeepSeek 结合持仓与宏观局势生成复盘分析并推送。
        </small>

        <div class="form-group mt-3" :class="{ 'disabled-group': !settings.deepseek_review_enabled }">
          <div class="label-row" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <label style="margin-bottom:0">复盘提示词模板 (Prompt Template)</label>
            <button class="btn-text" @click="resetDefaultPrompt" style="font-size:0.8rem; color:var(--accent-primary);">
              ↺ 恢复默认模板
            </button>
          </div>
          <textarea class="form-control" rows="6" v-model="settings.deepseek_prompt_template"
                    placeholder="输入复盘提示词模板..." style="font-family: inherit; font-size:0.85rem; line-height:1.4;"></textarea>
          <small class="text-secondary" style="margin-top: 4px; display: block; font-size: 0.78rem;">
            💡 可用占位符：<code style="color:var(--accent-primary)">{holdings_summary}</code> (持仓行情明细), 
            <code style="color:var(--accent-primary)">{session_name}</code> (午盘复盘/收盘复盘), 
            <code style="color:var(--accent-primary)">{date_str}</code> (日期时间)
          </small>
        </div>

        <div class="actions-row">
          <button class="btn btn-primary" @click="saveSettings">💾 保存配置</button>
          <button class="btn btn-glass" @click="testDeepseekReview" :disabled="testingDeepseek">
            <span v-if="testingDeepseek">🤖 AI 思考生成与推送中...</span>
            <span v-else>🧪 测试 DeepSeek 复盘并推送</span>
          </button>
        </div>
        <div v-if="deepseekTestResult" class="test-result mt-2" :class="deepseekTestResult.success ? 'success' : 'error'" style="white-space: pre-wrap; font-size:0.85rem;">
          {{ deepseekTestResult.message }}
        </div>
      </div>

      <!-- 管理员：用户账号管理 -->
      <div v-if="currentUser?.role === 'admin'" class="glass-card settings-section full-width-card">
        <div class="section-header-row">
          <h3 class="section-title" style="margin-bottom:0; border-bottom:none; padding-bottom:0;">👤 用户账号管理</h3>
          <button class="btn btn-primary btn-sm" @click="openCreateUserModal">
            ➕ 分配新账号
          </button>
        </div>

        <p class="text-secondary mt-2 mb-3" style="font-size:0.85rem">
          管理员可以分配新用户账号、重置密码及管理权限。如忘记管理员密码，可随时在后端服务器 <code>backend/admin_config.json</code> 中修改找回。
        </p>

        <div class="user-table-container">
          <table class="user-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>用户名</th>
                <th>角色</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in usersList" :key="u.id">
                <td>#{{ u.id }}</td>
                <td class="font-bold">{{ u.username }}</td>
                <td>
                  <span class="role-tag" :class="u.role">
                    {{ u.role === 'admin' ? '管理员' : '普通用户' }}
                  </span>
                </td>
                <td>{{ formatDate(u.created_at) }}</td>
                <td>
                  <div class="table-actions">
                    <button class="btn-text btn-edit" @click="openResetPasswordModal(u)">
                      🔑 重置密码
                    </button>
                    <button v-if="u.id !== currentUser.id && u.role !== 'admin'" class="btn-text btn-delete" @click="confirmDeleteUser(u)">
                      🗑️ 删除
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 关于 -->
      <div class="glass-card settings-section about-section">
        <div class="about-icon">📈</div>
        <h3>持仓看板</h3>
        <p class="version">v1.1.0 多用户增强版</p>
        <p class="text-secondary mt-3">
          轻量级股票基金实时监控系统，支持多用户独立持仓隔离、企业微信推送、DeepSeek AI 复盘与管理员账号找回。
        </p>
        <div class="data-source mt-4">
          数据来源：新浪财经（股票）/ 天天基金（基金估值）
        </div>
        <div class="data-source mt-2">
          推送平台：企业微信应用消息 API
        </div>
      </div>
    </div>

    <!-- 创建新用户 Modal -->
    <div v-if="showCreateUserModal" class="modal-backdrop" @click.self="showCreateUserModal = false">
      <div class="modal-card">
        <h3>➕ 分配新账号</h3>
        <form @submit.prevent="handleCreateUser">
          <div class="form-group mt-3">
            <label>用户名 / 账号</label>
            <input type="text" v-model="newUserForm.username" class="form-control" placeholder="请输入用户名" required />
          </div>
          <div class="form-group mt-3">
            <label>初始密码</label>
            <input type="password" v-model="newUserForm.password" class="form-control" placeholder="请输入初始密码" required />
          </div>
          <div class="form-group mt-3">
            <label>账号角色</label>
            <select v-model="newUserForm.role" class="form-control">
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
            </select>
          </div>
          <div class="modal-actions mt-4">
            <button type="button" class="btn btn-glass" @click="showCreateUserModal = false">取消</button>
            <button type="submit" class="btn btn-primary">确认创建</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 重置密码 Modal -->
    <div v-if="showResetPasswordModal" class="modal-backdrop" @click.self="showResetPasswordModal = false">
      <div class="modal-card">
        <h3>🔑 重置用户密码 ({{ selectedUserForReset?.username }})</h3>
        <form @submit.prevent="handleResetPassword">
          <div class="form-group mt-3">
            <label>新密码</label>
            <input type="password" v-model="resetPasswordForm.new_password" class="form-control" placeholder="请输入新密码" required />
          </div>
          <div class="modal-actions mt-4">
            <button type="button" class="btn btn-glass" @click="showResetPasswordModal = false">取消</button>
            <button type="submit" class="btn btn-primary">确认重置</button>
          </div>
        </form>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, inject } from 'vue'
import api from '../api'

const showToast = inject('showToast')
const loading = ref(true)
const testing = ref(false)
const testingFormat = ref(false)
const testingDeepseek = ref(false)
const testingAiNews = ref(false)
const testingAlert = ref(false)
const showSecret = ref(false)
const showDeepseekKey = ref(false)
const testResult = ref(null)
const formatTestResult = ref(null)
const deepseekTestResult = ref(null)
const aiNewsTestResult = ref(null)
const alertTestResult = ref(null)

const currentUser = ref(null)
const usersList = ref([])
const showCreateUserModal = ref(false)
const showResetPasswordModal = ref(false)
const selectedUserForReset = ref(null)

const newUserForm = reactive({ username: '', password: '', role: 'user' })
const resetPasswordForm = reactive({ new_password: '' })

const stocksList = ref([])
const fundsList = ref([])
const selectedStockCodes = ref([])
const selectedFundCodes = ref([])
const alertMonitoredStockCodes = ref([])
const alertMonitoredFundCodes = ref([])

const selectedSchedulePreset = ref('30min')
const customMinutes = ref(3)
const presets = ['3min', '5min', '10min', '15min', '30min', '60min', '120min']

const DEFAULT_PROMPT = `你是一位专业且严谨的股市宏观与投资分析专家。请根据以下投资者当前的持仓明细和市场数据，结合大盘环境、板块热点与资金流向、近期政治政策局势、以及全球金融市场动态，撰写一份条理清晰、排版美观的收盘复盘报告（适合手机微信直观阅读）。

当前持仓与市场数据：
{holdings_summary}

复盘与分析要求：
1. 📊【持仓与市场点评】：总结{session_name}持仓的总体盈亏及主要贡献/拉胯品种，结合大盘及核心板块走势分析驱动逻辑；
2. 🌐【宏观与环境分析】：
   - 整体市场环境与大盘走势分析
   - 板块环境与热点资金轮动分析
   - 近期政治局势/宏观政策影响
   - 全球金融市场环境对A股的传导效应
3. 🔮【短中期走势展望】：
   - 短期（未来 7 天）市场走势预测与关键观察点
   - 中期（未来 1 个月）趋势判断与资产配置导向
4. 🎯【操作与风控建议】：针对当前持仓异动与仓位占比，给出具体的后续操作建议（如仓位调整、止盈止损线、加减仓时机等）。

排版与文本格式要求（极其重要）：
- 请直接使用简洁清晰的文本段落与丰富的 Emoji 表达；
- 切勿在文中输出包含 **粗体**、### 标题、--- 分割线 等 Markdown 语法符号，确保在手机微信客户端阅读时界面干净利落。`

const DEFAULT_NEWS_PROMPT = `你是一位顶尖的金融证券分析师与风险控制专家。请结合互联网最新抓取的财经快讯/个股新闻与投资者当前的实际持仓明细，进行深度利好利空分析与风险防范预警。

当前持仓情况：
{holdings_summary}

抓取的互联网最新新闻动态：
{news_summary}

分析要求与架构：
1. 💥【重点新闻利好/利空解读】：精炼解读最新新闻中对投资者持仓品种（包含对应行业板块）有直接或间接影响的关键消息，明确标注利好/利空级别（如：🟢 显著利好 / 🔴 显著利空 / 🟡 中性观望）；
2. 🌊【大盘与板块传导路径】：分析全网大盘快讯及政策/国际市场风向对投资者当前股票与基金资产组合的传导效应；
3. 🛡️【针对性持仓应对策略】：结合持仓盈亏状况与个股/基金占比，给出明确的短中线应对策略（加仓/减仓/观望/止损防范等）。

排版与文本格式要求（极其重要）：
- 请直接使用简洁清晰的段落与 Emoji，排版力求适合手机微信快速阅读；
- 严禁输出 **粗体**、### 标题、--- 分割线 等 Markdown 符号，保持界面利落清晰。`

const settings = ref({
  wxwork_corpid: '',
  wxwork_agentsecret: '',
  wxwork_agentid: '1000002',
  wxwork_touser: '@all',
  push_enabled: true,
  push_schedule: '30min',
  push_at_open: true,
  push_at_close: true,
  push_stocks: true,
  push_selected_stock_codes: '',
  push_funds: true,
  push_selected_fund_codes: '',
  push_pnl: true,
  token: '',
  encoding_aes_key: '',
  deepseek_api_key: '',
  deepseek_api_url: 'https://api.deepseek.com',
  deepseek_model: 'deepseek-chat',
  deepseek_review_enabled: true,
  deepseek_prompt_template: DEFAULT_PROMPT,
  ai_news_analysis_enabled: true,
  ai_news_schedule: '60min',
  ai_news_prompt_template: DEFAULT_NEWS_PROMPT,
  alert_enabled: true,
  alert_monitored_stock_codes: '',
  alert_rise_enabled: true,
  alert_rise_pct: 5.0,
  alert_fall_enabled: true,
  alert_fall_pct: -5.0,
  alert_reach_high_enabled: true,
  alert_reach_low_enabled: true,
  alert_swing_enabled: true,
  alert_swing_minutes: 5,
  alert_swing_pct: 3.0,
  alert_cooldown_minutes: 15,
  alert_funds_enabled: true,
  alert_monitored_fund_codes: '',
  alert_fund_rise_enabled: true,
  alert_fund_rise_pct: 2.0,
  alert_fund_fall_enabled: true,
  alert_fund_fall_pct: -2.0,
  alert_fund_swing_enabled: true,
  alert_fund_swing_minutes: 15,
  alert_fund_swing_pct: 1.5
})

const formatDate = (isoStr) => {
  if (!isoStr) return '-'
  try {
    const d = new Date(isoStr)
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch (e) {
    return isoStr
  }
}

const loadCurrentUser = () => {
  try {
    const raw = localStorage.getItem('user')
    if (raw) currentUser.value = JSON.parse(raw)
  } catch (e) {
    currentUser.value = null
  }
}

const fetchUsers = async () => {
  if (currentUser.value?.role === 'admin') {
    try {
      usersList.value = await api.getUsers()
    } catch (e) {
      console.error(e)
    }
  }
}

const openCreateUserModal = () => {
  newUserForm.username = ''
  newUserForm.password = ''
  newUserForm.role = 'user'
  showCreateUserModal.value = true
}

const handleCreateUser = async () => {
  try {
    await api.createUser(newUserForm)
    showToast('✅ 成功创建新账号！')
    showCreateUserModal.value = false
    fetchUsers()
  } catch (e) {
    const msg = e.response?.data?.detail || '创建失败'
    showToast('❌ ' + msg)
  }
}

const openResetPasswordModal = (u) => {
  selectedUserForReset.value = u
  resetPasswordForm.new_password = ''
  showResetPasswordModal.value = true
}

const handleResetPassword = async () => {
  if (!selectedUserForReset.value) return
  try {
    await api.resetPassword(selectedUserForReset.value.id, resetPasswordForm)
    showToast(`✅ 用户 ${selectedUserForReset.value.username} 密码重置成功！`)
    showResetPasswordModal.value = false
  } catch (e) {
    const msg = e.response?.data?.detail || '重置密码失败'
    showToast('❌ ' + msg)
  }
}

const confirmDeleteUser = async (u) => {
  if (!confirm(`确定要删除用户 "${u.username}" 及其所有股票和基金数据吗？此操作不可逆！`)) return
  try {
    await api.deleteUser(u.id)
    showToast(`✅ 用户 ${u.username} 已删除`)
    fetchUsers()
  } catch (e) {
    const msg = e.response?.data?.detail || '删除失败'
    showToast('❌ ' + msg)
  }
}

const resetDefaultPrompt = () => {
  settings.value.deepseek_prompt_template = DEFAULT_PROMPT
  showToast('↺ 已重置为默认提示词模板')
}

const resetDefaultNewsPrompt = () => {
  settings.value.ai_news_prompt_template = DEFAULT_NEWS_PROMPT
  showToast('↺ 已重置为默认新闻分析提示词模板')
}

const testAiNewsAnalysis = async () => {
  testingAiNews.value = true
  aiNewsTestResult.value = null
  try {
    const res = await api.testAiNewsAnalysis()
    aiNewsTestResult.value = {
      success: res.success,
      message: res.message || (res.success ? 'AI 实时新闻分析成功并已推送' : '新闻分析失败')
    }
    showToast(res.success ? '✅ AI 实时新闻分析并推送成功！' : '❌ ' + (res.message || '新闻分析失败'))
  } catch (e) {
    const detailMsg = e.response?.data?.detail || e.message || '网络连接异常'
    aiNewsTestResult.value = { success: false, message: '请求失败：' + detailMsg }
    showToast('❌ 测试 AI 新闻分析失败')
  } finally {
    testingAiNews.value = false
  }
}


const syncSelectionToSettings = () => {
  settings.value.push_selected_stock_codes = (selectedStockCodes.value || []).join(',')
  settings.value.push_selected_fund_codes = (selectedFundCodes.value || []).join(',')
  settings.value.alert_monitored_stock_codes = (alertMonitoredStockCodes.value || []).join(',')
  settings.value.alert_monitored_fund_codes = (alertMonitoredFundCodes.value || []).join(',')
}

watch([selectedStockCodes, selectedFundCodes, alertMonitoredStockCodes, alertMonitoredFundCodes], () => {
  syncSelectionToSettings()
}, { deep: true })

const initSelectionState = () => {
  const stockStr = settings.value.push_selected_stock_codes || ''
  selectedStockCodes.value = stockStr ? stockStr.split(',').map(c => c.trim()).filter(Boolean) : []

  const fundStr = settings.value.push_selected_fund_codes || ''
  selectedFundCodes.value = fundStr ? fundStr.split(',').map(c => c.trim()).filter(Boolean) : []

  const alertStockStr = settings.value.alert_monitored_stock_codes || ''
  alertMonitoredStockCodes.value = alertStockStr ? alertStockStr.split(',').map(c => c.trim()).filter(Boolean) : []

  const alertFundStr = settings.value.alert_monitored_fund_codes || ''
  alertMonitoredFundCodes.value = alertFundStr ? alertFundStr.split(',').map(c => c.trim()).filter(Boolean) : []
}

const initScheduleState = () => {
  const val = settings.value.push_schedule || '30min'
  if (presets.includes(val)) {
    selectedSchedulePreset.value = val
  } else {
    selectedSchedulePreset.value = 'custom'
    const num = parseInt(val)
    customMinutes.value = isNaN(num) || num < 3 ? 3 : num
  }
}

const onSchedulePresetChange = () => {
  if (selectedSchedulePreset.value !== 'custom') {
    settings.value.push_schedule = selectedSchedulePreset.value
  } else {
    if (!customMinutes.value || customMinutes.value < 3) {
      customMinutes.value = 3
    }
    settings.value.push_schedule = `${customMinutes.value}min`
  }
}

const onCustomMinutesInput = () => {
  if (customMinutes.value != null && customMinutes.value >= 3) {
    settings.value.push_schedule = `${customMinutes.value}min`
  }
}

const fetchSettings = async () => {
  loadCurrentUser()
  try {
    const [data, stocksData, fundsData] = await Promise.all([
      api.getSettings(),
      api.getStocks().catch(() => []),
      api.getFunds().catch(() => [])
    ])
    stocksList.value = stocksData || []
    fundsList.value = fundsData || []

    if (data) {
      Object.assign(settings.value, data)
      initScheduleState()
      initSelectionState()
    }
    await fetchUsers()
  } catch (e) {
    showToast('❌ 加载设置失败')
  } finally {
    loading.value = false
  }
}

const saveSettings = async () => {
  try {
    if (selectedSchedulePreset.value === 'custom') {
      if (!customMinutes.value || customMinutes.value < 3) {
        customMinutes.value = 3
        showToast('⚠️ 自定义推送频率最低为 3 分钟，已修正为 3 分钟')
      }
      settings.value.push_schedule = `${customMinutes.value}min`
    }

    syncSelectionToSettings()
    await api.updateSettings(settings.value)
    showToast('✅ 设置已保存')
  } catch (e) {
    showToast('❌ 保存失败，请重试')
  }
}

const testPush = async () => {
  testing.value = true
  testResult.value = null
  try {
    const res = await api.testPush()
    testResult.value = {
      success: res.success,
      message: res.message || (res.success ? '推送成功' : '推送失败')
    }
    showToast(res.success ? '✅ 测试推送发送成功！' : '❌ 测试推送失败：' + res.message)
  } catch (e) {
    testResult.value = { success: false, message: '请求失败，请检查网络连接' }
    showToast('❌ 测试推送失败')
  } finally {
    testing.value = false
  }
}

const testFormatPush = async () => {
  testingFormat.value = true
  formatTestResult.value = null
  try {
    const res = await api.testFormatPush()
    formatTestResult.value = {
      success: res.success,
      message: res.message || (res.success ? '推送效果测试发送成功' : '推送失败')
    }
    showToast(res.success ? '✅ 推送效果测试发送成功！' : '❌ ' + (res.message || '推送失败'))
  } catch (e) {
    const detailMsg = e.response?.data?.detail || e.message || '网络连接异常'
    formatTestResult.value = { success: false, message: '请求失败：' + detailMsg }
    showToast('❌ 测试推送效果失败')
  } finally {
    testingFormat.value = false
  }
}

const testDeepseekReview = async () => {
  testingDeepseek.value = true
  deepseekTestResult.value = null
  try {
    const res = await api.testDeepseekReview()
    deepseekTestResult.value = {
      success: res.success,
      message: res.message || (res.success ? 'DeepSeek 复盘生成成功并已推送' : '复盘失败')
    }
    showToast(res.success ? '✅ DeepSeek 复盘生成并推送成功！' : '❌ ' + (res.message || '复盘失败'))
  } catch (e) {
    const detailMsg = e.response?.data?.detail || e.message || '网络连接异常'
    deepseekTestResult.value = { success: false, message: '请求失败：' + detailMsg }
    showToast('❌ 测试 DeepSeek 复盘失败')
  } finally {
    testingDeepseek.value = false
  }
}

const testAlertPush = async () => {
  testingAlert.value = true
  alertTestResult.value = null
  try {
    const res = await api.testAlertPush()
    alertTestResult.value = {
      success: res.success,
      message: res.message || (res.success ? '预警测试推送成功' : '预警测试失败')
    }
    showToast(res.success ? '✅ 股票异动预警测试推送成功！' : '❌ ' + (res.message || '测试失败'))
  } catch (e) {
    const detailMsg = e.response?.data?.detail || e.message || '网络连接异常'
    alertTestResult.value = { success: false, message: '请求失败：' + detailMsg }
    showToast('❌ 测试异动预警失败')
  } finally {
    testingAlert.value = false
  }
}

const copyText = (text) => {
  if (!text) return
  navigator.clipboard.writeText(text).then(() => {
    showToast('✅ 已复制到剪贴板')
  })
}

onMounted(fetchSettings)
</script>

<style scoped>
.header { margin-bottom: 32px; }

.page-title {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 4px;
  background: linear-gradient(135deg, var(--text-primary), var(--accent-primary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.settings-grid {
  columns: 3 340px;
  column-gap: 24px;
}

.settings-section {
  break-inside: avoid-column;
  margin-bottom: 24px;
  display: inline-block;
  width: 100%;
}

.full-width-card {
  column-span: all;
  width: 100%;
}

.section-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-glass);
  padding-bottom: 12px;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.85rem;
}

.user-table-container {
  overflow-x: auto;
  margin-top: 12px;
}

.user-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.9rem;
}

.user-table th, .user-table td {
  padding: 12px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.user-table th {
  color: var(--text-secondary);
  font-weight: 600;
  background: rgba(0, 0, 0, 0.2);
}

.font-bold {
  font-weight: 600;
}

.role-tag {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 4px;
}

.role-tag.admin {
  background: rgba(255, 170, 0, 0.15);
  color: #ffaa00;
  border: 1px solid rgba(255, 170, 0, 0.3);
}

.role-tag.user {
  background: rgba(0, 212, 255, 0.15);
  color: #00d2ff;
  border: 1px solid rgba(0, 212, 255, 0.3);
}

.table-actions {
  display: flex;
  gap: 12px;
}

.btn-text {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-edit {
  color: var(--accent-primary);
}

.btn-edit:hover {
  text-decoration: underline;
}

.btn-delete {
  color: #f85149;
}

.btn-delete:hover {
  text-decoration: underline;
}

/* Modals */
.modal-backdrop {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.modal-card {
  width: 100%;
  max-width: 420px;
  background: #161b22;
  border: 1px solid var(--border-glass);
  border-radius: 14px;
  padding: 28px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
}

.modal-card h3 {
  font-size: 1.2rem;
  margin-bottom: 16px;
  color: var(--text-primary);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.section-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 24px;
  color: var(--accent-primary);
  border-bottom: 1px solid var(--border-glass);
  padding-bottom: 12px;
}

.input-row {
  display: flex;
  gap: 8px;
}

.input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}
.input-prefix, .input-suffix {
  color: var(--text-secondary);
  font-size: 0.9rem;
  white-space: nowrap;
}

.threshold-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 600px) {
  .threshold-grid {
    grid-template-columns: 1fr;
  }
}

.icon-btn {
  padding: 8px 12px;
  flex-shrink: 0;
}

.server-info {
  margin-top: 20px;
  padding: 16px;
  background: rgba(0,0,0,0.25);
  border-radius: 10px;
  border: 1px dashed var(--border-glass);
}
.server-info h4 {
  margin-bottom: 12px;
  font-size: 0.9rem;
  font-weight: 600;
}
.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-family: monospace;
  font-size: 0.82rem;
}
.info-row .label {
  width: 60px;
  color: var(--text-secondary);
  flex-shrink: 0;
}
.info-row .value {
  color: var(--accent-primary);
  flex: 1;
  overflow: hidden;
}
.info-row .value.truncate {
  text-overflow: ellipsis;
  white-space: nowrap;
}
.copy-btn {
  flex-shrink: 0;
  font-size: 0.75rem;
  padding: 2px 8px;
  border: 1px solid var(--border-glass);
  border-radius: 4px;
  cursor: pointer;
  background: var(--bg-glass);
  color: var(--text-secondary);
  transition: all 0.2s;
}
.copy-btn:hover {
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.actions-row {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  flex-wrap: wrap;
}

.test-result {
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 0.9rem;
}
.test-result.success {
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.3);
  color: var(--green);
}
.test-result.error {
  background: rgba(255, 68, 68, 0.1);
  border: 1px solid rgba(255, 68, 68, 0.3);
  color: var(--red);
}

/* Toggle */
.toggle-group { margin-bottom: 4px; }
.toggle-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 500;
  cursor: pointer;
  padding: 4px 0;
}
.switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 26px;
  flex-shrink: 0;
}
.switch input { opacity: 0; width: 0; height: 0; }
.slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background: var(--bg-primary);
  border: 1px solid var(--border-glass);
  transition: .3s;
  border-radius: 34px;
}
.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background: var(--text-secondary);
  transition: .3s;
  border-radius: 50%;
}
input:checked + .slider {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
}
input:checked + .slider:before {
  transform: translateX(24px);
  background: #000;
}

.disabled-group { opacity: 0.45; pointer-events: none; }

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: 0.95rem;
}
.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: var(--accent-primary);
}
.sub-checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 26px;
  margin-top: 6px;
  font-size: 0.85rem;
  color: var(--text-secondary);
  cursor: pointer;
}
.item-selection-box {
  margin-left: 26px;
  padding: 10px 14px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border: 1px dashed var(--border-glass);
}
.selection-header {
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.selection-tip {
  color: var(--accent-primary);
  font-size: 0.8rem;
}
.chip-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip-label {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  border-radius: 16px;
  font-size: 0.82rem;
  cursor: pointer;
  transition: all 0.2s;
}
.chip-label:hover {
  background: rgba(255, 255, 255, 0.1);
}
.chip-label.active {
  border-color: var(--accent-primary);
  background: rgba(0, 212, 255, 0.15);
  color: var(--accent-primary);
}
.text-sm {
  font-size: 0.8rem;
}

.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 16px; }
.mt-4 { margin-top: 24px; }
.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 12px; }

.about-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 8px;
}
.about-icon {
  font-size: 3rem;
  margin-bottom: 8px;
}
.about-section h3 { font-size: 1.3rem; font-weight: 700; }
.version {
  color: var(--accent-primary);
  font-family: monospace;
  font-size: 0.9rem;
}
.data-source {
  font-size: 0.82rem;
  color: var(--text-secondary);
  padding: 6px 16px;
  background: rgba(0,0,0,0.2);
  border-radius: 20px;
  width: 100%;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-glass);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: rotate 1s linear infinite;
  margin: 0 auto;
}
@keyframes rotate { 100% { transform: rotate(360deg); } }
</style>
