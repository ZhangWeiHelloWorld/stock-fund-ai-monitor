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


