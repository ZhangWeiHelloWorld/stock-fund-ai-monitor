"""
Backtest Engine for Fund Trading Strategies.
Simulates historical executions with:
1. Exact T+1 / T+2 settlement and NAV confirmation rules.
2. FIFO holding period tracking for accurate tiered redemption fees.
3. Subscription fee deductions (e.g. 0.1% Alipay discount).
4. Rich performance metrics (CAGR, Max Drawdown, Sharpe Ratio, Win Rate, Alpha).
5. Interactive timeseries equity curves and trade logs.
"""

import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from services.strategy.fee_calculator import (
    calculate_subscription,
    calculate_redemption,
    get_redemption_fee_rate,
    calculate_holding_days,
    DEFAULT_REDEMPTION_TIERS,
    DEFAULT_SUBSCRIPTION_RATE
)
from services.strategy.stock_data_provider import calculate_stock_trade_fee, DEFAULT_STOCK_FEE_STRUCTURE


def run_backtest(
    fund_code: str,
    fund_name: str,
    history_data: List[Dict[str, Any]],
    strategy_type: str,
    strategy_config: Dict[str, Any],
    fee_config: Optional[Dict[str, Any]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    asset_type: str = "fund"
) -> Dict[str, Any]:
    """
    Execute backtest simulation on historical NAV / Stock K-line data.
    Supports both Fund (open-end fund) and Stock (A-share 100-share lots & tax/commission) assets.
    """
    if not history_data or len(history_data) < 2:
        return {
            "success": False,
            "message": "历史净值数据不足，无法进行回测",
            "metrics": {},
            "equity_curve": [],
            "trades": []
        }

    is_stock = (asset_type == "stock") or strategy_type.startswith("stock_")
    # Normalize strategy_type (e.g. stock_dip_profit_take -> dip_buying_profit_take)
    norm_strategy_type = strategy_type
    if strategy_type.startswith("stock_"):
        suffix = strategy_type[6:]
        if suffix in ("dip_profit_take", "dip_buying_profit_take"):
            norm_strategy_type = "dip_buying_profit_take"
        elif suffix in ("intraday_t", "t_strategy"):
            norm_strategy_type = "intraday_t"
        else:
            norm_strategy_type = suffix

    # Filter date range
    sorted_history = sorted(history_data, key=lambda x: x["date"])
    if start_date or end_date:
        filtered = []
        for item in sorted_history:
            d = item["date"]
            if start_date and d < start_date:
                continue
            if end_date and d > end_date:
                continue
            filtered.append(item)
        sorted_history = filtered

    if len(sorted_history) < 2:
        return {
            "success": False,
            "message": "选定时间范围内的历史净值数据不足（至少需要2个交易日）",
            "metrics": {},
            "equity_curve": [],
            "trades": []
        }

    # Fee Configuration
    sub_rate = fee_config.get("subscription_rate", DEFAULT_SUBSCRIPTION_RATE) if fee_config else DEFAULT_SUBSCRIPTION_RATE
    red_tiers = fee_config.get("redemption_tiers", DEFAULT_REDEMPTION_TIERS) if fee_config else DEFAULT_REDEMPTION_TIERS

    # Strategy Parameters
    cfg = strategy_config or {}
    initial_capital = float(cfg.get("initial_capital", 10000.0))
    settlement_type = cfg.get("settlement_type", "T+1")
    settlement_offset_days = 2 if settlement_type == "T+2" else 1

    # State variables
    cash = 0.0
    total_invested = initial_capital
    holding_lots = []  # List of {'buy_date': str, 'confirm_date': str, 'shares': float, 'cost_nav': float, 'invested': float}
    trades = []
    equity_curve = []
    
    total_sub_fee = 0.0
    total_red_fee = 0.0
    winning_sells = 0
    losing_sells = 0
    total_sells = 0
    total_buys = 0

    last_buy_index = -999
    last_sell_index = -999
    last_trade_nav = sorted_history[0]["nav"]
    dca_cycle_counter = 0

    # Benchmark base nav on day 0
    benchmark_start_nav = sorted_history[0]["nav"]

    # Execute Day 0 Initial Purchase
    day0 = sorted_history[0]
    day0_date = day0["date"]
    day0_nav = float(day0["nav"])

    if is_stock:
        if norm_strategy_type == "intraday_t" and cfg.get("initial_base_shares"):
            init_shares = int(float(cfg.get("initial_base_shares", 1000)) / 100) * 100
        else:
            init_shares = int(initial_capital / day0_nav / 100) * 100
        if init_shares < 100 and initial_capital >= day0_nav * 50:
            init_shares = 100
        init_gross = round(init_shares * day0_nav, 2)
        init_fee_info = calculate_stock_trade_fee("BUY", init_gross, fee_config)
        init_fee = init_fee_info["total_fee"]
        init_net = round(init_gross + init_fee, 2)
        total_sub_fee += init_fee
        total_buys += 1
        last_buy_index = 0
        last_trade_nav = day0_nav
        total_invested = init_gross

        holding_lots.append({
            "buy_date": day0_date,
            "confirm_date": day0_date,
            "shares": float(init_shares),
            "cost_nav": day0_nav,
            "invested": init_gross
        })

        action_lbl = "初始底仓建仓" if norm_strategy_type == "intraday_t" else "初始建仓"
        rule_desc = "建立初始可卖底仓 (严格T+1，次日起可执行分时高抛)" if norm_strategy_type == "intraday_t" else "初始本金建仓"

        trades.append({
            "id": 1,
            "date": day0_date,
            "action": "BUY",
            "action_label": action_lbl,
            "nav": day0_nav,
            "open": day0.get("open", day0_nav),
            "high": day0.get("high", day0_nav),
            "low": day0.get("low", day0_nav),
            "close": day0.get("close", day0_nav),
            "change_pct": day0.get("change_pct", 0.0),
            "gross_amount": init_gross,
            "net_amount": init_net,
            "shares": float(init_shares),
            "fee": init_fee,
            "fee_breakdown": init_fee_info,
            "cost_nav_before": day0_nav,
            "cost_nav_after": day0_nav,
            "holding_days": 0,
            "rule_trigger": rule_desc,
            "cash_balance": cash,
            "holding_shares": float(init_shares),
            "market_value": round(init_shares * day0_nav, 2),
            "realized_pnl": 0.0
        })
    else:
        # Initial position allocation for fund
        sub_res = calculate_subscription(initial_capital, day0_nav, sub_rate)
        total_sub_fee += sub_res["fee"]
        total_buys += 1
        last_buy_index = 0
        last_trade_nav = day0_nav

        holding_lots.append({
            "buy_date": day0_date,
            "confirm_date": day0_date,
            "shares": sub_res["shares"],
            "cost_nav": day0_nav,
            "invested": initial_capital
        })

        trades.append({
            "id": 1,
            "date": day0_date,
            "action": "BUY",
            "action_label": "初始建仓",
            "nav": day0_nav,
            "open": day0.get("open", day0_nav),
            "high": day0.get("high", day0_nav),
            "low": day0.get("low", day0_nav),
            "close": day0.get("close", day0_nav),
            "change_pct": day0.get("change_pct", 0.0),
            "gross_amount": initial_capital,
            "net_amount": sub_res["net_amount"],
            "shares": sub_res["shares"],
            "fee": sub_res["fee"],
            "fee_breakdown": {"subscription_fee": sub_res["fee"]},
            "cost_nav_before": day0_nav,
            "cost_nav_after": day0_nav,
            "holding_days": 0,
            "rule_trigger": "初始本金建仓",
            "cash_balance": cash,
            "holding_shares": sub_res["shares"],
            "market_value": round(sub_res["shares"] * day0_nav, 2),
            "realized_pnl": 0.0
        })

    # Helper functions for holdings & round cost tracking
    round_base_cost_nav = day0_nav

    def get_current_shares():
        s = sum(lot["shares"] for lot in holding_lots)
        return round(s, 6) if s > 1e-5 else 0.0

    def get_avg_cost():
        tot_s = get_current_shares()
        if tot_s <= 1e-5:
            return 0.0
        return sum(lot["shares"] * lot["cost_nav"] for lot in holding_lots) / tot_s

    def evaluate_tier_condition(actual_val: float, op: str, threshold: float) -> bool:
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

    # Parse multi-tier buy configs (supporting drop, rise, routine with dynamic operators)
    raw_buy_tiers = cfg.get("buy_tiers") or cfg.get("dip_buy_tiers")
    drop_tiers = []
    rise_tiers = []
    routine_tier = None

    if raw_buy_tiers is not None and isinstance(raw_buy_tiers, list):
        for t in raw_buy_tiers:
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

    raw_surge_tiers = cfg.get("surge_profit_tiers")
    if raw_surge_tiers is not None and isinstance(raw_surge_tiers, list):
        surge_tiers = sorted([t for t in raw_surge_tiers if float(t.get("sell_ratio", 0.0)) > 0], key=lambda x: float(x.get("surge_pct", 0.0)), reverse=True)
    elif "surge_profit_pct" in cfg and cfg.get("surge_profit_pct") is not None:
        surge_tiers = [{"surge_pct": float(cfg.get("surge_profit_pct", 7.0)), "sell_ratio": float(cfg.get("surge_profit_sell_ratio", 0.25))}]
    else:
        surge_tiers = []

    cooldown_days = int(cfg.get("cooldown_trading_days", cfg.get("buy_cooldown_days", 1)))
    buy_cooldown_days = int(cfg.get("buy_cooldown_days", cooldown_days))
    sell_cooldown_days = int(cfg.get("sell_cooldown_days", cooldown_days))
    reset_profit_on_sell = bool(cfg.get("reset_profit_on_sell", True))

    # Pre-calculate MAs if ma_trend strategy
    ma_fast_series = []
    ma_slow_series = []
    if norm_strategy_type == "ma_trend":
        fast_p = int(cfg.get("ma_fast", 5))
        slow_p = int(cfg.get("ma_slow", 20))
        navs = [item["nav"] for item in sorted_history]
        for i in range(len(navs)):
            if i + 1 >= fast_p:
                ma_fast_series.append(sum(navs[i + 1 - fast_p : i + 1]) / fast_p)
            else:
                ma_fast_series.append(sum(navs[: i + 1]) / (i + 1))

            if i + 1 >= slow_p:
                ma_slow_series.append(sum(navs[i + 1 - slow_p : i + 1]) / slow_p)
            else:
                ma_slow_series.append(sum(navs[: i + 1]) / (i + 1))

    # Iterate through each trading day starting from day 0
    for idx, day_info in enumerate(sorted_history):
        cur_date = day_info["date"]
        cur_nav = float(day_info["nav"])
        day_change = float(day_info.get("change_pct", 0.0))

        cur_shares = get_current_shares()
        cum_profit_pct = (cur_nav - round_base_cost_nav) / round_base_cost_nav * 100.0 if round_base_cost_nav > 0 else 0.0

        trade_action = None
        trade_reason = ""
        buy_amount = 0.0
        sell_ratio = 0.0
        reset_this_trade = False

        # Don't trade on day 0 since initial buy happened
        if idx > 0:
            # -------------------------------------------------------------
            # Strategy 1: 跌幅加仓与阶梯止盈 (Dip-Buying & Tiered Profit-Taking)
            # -------------------------------------------------------------
            if norm_strategy_type == "dip_buying_profit_take":
                target_profit_th = float(cfg.get("cumulative_profit_target_pct") or 0.0)
                target_sell_r = float(cfg.get("cumulative_profit_sell_ratio") or 0.0)

                # 1. Check Multi-tier Surge Sell conditions
                matched_surge = None
                if cur_shares > 0 and (idx - last_sell_index >= sell_cooldown_days):
                    for st in surge_tiers:
                        s_pct = float(st.get("surge_pct", 0.0))
                        s_r = float(st.get("sell_ratio", 0.0))
                        if day_change >= s_pct and s_r > 0:
                            matched_surge = st
                            break

                if matched_surge:
                    trade_action = "SELL"
                    sell_ratio = float(matched_surge.get("sell_ratio", 0.25))
                    reset_this_trade = bool(matched_surge.get("reset_on_sell", False))
                    trade_reason = f"单日大涨阶梯止盈 (当日涨幅 +{day_change:.2f}% ≥ 目标 {matched_surge.get('surge_pct')}%)"
                elif target_profit_th > 0 and target_sell_r > 0 and cum_profit_pct >= target_profit_th and cur_shares > 0 and (idx - last_sell_index >= sell_cooldown_days):
                    trade_action = "SELL"
                    sell_ratio = target_sell_r
                    reset_this_trade = bool(cfg.get("cumulative_reset_on_sell", cfg.get("reset_profit_on_sell", True)))
                    trade_reason = f"本轮累计收益达标阶梯止盈 (本轮浮盈 +{cum_profit_pct:.2f}% ≥ 目标 {target_profit_th}%)"
                # 2. Check Multi-tier Buy conditions (Drop / Rise / Routine)
                elif (idx - last_buy_index >= buy_cooldown_days):
                    matched_drop = None
                    matched_rise = None

                    # Check drop tiers if market declined or flat
                    if day_change <= 0 and drop_tiers:
                        actual_drop = -day_change
                        matching_drops = []
                        for dt in drop_tiers:
                            op = dt.get("operator", ">=")
                            d_val = float(dt.get("drop_pct", 0.0))
                            if evaluate_tier_condition(actual_drop, op, d_val):
                                matching_drops.append(dt)
                        if matching_drops:
                            # Prioritize >= and > with largest threshold, <= and < with tightest threshold
                            matching_drops.sort(key=lambda x: (
                                0 if x.get("operator") in (">=", ">", "≥") else 1,
                                -float(x.get("drop_pct", 0)) if x.get("operator") in (">=", ">", "≥") else float(x.get("drop_pct", 0))
                            ))
                            matched_drop = matching_drops[0]

                    # Check rise tiers if market rose or flat
                    if day_change >= 0 and not matched_drop and rise_tiers:
                        actual_rise = day_change
                        matching_rises = []
                        for rt in rise_tiers:
                            op = rt.get("operator", "<=")
                            r_val = float(rt.get("rise_pct", 0.0))
                            if evaluate_tier_condition(actual_rise, op, r_val):
                                matching_rises.append(rt)
                        if matching_rises:
                            # Prioritize >= and > with largest threshold, <= and < with tightest threshold
                            matching_rises.sort(key=lambda x: (
                                0 if x.get("operator") in (">=", ">", "≥") else 1,
                                -float(x.get("rise_pct", 0)) if x.get("operator") in (">=", ">", "≥") else float(x.get("rise_pct", 0))
                            ))
                            matched_rise = matching_rises[0]

                    chosen_buy_tier = None
                    buy_reason_str = ""

                    if matched_drop:
                        chosen_buy_tier = matched_drop
                        op_str = matched_drop.get("operator", ">=")
                        buy_reason_str = f"单日下跌加仓 (当日跌幅 {day_change:.2f}%，满足下跌 {op_str} {matched_drop.get('drop_pct')}%)"
                    elif matched_rise:
                        chosen_buy_tier = matched_rise
                        op_str = matched_rise.get("operator", "<=")
                        buy_reason_str = f"单日上涨加仓 (当日涨幅 +{day_change:.2f}%，满足上涨 {op_str} {matched_rise.get('rise_pct')}%)"
                    elif routine_tier and float(routine_tier.get("amount", 0.0)) > 0:
                        chosen_buy_tier = routine_tier
                        buy_reason_str = f"日常底仓加仓 (当日涨跌 {day_change:+.2f}% 未满足任何涨跌加仓条件)"

                    if chosen_buy_tier:
                        b_amt = float(chosen_buy_tier.get("amount", 0.0))
                        if b_amt > 0:
                            max_pos = float(cfg.get("max_position_limit", 0))
                            cur_val = cur_shares * cur_nav
                            if max_pos <= 0 or cur_val + b_amt <= max_pos:
                                trade_action = "BUY"
                                buy_amount = b_amt
                                trade_reason = buy_reason_str

            # -------------------------------------------------------------
            # Strategy 2: 目标止盈定投 (Target Profit DCA)
            # -------------------------------------------------------------
            elif norm_strategy_type == "target_profit_dca":
                dca_interval = int(cfg.get("dca_interval_days", 5))
                base_dca_amt = float(cfg.get("dca_amount", 1000.0))
                target_profit = float(cfg.get("target_profit_pct", 15.0))
                target_sell_r = float(cfg.get("target_sell_ratio", 1.0))
                dip_multiplier = float(cfg.get("dip_extra_multiplier", 1.5))

                if cum_profit_pct >= target_profit and cur_shares > 0:
                    trade_action = "SELL"
                    sell_ratio = target_sell_r
                    trade_reason = f"定投累计收益达标止盈 (浮盈 +{cum_profit_pct:.2f}% ≥ 目标 {target_profit}%)"
                elif idx % dca_interval == 0:
                    trade_action = "BUY"
                    if day_change <= -1.5:
                        buy_amount = base_dca_amt * dip_multiplier
                        trade_reason = f"定期定额大跌倍投 (跌幅 {day_change:.2f}%，倍投 ¥{buy_amount:.0f})"
                    else:
                        buy_amount = base_dca_amt
                        trade_reason = f"定期定额纪律定投 (周期第 {idx} 交易日，定投 ¥{buy_amount:.0f})"

            # -------------------------------------------------------------
            # Strategy 3: 智能网格震荡 (Smart Dynamic Grid)
            # -------------------------------------------------------------
            elif norm_strategy_type == "smart_grid":
                step_down = float(cfg.get("grid_step_down_pct", 3.0))
                step_up = float(cfg.get("grid_step_up_pct", 4.0))
                grid_amt = float(cfg.get("grid_trade_amount", 2000.0))
                max_layers = int(cfg.get("max_grid_layers", 5))
                stop_loss = float(cfg.get("stop_loss_pct", 20.0))

                price_change_from_last = (cur_nav - last_trade_nav) / last_trade_nav * 100.0 if last_trade_nav > 0 else 0.0

                if cum_profit_pct <= -abs(stop_loss) and cur_shares > 0:
                    trade_action = "SELL"
                    sell_ratio = 1.0
                    trade_reason = f"触发网格硬止损保护 (浮亏 {cum_profit_pct:.2f}% ≤ -{stop_loss}%)"
                elif cum_profit_pct >= step_up and cur_shares > 0 and (idx - last_sell_index >= cooldown_days):
                    trade_action = "SELL"
                    sell_ratio = min(1.0, 1.0 / max(1, len(holding_lots)))
                    trade_reason = f"网格反弹获利平仓 (较持仓均价反弹 +{cum_profit_pct:.2f}% ≥ +{step_up}%)"
                elif price_change_from_last <= -abs(step_down) and len(holding_lots) < max_layers and (idx - last_buy_index >= cooldown_days):
                    trade_action = "BUY"
                    buy_amount = grid_amt
                    trade_reason = f"网格下跌档位加仓 (较前次成交下跌 {price_change_from_last:.2f}% ≤ -{step_down}%)"

            # -------------------------------------------------------------
            # Strategy 4: 均线趋势跟踪 (MA Trend Following)
            # -------------------------------------------------------------
            elif norm_strategy_type == "ma_trend":
                stop_loss = float(cfg.get("stop_loss_pct", 8.0))
                ma_buy_amt = float(cfg.get("buy_amount", 3000.0))
                ma_sell_r = float(cfg.get("sell_ratio", 0.5))

                f_ma = ma_fast_series[idx]
                s_ma = ma_slow_series[idx]
                prev_f_ma = ma_fast_series[idx - 1]
                prev_s_ma = ma_slow_series[idx - 1]

                is_golden_cross = (prev_f_ma <= prev_s_ma) and (f_ma > s_ma)
                is_death_cross = (prev_f_ma >= prev_s_ma) and (f_ma < s_ma)

                if cum_profit_pct <= -abs(stop_loss) and cur_shares > 0:
                    trade_action = "SELL"
                    sell_ratio = 1.0
                    trade_reason = f"触发趋势硬止损 (浮亏 {cum_profit_pct:.2f}% ≤ -{stop_loss}%)"
                elif is_death_cross and cur_shares > 0 and (idx - last_sell_index >= cooldown_days):
                    trade_action = "SELL"
                    sell_ratio = ma_sell_r
                    trade_reason = f"均线死叉减仓避险 (MA{cfg.get('ma_fast',5)} 下穿 MA{cfg.get('ma_slow',20)})"
                elif is_golden_cross and (idx - last_buy_index >= cooldown_days):
                    trade_action = "BUY"
                    buy_amount = ma_buy_amt
                    trade_reason = f"均线金叉右侧建仓 (MA{cfg.get('ma_fast',5)} 上穿 MA{cfg.get('ma_slow',20)})"

            # -------------------------------------------------------------
            # Strategy: 股票分时做T与底仓波段策略 (Intraday & Swing T Strategy)
            # -------------------------------------------------------------
            elif norm_strategy_type in ("intraday_t", "stock_intraday_t"):
                t_surge_pct = float(cfg.get("t_surge_sell_pct", 1.8))
                t_sell_shares_cfg = float(cfg.get("t_sell_shares", 300.0))
                t_pullback_pct = float(cfg.get("t_pullback_buy_pct", 1.5))
                base_protect_shares = float(cfg.get("base_protect_shares", 0.0))
                stop_loss_pct = float(cfg.get("stop_loss_pct", 10.0))
                target_profit_th = float(cfg.get("cumulative_profit_target_pct") or 0.0)
                target_sell_r = float(cfg.get("cumulative_profit_sell_ratio") or 0.5)
                reset_on_sell = bool(cfg.get("cumulative_reset_on_sell", True))

                day_high = float(day_info.get("high", cur_nav))
                day_low = float(day_info.get("low", cur_nav))
                day_open = float(day_info.get("open", cur_nav))

                # T+1 Available sellable shares (strictly shares bought before today)
                avail_sell_shares = sum(lot["shares"] for lot in holding_lots if lot["buy_date"] < cur_date)
                free_t_shares = max(0.0, avail_sell_shares - base_protect_shares)

                # 1. Hard Stop Loss
                if stop_loss_pct > 0 and cum_profit_pct <= -abs(stop_loss_pct) and avail_sell_shares > 0:
                    trade_action = "SELL"
                    sell_ratio = 1.0
                    reset_this_trade = True
                    trade_reason = f"触发硬止损防守 (浮亏 {cum_profit_pct:.2f}% ≤ -{stop_loss_pct}%)"

                # 2. Cumulative Target Profit
                elif target_profit_th > 0 and cum_profit_pct >= target_profit_th and avail_sell_shares > 0:
                    sell_target_s = int(avail_sell_shares * target_sell_r / 100) * 100
                    if sell_target_s >= 100:
                        trade_action = "SELL"
                        sell_ratio = sell_target_s / cur_shares if cur_shares > 0 else target_sell_r
                        reset_this_trade = reset_on_sell
                        trade_reason = f"累计收益达标阶段止盈 (本轮浮盈 +{cum_profit_pct:.2f}% ≥ 目标 {target_profit_th}%)"

                else:
                    # 3. Lot-by-lot Profit Taking (逐批次独立止盈做T：卖出比此前买入价涨幅达标的对应股数，严格T+1)
                    enable_lot_profit_take = bool(cfg.get("enable_lot_profit_take", True))
                    lot_profit_th = float(cfg.get("lot_profit_take_pct", 3.0))
                    lot_sell_r = float(cfg.get("lot_profit_sell_ratio", 1.0))
                    
                    matched_lot_idx = []
                    matched_lot_sell_shares = 0.0
                    if enable_lot_profit_take and free_t_shares >= 100:
                        for l_idx, lot in enumerate(holding_lots):
                            if lot["buy_date"] < cur_date:  # Strictly T+1
                                cost_p = float(lot.get("cost_nav", 0.0))
                                if cost_p > 0:
                                    gain_pct = (cur_nav - cost_p) / cost_p * 100.0
                                    if gain_pct >= lot_profit_th:
                                        s_to_sell = int(lot["shares"] * lot_sell_r / 100) * 100
                                        if s_to_sell >= 100:
                                            matched_lot_idx.append(l_idx)
                                            matched_lot_sell_shares += s_to_sell

                    if matched_lot_idx and matched_lot_sell_shares >= 100 and free_t_shares >= 100:
                        target_t_sell = min(matched_lot_sell_shares, int(free_t_shares / 100) * 100)
                        if target_t_sell >= 100:
                            trade_action = "SELL"
                            sell_ratio = target_t_sell / cur_shares if cur_shares > 0 else 0.0
                            reset_this_trade = reset_on_sell
                            # Prioritize matched profitable lots to be sold first
                            holding_lots = [holding_lots[i] for i in matched_lot_idx] + [holding_lots[i] for i in range(len(holding_lots)) if i not in matched_lot_idx]
                            first_matched = holding_lots[0]
                            first_gain = (cur_nav - first_matched['cost_nav']) / first_matched['cost_nav'] * 100.0
                            trade_reason = f"【批次独立做T止盈】当前价 ¥{cur_nav:.2f} 较 {first_matched['buy_date']} 买入价 ¥{first_matched['cost_nav']:.2f} 涨幅达 +{first_gain:.2f}% (≥ +{lot_profit_th}%)，满足T+1，卖出对应 {target_t_sell:.0f} 股锁定利润"

                    # 4. High Surge T-Sell (分时冲高高抛)
                    elif free_t_shares >= 100:
                        surge_trigger_price = round(round_base_cost_nav * (1 + t_surge_pct / 100.0), 2)
                        if day_high >= surge_trigger_price:
                            trade_action = "SELL"
                            target_t_sell = min(t_sell_shares_cfg, free_t_shares)
                            target_t_sell = int(target_t_sell / 100) * 100
                            sell_ratio = target_t_sell / cur_shares if cur_shares > 0 else 0.0
                            reset_this_trade = reset_on_sell
                            trade_reason = f"【做T高抛】分时冲高 (最高达 ¥{day_high:.2f} ≥ 触发价 ¥{surge_trigger_price:.2f}，涨幅 ≥ +{t_surge_pct}%)"

                    # 5. Multi-tier Dip Buying (大跌阶梯加仓) if no sell triggered
                    elif day_change <= 0 and drop_tiers:
                        actual_drop = -day_change
                        matching_drops = []
                        for dt in drop_tiers:
                            op = dt.get("operator", ">=")
                            d_val = float(dt.get("drop_pct", 0.0))
                            if evaluate_tier_condition(actual_drop, op, d_val):
                                matching_drops.append(dt)
                        if matching_drops:
                            matching_drops.sort(key=lambda x: -float(x.get("drop_pct", 0)))
                            chosen = matching_drops[0]
                            b_amt = float(chosen.get("amount", 0.0))
                            if b_amt > 0:
                                trade_action = "BUY"
                                buy_amount = b_amt
                                trade_reason = f"单日大跌阶梯加仓 (当日跌幅 {day_change:.2f}%，满足下跌 {chosen.get('operator','>=')} {chosen.get('drop_pct')}%)"

                    # 5. Multi-tier Surge Selling (极端大涨阶梯减仓)
                    elif day_change > 0 and surge_tiers and free_t_shares >= 100:
                        matching_surges = [st for st in surge_tiers if day_change >= float(st.get("surge_pct", 0.0))]
                        if matching_surges:
                            matching_surges.sort(key=lambda x: -float(x.get("surge_pct", 0)))
                            chosen = matching_surges[0]
                            s_ratio = float(chosen.get("sell_ratio", 0.25))
                            trade_action = "SELL"
                            sell_ratio = s_ratio
                            reset_this_trade = reset_on_sell
                            trade_reason = f"单日暴涨阶梯减仓 (当日涨幅 +{day_change:.2f}% ≥ {chosen.get('surge_pct')}%)"

            # -------------------------------------------------------------
            # Strategy 5: 自定义多因子策略 (Custom Rule-Builder)
            # -------------------------------------------------------------
            elif norm_strategy_type == "custom":
                buy_rules = cfg.get("buy_rules", [])
                sell_rules = cfg.get("sell_rules", [])

                # Check sell rules
                for r in sell_rules:
                    if not r.get("enabled", True):
                        continue
                    rtype = r.get("type")
                    th = float(r.get("threshold_pct", 10.0))
                    ratio = float(r.get("ratio", 0.3333))

                    if rtype == "cumulative_profit" and cum_profit_pct >= th and cur_shares > 0:
                        trade_action = "SELL"
                        sell_ratio = ratio
                        trade_reason = f"自定义卖出规则触发: 累计收益率 {cum_profit_pct:.2f}% ≥ {th}%"
                        break
                    elif rtype == "daily_surge" and day_change >= th and cur_shares > 0:
                        trade_action = "SELL"
                        sell_ratio = ratio
                        trade_reason = f"自定义卖出规则触发: 单日涨幅 {day_change:.2f}% ≥ {th}%"
                        break
                    elif rtype == "stop_loss" and cum_profit_pct <= -abs(th) and cur_shares > 0:
                        trade_action = "SELL"
                        sell_ratio = ratio
                        trade_reason = f"自定义止损规则触发: 浮亏 {cum_profit_pct:.2f}% ≤ -{abs(th)}%"
                        break

                # Check buy rules if no sell triggered
                if not trade_action and (idx - last_buy_index >= cooldown_days):
                    for r in buy_rules:
                        if not r.get("enabled", True):
                            continue
                        rtype = r.get("type")
                        th = float(r.get("threshold_pct", 2.0))
                        amt = float(r.get("amount", 5000.0))

                        if rtype == "daily_drop" and day_change <= -abs(th):
                            trade_action = "BUY"
                            buy_amount = amt
                            trade_reason = f"自定义买入规则触发: 单日跌幅 {day_change:.2f}% ≤ -{abs(th)}%"
                            break

        # Execute BUY
        if trade_action == "BUY" and buy_amount > 0:
            old_s = get_current_shares()

            if is_stock:
                buy_shares = int(buy_amount / cur_nav / 100) * 100
                if buy_shares < 100 and buy_amount >= cur_nav * 50:
                    buy_shares = 100
                if buy_shares > 0:
                    trade_gross = round(buy_shares * cur_nav, 2)
                    trade_fee_info = calculate_stock_trade_fee("BUY", trade_gross, fee_config)
                    trade_fee = trade_fee_info["total_fee"]
                    trade_net = round(trade_gross + trade_fee, 2)
                    total_sub_fee += trade_fee
                    total_buys += 1
                    last_buy_index = idx
                    last_trade_nav = cur_nav

                    if cash >= trade_net:
                        cash -= trade_net
                    else:
                        total_invested += (trade_net - cash)
                        cash = 0.0

                    holding_lots.append({
                        "buy_date": cur_date,
                        "confirm_date": cur_date,
                        "shares": float(buy_shares),
                        "cost_nav": cur_nav,
                        "invested": trade_gross
                    })

                    old_cost_nav = round_base_cost_nav
                    new_tot_shares = get_current_shares()
                    if old_s <= 1e-5:
                        round_base_cost_nav = cur_nav
                    elif new_tot_shares > 1e-5:
                        round_base_cost_nav = (old_s * round_base_cost_nav + buy_shares * cur_nav) / new_tot_shares

                    trades.append({
                        "id": len(trades) + 1,
                        "date": cur_date,
                        "action": "BUY",
                        "action_label": "加仓买入",
                        "nav": cur_nav,
                        "open": day_info.get("open", cur_nav),
                        "high": day_info.get("high", cur_nav),
                        "low": day_info.get("low", cur_nav),
                        "close": day_info.get("close", cur_nav),
                        "change_pct": day_change,
                        "gross_amount": trade_gross,
                        "net_amount": trade_net,
                        "shares": float(buy_shares),
                        "fee": trade_fee,
                        "fee_breakdown": trade_fee_info,
                        "cost_nav_before": round(old_cost_nav, 4),
                        "cost_nav_after": round(round_base_cost_nav, 4),
                        "holding_days": 0,
                        "rule_trigger": trade_reason,
                        "cash_balance": round(cash, 2),
                        "holding_shares": round(new_tot_shares, 4),
                        "market_value": round(new_tot_shares * cur_nav, 2),
                        "realized_pnl": 0.0
                    })
            else:
                sub_res = calculate_subscription(buy_amount, cur_nav, sub_rate)
                total_sub_fee += sub_res["fee"]
                total_buys += 1
                last_buy_index = idx
                last_trade_nav = cur_nav
                
                if cash >= sub_res["net_amount"]:
                    cash -= sub_res["net_amount"]
                else:
                    total_invested += (sub_res["net_amount"] - cash)
                    cash = 0.0

                holding_lots.append({
                    "buy_date": cur_date,
                    "confirm_date": cur_date,
                    "shares": sub_res["shares"],
                    "cost_nav": cur_nav,
                    "invested": buy_amount
                })

                old_cost_nav = round_base_cost_nav
                new_tot_shares = get_current_shares()
                if old_s <= 1e-5:
                    round_base_cost_nav = cur_nav
                elif new_tot_shares > 1e-5:
                    round_base_cost_nav = (old_s * round_base_cost_nav + sub_res["shares"] * cur_nav) / new_tot_shares

                trades.append({
                    "id": len(trades) + 1,
                    "date": cur_date,
                    "action": "BUY",
                    "action_label": "加仓买入",
                    "nav": cur_nav,
                    "open": day_info.get("open", cur_nav),
                    "high": day_info.get("high", cur_nav),
                    "low": day_info.get("low", cur_nav),
                    "close": day_info.get("close", cur_nav),
                    "change_pct": day_change,
                    "gross_amount": buy_amount,
                    "net_amount": sub_res["net_amount"],
                    "shares": sub_res["shares"],
                    "fee": sub_res["fee"],
                    "fee_breakdown": {"subscription_fee": sub_res["fee"]},
                    "cost_nav_before": round(old_cost_nav, 4),
                    "cost_nav_after": round(round_base_cost_nav, 4),
                    "holding_days": 0,
                    "rule_trigger": trade_reason,
                    "cash_balance": round(cash, 2),
                    "holding_shares": round(new_tot_shares, 4),
                    "market_value": round(new_tot_shares * cur_nav, 2),
                    "realized_pnl": 0.0
                })

        # Execute SELL (FIFO holding lot matching)
        elif trade_action == "SELL" and sell_ratio > 0 and cur_shares > 1e-5:
            if is_stock:
                target_shares_to_sell = int(cur_shares * sell_ratio / 100) * 100
                if sell_ratio >= 0.9999 or target_shares_to_sell <= 0:
                    target_shares_to_sell = cur_shares
            else:
                target_shares_to_sell = cur_shares * sell_ratio
                if target_shares_to_sell > cur_shares:
                    target_shares_to_sell = cur_shares

            sold_shares = 0.0
            sell_gross_val = 0.0
            sell_total_fee = 0.0
            total_cost_of_sold = 0.0
            avg_holding_days = 0.0
            sold_lots_count = 0

            new_lots = []
            if sell_ratio >= 0.9999:
                # 100% full clearance - sell all holding lots
                for lot in holding_lots:
                    lot_s = lot["shares"]
                    h_days = calculate_holding_days(lot["buy_date"], cur_date)
                    lot_gross = lot_s * cur_nav
                    if is_stock:
                        lot_fee_info = calculate_stock_trade_fee("SELL", lot_gross, fee_config)
                        lot_fee = lot_fee_info["total_fee"]
                    else:
                        red_rate = get_redemption_fee_rate(h_days, red_tiers)
                        lot_fee = lot_gross * red_rate
                    sell_gross_val += lot_gross
                    sell_total_fee += lot_fee
                    sold_shares += lot_s
                    total_cost_of_sold += lot_s * lot["cost_nav"]
                    avg_holding_days += h_days
                    sold_lots_count += 1
                holding_lots = []
            else:
                for lot in holding_lots:
                    if sold_shares >= target_shares_to_sell - 1e-5:
                        new_lots.append(lot)
                        continue

                    needed = target_shares_to_sell - sold_shares
                    lot_s = lot["shares"]
                    h_days = calculate_holding_days(lot["buy_date"], cur_date)

                    if lot_s <= needed + 1e-5:
                        # Sell entire lot
                        lot_gross = lot_s * cur_nav
                        if is_stock:
                            lot_fee_info = calculate_stock_trade_fee("SELL", lot_gross, fee_config)
                            lot_fee = lot_fee_info["total_fee"]
                        else:
                            red_rate = get_redemption_fee_rate(h_days, red_tiers)
                            lot_fee = lot_gross * red_rate
                        sell_gross_val += lot_gross
                        sell_total_fee += lot_fee
                        sold_shares += lot_s
                        total_cost_of_sold += lot_s * lot["cost_nav"]
                        avg_holding_days += h_days
                        sold_lots_count += 1
                    else:
                        # Partial sell this lot
                        part_gross = needed * cur_nav
                        if is_stock:
                            part_fee_info = calculate_stock_trade_fee("SELL", part_gross, fee_config)
                            part_fee = part_fee_info["total_fee"]
                        else:
                            red_rate = get_redemption_fee_rate(h_days, red_tiers)
                            part_fee = part_gross * red_rate
                        sell_gross_val += part_gross
                        sell_total_fee += part_fee
                        sold_shares += needed
                        total_cost_of_sold += needed * lot["cost_nav"]
                        avg_holding_days += h_days
                        sold_lots_count += 1

                        rem_s = lot_s - needed
                        if rem_s > 1e-5:
                            lot["shares"] = rem_s
                            lot["invested"] = rem_s * lot["cost_nav"]
                            new_lots.append(lot)

                holding_lots = new_lots

            # Only commit trade if actual shares were sold
            if sold_shares > 1e-5 and sell_gross_val > 0.01:
                net_proceeds = sell_gross_val - sell_total_fee
                cash += net_proceeds
                total_red_fee += sell_total_fee
                total_sells += 1
                last_sell_index = idx
                last_trade_nav = cur_nav

                realized_pnl = round(sell_gross_val - sell_total_fee - total_cost_of_sold, 2)
                if realized_pnl > 0:
                    winning_sells += 1
                else:
                    losing_sells += 1

                calc_avg_days = int(round(avg_holding_days / max(1, sold_lots_count)))
                rem_shares = get_current_shares()

                old_cost_nav = round_base_cost_nav
                # Reset round base cost nav for remaining shares to cur_nav if this specific trade requested reset
                if rem_shares <= 1e-5:
                    round_base_cost_nav = 0.0
                elif reset_this_trade:
                    round_base_cost_nav = cur_nav
                else:
                    round_base_cost_nav = get_avg_cost()

                if "做T高抛" in trade_reason:
                    sell_action_lbl = "做T高抛"
                elif "阶段止盈" in trade_reason or "目标止盈" in trade_reason:
                    sell_action_lbl = "目标止盈"
                elif "阶梯减仓" in trade_reason or "阶梯止盈" in trade_reason:
                    sell_action_lbl = "阶梯减仓"
                elif realized_pnl >= 0:
                    sell_action_lbl = "止盈卖出"
                else:
                    sell_action_lbl = "止损减仓"

                if is_stock:
                    sell_fee_breakdown = calculate_stock_trade_fee("SELL", sell_gross_val, fee_config)
                else:
                    sell_fee_breakdown = {"redemption_fee": round(sell_total_fee, 2), "total_fee": round(sell_total_fee, 2)}

                trades.append({
                    "id": len(trades) + 1,
                    "date": cur_date,
                    "action": "SELL",
                    "action_label": sell_action_lbl,
                    "nav": cur_nav,
                    "open": day_info.get("open", cur_nav),
                    "high": day_info.get("high", cur_nav),
                    "low": day_info.get("low", cur_nav),
                    "close": day_info.get("close", cur_nav),
                    "change_pct": day_change,
                    "gross_amount": round(sell_gross_val, 2),
                    "net_amount": round(net_proceeds, 2),
                    "shares": round(sold_shares, 4),
                    "fee": round(sell_total_fee, 2),
                    "fee_breakdown": sell_fee_breakdown,
                    "cost_nav_before": round(old_cost_nav, 4),
                    "cost_nav_after": round(round_base_cost_nav, 4),
                    "holding_days": calc_avg_days,
                    "rule_trigger": trade_reason,
                    "cash_balance": round(cash, 2),
                    "holding_shares": round(rem_shares, 4),
                    "market_value": round(rem_shares * cur_nav, 2),
                    "realized_pnl": realized_pnl
                })

                # If this was a 做T高抛 and intraday_t strategy, check if day_low triggers pullback buyback!
                enable_buyback = bool(cfg.get("enable_pullback_buyback", True))
                if enable_buyback and norm_strategy_type in ("intraday_t", "stock_intraday_t") and "做T高抛" in trade_reason and is_stock:
                    pullback_ref = cfg.get("pullback_ref_type", "from_sell_price")
                    day_low_p = float(day_info.get("low", cur_nav))
                    
                    is_pullback_triggered = False
                    actual_buyback_p = day_low_p
                    buyback_reason_str = ""

                    if pullback_ref == "from_daily_change":
                        # Reference: 当天总跌幅
                        daily_drop_th = float(cfg.get("daily_drop_buyback_pct", 2.0))
                        if day_change <= -abs(daily_drop_th):
                            is_pullback_triggered = True
                            actual_buyback_p = cur_nav
                            buyback_reason_str = f"做T回踩接回 (触发当天总跌幅 {day_change:.2f}% ≤ -{daily_drop_th}%，买回限制 ≤ 当日卖出 {sold_shares:.0f}股)"
                    else:
                        # Reference: 较高抛卖出点的跌幅 (from_sell_price)
                        t_pullback_pct = float(cfg.get("t_pullback_buy_pct", 1.5))
                        pullback_target_p = round(cur_nav * (1 - t_pullback_pct / 100.0), 2)
                        if day_low_p <= pullback_target_p:
                            is_pullback_triggered = True
                            actual_buyback_p = max(day_low_p, pullback_target_p)
                            buyback_reason_str = f"做T回踩接回 (最低跌至 ¥{day_low_p:.2f} ≤ 目标接回价 ¥{pullback_target_p:.2f}，较高抛价回落 ≥ -{t_pullback_pct}%，买回限制 ≤ 当日卖出 {sold_shares:.0f}股)"

                    if is_pullback_triggered:
                        # Strict limit: buyback shares <= sold_shares (strictly no more than sold today!)
                        buyback_shares = int(sold_shares / 100) * 100
                        if buyback_shares >= 100:
                            bb_gross = round(buyback_shares * actual_buyback_p, 2)
                            bb_fee_info = calculate_stock_trade_fee("BUY", bb_gross, fee_config)
                            bb_fee = bb_fee_info["total_fee"]
                            bb_net = round(bb_gross + bb_fee, 2)
                            total_sub_fee += bb_fee
                            total_buys += 1
                            last_buy_index = idx
                            last_trade_nav = actual_buyback_p
                            
                            if cash >= bb_net:
                                cash -= bb_net
                            else:
                                total_invested += (bb_net - cash)
                                cash = 0.0

                            # Stamped with buy_date = cur_date (T+1 rule: frozen until tomorrow!)
                            holding_lots.append({
                                "buy_date": cur_date,
                                "confirm_date": cur_date,
                                "shares": float(buyback_shares),
                                "cost_nav": actual_buyback_p,
                                "invested": bb_gross
                            })

                            bb_cost_before = round_base_cost_nav
                            new_tot_s = get_current_shares()
                            if reset_this_trade and new_tot_s > 0:
                                pnl_diff = (cur_nav - actual_buyback_p) * buyback_shares
                                if pnl_diff > 0:
                                    round_base_cost_nav = max(0.01, round(round_base_cost_nav - (pnl_diff / new_tot_s), 3))

                            trades.append({
                                "id": len(trades) + 1,
                                "date": cur_date,
                                "action": "BUY",
                                "action_label": "做T低吸",
                                "nav": actual_buyback_p,
                                "open": day_info.get("open", cur_nav),
                                "high": day_info.get("high", cur_nav),
                                "low": day_info.get("low", cur_nav),
                                "close": day_info.get("close", cur_nav),
                                "change_pct": day_change,
                                "gross_amount": bb_gross,
                                "net_amount": bb_net,
                                "shares": float(buyback_shares),
                                "fee": bb_fee,
                                "fee_breakdown": bb_fee_info,
                                "cost_nav_before": round(bb_cost_before, 4),
                                "cost_nav_after": round(round_base_cost_nav, 4),
                                "holding_days": 0,
                                "rule_trigger": buyback_reason_str,
                                "cash_balance": round(cash, 2),
                                "holding_shares": round(new_tot_s, 4),
                                "market_value": round(new_tot_s * cur_nav, 2),
                                "realized_pnl": 0.0
                            })

        # Calculate daily equity state
        rem_shares_today = get_current_shares()
        market_val_today = rem_shares_today * cur_nav
        total_assets_today = cash + market_val_today

        # Strategy Return from Total Invested
        strat_return_pct = (total_assets_today - total_invested) / total_invested * 100.0 if total_invested > 0 else 0.0

        # Benchmark Return (Fund Buy & Hold 100% since start date)
        bm_return_pct = (cur_nav - benchmark_start_nav) / benchmark_start_nav * 100.0 if benchmark_start_nav > 0 else 0.0

        equity_curve.append({
            "date": cur_date,
            "nav": cur_nav,
            "cash": round(cash, 2),
            "market_value": round(market_val_today, 2),
            "total_assets": round(total_assets_today, 2),
            "total_invested": round(total_invested, 2),
            "strategy_return_pct": round(strat_return_pct, 2),
            "benchmark_return_pct": round(bm_return_pct, 2),
            "holding_shares": round(rem_shares_today, 4),
            "action": trade_action if (trade_action == "BUY" and buy_amount > 0) or (trade_action == "SELL" and sell_ratio > 0) else None
        })

    # Performance Metrics Calculations
    final_equity = equity_curve[-1]
    final_total_assets = final_equity["total_assets"]
    final_strategy_return = final_equity["strategy_return_pct"]
    final_benchmark_return = final_equity["benchmark_return_pct"]
    alpha_return = final_strategy_return - final_benchmark_return

    # Total trading days & Annualized Return (CAGR)
    total_days = len(equity_curve)
    cagr = 0.0
    if total_days > 10 and total_invested > 0:
        years = total_days / 244.0  # ~244 trading days per year
        if years > 0:
            growth = max(0.0001, final_total_assets / total_invested)
            cagr = round((math.pow(growth, 1.0 / years) - 1.0) * 100.0, 2)

    # Max Drawdown Calculation
    max_peak = -1e9
    max_drawdown = 0.0
    for pt in equity_curve:
        val = pt["total_assets"]
        if val > max_peak:
            max_peak = val
        if max_peak > 0:
            dd = (max_peak - val) / max_peak * 100.0
            if dd > max_drawdown:
                max_drawdown = dd

    # Daily returns & Sharpe Ratio (Risk-free rate = 2.0% annual => ~0.008% daily)
    daily_returns = []
    for i in range(1, len(equity_curve)):
        prev_a = equity_curve[i - 1]["total_assets"]
        cur_a = equity_curve[i]["total_assets"]
        if prev_a > 0:
            daily_returns.append((cur_a - prev_a) / prev_a)

    sharpe_ratio = 0.0
    if len(daily_returns) > 5:
        mean_r = sum(daily_returns) / len(daily_returns)
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in daily_returns) / len(daily_returns))
        rf_daily = 0.02 / 244.0
        if std_r > 1e-6:
            sharpe_ratio = round((mean_r - rf_daily) / std_r * math.sqrt(244), 2)

    # Win Rate
    win_rate = round((winning_sells / total_sells * 100.0), 1) if total_sells > 0 else 0.0

    return {
        "success": True,
        "asset_type": asset_type,
        "fund_code": fund_code,
        "fund_name": fund_name,
        "target_code": fund_code,
        "target_name": fund_name,
        "strategy_type": strategy_type,
        "start_date": sorted_history[0]["date"],
        "end_date": sorted_history[-1]["date"],
        "total_days": total_days,
        "metrics": {
            "strategy_return_pct": round(final_strategy_return, 2),
            "benchmark_return_pct": round(final_benchmark_return, 2),
            "excess_return_pct": round(alpha_return, 2),
            "annualized_return_pct": cagr,
            "max_drawdown_pct": round(max_drawdown, 2),
            "sharpe_ratio": sharpe_ratio,
            "initial_capital": round(initial_capital, 2),
            "total_invested": round(total_invested, 2),
            "final_assets": round(final_total_assets, 2),
            "final_cash": round(final_equity["cash"], 2),
            "final_holding_value": round(final_equity["market_value"], 2),
            "final_holding_shares": round(final_equity["holding_shares"], 4),
            "total_trades": len(trades),
            "buy_trades": total_buys,
            "sell_trades": total_sells,
            "winning_sells": winning_sells,
            "win_rate": win_rate,
            "total_fees_paid": round(total_sub_fee + total_red_fee, 2),
            "subscription_fees": round(total_sub_fee, 2),
            "redemption_fees": round(total_red_fee, 2)
        },
        "equity_curve": equity_curve,
        "trades": trades
    }
