"""
Trading Strategies REST API Router.
Independent endpoints for strategy templates, fee structures, backtesting, CRUD, and live execution.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

from routers.auth import get_current_user
from services.market_service import fetch_fund_data, fetch_stock_data
from services.strategy.fee_calculator import fetch_fund_fee_structure
from services.strategy.fund_data_provider import fetch_fund_history, filter_history_by_date as filter_fund_history
from services.strategy.stock_data_provider import (
    fetch_stock_history,
    fetch_stock_minute_data,
    fetch_stock_today_timeline,
    fetch_stock_fee_structure,
    filter_history_by_date as filter_stock_history,
    format_stock_symbol
)
from services.strategy.strategy_templates import PRESET_TEMPLATES, get_preset_template
from services.strategy.backtest_engine import run_backtest
from services.strategy.tianjit_strategy import (
    compute_daily_bazi_score,
    compute_monthly_regime,
    compute_t1_lookahead_signal,
    get_next_trading_day,
)
from services.strategy.strategy_service import (
    list_user_strategies,
    get_strategy_by_id,
    create_strategy,
    update_strategy,
    delete_strategy,
    scan_strategy_signals,
    list_strategy_signals,
    execute_strategy_trade,
    list_strategy_trades
)
from database import get_settings_dict

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


# -------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------
class BacktestRequest(BaseModel):
    fund_code: Optional[str] = None
    target_code: Optional[str] = None
    asset_type: str = "fund"
    strategy_type: str = "dip_buying_profit_take"
    strategy_config: Dict[str, Any] = Field(default_factory=dict)
    fee_config: Optional[Dict[str, Any]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class StrategyCreateRequest(BaseModel):
    asset_type: str = "fund"
    target_code: str
    target_name: Optional[str] = ""
    strategy_type: str = "dip_buying_profit_take"
    name: Optional[str] = ""
    initial_capital: float = 10000.0
    current_cash: Optional[float] = 0.0
    current_shares: Optional[float] = 0.0
    total_cost: Optional[float] = 0.0
    settlement_type: str = "T+1"
    config: Dict[str, Any] = Field(default_factory=dict)
    fee_config: Optional[Dict[str, Any]] = None
    status: str = "running"


class StrategyUpdateRequest(BaseModel):
    name: Optional[str] = None
    initial_capital: Optional[float] = None
    current_cash: Optional[float] = None
    current_shares: Optional[float] = None
    total_cost: Optional[float] = None
    settlement_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    fee_config: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class TradeExecuteRequest(BaseModel):
    nav: Optional[float] = None
    amount: Optional[float] = None
    shares: Optional[float] = None


# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------
@router.get("/templates")
def get_templates():
    """Get all preset strategy templates."""
    return PRESET_TEMPLATES


@router.get("/fee-structure/{code}")
async def get_fee_structure(code: str, current_user: dict = Depends(get_current_user)):
    """Fetch real-time parsed fee structures for a fund."""
    fees = await fetch_fund_fee_structure(code)
    return fees


@router.get("/stock-fee-structure/{code}")
async def get_stock_fee_structure(code: str, current_user: dict = Depends(get_current_user)):
    """Fetch real-time parsed fee structures for a stock."""
    fees = await fetch_stock_fee_structure(code)
    return fees


@router.get("/history/{code}")
async def get_history(
    code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get historical NAV data for a fund."""
    try:
        data = await fetch_fund_history(code)
        if start_date or end_date:
            filtered_history = filter_fund_history(data["history"], start_date, end_date)
            return {
                **data,
                "history": filtered_history,
                "data_count": len(filtered_history)
            }
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取基金历史数据失败: {str(e)}")


@router.get("/stock-history/{code}")
async def get_stock_history(
    code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get historical K-line data for a stock."""
    try:
        data = await fetch_stock_history(code)
        if start_date or end_date:
            filtered_history = filter_stock_history(data["history"], start_date, end_date)
            return {
                **data,
                "history": filtered_history,
                "data_count": len(filtered_history)
            }
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取股票历史数据失败: {str(e)}")


@router.get("/stock-timeline/{code}")
async def get_stock_timeline(code: str, current_user: dict = Depends(get_current_user)):
    """Get real-time today 1-minute time-share points with VWAP for a stock."""
    try:
        data = await fetch_stock_today_timeline(code)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取股票分时数据失败: {str(e)}")


@router.get("/stock-minute-history/{code}")
async def get_stock_minute_history(
    code: str,
    period: str = Query("m1", description="m1, m5, m15, m30, m60"),
    count: int = Query(640, description="Number of bars"),
    current_user: dict = Depends(get_current_user)
):
    """Get historical minute K-lines for a stock."""
    try:
        data = await fetch_stock_minute_data(code, period=period, count=count)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取股票分钟K线失败: {str(e)}")


@router.post("/backtest")
async def execute_backtest(req: BacktestRequest, current_user: dict = Depends(get_current_user)):
    """Execute strategy backtesting on historical fund/stock data."""
    try:
        code = req.target_code or req.fund_code
        if not code:
            raise ValueError("必须提供回测标的代码")

        is_stock = (req.asset_type == "stock") or req.strategy_type.startswith("stock_")

        if is_stock:
            # 1. Fetch stock history
            stock_data = await fetch_stock_history(code)
            target_name = stock_data.get("name", code)

            # 2. Stock fee structure
            fee_cfg = req.fee_config or await fetch_stock_fee_structure(code)
            if req.strategy_type in ("tianjit", "stock_tianjit"):
                fee_cfg = {**fee_cfg, "_bazi_settings": get_settings_dict(current_user["id"])}

            # 3. Run backtest engine with stock rules
            res = run_backtest(
                fund_code=code,
                fund_name=target_name,
                history_data=stock_data.get("history", []),
                strategy_type=req.strategy_type,
                strategy_config=req.strategy_config,
                fee_config=fee_cfg,
                start_date=req.start_date,
                end_date=req.end_date,
                asset_type="stock"
            )
            return res
        else:
            # 1. Fetch fund history
            fund_history_data = await fetch_fund_history(code)
            fund_name = fund_history_data.get("name", code)

            # 2. If fee config not supplied or incomplete, fetch automatically
            fee_cfg = req.fee_config
            if not fee_cfg or "redemption_tiers" not in fee_cfg:
                auto_fee = await fetch_fund_fee_structure(code)
                fee_cfg = auto_fee
            if req.strategy_type in ("tianjit", "stock_tianjit"):
                fee_cfg = {**fee_cfg, "_bazi_settings": get_settings_dict(current_user["id"])}

            # 3. Run backtest engine
            res = run_backtest(
                fund_code=code,
                fund_name=fund_name,
                history_data=fund_history_data.get("history", []),
                strategy_type=req.strategy_type,
                strategy_config=req.strategy_config,
                fee_config=fee_cfg,
                start_date=req.start_date,
                end_date=req.end_date,
                asset_type="fund"
            )
            return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"回测执行失败: {str(e)}")


@router.get("")
async def get_user_strategies(
    asset_type: Optional[str] = Query("fund"),
    current_user: dict = Depends(get_current_user)
):
    """List all strategies of current user with latest market valuation & today's signals."""
    user_id = current_user["id"]
    strategies = list_user_strategies(user_id, asset_type)

    if not strategies:
        return []

    # Enrich with latest market prices
    if asset_type == "stock":
        codes = list(set([s["target_code"] for s in strategies]))
        symbols = [format_stock_symbol(c) for c in codes]
        stock_quotes = await fetch_stock_data(symbols)
    else:
        codes = list(set([s["target_code"] for s in strategies if s["asset_type"] == "fund"]))
        market_data = await fetch_fund_data(codes)

    # Get today's pending signals
    signals = list_strategy_signals(user_id, status="pending")
    signals_by_strat = {sig["strategy_id"]: sig for sig in signals}

    enriched = []
    for s in strategies:
        code = s["target_code"]
        if asset_type == "stock":
            sym = format_stock_symbol(code)
            m = stock_quotes.get(sym, {})
            cur_nav = float(m.get("current", 0.0))
            change_pct = float(m.get("change_pct", 0.0))
            nav_type = "实时股票现价"
        else:
            m = market_data.get(code, {})
            cur_nav = float(m.get("current_nav", 0.0))
            change_pct = float(m.get("change_pct", 0.0))
            nav_type = m.get("nav_type", "官方净值")

        shares = float(s.get("current_shares", 0.0))
        cash = float(s.get("current_cash", 0.0))
        cost = float(s.get("total_cost", 0.0))
        market_value = round(shares * cur_nav, 2)
        total_assets = round(cash + market_value, 2)

        floating_pnl = round(market_value - cost, 2)
        floating_pnl_pct = round((cur_nav - (cost / shares)) / (cost / shares) * 100.0, 2) if shares > 0 and cost > 0 else 0.0

        init_cap = float(s.get("initial_capital", 10000.0))
        total_pnl = round(total_assets - init_cap, 2)
        total_pnl_pct = round(total_pnl / init_cap * 100.0, 2) if init_cap > 0 else 0.0

        # Calculate current stage target profit point details
        cfg = s.get("config", {})
        target_pct = float(
            cfg.get("cumulative_profit_target_pct") or
            cfg.get("target_profit_pct") or
            cfg.get("grid_step_up_pct") or
            0.0
        )
        if not target_pct and cfg.get("sell_rules"):
            for sr in cfg.get("sell_rules", []):
                if sr.get("type") in ("cumulative_profit", "target_profit") and sr.get("enabled", True):
                    target_pct = float(sr.get("threshold_pct") or 0.0)
                    break

        target_sell_ratio = float(
            cfg.get("cumulative_profit_sell_ratio") or
            cfg.get("target_sell_ratio") or
            0.3333
        )
        cost_price = (cost / shares) if (shares > 0 and cost > 0) else 0.0
        target_price = cost_price * (1.0 + target_pct / 100.0) if (cost_price > 0 and target_pct > 0) else 0.0
        gap_pct = round(target_pct - floating_pnl_pct, 2) if target_pct > 0 else 0.0
        gap_price = round(target_price - cur_nav, 4) if (target_price > 0 and cur_nav > 0) else 0.0
        is_reached = bool(floating_pnl_pct >= target_pct) if (shares > 0 and target_pct > 0) else False
        progress_pct = min(100.0, max(0.0, round(floating_pnl_pct / target_pct * 100.0, 1))) if (target_pct > 0 and floating_pnl_pct > 0) else 0.0

        target_profit_info = {
            "target_pct": target_pct,
            "target_sell_ratio": target_sell_ratio,
            "cost_price": round(cost_price, 4),
            "target_price": round(target_price, 4),
            "current_nav": round(cur_nav, 4),
            "has_holding": shares > 0,
            "gap_pct": gap_pct,
            "gap_price": gap_price,
            "is_reached": is_reached,
            "progress_pct": progress_pct,
            "reset_on_sell": bool(cfg.get("cumulative_reset_on_sell", cfg.get("reset_profit_on_sell", True)))
        }

        enriched.append({
            **s,
            "market_nav": cur_nav,
            "day_change_pct": change_pct,
            "nav_type": nav_type,
            "market_value": market_value,
            "total_assets": total_assets,
            "floating_pnl": floating_pnl,
            "floating_pnl_pct": floating_pnl_pct,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "target_profit_info": target_profit_info,
            "pending_signal": signals_by_strat.get(s["id"])
        })

    return enriched


@router.post("")
async def create_user_strategy(req: StrategyCreateRequest, current_user: dict = Depends(get_current_user)):
    """Create a new strategy."""
    strat = await create_strategy(req.model_dump(), current_user["id"])
    return strat


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: int, current_user: dict = Depends(get_current_user)):
    """Get single strategy details."""
    strat = get_strategy_by_id(strategy_id, current_user["id"])
    if not strat:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strat


@router.put("/{strategy_id}")
async def update_user_strategy(strategy_id: int, req: StrategyUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Update strategy."""
    strat = update_strategy(strategy_id, req.model_dump(exclude_unset=True), current_user["id"])
    if not strat:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strat


@router.delete("/{strategy_id}")
def delete_user_strategy(strategy_id: int, current_user: dict = Depends(get_current_user)):
    """Delete strategy."""
    delete_strategy(strategy_id, current_user["id"])
    return {"success": True}


@router.post("/scan-signals")
async def scan_signals(current_user: dict = Depends(get_current_user)):
    """Manually trigger daily signal scan for user's active strategies."""
    sigs = await scan_strategy_signals(current_user["id"])
    return {"success": True, "count": len(sigs), "signals": sigs}


@router.get("/signals/list")
def get_signals(status: Optional[str] = "pending", current_user: dict = Depends(get_current_user)):
    """List signals."""
    return list_strategy_signals(current_user["id"], status)


@router.post("/signals/{signal_id}/execute")
def execute_signal(signal_id: int, req: TradeExecuteRequest, current_user: dict = Depends(get_current_user)):
    """Confirm and execute a signal into the trade book."""
    try:
        res = execute_strategy_trade(signal_id, current_user["id"], req.model_dump(exclude_unset=True))
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{strategy_id}/trades")
def get_trades(strategy_id: int, current_user: dict = Depends(get_current_user)):
    """List trade records of a strategy."""
    return list_strategy_trades(strategy_id, current_user["id"])


# -------------------------------------------------------------
# TianJi TimingStrategy — 专属接口
# -------------------------------------------------------------

@router.get("/tianjit/daily-score")
def get_tianjit_daily_score(
    date: Optional[str] = Query(None, description="YYYY-MM-DD，默认今日"),
    current_user: dict = Depends(get_current_user),
):
    """
    返回指定日期的天机时空策略综合评分详情（流日干支、十神、神煞、四层信号分析）。
    同时返回次日（下一交易日）前瞻评分，便于前端展示「明日预告」。
    """
    from datetime import date as date_cls
    try:
        target_date = date_cls.fromisoformat(date) if date else date_cls.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")

    settings = get_settings_dict(current_user["id"])
    cfg = {}  # 使用默认权重；前端可在 query 中传入 strategy_id 获取自定义权重

    today_score = compute_daily_bazi_score(target_date, settings, cfg)
    monthly_regime = compute_monthly_regime(target_date.year, target_date.month, settings, cfg, as_of=target_date)

    # 计算次日前瞻（严格基于下一开市交易日历法推算，自动跳过周末与法定节假日）
    from services.trading_calendar import get_next_trading_day_info
    next_info = get_next_trading_day_info(target_date, max_lookahead=20)
    tomorrow = date_cls.fromisoformat(next_info["next_trading_date"]) if next_info.get("next_trading_date") else None
    tomorrow_score = compute_daily_bazi_score(tomorrow, settings, cfg) if tomorrow else None

    return {
        "date": target_date.isoformat(),
        "today": today_score,
        "monthly_regime": monthly_regime,
        "tomorrow": tomorrow_score,
        "next_trading_day_info": next_info,
        "t1_preview": {
            "tomorrow_date": tomorrow.isoformat() if tomorrow else None,
            "tomorrow_ganzhi": tomorrow_score["ganzhi"] if tomorrow_score else None,
            "tomorrow_score": tomorrow_score["score"] if tomorrow_score else None,
            "tomorrow_signal_level": tomorrow_score["signal_level"] if tomorrow_score else None,
            "tomorrow_rating": tomorrow_score["rating"] if tomorrow_score else None,
            "tomorrow_shenshas": tomorrow_score["shensha_names"] if tomorrow_score else [],
            # 下一实际交易日增强字段
            "next_trading_date": tomorrow.isoformat() if tomorrow else None,
            "next_trading_label": next_info.get("display_label", ""),
            "next_trading_weekday": next_info.get("weekday_cn", ""),
            "is_weekend_skipped": next_info.get("is_weekend_skipped", False),
            "skip_reason": next_info.get("skip_reason", ""),
            "days_ahead": next_info.get("days_ahead", 1),
        }
    }


async def run_strategy_backtest(req: BacktestRequest, current_user: dict = Depends(get_current_user)):
    """Run strategy backtest (overrides base route to inject bazi settings for tianjit)."""
    code = req.fund_code or req.target_code
    if not code:
        raise HTTPException(status_code=400, detail="fund_code or target_code required")

    asset_type   = req.asset_type or "fund"
    strategy_type = req.strategy_type or "dip_buying_profit_take"
    fee_config   = req.fee_config or {}

    # 为天机时空策略注入系统设置（命盘参数）
    if strategy_type in ("tianjit", "stock_tianjit"):
        settings = get_settings_dict(current_user["id"])
        fee_config["_bazi_settings"] = settings

    if asset_type == "stock":
        from services.strategy.stock_data_provider import (
            fetch_stock_history, filter_history_by_date as filter_stock_history, format_stock_symbol
        )
        sym = format_stock_symbol(code)
        history = await fetch_stock_history(sym)
        if req.start_date or req.end_date:
            history = filter_stock_history(history, req.start_date, req.end_date)
        try:
            sdata = await fetch_stock_data([sym])
            fund_name = sdata.get(sym, {}).get("name") or sym
        except Exception:
            fund_name = sym
    else:
        from services.strategy.fund_data_provider import fetch_fund_history, filter_history_by_date as filter_fund_history
        h_res = await fetch_fund_history(code)
        history = h_res.get("history", []) if isinstance(h_res, dict) else (h_res or [])
        if req.start_date or req.end_date:
            history = filter_fund_history(history, req.start_date, req.end_date)
        try:
            fdata = await fetch_fund_data([code])
            fund_name = fdata.get(code, {}).get("name") or code
        except Exception:
            fund_name = code

    result = run_backtest(
        fund_code=code,
        fund_name=fund_name,
        history_data=history,
        strategy_type=strategy_type,
        strategy_config=req.strategy_config,
        fee_config=fee_config,
        start_date=req.start_date,
        end_date=req.end_date,
        asset_type=asset_type,
    )
    return result
