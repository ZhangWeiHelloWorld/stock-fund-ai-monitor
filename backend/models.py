from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class StockBase(BaseModel):
    code: str
    name: Optional[str] = ""
    shares: float
    cost_price: float
    is_holding: bool = True
    note: Optional[str] = ""

class StockCreate(StockBase):
    pass

class StockUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    shares: Optional[float] = None
    cost_price: Optional[float] = None
    is_holding: Optional[bool] = None
    note: Optional[str] = None

class Stock(StockBase):
    id: int
    created_at: str
    updated_at: str

class FundBase(BaseModel):
    code: str
    name: Optional[str] = ""
    shares: float
    cost_nav: float
    is_holding: bool = True
    note: Optional[str] = ""

class FundCreate(FundBase):
    pass

class FundUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    shares: Optional[float] = None
    cost_nav: Optional[float] = None
    is_holding: Optional[bool] = None
    note: Optional[str] = None

class Fund(FundBase):
    id: int
    created_at: str
    updated_at: str

class SettingsUpdate(BaseModel):
    wxwork_corpid: Optional[str] = None
    wxwork_agentsecret: Optional[str] = None
    wxwork_agentid: Optional[str] = None
    wxwork_touser: Optional[str] = None
    push_enabled: Optional[bool] = None
    push_schedule: Optional[str] = None
    push_at_open: Optional[bool] = None
    push_at_close: Optional[bool] = None
    push_stocks: Optional[bool] = None
    push_stocks_only_holding: Optional[bool] = None
    push_selected_stock_codes: Optional[str] = None
    push_funds: Optional[bool] = None
    push_funds_only_holding: Optional[bool] = None
    push_selected_fund_codes: Optional[str] = None
    push_pnl: Optional[bool] = None
    token: Optional[str] = None
    encoding_aes_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    deepseek_api_url: Optional[str] = None
    deepseek_model: Optional[str] = None
    deepseek_review_enabled: Optional[bool] = None
    deepseek_prompt_template: Optional[str] = None
    ai_news_analysis_enabled: Optional[bool] = None
    ai_news_schedule: Optional[str] = None
    ai_news_prompt_template: Optional[str] = None
    alert_enabled: Optional[bool] = None
    alert_monitored_stock_codes: Optional[str] = None
    alert_rise_enabled: Optional[bool] = None
    alert_rise_pct: Optional[float] = None
    alert_fall_enabled: Optional[bool] = None
    alert_fall_pct: Optional[float] = None
    alert_reach_high_enabled: Optional[bool] = None
    alert_reach_low_enabled: Optional[bool] = None
    alert_swing_enabled: Optional[bool] = None
    alert_swing_minutes: Optional[int] = None
    alert_swing_pct: Optional[float] = None
    alert_cooldown_minutes: Optional[int] = None
    alert_funds_enabled: Optional[bool] = None
    alert_monitored_fund_codes: Optional[str] = None
    alert_fund_rise_enabled: Optional[bool] = None
    alert_fund_rise_pct: Optional[float] = None
    alert_fund_fall_enabled: Optional[bool] = None
    alert_fund_fall_pct: Optional[float] = None
    alert_fund_swing_enabled: Optional[bool] = None
    alert_fund_swing_minutes: Optional[int] = None
    alert_fund_swing_pct: Optional[float] = None
    calendar_birth_date: Optional[str] = None
    calendar_birth_time: Optional[str] = None
    calendar_calendar_type: Optional[str] = None
    calendar_gender: Optional[str] = None
    calendar_birth_province: Optional[str] = None
    calendar_birth_city: Optional[str] = None
    calendar_birth_longitude: Optional[float] = None
    calendar_true_solar_time: Optional[str] = None
    calendar_zodiac: Optional[str] = None
    calendar_constellation: Optional[str] = None
    calendar_wuxing_counts: Optional[str] = None
    calendar_bazi_year: Optional[str] = None
    calendar_bazi_month: Optional[str] = None
    calendar_bazi_day: Optional[str] = None
    calendar_bazi_hour: Optional[str] = None
    calendar_bazi_day_master: Optional[str] = None
    calendar_bazi_favorable: Optional[str] = None
    calendar_bazi_unfavorable: Optional[str] = None
    calendar_profit_display_mode: Optional[str] = None
    calendar_show_metaphysics: Optional[bool] = None
    calendar_show_auspicious: Optional[bool] = None
    calendar_show_shensha: Optional[bool] = None
    calendar_ai_enabled: Optional[bool] = None
    calendar_ai_prompt_template: Optional[str] = None
    risk_cron_enabled: Optional[bool] = None
    risk_cron_time: Optional[str] = None
    risk_default_model_id: Optional[str] = None
    risk_notify_wx: Optional[bool] = None
    risk_alert_threshold: Optional[int] = None
    data_source_provider: Optional[str] = None
    mx_api_key: Optional[str] = None
    data_analysis_max_panels: Optional[int] = None

class CalculateBaziRequest(BaseModel):
    birth_date: str # YYYY-MM-DD
    birth_time: Optional[str] = "12:00" # HH:MM
    calendar_type: Optional[str] = "solar" # 'solar' or 'lunar'
    gender: Optional[str] = "male" # 'male' or 'female'
    province: Optional[str] = "北京市"
    city: Optional[str] = "北京市"
    is_leap_month: Optional[bool] = False
    lunar_year: Optional[int] = None
    lunar_month: Optional[int] = None
    lunar_day: Optional[int] = None

class VerifyAdviceRequest(BaseModel):
    verified_status: str # 'pending', 'accurate', 'partial', 'divergent'
    verified_notes: Optional[str] = ""

class GenerateAiAdviceRequest(BaseModel):
    date: Optional[str] = None # defaults to today if omitted
    time_slot: Optional[str] = None # '早盘' / '午盘' / '收盘' / '盘后' / '前瞻推演'

class RiskModelCreate(BaseModel):
    model_id: str
    name: str
    version: Optional[str] = "v1.0"
    description: Optional[str] = ""
    category: Optional[str] = "top_warning"
    system_prompt: Optional[str] = ""
    prompt_template: str
    alert_threshold: Optional[int] = 60
    is_enabled: Optional[bool] = True
    is_default: Optional[bool] = False

class RiskModelUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    system_prompt: Optional[str] = None
    prompt_template: Optional[str] = None
    alert_threshold: Optional[int] = None
    is_enabled: Optional[bool] = None
    is_default: Optional[bool] = None

class AnalyzeManualNewsRequest(BaseModel):
    news_title: str
    news_source: Optional[str] = "央视《新闻联播》"
    news_time: Optional[str] = None
    news_content: Optional[str] = ""
    model_id: Optional[str] = "om_stw"
    push_to_wx: Optional[bool] = False

class AnalyzeCrawlNewsRequest(BaseModel):
    model_id: Optional[str] = "om_stw"
    push_to_wx: Optional[bool] = False
    limit: Optional[int] = 10

class DailyRiskSnapshotRequest(BaseModel):
    trade_date: Optional[str] = None
    risk_record_id: Optional[int] = None

class DailyRiskSyncCloseRequest(BaseModel):
    trade_date: Optional[str] = None

class DailyRiskRecordUpdate(BaseModel):
    pre_market_score: Optional[int] = None
    pre_market_level: Optional[str] = None
    pre_market_level_name: Optional[str] = None
    lead_time: Optional[str] = None
    news_title: Optional[str] = None
    news_source: Optional[str] = None
    summary: Optional[str] = None
    sh_close: Optional[float] = None
    sh_change_pct: Optional[float] = None
    sz_close: Optional[float] = None
    sz_change_pct: Optional[float] = None
    cy_close: Optional[float] = None
    cy_change_pct: Optional[float] = None
    kc_close: Optional[float] = None
    kc_change_pct: Optional[float] = None
    hs300_close: Optional[float] = None
    hs300_change_pct: Optional[float] = None
    bj50_close: Optional[float] = None
    bj50_change_pct: Optional[float] = None
    turnover_billion: Optional[float] = None
    validation_status: Optional[str] = None

