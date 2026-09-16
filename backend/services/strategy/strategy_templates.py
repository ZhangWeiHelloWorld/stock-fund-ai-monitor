"""
Strategy Templates & Rule Definitions.
Provides preset templates, validation schemas, and descriptions.
"""

from typing import List, Dict, Any

PRESET_TEMPLATES = [
    {
        "id": "dip_buying_profit_take",
        "name": "跌幅加仓与阶梯止盈策略",
        "category": "fund",
        "badge": "经典推荐",
        "description": "专为波动市设计：初始投入底仓，单日大跌或上涨或日常打底按档位加仓；单日暴涨或累计收益达到目标时分批阶梯卖出锁定利润。",
        "default_config": {
            "initial_capital": 10000.0,
            "settlement_type": "T+1",      # T+1 或 T+2
            "buy_tiers": [
                {"type": "drop", "operator": ">=", "drop_pct": 2.0, "amount": 5000.0, "label": "单日下跌 ≥ 2.0% 加仓 ¥5000"},
                {"type": "drop", "operator": ">=", "drop_pct": 5.0, "amount": 8000.0, "label": "单日下跌 ≥ 5.0% 加仓 ¥8000"},
                {"type": "drop", "operator": ">=", "drop_pct": 10.0, "amount": 10000.0, "label": "单日下跌 ≥ 10.0% 加仓 ¥10000"}
            ],
            "dip_buy_tiers": [
                {"type": "drop", "operator": ">=", "drop_pct": 2.0, "amount": 5000.0, "label": "单日下跌 ≥ 2.0% 加仓 ¥5000"},
                {"type": "drop", "operator": ">=", "drop_pct": 5.0, "amount": 8000.0, "label": "单日下跌 ≥ 5.0% 加仓 ¥8000"},
                {"type": "drop", "operator": ">=", "drop_pct": 10.0, "amount": 10000.0, "label": "单日下跌 ≥ 10.0% 加仓 ¥10000"}
            ],
            "surge_profit_tiers": [
                {"surge_pct": 3.0, "sell_ratio": 0.20, "reset_on_sell": False, "label": "单日上涨 ≥ 3.0% 卖出 1/5 (20%)"},
                {"surge_pct": 5.0, "sell_ratio": 0.25, "reset_on_sell": False, "label": "单日上涨 ≥ 5.0% 卖出 1/4 (25%)"},
                {"surge_pct": 7.0, "sell_ratio": 0.3333, "reset_on_sell": False, "label": "单日上涨 ≥ 7.0% 卖出 1/3 (33.33%)"}
            ],
            "cumulative_profit_target_pct": 10.0, # 累计浮动收益率 >= 10%
            "cumulative_profit_sell_ratio": 0.3333, # 卖出 1/3 (33.33%)
            "cumulative_reset_on_sell": True,  # 达标卖出后将当前浮盈重置为 0%（以成交净值作为新一轮基准）
            "buy_cooldown_days": 1,        # 加仓冷却交易日数
            "sell_cooldown_days": 1,       # 止盈/减仓冷却交易日数
            "max_position_limit": 50000.0, # 最大持仓上限金额（0表示不限）
            "avoid_7day_penalty": True     # 止盈赎回时是否优先避开小于7天1.5%惩罚费率
        }
    },
    {
        "id": "target_profit_dca",
        "name": "目标止盈定投策略",
        "category": "fund",
        "badge": "省心定投",
        "description": "纪律性微笑曲线定投：按设定周期定额买入，当组合累计收益率达到预期目标（如 15%）自动分批或全部止盈锁定收益，进入下一轮循环。",
        "default_config": {
            "initial_capital": 10000.0,
            "settlement_type": "T+1",
            "dca_interval_days": 5,        # 每 5 个交易日（约每周）定投一次
            "dca_amount": 1000.0,          # 每次定投金额
            "target_profit_pct": 15.0,     # 目标累计收益率
            "target_sell_ratio": 1.0,      # 达标卖出比例（1.0为全部清仓锁定收益，0.5为半仓止盈）
            "dip_extra_multiplier": 1.5,   # 定投日若下跌超过1.5%，定投额度自动加倍系数 (1.0表示不加倍)
            "reinvest_after_take": True    # 止盈后自动开启新一轮定投
        }
    },
    {
        "id": "smart_grid",
        "name": "智能网格震荡策略",
        "category": "fund",
        "badge": "震荡市利器",
        "description": "利用净值箱体波动自动高抛低吸：净值每阶梯下跌买入一格，反弹至目标阶梯卖出一格，持续收割波动差价。",
        "default_config": {
            "initial_capital": 10000.0,
            "settlement_type": "T+1",
            "grid_step_down_pct": 3.0,     # 每次较上一次买入点下跌 3.0% 买入一格
            "grid_step_up_pct": 4.0,       # 每次较持仓成本反弹 4.0% 卖出一格
            "grid_trade_amount": 2000.0,   # 每格投入金额
            "max_grid_layers": 5,          # 最大网格层数
            "stop_loss_pct": 20.0          # 极限风控止损线（%）
        }
    },
    {
        "id": "ma_trend",
        "name": "均线趋势跟踪策略",
        "category": "fund",
        "badge": "趋势动量",
        "description": "顺应中短期趋势运行：净值上穿短期均线（如 MA5/MA20）确立上升趋势时分批买入，跌破均线或触发止损时减仓避险。",
        "default_config": {
            "initial_capital": 10000.0,
            "settlement_type": "T+1",
            "ma_fast": 5,                  # 快线周期（日）
            "ma_slow": 20,                 # 慢线周期（日）
            "buy_amount": 3000.0,          # 趋势向上买入金额
            "sell_ratio": 0.5,             # 趋势转弱卖出比例
            "stop_loss_pct": 8.0,          # 移动止损线（%）
            "cooldown_trading_days": 3     # 信号冷却交易日数
        }
    },
    {
        "id": "custom",
        "name": "自定义多因子组合策略",
        "category": "fund",
        "badge": "高度自由",
        "description": "自由组合单日涨跌、累计收益率、高点回撤、定投等多种买入与卖出触发条件，量身定制专属交易系统。",
        "default_config": {
            "initial_capital": 10000.0,
            "settlement_type": "T+1",
            "buy_rules": [
                {"type": "daily_drop", "threshold_pct": 2.0, "amount": 5000.0, "enabled": True, "label": "单日跌幅 ≥ 2.0% 时加仓 ¥5000"}
            ],
            "sell_rules": [
                {"type": "cumulative_profit", "threshold_pct": 10.0, "ratio": 0.3333, "enabled": True, "label": "累计收益率 ≥ 10.0% 时卖出 1/3"},
                {"type": "daily_surge", "threshold_pct": 7.0, "ratio": 0.25, "enabled": True, "label": "单日大涨 ≥ 7.0% 时卖出 1/4"}
            ],
            "cooldown_trading_days": 1,
            "avoid_7day_penalty": True
        }
    },
    # =========================================================================
    # STOCK TRADING STRATEGY TEMPLATES (股票买卖策略模板)
    # =========================================================================
    {
        "id": "dip_buying_profit_take",
        "name": "跌幅加仓与阶梯止盈策略",
        "category": "stock",
        "badge": "A股经典",
        "description": "专为股票波动设计：支持单日大跌、上涨或日常打底多档位加仓（自动按100股整手取整）；单日暴涨或轮次累计浮盈达标分批止盈并重置基准。",
        "default_config": {
            "initial_capital": 20000.0,
            "settlement_type": "T+1",
            "buy_tiers": [
                {"type": "drop", "operator": ">=", "drop_pct": 2.0, "amount": 5000.0, "label": "单日下跌 ≥ 2.0% 加仓约 ¥5000"},
                {"type": "drop", "operator": ">=", "drop_pct": 5.0, "amount": 8000.0, "label": "单日下跌 ≥ 5.0% 加仓约 ¥8000"},
                {"type": "drop", "operator": ">=", "drop_pct": 10.0, "amount": 10000.0, "label": "单日下跌 ≥ 10.0% 加仓约 ¥10000"}
            ],
            "dip_buy_tiers": [
                {"type": "drop", "operator": ">=", "drop_pct": 2.0, "amount": 5000.0, "label": "单日下跌 ≥ 2.0% 加仓约 ¥5000"},
                {"type": "drop", "operator": ">=", "drop_pct": 5.0, "amount": 8000.0, "label": "单日下跌 ≥ 5.0% 加仓约 ¥8000"},
                {"type": "drop", "operator": ">=", "drop_pct": 10.0, "amount": 10000.0, "label": "单日下跌 ≥ 10.0% 加仓约 ¥10000"}
            ],
            "surge_profit_tiers": [
                {"surge_pct": 3.0, "sell_ratio": 0.20, "reset_on_sell": False, "label": "单日上涨 ≥ 3.0% 卖出 1/5 (20%)"},
                {"surge_pct": 5.0, "sell_ratio": 0.25, "reset_on_sell": False, "label": "单日上涨 ≥ 5.0% 卖出 1/4 (25%)"},
                {"surge_pct": 7.0, "sell_ratio": 0.3333, "reset_on_sell": False, "label": "单日上涨 ≥ 7.0% 卖出 1/3 (33.33%)"}
            ],
            "cumulative_profit_target_pct": 10.0,
            "cumulative_profit_sell_ratio": 0.3333,
            "cumulative_reset_on_sell": True,
            "buy_cooldown_days": 1,
            "sell_cooldown_days": 1,
            "max_position_limit": 100000.0
        }
    },
    {
        "id": "intraday_t",
        "name": "分时做T与底仓波段策略",
        "category": "stock",
        "badge": "T+1底仓做T",
        "description": "严格遵循A股T+1与底仓制度：以初始底仓为依托，分时冲高时高抛卖出，回踩时低吸接回（买回手数≤当日卖出手数），支持多档跌加涨减、利润重置摊薄持仓成本与全局目标止盈。",
        "default_config": {
            "initial_capital": 30000.0,
            "initial_base_shares": 1000,
            "base_protect_shares": 300,
            "settlement_type": "T+1",
            "t_surge_sell_pct": 1.8,
            "t_sell_shares": 300,
            "enable_pullback_buyback": True,
            "pullback_ref_type": "from_sell_price",  # "from_sell_price" (较卖出点跌幅) 或 "from_daily_change" (当天跌幅)
            "t_pullback_buy_pct": 1.5,
            "daily_drop_buyback_pct": 2.0,
            "t_max_buyback_ratio": 1.0,
            "max_daily_t_rounds": 2,
            "buy_tiers": [
                {"type": "drop", "operator": ">=", "drop_pct": 3.0, "amount": 5000.0, "label": "单日大跌 ≥ 3.0% 加仓约 ¥5000"},
                {"type": "drop", "operator": ">=", "drop_pct": 6.0, "amount": 8000.0, "label": "单日大跌 ≥ 6.0% 加仓约 ¥8000"}
            ],
            "surge_profit_tiers": [
                {"surge_pct": 5.0, "sell_ratio": 0.25, "reset_on_sell": True, "label": "单日暴涨 ≥ 5.0% 阶梯减仓 1/4 (25%)"},
                {"surge_pct": 8.0, "sell_ratio": 0.3333, "reset_on_sell": True, "label": "单日暴涨 ≥ 8.0% 阶梯减仓 1/3 (33%)"}
            ],
            "cumulative_profit_target_pct": 15.0,
            "cumulative_profit_sell_ratio": 0.5,
            "cumulative_reset_on_sell": True,
            "enable_lot_profit_take": True,
            "lot_profit_take_pct": 3.0,
            "lot_profit_sell_ratio": 1.0,
            "stop_loss_pct": 10.0,
            "buy_cooldown_days": 0,
            "sell_cooldown_days": 0
        }
    },
    {
        "id": "smart_grid",
        "name": "智能网格震荡策略",
        "category": "stock",
        "badge": "网格做T",
        "description": "适合区间震荡大盘股与白马股：以底仓为基础，股价每下跌设定步长自动买入固定手数，反弹时挂单卖出，持续赚取网格波动价差。",
        "default_config": {
            "initial_capital": 30000.0,
            "settlement_type": "T+1",
            "grid_step_down_pct": 3.5,     # 每次较上一次买入点下跌 3.5% 买入一格
            "grid_step_up_pct": 4.5,       # 每次较持仓成本反弹 4.5% 卖出一格
            "grid_trade_amount": 5000.0,   # 每格加仓金额（自动换算为整手）
            "max_grid_layers": 6,          # 最大网格层数
            "stop_loss_pct": 15.0          # 个股止损线（%）
        }
    },
    {
        "id": "ma_trend",
        "name": "均线趋势跟踪策略",
        "category": "stock",
        "badge": "波段趋势",
        "description": "基于经典量化均线系统：短期均线（如 MA5）向上突破长期均线（如 MA20）确立右侧上升通道时买入，死叉时果断减仓离场。",
        "default_config": {
            "initial_capital": 20000.0,
            "settlement_type": "T+1",
            "ma_fast": 5,                  # 快线周期（5日线）
            "ma_slow": 20,                 # 慢线周期（20日线）
            "buy_amount": 8000.0,          # 金叉建仓金额
            "sell_ratio": 0.5,             # 死叉卖出比例
            "stop_loss_pct": 7.0,          # 趋势破位硬止损线（%）
            "cooldown_trading_days": 2     # 信号冷却交易日数
        }
    },
    {
        "id": "custom",
        "name": "自定义多因子组合策略",
        "category": "stock",
        "badge": "高度定制",
        "description": "自由组合股价涨跌幅、持仓盈亏比、回撤幅度等复合因子，量身定制专属股票量化风控模型。",
        "default_config": {
            "initial_capital": 20000.0,
            "settlement_type": "T+1",
            "buy_rules": [
                {"type": "daily_drop", "threshold_pct": 3.0, "amount": 6000.0, "enabled": True, "label": "单日跌幅 ≥ 3.0% 时加仓 ¥6000"}
            ],
            "sell_rules": [
                {"type": "cumulative_profit", "threshold_pct": 12.0, "ratio": 0.5, "enabled": True, "label": "累计收益率 ≥ 12.0% 时减仓 1/2"},
                {"type": "daily_surge", "threshold_pct": 6.0, "ratio": 0.3333, "enabled": True, "label": "单日大涨 ≥ 6.0% 时卖出 1/3"}
            ],
            "cooldown_trading_days": 1
        }
    },
    # =========================================================================
    # TIANJIT STRATEGY TEMPLATES (天机时空策略模板)
    # =========================================================================
    {
        "id": "tianjit",
        "name": "天机时空策略",
        "category": "fund",
        "badge": "时空择时",
        "description": "融合生辰八字流日五行、神煞、十神四层因子打分（含下一交易日前瞻联动，自动跳过周末及法定休市，周五推演下周一），以「月度大势滤网+流日评分+下一交易日前瞻+价格触发」智能选择买卖时点。今日大跌+下一交易日大吉→逆势加仓；今日有盈+下一交易日凶→提前止盈。所有因子权重均可自由调整。",
        "default_config": {
            "initial_capital": 50000.0,
            "settlement_type": "T+1",
            "day_master": "", "year_branch": "", "day_branch": "",
            "score_threshold_s": 88, "score_threshold_a": 75, "score_threshold_b": 60,
            "monthly_regime_enabled": True,
            "favorable_elements": ["金", "水"],
            "pressure_elements": ["火", "土"],
            "pressure_max_position_pct": 30,
            "shensha_weights": {
                "天乙贵人": 10, "太极贵人": 8, "禄神临日": 8,
                "将星坐镇": 4,  "文昌贵人": 6, "华盖星": 2, "驿马星": 2,
                "羊刃警示": -10, "咸池惑心": -5
            },
            "ten_god_weights": {
                "正印": 6, "偏印": 5, "比肩": 3, "劫财": 2,
                "食神": -2, "伤官": -6,
                "正财": 2, "偏财": 1, "正官": -3, "七杀": -5
            },
            "branch_element_weights": {
                "金": 6, "水": 6, "木": -2, "火": -6, "土": -3
            },
            "signal_s": {
                "enabled": True, "amount": 5000.0,
                "price_drop_required": 0.0,
                "price_rise_sell": 5.0, "sell_ratio_on_rise": 0.25
            },
            "signal_a": {"enabled": True, "amount": 2000.0, "price_drop_required": 1.5},
            "signal_b": {"enabled": True, "max_position_pct": 60},
            "signal_c": {
                "enabled": True, "sell_ratio": 0.30,
                "price_drop_sell_trigger": 2.0, "extra_sell_ratio": 0.20,
                "force_clear_on_drop": 5.0
            },
            "sha_enhanced_rules": {
                "enabled": True, "ten_gods": ["伤官", "七杀"],
                "buy_only_on_big_drop": True, "buy_drop_pct": 3.0, "buy_amount": 1000.0
            },
            "t1_lookahead": {
                "enabled": True,
                "tomorrow_good_threshold": 82,
                "tomorrow_bad_threshold": 62,
                "tomorrow_danger_threshold": 50,
                "today_drop_required_pct": 1.0,
                "tomorrow_boost_multiplier": 1.5,
                "consecutive_good_boost": 1.2,
                "max_boost_cap_multiplier": 2.0,
                "min_profit_to_sell_pct": 0.0,
                "tomorrow_reduce_ratio": 0.25,
                "tomorrow_danger_ratio": 0.40,
                "preview_today_max_score": 74,
                "preview_tomorrow_threshold": 88,
                "preview_amount": 1500.0,
                "skip_if_today_is_danger": True
            },
            "global_stop_loss_pct": 8.0,
            "global_profit_target_pct": 15.0,
            "global_profit_sell_ratio": 0.40,
            "global_profit_reset": True,
            "reset_profit_on_sell": True,
            "buy_cooldown_days": 1, "sell_cooldown_days": 1,
            "max_position_limit": 0, "avoid_7day_penalty": True
        }
    },
    {
        "id": "tianjit",
        "name": "天机时空策略",
        "category": "stock",
        "badge": "时空择时",
        "description": "融合生辰八字流日五行、神煞、十神四层因子打分（含T+1次日前瞻信号），智能选择A股买卖时点，支持整手取整与印花税。",
        "default_config": {
            "initial_capital": 50000.0,
            "settlement_type": "T+1",
            "day_master": "", "year_branch": "", "day_branch": "",
            "score_threshold_s": 88, "score_threshold_a": 75, "score_threshold_b": 60,
            "monthly_regime_enabled": True,
            "favorable_elements": ["金", "水"],
            "pressure_elements": ["火", "土"],
            "pressure_max_position_pct": 30,
            "shensha_weights": {
                "天乙贵人": 10, "太极贵人": 8, "禄神临日": 8,
                "将星坐镇": 4,  "文昌贵人": 6, "华盖星": 2, "驿马星": 2,
                "羊刃警示": -10, "咸池惑心": -5
            },
            "ten_god_weights": {
                "正印": 6, "偏印": 5, "比肩": 3, "劫财": 2,
                "食神": -2, "伤官": -6,
                "正财": 2, "偏财": 1, "正官": -3, "七杀": -5
            },
            "branch_element_weights": {
                "金": 6, "水": 6, "木": -2, "火": -6, "土": -3
            },
            "signal_s": {
                "enabled": True, "amount": 8000.0,
                "price_drop_required": 0.0,
                "price_rise_sell": 5.0, "sell_ratio_on_rise": 0.25
            },
            "signal_a": {"enabled": True, "amount": 4000.0, "price_drop_required": 1.5},
            "signal_b": {"enabled": True, "max_position_pct": 60},
            "signal_c": {
                "enabled": True, "sell_ratio": 0.30,
                "price_drop_sell_trigger": 2.0, "extra_sell_ratio": 0.20,
                "force_clear_on_drop": 5.0
            },
            "sha_enhanced_rules": {
                "enabled": True, "ten_gods": ["伤官", "七杀"],
                "buy_only_on_big_drop": True, "buy_drop_pct": 3.0, "buy_amount": 2000.0
            },
            "t1_lookahead": {
                "enabled": True,
                "tomorrow_good_threshold": 82,
                "tomorrow_bad_threshold": 62,
                "tomorrow_danger_threshold": 50,
                "today_drop_required_pct": 1.0,
                "tomorrow_boost_multiplier": 1.5,
                "consecutive_good_boost": 1.2,
                "max_boost_cap_multiplier": 2.0,
                "min_profit_to_sell_pct": 0.0,
                "tomorrow_reduce_ratio": 0.25,
                "tomorrow_danger_ratio": 0.40,
                "preview_today_max_score": 74,
                "preview_tomorrow_threshold": 88,
                "preview_amount": 2000.0,
                "skip_if_today_is_danger": True
            },
            "global_stop_loss_pct": 8.0,
            "global_profit_target_pct": 15.0,
            "global_profit_sell_ratio": 0.40,
            "global_profit_reset": True,
            "reset_profit_on_sell": True,
            "buy_cooldown_days": 1, "sell_cooldown_days": 1,
            "max_position_limit": 0
        }
    }
]



def get_preset_template(template_id: str, category: str = None) -> Dict[str, Any]:
    """Retrieve template by id and optional category."""
    norm_id = template_id.replace("stock_", "")
    for t in PRESET_TEMPLATES:
        if (t["id"] == template_id or t["id"] == norm_id) and (not category or t.get("category") == category):
            return t
    for t in PRESET_TEMPLATES:
        if t["id"] == template_id or t["id"] == norm_id:
            return t
    return PRESET_TEMPLATES[0]


def get_templates_by_category(category: str = "fund") -> List[Dict[str, Any]]:
    """Retrieve templates filtered by category."""
    return [t for t in PRESET_TEMPLATES if t.get("category") == category]

