"""
Strategy Service: Manages Live Strategies, Signal Generation, and Execution.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from database import DB_PATH
from services.market_service import fetch_fund_data, fetch_stock_data
from services.strategy.fee_calculator import (
    calculate_subscription,
    calculate_redemption,
    get_redemption_fee_rate,
    calculate_holding_days,
    fetch_fund_fee_structure,
    DEFAULT_REDEMPTION_TIERS,
    DEFAULT_SUBSCRIPTION_RATE
)
from services.strategy.stock_data_provider import (
    calculate_stock_trade_fee,
    format_stock_symbol,
    fetch_stock_fee_structure,
    DEFAULT_STOCK_FEE_STRUCTURE
)
from services.wxwork_service import send_wxwork_message
from database import get_settings_dict


def init_strategy_tables():
    """Create trading_strategies, strategy_trades, and strategy_signals tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Strategies Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trading_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            asset_type TEXT NOT NULL DEFAULT 'fund',
            target_code TEXT NOT NULL,
            target_name TEXT NOT NULL,
            strategy_type TEXT NOT NULL,
            name TEXT NOT NULL,
            initial_capital REAL NOT NULL DEFAULT 10000.0,
            current_cash REAL NOT NULL DEFAULT 0.0,
            current_shares REAL NOT NULL DEFAULT 0.0,
            total_cost REAL NOT NULL DEFAULT 0.0,
            settlement_type TEXT NOT NULL DEFAULT 'T+1',
            config_json TEXT NOT NULL,
            fee_config_json TEXT,
            status TEXT NOT NULL DEFAULT 'running',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')

    # 2. Strategy Trades Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS strategy_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            trade_date TEXT NOT NULL,
            action TEXT NOT NULL,
            action_label TEXT,
            nav_or_price REAL NOT NULL,
            gross_amount REAL NOT NULL,
            net_amount REAL NOT NULL,
            shares REAL NOT NULL,
            fee REAL NOT NULL DEFAULT 0.0,
            holding_days INTEGER DEFAULT 0,
            trigger_reason TEXT,
            created_at TEXT NOT NULL
        )
    ''')

    # 3. Strategy Signals Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS strategy_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            signal_date TEXT NOT NULL,
            action TEXT NOT NULL,
            suggested_amount REAL DEFAULT 0.0,
            suggested_shares REAL DEFAULT 0.0,
            current_nav REAL NOT NULL,
            change_pct REAL DEFAULT 0.0,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def list_user_strategies(user_id: int, asset_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all strategies for a given user."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if asset_type:
        cursor.execute("SELECT * FROM trading_strategies WHERE user_id = ? AND asset_type = ? ORDER BY id DESC", (user_id, asset_type))
    else:
        cursor.execute("SELECT * FROM trading_strategies WHERE user_id = ? ORDER BY id DESC", (user_id,))

    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        item = dict(r)
        try:
            item["config"] = json.loads(item.get("config_json") or "{}")
        except Exception:
            item["config"] = {}
        try:
            item["fee_config"] = json.loads(item.get("fee_config_json") or "{}")
        except Exception:
            item["fee_config"] = {}
        result.append(item)
    return result


def get_strategy_by_id(strategy_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve strategy details by ID."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trading_strategies WHERE id = ? AND user_id = ?", (strategy_id, user_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    item = dict(row)
    try:
        item["config"] = json.loads(item.get("config_json") or "{}")
    except Exception:
        item["config"] = {}
    try:
        item["fee_config"] = json.loads(item.get("fee_config_json") or "{}")
    except Exception:
        item["fee_config"] = {}
    return item


async def create_strategy(data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    """Create a new trading strategy for user."""
    code = data.get("target_code", "").strip()
    name = data.get("target_name", "").strip()
    asset_type = data.get("asset_type", "fund")

    if not name:
        if asset_type == "stock":
            sym = format_stock_symbol(code)
            sdata = await fetch_stock_data([sym])
            name = sdata.get(sym, {}).get("name") or code
        else:
            # Lookup fund name
            mdata = await fetch_fund_data([code])
            name = mdata.get(code, {}).get("name") or code

    strategy_type = data.get("strategy_type", "dip_buying_profit_take")
    strat_name = data.get("name") or f"{name} - {strategy_type}"
    initial_capital = float(data.get("initial_capital", 10000.0))
    current_shares = float(data.get("current_shares", 0.0))
    current_cash = float(data.get("current_cash", 0.0))
    total_cost = float(data.get("total_cost", initial_capital if current_shares > 0 else 0.0))
    settlement_type = data.get("settlement_type", "T+1")
    config = data.get("config", {})
    fee_config = data.get("fee_config", {})

    now_iso = datetime.now().isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO trading_strategies (
            user_id, asset_type, target_code, target_name, strategy_type, name,
            initial_capital, current_cash, current_shares, total_cost,
            settlement_type, config_json, fee_config_json, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        data.get("asset_type", "fund"),
        code,
        name,
        strategy_type,
        strat_name,
        initial_capital,
        current_cash,
        current_shares,
        total_cost,
        settlement_type,
        json.dumps(config, ensure_ascii=False),
        json.dumps(fee_config, ensure_ascii=False),
        data.get("status", "running"),
        now_iso,
        now_iso
    ))

    strat_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return get_strategy_by_id(strat_id, user_id)


def update_strategy(strategy_id: int, data: Dict[str, Any], user_id: int) -> Optional[Dict[str, Any]]:
    """Update existing strategy fields."""
    existing = get_strategy_by_id(strategy_id, user_id)
    if not existing:
        return None

    now_iso = datetime.now().isoformat()
    fields = []
    values = []

    for k in ["name", "initial_capital", "current_cash", "current_shares", "total_cost", "settlement_type", "status"]:
        if k in data:
            fields.append(f"{k} = ?")
            values.append(data[k])

    if "config" in data:
        fields.append("config_json = ?")
        values.append(json.dumps(data["config"], ensure_ascii=False))

    if "fee_config" in data:
        fields.append("fee_config_json = ?")
        values.append(json.dumps(data["fee_config"], ensure_ascii=False))

    fields.append("updated_at = ?")
    values.append(now_iso)

    values.extend([strategy_id, user_id])

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE trading_strategies SET {', '.join(fields)} WHERE id = ? AND user_id = ?", values)
    conn.commit()
    conn.close()

    return get_strategy_by_id(strategy_id, user_id)


def delete_strategy(strategy_id: int, user_id: int) -> bool:
    """Delete strategy and its associated signals & trades."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trading_strategies WHERE id = ? AND user_id = ?", (strategy_id, user_id))
    cursor.execute("DELETE FROM strategy_signals WHERE strategy_id = ? AND user_id = ?", (strategy_id, user_id))
    cursor.execute("DELETE FROM strategy_trades WHERE strategy_id = ? AND user_id = ?", (strategy_id, user_id))
    conn.commit()
    conn.close()
    return True


async def scan_strategy_signals(user_id: int) -> List[Dict[str, Any]]:
    """
    Scan all active strategies for user, comparing latest market data with strategy trigger rules.
    Supports both Fund and Stock strategies.
    Returns list of generated or pending signals.
    """
    strategies = list_user_strategies(user_id)
    active_strategies = [s for s in strategies if s.get("status") == "running"]
    if not active_strategies:
        return []

    fund_codes = list(set([s["target_code"] for s in active_strategies if s.get("asset_type", "fund") == "fund"]))
    stock_codes = list(set([s["target_code"] for s in active_strategies if s.get("asset_type") == "stock"]))

    fund_market_data = await fetch_fund_data(fund_codes) if fund_codes else {}
    stock_symbols = [format_stock_symbol(c) for c in stock_codes]
    stock_market_data = await fetch_stock_data(stock_symbols) if stock_symbols else {}
    today_str = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    generated_signals = []

    for strat in active_strategies:
        sid = strat["id"]
        code = strat["target_code"]
        name = strat["target_name"]
        stype = strat["strategy_type"]
        asset_type = strat.get("asset_type", "fund")
        is_stock = (asset_type == "stock") or stype.startswith("stock_")

        norm_stype = stype
        if stype.startswith("stock_"):
            suffix = stype[6:]
            if suffix in ("dip_profit_take", "dip_buying_profit_take"):
                norm_stype = "dip_buying_profit_take"
            elif suffix in ("intraday_t", "t_strategy"):
                norm_stype = "intraday_t"
            else:
                norm_stype = suffix

        cfg = strat.get("config", {})
        cur_shares = float(strat.get("current_shares", 0.0))
        tot_cost = float(strat.get("total_cost", 0.0))
        avg_cost = tot_cost / cur_shares if cur_shares > 0 else 0.0

        if is_stock:
            sym = format_stock_symbol(code)
            m_item = stock_market_data.get(sym, {})
            cur_nav = float(m_item.get("current", 0.0))
            change_pct = float(m_item.get("change_pct", 0.0))
        else:
            m_item = fund_market_data.get(code, {})
            cur_nav = float(m_item.get("current_nav", 0.0))
            change_pct = float(m_item.get("change_pct", 0.0))

        if cur_nav <= 0:
            continue

        cum_profit_pct = (cur_nav - avg_cost) / avg_cost * 100.0 if avg_cost > 0 else 0.0

        # Check existing pending signal for today
        cursor.execute("SELECT * FROM strategy_signals WHERE strategy_id = ? AND signal_date = ? AND status = 'pending'", (sid, today_str))
        existing_sig = cursor.fetchone()

        signal_action = None
        suggested_amt = 0.0
        suggested_shares = 0.0
        signal_reason = ""

        # Strategy Rules
        if norm_stype == "dip_buying_profit_take":
            def eval_tier_op(actual_val: float, op: str, threshold: float) -> bool:
                op = (op or ">=").strip()
                if op in (">=", "≥", "gte"):
                    return actual_val >= threshold - 1e-6
                elif op in (">", "gt"):
                    return actual_val > threshold + 1e-6
                elif op in ("<=", "≤", "lte"):
                    return actual_val <= threshold + 1e-6
                elif op in ("<", "lt"):
                    return actual_val < threshold - 1e-6
                elif op in ("=", "==", "eq"):
                    return abs(actual_val - threshold) < 0.05
                return actual_val >= threshold

            raw_buy = cfg.get("buy_tiers") or cfg.get("dip_buy_tiers")
            drop_tiers = []
            rise_tiers = []
            routine_tier = None

            if raw_buy is not None and isinstance(raw_buy, list):
                for t in raw_buy:
                    t_amt = float(t.get("amount", 0.0))
                    if t_amt < 0:
                        continue
                    t_type = t.get("type")
                    if not t_type:
                        if "rise_pct" in t or t.get("is_rise"):
                            t_type = "rise"
                        elif t.get("is_routine") or ("drop_pct" not in t and "threshold_pct" not in t):
                            t_type = "routine"
                        else:
                            t_type = "drop"

                    t_op = t.get("operator") or t.get("op")
                    if t_type == "drop":
                        d_val = float(t.get("drop_pct", t.get("threshold_pct", 2.0)))
                        op = t_op or ">="
                        drop_tiers.append({**t, "type": "drop", "operator": op, "drop_pct": d_val, "amount": t_amt})
                    elif t_type == "rise":
                        r_val = float(t.get("rise_pct", t.get("threshold_pct", 1.5)))
                        op = t_op or "<="
                        rise_tiers.append({**t, "type": "rise", "operator": op, "rise_pct": r_val, "amount": t_amt})
                    elif t_type == "routine":
                        if routine_tier is None or t_amt > float(routine_tier.get("amount", 0.0)):
                            routine_tier = {**t, "type": "routine", "amount": t_amt}

            elif "dip_buy_drop_pct" in cfg and cfg.get("dip_buy_drop_pct") is not None:
                drop_tiers = [{"type": "drop", "operator": ">=", "drop_pct": float(cfg.get("dip_buy_drop_pct", 2.0)), "amount": float(cfg.get("dip_buy_amount", 5000.0))}]

            raw_surge = cfg.get("surge_profit_tiers")
            if raw_surge is not None and isinstance(raw_surge, list):
                surge_tiers = sorted([t for t in raw_surge if float(t.get("sell_ratio", 0.0)) > 0], key=lambda x: float(x.get("surge_pct", 0.0)), reverse=True)
            elif "surge_profit_pct" in cfg and cfg.get("surge_profit_pct") is not None:
                surge_tiers = [{"surge_pct": float(cfg.get("surge_profit_pct", 7.0)), "sell_ratio": float(cfg.get("surge_profit_sell_ratio", 0.25))}]
            else:
                surge_tiers = []

            target_profit_th = float(cfg.get("cumulative_profit_target_pct") or 0.0)
            target_sell_r = float(cfg.get("cumulative_profit_sell_ratio") or 0.0)

            matched_surge = None
            if cur_shares > 1e-4:
                for st in surge_tiers:
                    s_pct = float(st.get("surge_pct", 0.0))
                    s_r = float(st.get("sell_ratio", 0.0))
                    if change_pct >= s_pct and s_r > 0:
                        matched_surge = st
                        break

            if matched_surge:
                signal_action = "SELL"
                s_r = float(matched_surge.get("sell_ratio", 0.25))
                suggested_shares = round(cur_shares * s_r, 2)
                suggested_amt = round(suggested_shares * cur_nav, 2)
                signal_reason = f"【单日大涨阶梯止盈】今日涨幅达到 +{change_pct:.2f}% (≥ {matched_surge.get('surge_pct')}%)，建议止盈赎回约 {s_r*100:.1f}% 持仓（约 {suggested_shares:.0f} 份，¥{suggested_amt:.0f}）"
            elif target_profit_th > 0 and target_sell_r > 0 and cum_profit_pct >= target_profit_th and cur_shares > 1e-4:
                signal_action = "SELL"
                suggested_shares = round(cur_shares * target_sell_r, 2)
                suggested_amt = round(suggested_shares * cur_nav, 2)
                signal_reason = f"【本轮累计收益达标】当前浮盈达到 +{cum_profit_pct:.2f}% (≥ {target_profit_th}%)，建议阶梯止盈卖出约 {target_sell_r*100:.1f}% 持仓（约 {suggested_shares:.0f} 份，¥{suggested_amt:.0f}）"
            else:
                matched_drop = None
                matched_rise = None

                if change_pct <= 0 and drop_tiers:
                    actual_drop = -change_pct
                    matching_drops = []
                    for dt in drop_tiers:
                        op = dt.get("operator", ">=")
                        d_val = float(dt.get("drop_pct", 0.0))
                        if eval_tier_op(actual_drop, op, d_val):
                            matching_drops.append(dt)
                    if matching_drops:
                        matching_drops.sort(key=lambda x: (
                            0 if x.get("operator") in (">=", ">", "≥") else 1,
                            -float(x.get("drop_pct", 0)) if x.get("operator") in (">=", ">", "≥") else float(x.get("drop_pct", 0))
                        ))
                        matched_drop = matching_drops[0]

                # Check rise tiers if market rose or flat
                if change_pct >= 0 and not matched_drop and rise_tiers:
                    actual_rise = change_pct
                    matching_rises = []
                    for rt in rise_tiers:
                        op = rt.get("operator", "<=")
                        r_val = float(rt.get("rise_pct", 0.0))
                        if eval_tier_op(actual_rise, op, r_val):
                            matching_rises.append(rt)
                    if matching_rises:
                        matching_rises.sort(key=lambda x: (
                            0 if x.get("operator") in (">=", ">", "≥") else 1,
                            -float(x.get("rise_pct", 0)) if x.get("operator") in (">=", ">", "≥") else float(x.get("rise_pct", 0))
                        ))
                        matched_rise = matching_rises[0]

                chosen_buy = None
                reason_str = ""

                if matched_drop:
                    chosen_buy = matched_drop
                    op_str = matched_drop.get("operator", ">=")
                    reason_str = f"【单日下跌加仓】今日估算下跌 {change_pct:.2f}%，满足下跌 {op_str} {matched_drop.get('drop_pct')}%，建议加仓申购 ¥{chosen_buy.get('amount', 5000.0):.0f}"
                elif matched_rise:
                    chosen_buy = matched_rise
                    op_str = matched_rise.get("operator", "<=")
                    reason_str = f"【单日上涨加仓】今日估算上涨 +{change_pct:.2f}%，满足上涨 {op_str} {matched_rise.get('rise_pct')}%，建议加仓申购 ¥{chosen_buy.get('amount', 5000.0):.0f}"
                elif routine_tier and float(routine_tier.get("amount", 0.0)) > 0:
                    chosen_buy = routine_tier
                    reason_str = f"【日常底仓加仓】今日估算涨跌幅为 {change_pct:+.2f}% (未触发特殊涨跌补仓条件)，触发日常加仓，建议加仓申购 ¥{chosen_buy.get('amount', 5000.0):.0f}"

                if chosen_buy:
                    b_amt = float(chosen_buy.get("amount", 0.0))
                    if b_amt > 0:
                        signal_action = "BUY"
                        suggested_amt = b_amt
                        if is_stock:
                            lot_s = int(b_amt / cur_nav / 100) * 100 if cur_nav > 0 else 0
                            if lot_s < 100 and b_amt >= cur_nav * 50:
                                lot_s = 100
                            suggested_shares = float(lot_s)
                            suggested_amt = round(lot_s * cur_nav, 2)
                        else:
                            suggested_shares = round(b_amt / cur_nav, 2)
                        signal_reason = reason_str

        elif norm_stype == "target_profit_dca":
            target_p = float(cfg.get("target_profit_pct", 15.0))
            target_sell_r = float(cfg.get("target_sell_ratio", 1.0))
            dca_amt = float(cfg.get("dca_amount", 1000.0))

            if cum_profit_pct >= target_p and cur_shares > 0:
                signal_action = "SELL"
                if is_stock:
                    lot_s = int(cur_shares * target_sell_r / 100) * 100
                    if target_sell_r >= 0.999 or lot_s <= 0:
                        lot_s = cur_shares
                    suggested_shares = float(lot_s)
                else:
                    suggested_shares = round(cur_shares * target_sell_r, 2)
                suggested_amt = round(suggested_shares * cur_nav, 2)
                signal_reason = f"【定投目标止盈】累计收益达到 +{cum_profit_pct:.2f}% (≥ {target_p}%)，建议止盈锁定收益 ¥{suggested_amt:.0f}"

        elif norm_stype in ("intraday_t", "stock_intraday_t"):
            t_surge_pct = float(cfg.get("t_surge_sell_pct", 1.8))
            t_sell_shares_cfg = float(cfg.get("t_sell_shares", 300.0))
            t_pullback_pct = float(cfg.get("t_pullback_buy_pct", 1.5))
            base_protect_shares = float(cfg.get("base_protect_shares", 0.0))
            stop_loss_pct = float(cfg.get("stop_loss_pct", 10.0))
            target_profit_th = float(cfg.get("cumulative_profit_target_pct") or 0.0)
            target_sell_r = float(cfg.get("cumulative_profit_sell_ratio") or 0.5)

            # Query today's trades for this strategy
            cursor.execute("SELECT * FROM strategy_trades WHERE strategy_id = ? AND trade_date = ?", (sid, today_str))
            today_trades = [dict(r) for r in cursor.fetchall()]
            today_t_sells = [t for t in today_trades if t.get("action") == "SELL" and "做T高抛" in (t.get("action_label") or "")]
            today_t_buys = [t for t in today_trades if t.get("action") == "BUY" and "做T低吸" in (t.get("action_label") or "")]

            tot_sold_s = sum(float(t.get("shares", 0.0)) for t in today_t_sells)
            tot_bought_s = sum(float(t.get("shares", 0.0)) for t in today_t_buys)
            free_t_shares = max(0.0, cur_shares - base_protect_shares)

            # 1. Hard Stop Loss
            if stop_loss_pct > 0 and cum_profit_pct <= -abs(stop_loss_pct) and cur_shares > 0:
                signal_action = "SELL"
                suggested_shares = cur_shares
                suggested_amt = round(cur_shares * cur_nav, 2)
                signal_reason = f"【硬止损防守】当前浮亏已达 {cum_profit_pct:.2f}% (≤ -{stop_loss_pct}%)，建议止损清仓避险"

            # 2. Cumulative Target Profit
            elif target_profit_th > 0 and cum_profit_pct >= target_profit_th and cur_shares > 0:
                target_s = int(cur_shares * target_sell_r / 100) * 100
                if target_s >= 100:
                    signal_action = "SELL"
                    suggested_shares = float(target_s)
                    suggested_amt = round(target_s * cur_nav, 2)
                    signal_reason = f"【累计收益达标】当前浮盈达 +{cum_profit_pct:.2f}% (≥ {target_profit_th}%)，建议阶段止盈卖出约 ¥{suggested_amt:.0f}"

            # 3. Pullback Buy-back (做T回踩接回) if sold earlier today
            elif bool(cfg.get("enable_pullback_buyback", True)) and tot_sold_s > tot_bought_s and today_t_sells:
                last_sell = today_t_sells[-1]
                sell_p = float(last_sell.get("nav_or_price", 0.0))
                pullback_ref = cfg.get("pullback_ref_type", "from_sell_price")
                
                is_buyback_triggered = False
                reason_detail = ""

                if pullback_ref == "from_daily_change":
                    daily_drop_th = float(cfg.get("daily_drop_buyback_pct", 2.0))
                    if change_pct <= -abs(daily_drop_th):
                        is_buyback_triggered = True
                        reason_detail = f"今日整体跌幅已达 {change_pct:.2f}% (≤ -{daily_drop_th}%)"
                else:
                    t_pullback_pct = float(cfg.get("t_pullback_buy_pct", 1.5))
                    pullback_trigger_p = round(sell_p * (1 - t_pullback_pct / 100.0), 2)
                    if cur_nav <= pullback_trigger_p:
                        is_buyback_triggered = True
                        fall_pct = (sell_p - cur_nav) / sell_p * 100.0 if sell_p > 0 else 0.0
                        reason_detail = f"当前价 ¥{cur_nav:.2f} 较今日高抛价 ¥{sell_p:.2f} 回落已达 {fall_pct:.2f}% (≥ {t_pullback_pct}%)"

                if is_buyback_triggered:
                    max_buyback_s = int((tot_sold_s - tot_bought_s) / 100) * 100
                    if max_buyback_s >= 100:
                        signal_action = "BUY"
                        suggested_shares = float(max_buyback_s)
                        suggested_amt = round(max_buyback_s * cur_nav, 2)
                        signal_reason = f"【做T回踩低吸接回】{reason_detail}，建议买入接回 {suggested_shares:.0f} 股（约 ¥{suggested_amt:.0f}，买回上限 ≤ 今日已卖出 {tot_sold_s:.0f}股）"

            # 4. Surge High-Sell (分时冲高做T)
            elif free_t_shares >= 100:
                surge_p = round(avg_cost * (1 + t_surge_pct / 100.0), 2)
                if (cur_nav >= surge_p or change_pct >= t_surge_pct):
                    target_s = min(t_sell_shares_cfg, free_t_shares)
                    target_s = int(target_s / 100) * 100
                    if target_s >= 100:
                        signal_action = "SELL"
                        suggested_shares = float(target_s)
                        suggested_amt = round(target_s * cur_nav, 2)
                        up_pct = (cur_nav - avg_cost) / avg_cost * 100.0 if avg_cost > 0 else change_pct
                        signal_reason = f"【分时冲高高抛做T】当前分时价 ¥{cur_nav:.2f}（今日涨幅 +{change_pct:.2f}%），较持仓成本 ¥{avg_cost:.2f} 涨幅达到 +{up_pct:.2f}% (≥ +{t_surge_pct}%)，建议做T高抛卖出 {suggested_shares:.0f} 股（约 ¥{suggested_amt:.0f}）"

            # 5. Multi-tier Dip Buy if large drop
            if not signal_action and change_pct <= 0:
                raw_buy = cfg.get("buy_tiers")
                if raw_buy and isinstance(raw_buy, list):
                    actual_drop = -change_pct
                    matched_drops = [dt for dt in raw_buy if float(dt.get("drop_pct", 3.0)) <= actual_drop]
                    if matched_drops:
                        matched_drops.sort(key=lambda x: -float(x.get("drop_pct", 0)))
                        chosen = matched_drops[0]
                        b_amt = float(chosen.get("amount", 5000.0))
                        lot_s = int(b_amt / cur_nav / 100) * 100
                        if lot_s >= 100:
                            signal_action = "BUY"
                            suggested_shares = float(lot_s)
                            suggested_amt = round(lot_s * cur_nav, 2)
                            signal_reason = f"【单日大跌阶梯加仓】今日跌幅达 {change_pct:.2f}% (≤ -{chosen.get('drop_pct')}%)，建议阶梯加仓 {suggested_shares:.0f} 股（约 ¥{suggested_amt:.0f}）"

        if signal_action:
            now_iso = datetime.now().isoformat()
            if existing_sig:
                # Update existing pending signal
                cursor.execute('''
                    UPDATE strategy_signals SET
                        action = ?, suggested_amount = ?, suggested_shares = ?,
                        current_nav = ?, change_pct = ?, reason = ?
                    WHERE id = ?
                ''', (signal_action, suggested_amt, suggested_shares, cur_nav, change_pct, signal_reason, existing_sig['id']))
                sig_id = existing_sig['id']
            else:
                cursor.execute('''
                    INSERT INTO strategy_signals (
                        strategy_id, user_id, signal_date, action,
                        suggested_amount, suggested_shares, current_nav, change_pct,
                        reason, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                ''', (sid, user_id, today_str, signal_action, suggested_amt, suggested_shares, cur_nav, change_pct, signal_reason, now_iso))
                sig_id = cursor.lastrowid

            generated_signals.append({
                "id": sig_id,
                "strategy_id": sid,
                "strategy_name": strat["name"],
                "target_code": code,
                "target_name": name,
                "signal_date": today_str,
                "action": signal_action,
                "suggested_amount": suggested_amt,
                "suggested_shares": suggested_shares,
                "current_nav": cur_nav,
                "change_pct": change_pct,
                "reason": signal_reason,
                "status": "pending"
            })

    conn.commit()
    conn.close()
    return generated_signals


def list_strategy_signals(user_id: int, status: Optional[str] = "pending") -> List[Dict[str, Any]]:
    """List signals for user."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if status:
        cursor.execute('''
            SELECT s.*, ts.name as strategy_name, ts.target_code, ts.target_name
            FROM strategy_signals s
            LEFT JOIN trading_strategies ts ON s.strategy_id = ts.id
            WHERE s.user_id = ? AND s.status = ?
            ORDER BY s.id DESC
        ''', (user_id, status))
    else:
        cursor.execute('''
            SELECT s.*, ts.name as strategy_name, ts.target_code, ts.target_name
            FROM strategy_signals s
            LEFT JOIN trading_strategies ts ON s.strategy_id = ts.id
            WHERE s.user_id = ?
            ORDER BY s.id DESC
        ''', (user_id,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def execute_strategy_trade(signal_id: int, user_id: int, trade_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Confirm and record trade execution from a strategy signal or manual entry.
    Updates holding shares, cash, cost, and sets signal status to 'executed'.
    Supports both Fund and Stock asset types.
    """
    trade_params = trade_params or {}
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM strategy_signals WHERE id = ? AND user_id = ?", (signal_id, user_id))
    sig = cursor.fetchone()
    if not sig:
        conn.close()
        raise ValueError("信号不存在或无权限")

    sig_dict = dict(sig)
    strat_id = sig_dict["strategy_id"]

    cursor.execute("SELECT * FROM trading_strategies WHERE id = ? AND user_id = ?", (strat_id, user_id))
    strat = cursor.fetchone()
    if not strat:
        conn.close()
        raise ValueError("策略不存在")

    strat_dict = dict(strat)
    asset_type = strat_dict.get("asset_type", "fund")
    is_stock = (asset_type == "stock") or strat_dict.get("strategy_type", "").startswith("stock_")

    fee_cfg = json.loads(strat_dict.get("fee_config_json") or "{}")
    sub_rate = fee_cfg.get("subscription_rate", DEFAULT_SUBSCRIPTION_RATE)
    red_tiers = fee_cfg.get("redemption_tiers", DEFAULT_REDEMPTION_TIERS)

    nav = float(trade_params.get("nav") or sig_dict["current_nav"])
    action = sig_dict["action"]
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_iso = datetime.now().isoformat()

    cur_shares = float(strat_dict["current_shares"])
    cur_cash = float(strat_dict["current_cash"])
    tot_cost = float(strat_dict["total_cost"])

    if action == "BUY":
        gross_amt = float(trade_params.get("amount") or sig_dict["suggested_amount"])
        if is_stock:
            shares_param = float(trade_params.get("shares") or sig_dict.get("suggested_shares") or 0)
            if shares_param > 0 and not trade_params.get("amount"):
                bought_shares = shares_param
                gross_amt = round(bought_shares * nav, 2)
            else:
                bought_shares = int(gross_amt / nav / 100) * 100 if nav > 0 else 0
                if bought_shares < 100 and gross_amt >= nav * 50:
                    bought_shares = 100
                gross_amt = round(bought_shares * nav, 2)

            fee_info = calculate_stock_trade_fee("BUY", gross_amt, fee_cfg)
            fee = fee_info["total_fee"]
            net_amt = round(gross_amt + fee, 2)
        else:
            sub_res = calculate_subscription(gross_amt, nav, sub_rate)
            fee = sub_res["fee"]
            net_amt = sub_res["net_amount"]
            bought_shares = sub_res["shares"]

        new_shares = round(cur_shares + bought_shares, 4)
        new_cost = round(tot_cost + gross_amt, 2)
        new_cash = round(max(0, cur_cash - gross_amt), 2)
        action_label = "加仓买入"
        h_days = 0

    else:  # SELL
        shares_to_sell = float(trade_params.get("shares") or sig_dict["suggested_shares"])
        if shares_to_sell > cur_shares:
            shares_to_sell = cur_shares

        # Approximate holding days from strategy created date or 30 days
        strat_created = strat_dict["created_at"]
        h_days = calculate_holding_days(strat_created, today_str)

        if is_stock:
            gross_amt = round(shares_to_sell * nav, 2)
            fee_info = calculate_stock_trade_fee("SELL", gross_amt, fee_cfg)
            fee = fee_info["total_fee"]
            net_amt = round(gross_amt - fee, 2)
        else:
            red_rate = get_redemption_fee_rate(h_days, red_tiers)
            red_res = calculate_redemption(shares_to_sell, nav, red_rate)
            gross_amt = red_res["gross_amount"]
            fee = red_res["fee"]
            net_amt = red_res["net_amount"]

        new_shares = round(max(0.0, cur_shares - shares_to_sell), 4)
        strat_cfg = json.loads(strat_dict.get("config_json") or "{}")
        sig_reason = sig_dict.get("reason", "")
        
        # Check whether this specific sell condition requires reset
        reset_on_sell = False
        if "单日大涨" in sig_reason:
            surge_tiers = strat_cfg.get("surge_profit_tiers", [])
            for st in surge_tiers:
                if f"{st.get('surge_pct')}%" in sig_reason:
                    reset_on_sell = bool(st.get("reset_on_sell", False))
                    break
        elif "累计收益" in sig_reason or "本轮累计" in sig_reason or "定投" in sig_reason:
            reset_on_sell = bool(strat_cfg.get("cumulative_reset_on_sell", strat_cfg.get("reset_profit_on_sell", True)))

        if new_shares <= 1e-4:
            new_shares = 0.0
            new_cost = 0.0
        elif reset_on_sell:
            # Reset remaining cost to remaining market value so round floating profit starts from 0%
            new_cost = round(new_shares * nav, 2)
        else:
            cost_ratio = (shares_to_sell / cur_shares) if cur_shares > 0 else 1.0
            new_cost = round(max(0, tot_cost * (1.0 - cost_ratio)), 2)
        new_cash = round(cur_cash + net_amt, 2)
        action_label = "止盈卖出"

    # Insert Trade Record
    cursor.execute('''
        INSERT INTO strategy_trades (
            strategy_id, user_id, trade_date, action, action_label,
            nav_or_price, gross_amount, net_amount, shares, fee,
            holding_days, trigger_reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        strat_id, user_id, today_str, action, action_label,
        nav, gross_amt, net_amt, bought_shares if action == "BUY" else shares_to_sell,
        fee, h_days, sig_dict["reason"], now_iso
    ))

    # Update Strategy State
    cursor.execute('''
        UPDATE trading_strategies SET
            current_shares = ?, current_cash = ?, total_cost = ?, updated_at = ?
        WHERE id = ?
    ''', (new_shares, new_cash, new_cost, now_iso, strat_id))

    # Update Signal Status
    cursor.execute("UPDATE strategy_signals SET status = 'executed' WHERE id = ?", (signal_id,))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "strategy_id": strat_id,
        "action": action,
        "nav": nav,
        "shares": bought_shares if action == "BUY" else shares_to_sell,
        "gross_amount": gross_amt,
        "fee": fee,
        "net_amount": net_amt,
        "new_shares": new_shares,
        "new_cash": new_cash
    }


def list_strategy_trades(strategy_id: int, user_id: int) -> List[Dict[str, Any]]:
    """List trade history of a strategy."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM strategy_trades WHERE strategy_id = ? AND user_id = ? ORDER BY id DESC", (strategy_id, user_id))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
