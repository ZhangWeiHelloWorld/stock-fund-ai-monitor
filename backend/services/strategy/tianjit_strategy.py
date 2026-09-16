"""
天机时空策略引擎 (TianJi TimingStrategy Engine)
=====================================
策略口诀：「顺天时而动，逆五行者退」

核心架构（四层信号过滤）:
  Layer 1: 月度五行大势滤网 (Regime Filter)
  Layer 2: 流日多因子打分 (Daily Bazi Score, 35~98分)
  Layer 3: 次日前瞻信号 (T+1 Lookahead) — 干支为历法推算，明日吉凶今日即可确定
  Layer 4: 价格触发阀值 (Price Trigger)

历法评分属于未经验证的研究因子，不是上涨概率。
事后选取的案例不能证明预测能力；收益须经扣费、样本外回测验证。

所有因子权重、触发阈值均可通过 config 自定义配置。
"""

import math
from datetime import date, timedelta
from typing import Dict, Any, List, Optional, Tuple

# 复用日历服务已有的干支计算函数
from services.calendar_service import (
    get_day_ganzhi,
    calculate_ten_god,
    calculate_daily_shensha,
    evaluate_metaphysics_luck,
    TIANGAN,
    DIZHI,
    TG_WUXING,
    DZ_WUXING,
)
from services.trading_calendar import (
    is_trading_day,
    get_next_trading_day,
    get_next_trading_day_info,
)

# ===========================================================================
# 默认配置常量
# ===========================================================================

DEFAULT_SHENSHA_WEIGHTS = {
    "天乙贵人": 10,
    "太极贵人": 8,
    "禄神临日": 8,
    "将星坐镇": 4,
    "文昌贵人": 6,
    "华盖星":   2,
    "驿马星":   2,
    "羊刃警示": -10,
    "咸池惑心": -5,
}

DEFAULT_TEN_GOD_WEIGHTS = {
    "正印": 6,  "偏印": 5,
    "比肩": 3,  "劫财": 2,
    "食神": -2, "伤官": -6,
    "正财": 2,  "偏财": 1,
    "正官": -3, "七杀": -5,
}

DEFAULT_BRANCH_ELEMENT_WEIGHTS = {
    "金": 6,   # 喜用
    "水": 6,   # 喜用
    "木": -2,
    "火": -6,  # 忌神
    "土": -3,
}

# 月柱月令五行（以节气精确划分，简化版按月干支主气）
# key = 月干支主气五行
FAVORABLE_ELEMENTS_DEFAULT = ["金", "水"]
PRESSURE_ELEMENTS_DEFAULT  = ["火", "土"]

# 月令地支五行映射（公历月粗略对应）
MONTH_BRANCH_MAP = {
    1: "丑", 2: "寅", 3: "卯", 4: "辰",
    5: "巳", 6: "午", 7: "未", 8: "申",
    9: "酉", 10:"戌", 11:"亥", 12:"子"
}


# ===========================================================================
# Layer 1: 月度五行大势评估
# ===========================================================================

def compute_monthly_regime(
    year: int,
    month: int,
    settings: Dict[str, Any],
    cfg: Dict[str, Any],
    as_of: Optional[date] = None,
) -> Dict[str, Any]:
    """
    判断当月月令五行与日主喜忌，返回大势状态与最大仓位系数。

    Returns:
        {
            "regime": "SUPPORT" | "NEUTRAL" | "PRESSURE",
            "max_position_ratio": float,   # 0.0~1.0
            "month_branch": str,
            "month_element": str,
            "reason": str
        }
    """
    favorable = cfg.get("favorable_elements", FAVORABLE_ELEMENTS_DEFAULT)
    pressure  = cfg.get("pressure_elements",  PRESSURE_ELEMENTS_DEFAULT)
    pressure_max_pct = float(cfg.get("pressure_max_position_pct", 30)) / 100.0

    from services.bazi_calculator import get_solar_term_day
    target_date = as_of or date(year, month, 15)
    effective_month = target_date.month
    if target_date.day < get_solar_term_day(target_date.year, target_date.month):
        effective_month = effective_month - 1 or 12
    month_branch = MONTH_BRANCH_MAP[effective_month]
    month_element = DZ_WUXING.get(month_branch, ("水", "癸", ""))[0]

    if not cfg.get("monthly_regime_enabled", True):
        regime, max_ratio, reason = "NEUTRAL", 1.0, "月度滤网已关闭"
    elif month_element in favorable:
        regime = "SUPPORT"
        max_ratio = 1.0
        reason = f"月令{month_branch}（{month_element}），属喜用五行，大势顺遂，最大仓位 100%"
    elif month_element in pressure:
        regime = "PRESSURE"
        max_ratio = max(0.0, min(1.0, pressure_max_pct))
        reason = f"月令{month_branch}（{month_element}），属逆境五行，大势承压，最大仓位强制压至 {int(pressure_max_pct*100)}%"
    else:
        regime = "NEUTRAL"
        max_ratio = 0.70
        reason = f"月令{month_branch}（{month_element}），五行中性，正常操作，最大仓位 70%"

    return {
        "regime": regime,
        "max_position_ratio": max_ratio,
        "month_branch": month_branch,
        "month_element": month_element,
        "reason": reason,
        "calendar_precision": "approximate_solar_term_day",
    }


# ===========================================================================
# Layer 2: 流日多因子打分引擎
# ===========================================================================

def compute_daily_bazi_score(
    dt: date,
    settings: Dict[str, Any],
    cfg: Dict[str, Any]
) -> Dict[str, Any]:
    """
    计算指定日期的天机综合评分（35~98分），输出信号级别与详细因子分解。

    Args:
        dt: 目标日期
        settings: 系统设置（含 calendar_bazi_day_master / calendar_bazi_year / calendar_bazi_day）
        cfg: 策略配置（含自定义权重）

    Returns:
        {
            "date": str,
            "ganzhi": str,
            "stem": str, "branch": str,
            "ten_god": str,
            "score": int,
            "signal_level": "S" | "A" | "B" | "C",   # S=大吉 A=吉 B=平 C=冲/凶
            "rating": str,
            "tag": str,
            "shenshas": list,
            "primary_shensha": dict | None,
            "score_breakdown": dict,
            "reason": str
        }
    """
    # 命盘参数
    dm     = settings.get("calendar_bazi_day_master", "壬水").strip()
    bazi_year = settings.get("calendar_bazi_year", "壬申").strip()
    bazi_day  = settings.get("calendar_bazi_day",  "壬辰").strip()
    year_b = bazi_year[-1] if len(bazi_year) >= 2 else "申"
    day_b  = bazi_day[-1]  if len(bazi_day)  >= 2 else "辰"
    dm_stem = dm[0] if dm else "壬"

    # 自定义权重（允许覆盖默认值）
    shensha_w    = {**DEFAULT_SHENSHA_WEIGHTS,    **cfg.get("shensha_weights", {})}
    ten_god_w    = {**DEFAULT_TEN_GOD_WEIGHTS,    **cfg.get("ten_god_weights", {})}
    branch_elem_w= {**DEFAULT_BRANCH_ELEMENT_WEIGHTS, **cfg.get("branch_element_weights", {})}

    # 阈值
    threshold_s = int(cfg.get("score_threshold_s", 88))
    threshold_a = int(cfg.get("score_threshold_a", 75))
    threshold_b = int(cfg.get("score_threshold_b", 60))

    # 获取流日干支
    day_info = get_day_ganzhi(dt)
    stem   = day_info["stem"]
    branch = day_info["branch"]
    stem_wx   = day_info["stem_wuxing"]
    branch_wx = day_info["branch_wuxing"]

    # 十神
    ten_god = calculate_ten_god(dm, stem)

    # 神煞
    shenshas = calculate_daily_shensha(dm_stem, year_b, day_b, stem, branch)

    # 基础分 75
    score = 75
    breakdown = {"base": 75, "shensha": 0, "ten_god": 0, "stem": 0, "branch": 0}
    reasons = []

    # ── 神煞加减分 ──
    for s in shenshas:
        w = shensha_w.get(s["name"], 0)
        score += w
        breakdown["shensha"] += w
        if w > 0:
            reasons.append(f"【{s['name']}】+{w}分")
        elif w < 0:
            reasons.append(f"【{s['name']}】{w}分")

    # ── 十神加减分 ──
    tg_delta = ten_god_w.get(ten_god, 0)
    score += tg_delta
    breakdown["ten_god"] = tg_delta
    if tg_delta != 0:
        reasons.append(f"十神{ten_god}：{'+' if tg_delta>0 else ''}{tg_delta}分")

    # ── 天干五行加减分 ──
    stem_delta = branch_elem_w.get(stem_wx, 0)
    score += stem_delta
    breakdown["stem"] = stem_delta
    if stem_delta != 0:
        reasons.append(f"天干{stem}({stem_wx})：{'+' if stem_delta>0 else ''}{stem_delta}分")

    # ── 地支五行加减分 ──
    branch_delta = branch_elem_w.get(branch_wx, 0)
    # 地支权重减半（天干透出权重高于地支藏干）
    branch_delta_half = round(branch_delta * 0.7)
    score += branch_delta_half
    breakdown["branch"] = branch_delta_half
    if branch_delta_half != 0:
        reasons.append(f"地支{branch}({branch_wx})：{'+' if branch_delta_half>0 else ''}{branch_delta_half}分")

    # 边界限制
    score = max(35, min(98, score))

    # 信号级别
    if score >= threshold_s:
        signal_level = "S"
        rating = "大吉"
        tag    = "大吉·顺势进攻"
    elif score >= threshold_a:
        signal_level = "A"
        rating = "吉"
        tag    = "吉·逢低潜伏"
    elif score >= threshold_b:
        signal_level = "B"
        rating = "平"
        tag    = "平·观望蓄势"
    else:
        signal_level = "C"
        rating = "冲/凶"
        tag    = "冲·防洗盘回撤"

    primary_shensha = shenshas[0] if shenshas else None

    return {
        "date": dt.isoformat(),
        "ganzhi": day_info["ganzhi"],
        "stem": stem,
        "branch": branch,
        "stem_wuxing": stem_wx,
        "branch_wuxing": branch_wx,
        "ten_god": ten_god,
        "score": score,
        "signal_level": signal_level,
        "rating": rating,
        "tag": tag,
        "shenshas": shenshas,
        "shensha_names": [s["name"] for s in shenshas],
        "primary_shensha": primary_shensha,
        "score_breakdown": breakdown,
        "reason": "；".join(reasons) or "气场平稳，随行就市",
    }


# ===========================================================================
# Layer 3: 次日前瞻信号 (T+1 Bazi Lookahead - 下一交易日)
# ===========================================================================

def compute_t1_lookahead_signal(
    today: date,
    today_score_data: Dict[str, Any],
    today_change_pct: float,
    cur_profit_pct: float,
    has_position: bool,
    settings: Dict[str, Any],
    cfg: Dict[str, Any],
    next_trading_day: Optional[date] = None,
) -> Dict[str, Any]:
    """
    计算下一实际交易日前瞻信号（T+1 Lookahead）。
    严格推导下一个交易日（如周五推导下周一，长假前夕推导节后首日），杜绝自然日误判。

    核心逻辑（基于实盘验证的4个场景）:
      场景A: 今日跌幅 >= drop_trigger + 下一交易日大吉 → 增强今日买入（1.5x）
      场景B: 持仓有浮盈 + 下一交易日凶            → 提前今日减仓（25%~40%）
      场景C: 今日B级平 + 下一交易日大吉           → 打破平日限制，提前预建仓
      场景D: 今日S级 + 下一交易日S/A级            → 连续大吉额外放大买入（1.2x）
    """
    t1_cfg = cfg.get("t1_lookahead", {})
    if not t1_cfg.get("enabled", True):
        return _no_t1_signal()

    # 1. 确定下一个实际交易日
    if next_trading_day:
        tomorrow = next_trading_day
        days_ahead = (tomorrow - today).days
        is_natural_tomorrow = (days_ahead == 1)
        weekday_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][tomorrow.weekday()]
        date_short = tomorrow.strftime("%m-%d")
        is_weekend_skipped = (today.weekday() == 4 and tomorrow.weekday() == 0) or (days_ahead >= 3)
        
        if is_weekend_skipped and today.weekday() == 4:
            display_label = f"下周一 ({date_short})"
            skip_desc = "已跳过周末双休"
        elif days_ahead > 1:
            display_label = f"下一交易日 ({weekday_cn} {date_short})"
            skip_desc = f"相隔{days_ahead}日·跳过休市"
        else:
            display_label = f"明日 ({weekday_cn} {date_short})"
            skip_desc = "正常次日开盘"

        next_day_info = {
            "target_date": today.isoformat(),
            "next_trading_date": tomorrow.isoformat(),
            "days_ahead": days_ahead,
            "is_natural_tomorrow": is_natural_tomorrow,
            "is_weekend_skipped": is_weekend_skipped,
            "weekday_cn": weekday_cn,
            "display_label": display_label,
            "skip_reason": skip_desc,
        }
    else:
        next_day_info = get_next_trading_day_info(today, max_lookahead=20)
        if not next_day_info.get("next_trading_date"):
            return _no_t1_signal()
        tomorrow = date.fromisoformat(next_day_info["next_trading_date"])

    # 计算下一交易日评分
    tomorrow_data = compute_daily_bazi_score(tomorrow, settings, cfg)
    t_score = tomorrow_data["score"]
    t_level = tomorrow_data["signal_level"]
    t_ganzhi = tomorrow_data["ganzhi"]
    t_shenshas = tomorrow_data["shensha_names"]

    today_level = today_score_data["signal_level"]

    # 参数读取
    good_th    = int(t1_cfg.get("tomorrow_good_threshold", 82))
    bad_th     = int(t1_cfg.get("tomorrow_bad_threshold", 62))
    danger_th  = int(t1_cfg.get("tomorrow_danger_threshold", 50))

    drop_req   = float(t1_cfg.get("today_drop_required_pct", 1.0))
    boost_mul  = float(t1_cfg.get("tomorrow_boost_multiplier", 1.5))
    consec_mul = float(t1_cfg.get("consecutive_good_boost", 1.2))
    max_cap    = float(t1_cfg.get("max_boost_cap_multiplier", 2.0))

    min_profit = float(t1_cfg.get("min_profit_to_sell_pct", 0.0))
    reduce_r   = float(t1_cfg.get("tomorrow_reduce_ratio", 0.25))
    danger_r   = float(t1_cfg.get("tomorrow_danger_ratio", 0.40))

    prev_th      = int(t1_cfg.get("preview_today_max_score", 74))
    prev_tmr_th  = int(t1_cfg.get("preview_tomorrow_threshold", 88))
    preview_amt  = float(t1_cfg.get("preview_amount", 1500.0))
    skip_if_danger = bool(t1_cfg.get("skip_if_today_is_danger", True))

    # 构建带星期与跳休标识的提示头
    next_label = next_day_info["display_label"]
    skip_badge = f"[{next_day_info['skip_reason']}]" if not next_day_info["is_natural_tomorrow"] else ""
    full_next_name = f"{next_label}{(' ' + skip_badge) if skip_badge else ''}"

    base_output = {
        "tomorrow_date": tomorrow.isoformat(),
        "tomorrow_score": t_score,
        "tomorrow_signal_level": t_level,
        "tomorrow_ganzhi": t_ganzhi,
        "tomorrow_shenshas": t_shenshas,
        "next_trading_date": tomorrow.isoformat(),
        "next_trading_score": t_score,
        "next_trading_signal_level": t_level,
        "next_trading_ganzhi": t_ganzhi,
        "next_trading_shenshas": t_shenshas,
        "next_trading_label": next_day_info["display_label"],
        "next_trading_weekday": next_day_info["weekday_cn"],
        "is_weekend_skipped": next_day_info["is_weekend_skipped"],
        "days_ahead": next_day_info["days_ahead"],
    }

    # ── 场景 D：今日S级 + 下一交易日S/A级 → 连续大吉额外放大 ──
    if today_level == "S" and t_score >= good_th:
        mul = min(consec_mul, max_cap)
        return {
            **base_output,
            "scenario": "D",
            "action_modifier": "EXTRA_BOOST",
            "buy_multiplier": mul,
            "sell_ratio_override": 0.0,
            "preview_amount": 0.0,
            "reason": f"📅 今日{today_score_data['ganzhi']}大吉(S级)，下一交易日（{full_next_name} {t_ganzhi}）同为吉日(score={t_score})，连续大吉强化买入×{mul}",
        }

    # ── 场景 A：今日大跌 + 下一交易日大吉 → 增强今日买入 ──
    today_actual_drop = -today_change_pct
    if today_actual_drop >= drop_req and t_score >= good_th:
        mul = min(boost_mul, max_cap)
        shensha_str = f"【{'·'.join(t_shenshas)}】" if t_shenshas else ""
        return {
            **base_output,
            "scenario": "A",
            "action_modifier": "BUY_BOOST",
            "buy_multiplier": mul,
            "sell_ratio_override": 0.0,
            "preview_amount": 0.0,
            "reason": (
                f"🔮 下一交易日前瞻·买入增强：今日跌幅{today_change_pct:.2f}%（≥{drop_req}%），"
                f"下一交易日（{full_next_name} {t_ganzhi}{shensha_str}）大吉(score={t_score}≥{good_th})，"
                f"今日买入金额放大×{mul}，把握逆势加仓良机"
            ),
        }

    # ── 场景 B：持仓有浮盈 + 下一交易日凶/偏弱 → 提前减仓 ──
    t_ten_god = tomorrow_data.get("ten_god", "")
    bad_shensha_hit = [s for s in t_shenshas if s in ("咸池惑心", "羊刃警示")]
    is_sha_pressure = (t_ten_god in ("伤官", "七杀") and t_score < 75)

    is_tomorrow_bad = (
        t_score < bad_th
        or t_level == "C"
        or bool(bad_shensha_hit)
        or is_sha_pressure
    )

    if has_position and cur_profit_pct >= min_profit and is_tomorrow_bad:
        if t_score < danger_th or "羊刃警示" in t_shenshas:
            sell_r = danger_r
            level_str = f"极凶(score={t_score})"
        else:
            sell_r = reduce_r
            traits = []
            if bad_shensha_hit:
                traits.append("·".join(bad_shensha_hit))
            if is_sha_pressure:
                traits.append(f"{t_ten_god}泄气")
            if t_score < bad_th:
                traits.append(f"评分偏低{t_score}分")
            trait_str = f"【{'、'.join(traits)}】" if traits else ""
            level_str = f"偏弱/凶日{trait_str}"

        return {
            **base_output,
            "scenario": "B",
            "action_modifier": "SELL_EARLY",
            "buy_multiplier": 1.0,
            "sell_ratio_override": sell_r,
            "preview_amount": 0.0,
            "reason": (
                f"⚠️ 下一交易日前瞻·提前减仓：下一交易日（{full_next_name} {t_ganzhi}{level_str}），"
                f"当前持仓浮盈{cur_profit_pct:.2f}%，今日提前减仓{int(sell_r*100)}%锁利防守"
            ),
        }

    # ── 场景 C：今日B级平 + 下一交易日大吉 → 提前预建仓 ──
    if (today_score_data["score"] <= prev_th and t_score >= prev_tmr_th
            and not (skip_if_danger and today_level == "C")):
        shensha_str = f"【{'·'.join(t_shenshas)}】" if t_shenshas else ""
        return {
            **base_output,
            "scenario": "C",
            "action_modifier": "PREVIEW_BUY",
            "buy_multiplier": 1.0,
            "sell_ratio_override": 0.0,
            "preview_amount": preview_amt,
            "reason": (
                f"🌅 下一交易日前瞻·预建仓：今日气场平淡(score={today_score_data['score']})，"
                f"下一交易日（{full_next_name} {t_ganzhi}{shensha_str}）大吉(score={t_score})，"
                f"提前预建仓¥{preview_amt:.0f}，为后市主升浪布局"
            ),
        }

    return _no_t1_signal(tomorrow, tomorrow_data, next_day_info)


def _no_t1_signal(
    tomorrow: Optional[date] = None,
    tomorrow_data: Optional[Dict[str, Any]] = None,
    next_day_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    base = {
        "scenario": None,
        "action_modifier": None,
        "buy_multiplier": 1.0,
        "sell_ratio_override": 0.0,
        "preview_amount": 0.0,
        "reason": "",
    }
    if tomorrow and tomorrow_data:
        base.update({
            "tomorrow_date": tomorrow.isoformat(),
            "tomorrow_score": tomorrow_data["score"],
            "tomorrow_signal_level": tomorrow_data["signal_level"],
            "tomorrow_ganzhi": tomorrow_data["ganzhi"],
            "tomorrow_shenshas": tomorrow_data["shensha_names"],
            "next_trading_date": tomorrow.isoformat(),
            "next_trading_score": tomorrow_data["score"],
            "next_trading_signal_level": tomorrow_data["signal_level"],
            "next_trading_ganzhi": tomorrow_data["ganzhi"],
            "next_trading_shenshas": tomorrow_data["shensha_names"],
        })
        if next_day_info:
            base.update({
                "next_trading_label": next_day_info.get("display_label", ""),
                "next_trading_weekday": next_day_info.get("weekday_cn", ""),
                "is_weekend_skipped": next_day_info.get("is_weekend_skipped", False),
                "days_ahead": next_day_info.get("days_ahead", 1),
            })
    return base


# ===========================================================================
# Layer 4: 信号 → 操作决策（买入/卖出/观望）
# ===========================================================================

def resolve_tianjit_action(
    today: date,
    today_bazi: Dict[str, Any],
    t1_signal: Dict[str, Any],
    monthly_regime: Dict[str, Any],
    day_change_pct: float,
    cur_shares: float,
    cur_nav: float,
    avg_cost: float,
    last_buy_index: int,
    last_sell_index: int,
    cur_day_index: int,
    cfg: Dict[str, Any],
    round_base_cost_nav: float = 0.0,
) -> Tuple[Optional[str], float, float, str]:
    """
    综合四层信号，输出最终交易决策。

    Returns:
        (trade_action, buy_amount, sell_ratio, trade_reason)
        trade_action: "BUY" | "SELL" | None
    """
    signal_level = today_bazi["signal_level"]
    score = today_bazi["score"]
    ten_god = today_bazi["ten_god"]
    shenshas = today_bazi["shensha_names"]

    buy_cooldown  = int(cfg.get("buy_cooldown_days",  1))
    sell_cooldown = int(cfg.get("sell_cooldown_days", 1))

    max_pos_limit = float(cfg.get("max_position_limit", 0))
    cur_val = cur_shares * cur_nav if cur_shares > 0 else 0.0

    # 浮盈基准：若开启卖出后利润重置，优先使用本轮波段基准 round_base_cost_nav，否则使用历史加权平均成本 avg_cost
    should_reset_profit = bool(cfg.get("reset_profit_on_sell", cfg.get("global_profit_reset", cfg.get("cumulative_reset_on_sell", True))))
    base_cost_for_profit = round_base_cost_nav if (should_reset_profit and round_base_cost_nav > 0) else avg_cost
    cum_profit_pct = (cur_nav - base_cost_for_profit) / base_cost_for_profit * 100.0 if (base_cost_for_profit > 0 and cur_shares > 0) else 0.0
    global_stop_loss  = float(cfg.get("global_stop_loss_pct", 8.0))
    global_profit_tgt = float(cfg.get("global_profit_target_pct", 15.0))
    global_profit_r   = float(cfg.get("global_profit_sell_ratio", 0.40))

    # ── 月度大势最大仓位系数 ──
    max_pos_ratio = monthly_regime.get("max_position_ratio", 1.0)
    regime_reason = monthly_regime.get("reason", "")

    # ══════════════════════════════════════════
    # 全局止损（最高优先级）
    # ══════════════════════════════════════════
    if (cur_shares > 0 and global_stop_loss > 0
            and cum_profit_pct <= -abs(global_stop_loss)):
        return (
            "SELL", 0.0, 1.0,
            f"⛔ 全局硬止损：持仓浮亏 {cum_profit_pct:.2f}% ≤ -{global_stop_loss}%，退出控制损失"
        )

    if max_pos_limit > 0 and cur_val > max_pos_limit * max_pos_ratio:
        excess_ratio = (cur_val - max_pos_limit * max_pos_ratio) / cur_val
        return "SELL", 0.0, min(1.0, excess_ratio), "仓位超过配置上限，减仓恢复风险预算"

    # ══════════════════════════════════════════
    # T+1 前瞻：场景B 提前减仓（高优先级）
    # ══════════════════════════════════════════
    t1_mod = t1_signal.get("action_modifier")
    t1_sell_r = float(t1_signal.get("sell_ratio_override", 0.0))
    if (t1_mod == "SELL_EARLY" and t1_sell_r > 0
            and cur_shares > 0
            and (cur_day_index - last_sell_index) >= sell_cooldown):
        return (
            "SELL", 0.0, t1_sell_r,
            t1_signal.get("reason", "次日前瞻减仓")
        )

    # ══════════════════════════════════════════
    # 全局止盈
    # ══════════════════════════════════════════
    if (cur_shares > 0 and global_profit_tgt > 0
            and cum_profit_pct >= global_profit_tgt
            and (cur_day_index - last_sell_index) >= sell_cooldown):
        return (
            "SELL", 0.0, global_profit_r,
            f"🎯 全局止盈：累计浮盈 +{cum_profit_pct:.2f}% ≥ {global_profit_tgt}%，减仓 {int(global_profit_r*100)}%"
        )

    # ══════════════════════════════════════════
    # 按信号级别处理
    # ══════════════════════════════════════════
    sig_s_cfg = cfg.get("signal_s", {})
    sig_a_cfg = cfg.get("signal_a", {})
    sig_b_cfg = cfg.get("signal_b", {})
    sig_c_cfg = cfg.get("signal_c", {})
    sha_cfg   = cfg.get("sha_enhanced_rules", {})

    actual_drop = -day_change_pct  # 正值=跌幅，负值=涨幅

    # ── C 级：冲/凶 ──
    if signal_level == "C" and sig_c_cfg.get("enabled", True):
        # 伤官/七杀日专项买入（低仓抄底）
        if sha_cfg.get("enabled", True) and ten_god in sha_cfg.get("ten_gods", ["伤官", "七杀"]):
            sha_drop_req = float(sha_cfg.get("buy_drop_pct", 3.0))
            sha_amt      = float(sha_cfg.get("buy_amount", 1000.0))
            if (sha_cfg.get("buy_only_on_big_drop", True) and actual_drop >= sha_drop_req
                    and sha_amt > 0
                    and (cur_day_index - last_buy_index) >= buy_cooldown):
                if max_pos_limit <= 0 or cur_val + sha_amt <= max_pos_limit * max_pos_ratio:
                    # 应用T+1增强
                    final_amt = sha_amt
                    t1_reason = ""
                    if t1_mod == "BUY_BOOST":
                        boost = min(float(t1_signal.get("buy_multiplier", 1.0)),
                                    float(cfg.get("t1_lookahead", {}).get("max_boost_cap_multiplier", 2.0)))
                        final_amt = round(sha_amt * boost, 2)
                        t1_reason = f"，{t1_signal.get('reason','')}"
                    if max_pos_limit > 0:
                        final_amt = min(final_amt, max(0.0, max_pos_limit * max_pos_ratio - cur_val))
                    return (
                        "BUY", final_amt, 0.0,
                        f"⚡ {ten_god}大跌抄底：跌幅 {actual_drop:.2f}% ≥ {sha_drop_req}%，小仓试探¥{final_amt:.0f}{t1_reason}"
                    )

        # C级减仓逻辑
        if cur_shares > 0 and (cur_day_index - last_sell_index) >= sell_cooldown:
            base_sell_r = float(sig_c_cfg.get("sell_ratio", 0.30))
            extra_drop_th = float(sig_c_cfg.get("price_drop_sell_trigger", 2.0))
            extra_sell_r  = float(sig_c_cfg.get("extra_sell_ratio", 0.20))
            force_clear_drop = float(sig_c_cfg.get("force_clear_on_drop", 5.0))

            if actual_drop >= force_clear_drop:
                sell_r = 1.0
                reason = (
                    f"🔴 {today_bazi['ganzhi']}凶日大跌止损：跌幅{actual_drop:.2f}%≥{force_clear_drop}%，"
                    f"凶日{'+'.join(shenshas) if shenshas else ''}，强制清仓"
                )
            elif actual_drop >= extra_drop_th:
                sell_r = min(1.0, base_sell_r + extra_sell_r)
                reason = (
                    f"🟠 {today_bazi['ganzhi']}冲日叠加大跌：跌幅{actual_drop:.2f}%≥{extra_drop_th}%，"
                    f"减仓{int(sell_r*100)}%"
                )
            else:
                sell_r = base_sell_r
                reason = (
                    f"🟡 {today_bazi['ganzhi']}冲/凶日(score={score})防守减仓{int(sell_r*100)}%，"
                    f"{today_bazi.get('reason','')}"
                )
            return "SELL", 0.0, sell_r, reason

    # ── B 级：平/观望 ──
    elif signal_level == "B":
        # B级 + T+1预建仓（场景C）
        t1_prev_amt = float(t1_signal.get("preview_amount", 0.0))
        if (t1_mod == "PREVIEW_BUY" and t1_prev_amt > 0
                and (cur_day_index - last_buy_index) >= buy_cooldown):
            if max_pos_limit <= 0 or cur_val + t1_prev_amt <= max_pos_limit * max_pos_ratio:
                return (
                    "BUY", t1_prev_amt, 0.0,
                    t1_signal.get("reason", "次日前瞻预建仓")
                )
        # 纯B级：观望，不操作
        return None, 0.0, 0.0, ""

    # ── A 级：吉·逢低潜伏 ──
    elif signal_level == "A" and sig_a_cfg.get("enabled", True):
        if (cur_day_index - last_buy_index) >= buy_cooldown:
            drop_req = float(sig_a_cfg.get("price_drop_required", 1.5))
            base_amt = float(sig_a_cfg.get("amount", 2000.0))
            amt_pct  = float(sig_a_cfg.get("amount_pct", 0.0))

            buy_amt = base_amt
            if actual_drop >= drop_req:
                # 计算T+1放大
                if t1_mod in ("BUY_BOOST", "EXTRA_BOOST"):
                    boost = min(float(t1_signal.get("buy_multiplier", 1.0)),
                                float(cfg.get("t1_lookahead", {}).get("max_boost_cap_multiplier", 2.0)))
                    buy_amt = round(buy_amt * boost, 2)
                    t1_str = f"，次日前瞻增强×{boost}"
                else:
                    t1_str = ""

                if max_pos_limit <= 0 or cur_val + buy_amt <= max_pos_limit * max_pos_ratio:
                    return (
                        "BUY", buy_amt, 0.0,
                        f"🟢 {today_bazi['ganzhi']}吉日逢低加仓：跌幅{actual_drop:.2f}%≥{drop_req}%，"
                        f"加仓¥{buy_amt:.0f}{t1_str}（score={score}，{today_bazi.get('reason','')}）"
                    )

    # ── S 级：大吉·顺势进攻 ──
    elif signal_level == "S" and sig_s_cfg.get("enabled", True):
        rise_sell_pct = float(sig_s_cfg.get("price_rise_sell", 5.0))
        if (cur_shares > 0 and rise_sell_pct > 0 and day_change_pct >= rise_sell_pct
                and (cur_day_index - last_sell_index) >= sell_cooldown):
            return "SELL", 0.0, float(sig_s_cfg.get("sell_ratio_on_rise", 0.25)), "涨幅达标止盈优先于加仓"
        if (cur_day_index - last_buy_index) >= buy_cooldown:
            drop_req  = float(sig_s_cfg.get("price_drop_required", 0.0))
            base_amt  = float(sig_s_cfg.get("amount", 5000.0))

            # T+1放大系数
            boost = 1.0
            t1_str = ""
            if t1_mod in ("BUY_BOOST", "EXTRA_BOOST"):
                boost = min(float(t1_signal.get("buy_multiplier", 1.0)),
                            float(cfg.get("t1_lookahead", {}).get("max_boost_cap_multiplier", 2.0)))
                t1_str = f"，次日前瞻增强×{boost}"

            buy_amt = round(base_amt * boost, 2)

            if drop_req <= 0 or actual_drop >= drop_req:
                if max_pos_limit <= 0 or cur_val + buy_amt <= max_pos_limit * max_pos_ratio:
                    shensha_str = "·".join(shenshas) if shenshas else ""
                    return (
                        "BUY", buy_amt, 0.0,
                        f"🚀 {today_bazi['ganzhi']}大吉日顺势进攻：score={score}，"
                        f"{shensha_str}，加仓¥{buy_amt:.0f}{t1_str}"
                    )

        # 大吉日上涨触发止盈
        rise_sell_pct = float(sig_s_cfg.get("price_rise_sell", 5.0))
        rise_sell_r   = float(sig_s_cfg.get("sell_ratio_on_rise", 0.25))
        if (cur_shares > 0 and rise_sell_pct > 0
                and day_change_pct >= rise_sell_pct
                and (cur_day_index - last_sell_index) >= sell_cooldown):
            return (
                "SELL", 0.0, rise_sell_r,
                f"💰 大吉日涨幅达标止盈：涨幅{day_change_pct:.2f}%≥{rise_sell_pct}%，减仓{int(rise_sell_r*100)}%"
            )

    return None, 0.0, 0.0, ""


# ===========================================================================
# 主回测入口
# ===========================================================================

def run_tianjit_backtest(
    history_data: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    settings: Dict[str, Any],
    fee_config: Optional[Dict[str, Any]] = None,
    is_stock: bool = False,
    fund_code: str = "",
    fund_name: str = "",
    strategy_type: str = "tianjit",
    asset_type: str = "fund",
) -> Dict[str, Any]:
    """
    天机时空策略专属回测驱动器。
    输出格式与标准 backtest_engine 完全一致，完美适配前端图表与卡片。
    """
    from services.strategy.fee_calculator import (
        calculate_subscription, calculate_redemption,
        get_redemption_fee_rate, calculate_holding_days,
        DEFAULT_REDEMPTION_TIERS, DEFAULT_SUBSCRIPTION_RATE
    )
    from services.strategy.stock_data_provider import (
        calculate_stock_trade_fee, DEFAULT_STOCK_FEE_STRUCTURE
    )

    if not history_data or len(history_data) < 2:
        return {
            "success": False,
            "message": "选定时间范围内的历史净值数据不足（至少需要2个交易日）",
            "metrics": {},
            "equity_curve": [],
            "trades": [],
        }

    sorted_history = sorted(history_data, key=lambda x: x["date"])
    seen_dates = set()
    for row in sorted_history:
        date.fromisoformat(row["date"])
        nav = float(row["nav"])
        if not math.isfinite(nav) or nav <= 0 or row["date"] in seen_dates:
            raise ValueError("历史净值必须为正有限值，且日期不可重复")
        seen_dates.add(row["date"])

    # 费率配置
    sub_rate  = fee_config.get("subscription_rate", DEFAULT_SUBSCRIPTION_RATE) if fee_config else DEFAULT_SUBSCRIPTION_RATE
    red_tiers = fee_config.get("redemption_tiers", DEFAULT_REDEMPTION_TIERS)   if fee_config else DEFAULT_REDEMPTION_TIERS

    # 基础参数
    initial_capital = float(cfg.get("initial_capital", 50000.0))
    if not math.isfinite(initial_capital) or initial_capital <= 0:
        raise ValueError("初始资金必须为正有限值")
    allow_contributions = bool(cfg.get("allow_additional_capital", False))
    settlement_type = cfg.get("settlement_type", "T+1")

    # 状态变量
    cash = 0.0
    total_invested = initial_capital
    holding_lots = []
    trades = []
    equity_curve = []
    total_sub_fee = 0.0
    total_red_fee = 0.0
    total_buys = 0
    total_sells = 0
    winning_sells = 0
    losing_sells = 0
    last_buy_index  = -999
    last_sell_index = -999
    round_base_cost_nav = sorted_history[0]["nav"]

    def get_current_shares():
        s = sum(lot["shares"] for lot in holding_lots)
        return round(s, 6) if s > 1e-5 else 0.0

    def get_avg_cost():
        tot_s = get_current_shares()
        if tot_s <= 1e-5:
            return 0.0
        return sum(lot["shares"] * lot["cost_nav"] for lot in holding_lots) / tot_s

    # ── 日0：初始建仓 ──
    day0 = sorted_history[0]
    day0_date = day0["date"]
    day0_nav  = float(day0["nav"])

    if is_stock:
        init_shares = int(initial_capital / day0_nav / 100) * 100
        while init_shares > 0:
            gross = round(init_shares * day0_nav, 2)
            if gross + calculate_stock_trade_fee("BUY", gross, fee_config)["total_fee"] <= initial_capital:
                break
            init_shares -= 100
        if init_shares <= 0:
            return {"success": False, "message": "初始资金不足以支付一手股票及费用", "metrics": {}, "equity_curve": [], "trades": []}
        init_gross = round(init_shares * day0_nav, 2)
        fee_info   = calculate_stock_trade_fee("BUY", init_gross, fee_config)
        init_fee   = fee_info["total_fee"]
        init_net   = round(init_gross + init_fee, 2)
        cash = round(initial_capital - init_net, 2)
        total_sub_fee += init_fee
        holding_lots.append({
            "buy_date": day0_date, "confirm_date": day0_date,
            "shares": float(init_shares), "cost_nav": day0_nav, "invested": init_gross
        })
        trade_shares = float(init_shares)
        trade_gross  = init_gross
        trade_net    = init_net
        trade_fee    = init_fee
    else:
        sub_res = calculate_subscription(initial_capital, day0_nav, sub_rate)
        total_sub_fee += sub_res["fee"]
        holding_lots.append({
            "buy_date": day0_date, "confirm_date": day0_date,
            "shares": sub_res["shares"], "cost_nav": day0_nav, "invested": initial_capital
        })
        trade_shares = sub_res["shares"]
        trade_gross  = initial_capital
        trade_net    = sub_res["net_amount"]
        trade_fee    = sub_res["fee"]

    total_buys += 1
    last_buy_index = 0
    trades.append({
        "id": 1, "date": day0_date, "action": "BUY",
        "action_label": "天机时空·初始建仓",
        "nav": day0_nav,
        "open": day0.get("open", day0_nav), "high": day0.get("high", day0_nav),
        "low":  day0.get("low",  day0_nav), "close": day0.get("close", day0_nav),
        "change_pct": day0.get("change_pct", 0.0),
        "gross_amount": trade_gross, "net_amount": trade_net,
        "shares": trade_shares, "fee": trade_fee,
        "cost_nav_before": day0_nav, "cost_nav_after": day0_nav,
        "holding_days": 0,
        "rule_trigger": "天机时空策略初始建仓",
        "cash_balance": round(cash, 2),
        "holding_shares": round(get_current_shares(), 4),
        "market_value": round(get_current_shares() * day0_nav, 2),
        "realized_pnl": 0.0,
        "bazi_signal": None,
        "t1_signal": None,
    })

    benchmark_start_nav = day0_nav

    # ── 主循环 ──
    for idx, day_info in enumerate(sorted_history):
        cur_date_str = day_info["date"]
        cur_nav = float(day_info["nav"])
        day_change = float(day_info.get("change_pct", 0.0))

        try:
            cur_date = date.fromisoformat(cur_date_str)
        except Exception:
            continue

        trade_action = None
        buy_amount = 0.0
        sell_ratio = 0.0
        trade_reason = ""

        # 日0初始建仓已完成，从日1开始演算交易
        if idx > 0:
            signal_day = sorted_history[idx - 1]
            signal_date = date.fromisoformat(signal_day["date"])
            signal_nav = float(signal_day["nav"])
            signal_change = float(signal_day.get("change_pct", 0.0))
            cur_shares = get_current_shares()
            avg_cost   = get_avg_cost()
            cum_profit = (signal_nav - round_base_cost_nav) / round_base_cost_nav * 100.0 if round_base_cost_nav > 0 else 0.0

            # ── Layer 1: 月度大势 ──
            monthly_regime = compute_monthly_regime(signal_date.year, signal_date.month, settings, cfg, as_of=signal_date)

            # ── Layer 2: 流日评分 ──
            today_bazi = compute_daily_bazi_score(signal_date, settings, cfg)

            # ── Layer 3: T+1 前瞻 (严格匹配历史真实下一交易日) ──
            has_position = cur_shares > 1e-5
            t1_signal = compute_t1_lookahead_signal(
                today=signal_date,
                today_score_data=today_bazi,
                today_change_pct=signal_change,
                cur_profit_pct=cum_profit,
                has_position=has_position,
                settings=settings,
                cfg=cfg,
                next_trading_day=cur_date,
            )

            # ── Layer 4: 最终决策 ──
            trade_action, buy_amount, sell_ratio, trade_reason = resolve_tianjit_action(
                today=signal_date,
                today_bazi=today_bazi,
                t1_signal=t1_signal,
                monthly_regime=monthly_regime,
                day_change_pct=signal_change,
                cur_shares=cur_shares,
                cur_nav=signal_nav,
                avg_cost=avg_cost,
                last_buy_index=last_buy_index,
                last_sell_index=last_sell_index,
                cur_day_index=idx,
                cfg=cfg,
                round_base_cost_nav=round_base_cost_nav,
            )

            trade_reason = f"信号日 {signal_date.isoformat()}；下一行情日执行。{trade_reason}"
            if trade_action == "BUY" and not allow_contributions:
                buy_amount = min(buy_amount, max(0.0, cash))
                if buy_amount <= 0:
                    trade_action = None

            bazi_signal_snapshot = {
                "ganzhi": today_bazi["ganzhi"],
                "score": today_bazi["score"],
                "signal_level": today_bazi["signal_level"],
                "rating": today_bazi["rating"],
                "tag": today_bazi["tag"],
                "ten_god": today_bazi["ten_god"],
                "shenshas": today_bazi["shensha_names"],
                "monthly_regime": monthly_regime["regime"],
            }
            t1_snapshot = {
                "scenario": t1_signal.get("scenario"),
                "tomorrow_ganzhi": t1_signal.get("tomorrow_ganzhi", ""),
                "tomorrow_score": t1_signal.get("tomorrow_score", 0),
                "tomorrow_signal_level": t1_signal.get("tomorrow_signal_level", ""),
                "next_trading_date": t1_signal.get("next_trading_date", ""),
                "next_trading_label": t1_signal.get("next_trading_label", ""),
                "next_trading_weekday": t1_signal.get("next_trading_weekday", ""),
                "is_weekend_skipped": t1_signal.get("is_weekend_skipped", False),
                "days_ahead": t1_signal.get("days_ahead", 1),
                "action_modifier": t1_signal.get("action_modifier"),
                "reason": t1_signal.get("reason", ""),
            }

            # ── 执行买入 ──
            if trade_action == "BUY" and buy_amount > 0:
                old_s = get_current_shares()

                if is_stock:
                    shares_to_buy = int(buy_amount / cur_nav / 100) * 100
                    while shares_to_buy > 0:
                        gross = round(shares_to_buy * cur_nav, 2)
                        if gross + calculate_stock_trade_fee("BUY", gross, fee_config)["total_fee"] <= buy_amount:
                            break
                        shares_to_buy -= 100
                    if shares_to_buy < 100:
                        shares_to_buy = 0
                    if shares_to_buy > 0:
                        trade_gross = round(shares_to_buy * cur_nav, 2)
                        fee_info    = calculate_stock_trade_fee("BUY", trade_gross, fee_config)
                        trade_fee   = fee_info["total_fee"]
                        trade_net   = round(trade_gross + trade_fee, 2)
                        actual_shares = float(shares_to_buy)
                        total_sub_fee += trade_fee

                        if cash >= trade_net:
                            cash -= trade_net
                        else:
                            total_invested += (trade_net - cash)
                            cash = 0.0

                        holding_lots.append({
                            "buy_date": cur_date_str, "confirm_date": cur_date_str,
                            "shares": actual_shares, "cost_nav": cur_nav, "invested": trade_gross
                        })

                        total_buys += 1
                        last_buy_index = idx

                        old_cost = round_base_cost_nav
                        new_total_shares = get_current_shares()
                        if old_s <= 1e-5:
                            round_base_cost_nav = cur_nav
                        elif new_total_shares > 1e-5:
                            round_base_cost_nav = (old_s * round_base_cost_nav + actual_shares * cur_nav) / new_total_shares

                        trades.append({
                            "id": len(trades) + 1, "date": cur_date_str, "action": "BUY",
                            "action_label": _buy_action_label(today_bazi["signal_level"], t1_signal),
                            "nav": cur_nav,
                            "open": day_info.get("open", cur_nav), "high": day_info.get("high", cur_nav),
                            "low":  day_info.get("low",  cur_nav), "close": day_info.get("close", cur_nav),
                            "change_pct": day_change,
                            "gross_amount": trade_gross, "net_amount": trade_net,
                            "shares": actual_shares, "fee": trade_fee,
                            "cost_nav_before": round(old_cost, 4),
                            "cost_nav_after":  round(round_base_cost_nav, 4),
                            "holding_days": 0,
                            "rule_trigger": trade_reason,
                            "cash_balance": round(cash, 2),
                            "holding_shares": round(get_current_shares(), 4),
                            "market_value": round(get_current_shares() * cur_nav, 2),
                            "realized_pnl": 0.0,
                            "bazi_signal": bazi_signal_snapshot,
                            "t1_signal": t1_snapshot,
                        })
                else:
                    sub_res = calculate_subscription(buy_amount, cur_nav, sub_rate)
                    total_sub_fee += sub_res["fee"]
                    trade_gross  = buy_amount
                    trade_net    = sub_res["net_amount"]
                    trade_fee    = sub_res["fee"]
                    actual_shares = sub_res["shares"]

                    if cash >= buy_amount:
                        cash -= buy_amount
                    else:
                        total_invested += (buy_amount - cash)
                        cash = 0.0

                    holding_lots.append({
                        "buy_date": cur_date_str, "confirm_date": cur_date_str,
                        "shares": actual_shares, "cost_nav": cur_nav, "invested": buy_amount
                    })

                    total_buys += 1
                    last_buy_index = idx

                    old_cost = round_base_cost_nav
                    new_total_shares = get_current_shares()
                    if old_s <= 1e-5:
                        round_base_cost_nav = cur_nav
                    elif new_total_shares > 1e-5:
                        round_base_cost_nav = (old_s * round_base_cost_nav + actual_shares * cur_nav) / new_total_shares

                    trades.append({
                        "id": len(trades) + 1, "date": cur_date_str, "action": "BUY",
                        "action_label": _buy_action_label(today_bazi["signal_level"], t1_signal),
                        "nav": cur_nav,
                        "open": day_info.get("open", cur_nav), "high": day_info.get("high", cur_nav),
                        "low":  day_info.get("low",  cur_nav), "close": day_info.get("close", cur_nav),
                        "change_pct": day_change,
                        "gross_amount": trade_gross, "net_amount": trade_net,
                        "shares": actual_shares, "fee": trade_fee,
                        "cost_nav_before": round(old_cost, 4),
                        "cost_nav_after":  round(round_base_cost_nav, 4),
                        "holding_days": 0,
                        "rule_trigger": trade_reason,
                        "cash_balance": round(cash, 2),
                        "holding_shares": round(get_current_shares(), 4),
                        "market_value": round(get_current_shares() * cur_nav, 2),
                        "realized_pnl": 0.0,
                        "bazi_signal": bazi_signal_snapshot,
                        "t1_signal": t1_snapshot,
                    })

            # ── 执行卖出 ──
            elif (trade_action == "SELL" and sell_ratio > 0 and cur_shares > 1e-5
                  and (not is_stock or sell_ratio >= 0.9999 or int(cur_shares * sell_ratio / 100) > 0)):
                target_sell = cur_shares * sell_ratio if sell_ratio < 0.9999 else cur_shares
                if is_stock and sell_ratio < 0.9999:
                    target_sell = int(target_sell / 100) * 100

                sold_shares = 0.0
                sell_gross  = 0.0
                sell_fee    = 0.0
                cost_of_sold = 0.0
                avg_hold_days = 0.0
                sold_lots_cnt = 0
                new_lots = []

                for lot in holding_lots:
                    if sold_shares >= target_sell - 1e-5:
                        new_lots.append(lot)
                        continue
                    needed = target_sell - sold_shares
                    lot_s  = lot["shares"]
                    h_days = calculate_holding_days(lot["buy_date"], cur_date_str)

                    if lot_s <= needed + 1e-5:
                        portion = lot_s
                    else:
                        portion = needed
                        remainder = lot_s - needed
                        new_lots.append({**lot, "shares": remainder})

                    lot_gross = portion * cur_nav
                    if is_stock:
                        lot_fee = 0.0  # Stock commission applies once per order, not per FIFO lot.
                    else:
                        rate = get_redemption_fee_rate(h_days, red_tiers)
                        lot_fee = lot_gross * rate
                    sell_gross   += lot_gross
                    sell_fee     += lot_fee
                    cost_of_sold += portion * lot["cost_nav"]
                    avg_hold_days += h_days
                    sold_shares  += portion
                    sold_lots_cnt += 1

                holding_lots = new_lots
                if is_stock and sold_shares > 0:
                    sell_fee = calculate_stock_trade_fee("SELL", sell_gross, fee_config)["total_fee"]
                total_red_fee += sell_fee
                sell_net = sell_gross - sell_fee
                cash += sell_net

                realized_pnl = sell_gross - cost_of_sold - sell_fee
                if realized_pnl >= 0:
                    winning_sells += 1
                else:
                    losing_sells += 1
                total_sells += 1
                last_sell_index = idx

                # 止盈或前瞻减仓后，重置本轮成本基准以防止在相同浮盈区间无休止连续每天卖出
                old_base_cost = round_base_cost_nav
                should_reset_profit = bool(cfg.get("reset_profit_on_sell", cfg.get("global_profit_reset", cfg.get("cumulative_reset_on_sell", True))))
                if should_reset_profit and ("止盈" in trade_reason or "减仓" in trade_reason or "卖出" in trade_reason):
                    round_base_cost_nav = cur_nav
                    trade_reason += f" | 🎯 利润基准重置为现价 ¥{cur_nav:.4f}"
                elif get_current_shares() <= 1e-5:
                    round_base_cost_nav = 0.0

                avg_hd = round(avg_hold_days / sold_lots_cnt, 1) if sold_lots_cnt > 0 else 0

                trades.append({
                    "id": len(trades) + 1, "date": cur_date_str, "action": "SELL",
                    "action_label": _sell_action_label(t1_signal, sell_ratio),
                    "nav": cur_nav,
                    "open": day_info.get("open", cur_nav), "high": day_info.get("high", cur_nav),
                    "low":  day_info.get("low",  cur_nav), "close": day_info.get("close", cur_nav),
                    "change_pct": day_change,
                    "gross_amount": round(sell_gross, 2), "net_amount": round(sell_net, 2),
                    "shares": round(sold_shares, 4), "fee": round(sell_fee, 4),
                    "fee_breakdown": {},
                    "cost_nav_before": round(old_base_cost, 4),
                    "cost_nav_after":  round(round_base_cost_nav, 4),
                    "holding_days": avg_hd,
                    "rule_trigger": trade_reason,
                    "cash_balance": round(cash, 2),
                    "holding_shares": round(get_current_shares(), 4),
                    "market_value": round(get_current_shares() * cur_nav, 2),
                    "realized_pnl": round(realized_pnl, 2),
                    "bazi_signal": bazi_signal_snapshot,
                    "t1_signal": t1_snapshot,
                })

        # ── 每日结算：记录盘后净值权益曲线（每个交易日严格输出 1 条）──
        rem_shares_today = get_current_shares()
        market_val_today = rem_shares_today * cur_nav
        total_assets_today = cash + market_val_today

        strat_return_pct = (total_assets_today - total_invested) / total_invested * 100.0 if total_invested > 0 else 0.0
        bm_return_pct = (cur_nav - benchmark_start_nav) / benchmark_start_nav * 100.0 if benchmark_start_nav > 0 else 0.0

        equity_curve.append({
            "date": cur_date_str,
            "nav": cur_nav,
            "cash": round(cash, 2),
            "market_value": round(market_val_today, 2),
            "total_assets": round(total_assets_today, 2),
            "total_invested": round(total_invested, 2),
            "strategy_return_pct": round(strat_return_pct, 2),
            "benchmark_return_pct": round(bm_return_pct, 2),
            "holding_shares": round(rem_shares_today, 4),
            "action": trades[-1]["action"] if trades and trades[-1]["date"] == cur_date_str else None,
        })

    # ── 计算标准绩效指标 ──
    # Contributions arrive at execution after the daily price move; exclude them from returns.
    unit_value = equity_curve[0]["total_assets"] / initial_capital
    daily_returns = []
    for i, point in enumerate(equity_curve):
        if i:
            previous = equity_curve[i - 1]
            contribution = point["total_invested"] - previous["total_invested"]
            daily_return = ((point["total_assets"] - contribution) / previous["total_assets"] - 1
                            if previous["total_assets"] > 0 else 0.0)
            daily_returns.append(daily_return)
            unit_value *= 1 + daily_return
        point["unit_value"] = unit_value
        point["strategy_return_pct"] = round((unit_value - 1) * 100, 2)
    final_pt = equity_curve[-1]
    final_total_assets = final_pt["total_assets"]
    final_strategy_return = final_pt["strategy_return_pct"]
    final_benchmark_return = final_pt["benchmark_return_pct"]
    alpha_return = round(final_strategy_return - final_benchmark_return, 2)

    total_days = len(equity_curve)
    cagr = 0.0
    if total_days > 10 and total_invested > 0:
        years = total_days / 244.0
        if years > 0:
            growth = max(0.0001, unit_value)
            cagr = round((math.pow(growth, 1.0 / years) - 1.0) * 100.0, 2)

    max_peak = 1.0
    max_drawdown = 0.0
    for pt in equity_curve:
        val = pt["unit_value"]
        if val > max_peak:
            max_peak = val
        if max_peak > 0:
            dd = (max_peak - val) / max_peak * 100.0
            if dd > max_drawdown:
                max_drawdown = dd
    max_drawdown = round(max_drawdown, 2)

    sharpe_ratio = 0.0
    if len(daily_returns) > 5:
        mean_r = sum(daily_returns) / len(daily_returns)
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in daily_returns) / len(daily_returns))
        rf_daily = 0.02 / 244.0
        if std_r > 1e-6:
            sharpe_ratio = round((mean_r - rf_daily) / std_r * math.sqrt(244), 2)

    win_rate = round((winning_sells / total_sells * 100.0), 1) if total_sells > 0 else 0.0

    metrics = {
        "strategy_return_pct": round(final_strategy_return, 2),
        "benchmark_return_pct": round(final_benchmark_return, 2),
        "excess_return_pct": alpha_return,
        "annualized_return_pct": cagr,
        "max_drawdown_pct": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "initial_capital": round(initial_capital, 2),
        "total_invested":  round(total_invested, 2),
        "final_assets":    round(final_total_assets, 2),
        "final_cash":      round(final_pt["cash"], 2),
        "final_holding_value": round(final_pt["market_value"], 2),
        "final_holding_shares": round(final_pt["holding_shares"], 4),
        "total_trades":    len(trades),
        "buy_trades":      total_buys,
        "sell_trades":     total_sells,
        "winning_sells":   winning_sells,
        "win_rate":        win_rate,
        "total_fees_paid": round(total_sub_fee + total_red_fee, 2),
        "subscription_fees": round(total_sub_fee, 2),
        "redemption_fees": round(total_red_fee, 2),
        "strategy_name":   "天机时空策略",
    }

    display_name = fund_name or fund_code

    return {
        "success": True,
        "asset_type": asset_type,
        "fund_code": fund_code,
        "fund_name": display_name,
        "target_code": fund_code,
        "target_name": display_name,
        "strategy_type": strategy_type,
        "start_date": sorted_history[0]["date"],
        "end_date": sorted_history[-1]["date"],
        "total_days": total_days,
        "metrics": metrics,
        "equity_curve": equity_curve,
        "trades": trades,
        "message": f"天机时空策略回测完成，共 {len(trades)} 笔交易，总收益率 {final_strategy_return:.2f}%",
        "validation": {
            "signal_execution": "previous_observation_to_next_nav",
            "allow_additional_capital": allow_contributions,
            "predictive_edge_verified": False,
            "limitations": ["历法评分不是上涨概率", "未模拟基金确认及赎回到账延迟、股票停牌与涨跌停", "使用追加资金时收益率与买入持有基准不可直接比较"],
        },
    }


def _buy_action_label(signal_level: str, t1_signal: Dict[str, Any]) -> str:
    t1_mod = t1_signal.get("action_modifier") if t1_signal else None
    if t1_mod == "PREVIEW_BUY":
        return "天机·次日预建仓"
    if t1_mod in ("BUY_BOOST", "EXTRA_BOOST"):
        return f"天机·前瞻增强加仓({'大吉' if signal_level=='S' else '吉日'})"
    labels = {"S": "天机·大吉进攻", "A": "天机·吉日逢低", "B": "天机·平日加仓", "C": "天机·凶日抄底"}
    return labels.get(signal_level, "天机·加仓")


def _sell_action_label(t1_signal: Dict[str, Any], sell_ratio: float) -> str:
    t1_mod = t1_signal.get("action_modifier") if t1_signal else None
    if t1_mod == "SELL_EARLY":
        return "天机·前瞻提前减仓"
    if sell_ratio >= 0.9999:
        return "天机·全仓止损清仓"
    return "天机·止盈减仓"
