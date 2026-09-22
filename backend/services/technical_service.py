"""
Technical Analysis Service for Stocks and Funds.
Provides:
1. Technical Indicators: MACD (12, 26, 9), RSI (6, 12, 24), MA (5, 10, 20, 60), Volume metrics (VOL5, VOL10, Volume Ratio), KDJ, BOLL.
2. Divergence Analysis: Algorithmic detection of 顶背离 (Top/Bearish Divergence) and 底背离 (Bottom/Bullish Divergence).
3. Multi-factor comprehensive scoring & rating (0~100), support & resistance levels.
4. Fund constituent stocks weighted technical calculation (public top 10 holdings penetration).
"""

import asyncio
import logging
import math
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Cache for technical analysis results (10 minutes)
_TECH_CACHE: Dict[str, Dict[str, Any]] = {}
TECH_CACHE_TTL = 600  # 10 minutes


def _safe_float(val, default: float = 0.0) -> float:
    try:
        if val is None or val == "" or val == "-":
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


# ==========================================
# 1. Core Technical Indicator Calculators
# ==========================================

def calculate_ma(closes: List[float], periods: List[int] = [5, 10, 20, 60]) -> Dict[str, List[Optional[float]]]:
    """Calculate Simple Moving Averages for specified periods."""
    result = {}
    for p in periods:
        key = f"MA{p}"
        ma_vals: List[Optional[float]] = []
        for i in range(len(closes)):
            if i + 1 < p:
                ma_vals.append(None)
            else:
                window = closes[i + 1 - p : i + 1]
                ma_vals.append(round(sum(window) / p, 3))
        result[key] = ma_vals
    return result


def calculate_macd(
    closes: List[float], fast_p: int = 12, slow_p: int = 26, signal_p: int = 9
) -> Tuple[List[float], List[float], List[float]]:
    """
    Calculate MACD: DIF, DEA, MACD Bar (2 * (DIF - DEA)).
    Standard EMA smoothing formula: EMA = alpha * P + (1 - alpha) * Prev_EMA, alpha = 2 / (N + 1).
    """
    n = len(closes)
    if n == 0:
        return [], [], []

    alpha_fast = 2.0 / (fast_p + 1)
    alpha_slow = 2.0 / (slow_p + 1)
    alpha_sig = 2.0 / (signal_p + 1)

    ema_fast = [closes[0]]
    ema_slow = [closes[0]]

    for i in range(1, n):
        ema_fast.append(alpha_fast * closes[i] + (1 - alpha_fast) * ema_fast[-1])
        ema_slow.append(alpha_slow * closes[i] + (1 - alpha_slow) * ema_slow[-1])

    dif = [round(fast - slow, 4) for fast, slow in zip(ema_fast, ema_slow)]

    dea = [dif[0]]
    for i in range(1, n):
        dea.append(round(alpha_sig * dif[i] + (1 - alpha_sig) * dea[-1], 4))

    macd_bar = [round(2.0 * (d - a), 4) for d, a in zip(dif, dea)]
    return dif, dea, macd_bar


def calculate_rsi(closes: List[float], periods: List[int] = [6, 12, 24]) -> Dict[str, List[Optional[float]]]:
    """
    Calculate Wilder / Cutlers smoothed Relative Strength Index (RSI).
    """
    n = len(closes)
    result = {}

    for p in periods:
        key = f"RSI{p}"
        rsi_vals: List[Optional[float]] = [None] * min(p, n)
        if n <= p:
            result[key] = rsi_vals
            continue

        gains: List[float] = []
        losses: List[float] = []
        for i in range(1, n):
            change = closes[i] - closes[i - 1]
            gains.append(max(change, 0.0))
            losses.append(max(-change, 0.0))

        # Initial average
        avg_gain = sum(gains[:p]) / p
        avg_loss = sum(losses[:p]) / p

        if avg_loss == 0:
            rsi_vals.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_vals.append(round(100.0 - (100.0 / (1.0 + rs)), 2))

        # Smoothed
        for i in range(p, len(gains)):
            avg_gain = (avg_gain * (p - 1) + gains[i]) / p
            avg_loss = (avg_loss * (p - 1) + losses[i]) / p
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = round(100.0 - (100.0 / (1.0 + rs)), 2)
            rsi_vals.append(rsi)

        result[key] = rsi_vals

    return result


def calculate_kdj(
    highs: List[float], lows: List[float], closes: List[float], n: int = 9, m1: int = 3, m2: int = 3
) -> Tuple[List[float], List[float], List[float]]:
    """Calculate KDJ (9, 3, 3) stochastic indicators."""
    length = len(closes)
    k_vals = []
    d_vals = []
    j_vals = []

    last_k = 50.0
    last_d = 50.0

    for i in range(length):
        start_idx = max(0, i - n + 1)
        period_low = min(lows[start_idx : i + 1])
        period_high = max(highs[start_idx : i + 1])

        if period_high == period_low:
            rsv = 50.0
        else:
            rsv = ((closes[i] - period_low) / (period_high - period_low)) * 100.0

        cur_k = (1.0 / m1) * rsv + ((m1 - 1.0) / m1) * last_k
        cur_d = (1.0 / m2) * cur_k + ((m2 - 1.0) / m2) * last_d
        cur_j = 3.0 * cur_k - 2.0 * cur_d

        k_vals.append(round(cur_k, 2))
        d_vals.append(round(cur_d, 2))
        j_vals.append(round(cur_j, 2))

        last_k = cur_k
        last_d = cur_d

    return k_vals, d_vals, j_vals


def calculate_boll(
    closes: List[float], period: int = 20, num_std: float = 2.0
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """Calculate Bollinger Bands (Mid, Upper, Lower)."""
    mid_vals: List[Optional[float]] = []
    upper_vals: List[Optional[float]] = []
    lower_vals: List[Optional[float]] = []

    for i in range(len(closes)):
        if i + 1 < period:
            mid_vals.append(None)
            upper_vals.append(None)
            lower_vals.append(None)
        else:
            window = closes[i + 1 - period : i + 1]
            ma = sum(window) / period
            variance = sum((x - ma) ** 2 for x in window) / period
            std = math.sqrt(variance)
            mid_vals.append(round(ma, 3))
            upper_vals.append(round(ma + num_std * std, 3))
            lower_vals.append(round(ma - num_std * std, 3))

    return mid_vals, upper_vals, lower_vals


def calculate_volume_metrics(volumes: List[float], closes: List[float]) -> Dict[str, Any]:
    """Calculate Volume Moving Averages, Volume Ratio, and Volume-Price Patterns."""
    n = len(volumes)
    vol_ma5 = []
    vol_ma10 = []

    for i in range(n):
        if i >= 4:
            vol_ma5.append(round(sum(volumes[i - 4 : i + 1]) / 5.0, 1))
        else:
            vol_ma5.append(None)

        if i >= 9:
            vol_ma10.append(round(sum(volumes[i - 9 : i + 1]) / 10.0, 1))
        else:
            vol_ma10.append(None)

    # Latest volume ratio
    cur_vol = volumes[-1] if n > 0 else 0.0
    latest_ma5 = vol_ma5[-1] or cur_vol or 1.0
    vol_ratio = round(cur_vol / latest_ma5, 2) if latest_ma5 > 0 else 1.0

    # Pattern recognition
    cur_chg = 0.0
    if n >= 2 and closes[-2] > 0:
        cur_chg = (closes[-1] - closes[-2]) / closes[-2] * 100.0

    if vol_ratio >= 1.8 and cur_chg >= 1.5:
        pattern = "放量突破"
        pattern_desc = "成交量放大超 1.8 倍并伴随价格上涨，主力资金抢筹突破"
        signal_bias = "bullish"
    elif vol_ratio >= 1.8 and cur_chg <= -1.5:
        pattern = "放量杀跌"
        pattern_desc = "成交量异常放大但价格重挫，抛压沉重或恐慌盘出逃"
        signal_bias = "bearish"
    elif vol_ratio <= 0.75 and -1.8 <= cur_chg <= 0.0:
        pattern = "缩量回踩"
        pattern_desc = "价格小幅整理但成交量明显萎缩，属于良性洗盘回调"
        signal_bias = "bullish"
    elif vol_ratio <= 0.75 and cur_chg >= 1.0:
        pattern = "缩量空涨"
        pattern_desc = "价格上涨但量能匮乏未见增量资金，警惕诱多乏力回落"
        signal_bias = "neutral"
    elif vol_ratio <= 0.75 and cur_chg <= -1.5:
        pattern = "缩量阴跌"
        pattern_desc = "阴跌无抵抗，买盘匮乏，仍需等待放量筑底"
        signal_bias = "bearish"
    else:
        pattern = "温和换手"
        pattern_desc = "量价运行在常规波动区间内"
        signal_bias = "neutral"

    return {
        "vol_ma5": vol_ma5,
        "vol_ma10": vol_ma10,
        "current_volume": cur_vol,
        "volume_ratio": vol_ratio,
        "pattern": pattern,
        "pattern_desc": pattern_desc,
        "signal_bias": signal_bias,
    }


# ==========================================
# 2. Algorithmic Divergence Detection (顶背离与底背离)
# ==========================================

def _find_extrema(series: List[float], window: int = 3) -> Tuple[List[int], List[int]]:
    """
    Find indices of local peaks (swing highs) and local troughs (swing lows).
    A peak at i satisfies series[i] > series[i-k] for k in 1..window.
    """
    peaks = []
    troughs = []
    n = len(series)
    for i in range(window, n - window):
        is_peak = True
        is_trough = True
        for k in range(1, window + 1):
            if series[i] <= series[i - k] or series[i] < series[i + k]:
                is_peak = False
            if series[i] >= series[i - k] or series[i] > series[i + k]:
                is_trough = False
        if is_peak:
            peaks.append(i)
        if is_trough:
            troughs.append(i)
    return peaks, troughs


def detect_divergence(
    dates: List[str],
    closes: List[float],
    highs: List[float],
    lows: List[float],
    difs: List[float],
    macd_bars: List[float],
    rsis: List[float],
    lookback: int = 80,
) -> Dict[str, Any]:
    """
    Detects MACD & RSI Top Divergence (顶背离) and Bottom Divergence (底背离).
    1. 顶背离 (Top Divergence): Price makes higher high (P2 > P1), but indicator makes lower high (I2 < I1).
    2. 底背离 (Bottom Divergence): Price makes lower low (P2 < P1), but indicator makes higher low (I2 > I1).
    """
    n = len(closes)
    if n < 30:
        return {
            "has_divergence": False,
            "top_divergence": None,
            "bottom_divergence": None,
            "recent_signals": [],
        }

    start_idx = max(0, n - lookback)
    sub_closes = closes[start_idx:]
    sub_highs = highs[start_idx:]
    sub_lows = lows[start_idx:]
    sub_difs = difs[start_idx:]
    sub_rsis = rsis[start_idx:]
    sub_dates = dates[start_idx:]

    peaks, troughs = _find_extrema(sub_closes, window=3)

    top_div = None
    bottom_div = None
    signals = []

    # 1. Detect 顶背离 (Bearish / Top Divergence)
    # Compare the most recent two major peaks
    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        # Only valid if p2 is recent (e.g. within last 20 bars)
        if (len(sub_closes) - 1 - p2) <= 20 and (p2 - p1) >= 5:
            price_p1 = sub_highs[p1]
            price_p2 = sub_highs[p2]
            dif_p1 = sub_difs[p1]
            dif_p2 = sub_difs[p2]
            rsi_p1 = sub_rsis[p1]
            rsi_p2 = sub_rsis[p2]

            # Price higher high, but DIF lower high or RSI lower high
            is_macd_top = price_p2 > price_p1 * 1.005 and dif_p2 < dif_p1 * 0.95
            is_rsi_top = price_p2 > price_p1 * 1.005 and rsi_p2 < rsi_p1 - 2.0

            if is_macd_top or is_rsi_top:
                bars_ago = len(sub_closes) - 1 - p2
                top_div = {
                    "type": "top_divergence",
                    "label": "日线顶背离",
                    "severity": "high" if (is_macd_top and is_rsi_top) else "medium",
                    "date1": sub_dates[p1],
                    "price1": round(price_p1, 2),
                    "date2": sub_dates[p2],
                    "price2": round(price_p2, 2),
                    "indicator_type": "MACD + RSI 双重顶背离" if (is_macd_top and is_rsi_top) else ("MACD 顶背离" if is_macd_top else "RSI 顶背离"),
                    "bars_ago": bars_ago,
                    "desc": f"在 {sub_dates[p2]} 价格突破至 {price_p2:.2f} 创新高，但技术指标动能未同步放量（高点较 {sub_dates[p1]} 明显衰减），提示顶部动能衰竭，严防回落回调风险！",
                    "action_advice": "建议分批逢高减仓或收紧移动止盈线，切忌盲目追高"
                }
                signals.append(top_div)

    # 2. Detect 底背离 (Bullish / Bottom Divergence)
    # Compare the most recent two major troughs
    if len(troughs) >= 2:
        t1, t2 = troughs[-2], troughs[-1]
        if (len(sub_closes) - 1 - t2) <= 20 and (t2 - t1) >= 5:
            price_t1 = sub_lows[t1]
            price_t2 = sub_lows[t2]
            dif_t1 = sub_difs[t1]
            dif_t2 = sub_difs[t2]
            rsi_t1 = sub_rsis[t1]
            rsi_t2 = sub_rsis[t2]

            # Price lower low, but DIF higher low or RSI higher low
            is_macd_bottom = price_t2 < price_t1 * 0.995 and dif_t2 > dif_t1 + 0.02
            is_rsi_bottom = price_t2 < price_t1 * 0.995 and rsi_t2 > rsi_t1 + 2.0

            if is_macd_bottom or is_rsi_bottom:
                bars_ago = len(sub_closes) - 1 - t2
                bottom_div = {
                    "type": "bottom_divergence",
                    "label": "日线底背离",
                    "severity": "high" if (is_macd_bottom and is_rsi_bottom) else "medium",
                    "date1": sub_dates[t1],
                    "price1": round(price_t1, 2),
                    "date2": sub_dates[t2],
                    "price2": round(price_t2, 2),
                    "indicator_type": "MACD + RSI 双重底背离" if (is_macd_bottom and is_rsi_bottom) else ("MACD 底背离" if is_macd_bottom else "RSI 底背离"),
                    "bars_ago": bars_ago,
                    "desc": f"在 {sub_dates[t2]} 价格下探至 {price_t2:.2f} 创出新低，但技术指标筑底抬高（高于 {sub_dates[t1]} 对应点位），杀跌动能衰竭，底部反转信号强烈！",
                    "action_advice": "出现明确左侧筑底或右侧反弹契机，可逢低分批建仓试错"
                }
                signals.append(bottom_div)

    return {
        "has_divergence": bool(top_div or bottom_div),
        "top_divergence": top_div,
        "bottom_divergence": bottom_div,
        "recent_signals": signals,
    }


# ==========================================
# 3. Comprehensive Technical Scoring Model
# ==========================================

def evaluate_technical_posture(
    closes: List[float],
    highs: List[float],
    lows: List[float],
    volumes: List[float],
    difs: List[float],
    deas: List[float],
    macd_bars: List[float],
    rsis: Dict[str, List[Optional[float]]],
    mas: Dict[str, List[Optional[float]]],
    vol_metrics: Dict[str, Any],
    divergence: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Multi-factor quantitative scoring (0 to 100).
    Aggregates: MACD, RSI, Volume-Price, Moving Averages, and Divergences.
    Outputs rating, trading suggestion, and critical support & resistance prices.
    """
    score = 50.0
    signals = []
    details = []

    cur_close = closes[-1] if closes else 0.0

    # 1. MACD Factor (+18 ~ -18)
    cur_dif = difs[-1] if difs else 0.0
    cur_dea = deas[-1] if deas else 0.0
    prev_dif = difs[-2] if len(difs) >= 2 else cur_dif
    prev_dea = deas[-2] if len(deas) >= 2 else cur_dea
    cur_bar = macd_bars[-1] if macd_bars else 0.0
    prev_bar = macd_bars[-2] if len(macd_bars) >= 2 else 0.0

    macd_status = "中性震荡"
    if prev_dif <= prev_dea and cur_dif > cur_dea:
        if cur_dif >= 0:
            score += 18
            macd_status = "零上金叉 (强看多)"
            signals.append("MACD 0轴上方黄金交叉")
            details.append("MACD在0轴上方形成金叉，多头主升动能强劲")
        else:
            score += 12
            macd_status = "零下金叉 (反弹)"
            signals.append("MACD 0轴下方反弹金叉")
            details.append("MACD在0轴下方金叉，处于超跌企稳反弹阶段")
    elif prev_dif >= prev_dea and cur_dif < cur_dea:
        if cur_dif >= 0:
            score -= 12
            macd_status = "零上死叉 (多头减弱)"
            signals.append("MACD 0轴上方死叉")
            details.append("MACD高位死叉，短期上升动能衰减，注意回调")
        else:
            score -= 18
            macd_status = "零下死叉 (加速破位)"
            signals.append("MACD 0轴下方加速死叉")
            details.append("MACD在0轴下方形成死叉，空头主导加速探底")
    else:
        if cur_dif > cur_dea:
            if cur_bar > prev_bar:
                score += 8
                macd_status = "多头动能扩张"
                signals.append("MACD红柱连续放大")
            else:
                score += 3
                macd_status = "多头动能衰退"
                signals.append("MACD红柱缩短")
        else:
            if cur_bar < prev_bar:
                score -= 8
                macd_status = "空头动能扩张"
                signals.append("MACD绿柱连续放大")
            else:
                score -= 3
                macd_status = "空头动能收敛"
                signals.append("MACD绿柱缩短")

    # 2. Divergence Factor (+22 / -22)
    top_div = divergence.get("top_divergence")
    bottom_div = divergence.get("bottom_divergence")

    if bottom_div and bottom_div.get("bars_ago", 999) <= 15:
        score += 22
        signals.append("🔥 日线底背离确立")
        details.append(f"检出【{bottom_div.get('indicator_type')}】，杀跌动能枯竭，强烈反弹看多")
    if top_div and top_div.get("bars_ago", 999) <= 15:
        score -= 22
        signals.append("⚠️ 日线顶背离风险")
        details.append(f"检出【{top_div.get('indicator_type')}】，股价创新高指标背离，强烈警惕高位跳水")

    # 3. RSI Factor (+15 ~ -15)
    rsi6_series = rsis.get("RSI6", [])
    rsi12_series = rsis.get("RSI12", [])
    cur_rsi6 = rsi6_series[-1] if rsi6_series and rsi6_series[-1] is not None else 50.0
    cur_rsi12 = rsi12_series[-1] if rsi12_series and rsi12_series[-1] is not None else 50.0

    rsi_status = "常态运行"
    if cur_rsi6 >= 80.0:
        score -= 15
        rsi_status = "严重超买 (>80)"
        signals.append("RSI(6) 严重超买")
        details.append("RSI指标突破80超买极值，短期获利盘随时可能涌出回踩")
    elif cur_rsi6 <= 20.0:
        score += 15
        rsi_status = "严重超卖 (<20)"
        signals.append("RSI(6) 极度超卖")
        details.append("RSI指标下探至20超跌极值，随时具备技术性脉冲反弹动力")
    else:
        if cur_rsi6 > cur_rsi12:
            score += 5
            rsi_status = "多头偏强"
        else:
            score -= 5
            rsi_status = "空头偏弱"

    # 4. Volume & Price Factor (+12 ~ -15)
    vol_bias = vol_metrics.get("signal_bias")
    vol_pattern = vol_metrics.get("pattern")
    vol_ratio = vol_metrics.get("volume_ratio", 1.0)

    if vol_bias == "bullish":
        score += 12
        signals.append(f"{vol_pattern} (量比 {vol_ratio})")
        details.append(f"量价配合良好：{vol_metrics.get('pattern_desc')}")
    elif vol_bias == "bearish":
        score -= 15
        signals.append(f"{vol_pattern} (量比 {vol_ratio})")
        details.append(f"量价形态不佳：{vol_metrics.get('pattern_desc')}")
    else:
        details.append(f"成交量状况：{vol_pattern} (量比 {vol_ratio})")

    # 5. Moving Averages Trend Factor (+15 ~ -15)
    ma5 = mas.get("MA5", [])[-1]
    ma10 = mas.get("MA10", [])[-1]
    ma20 = mas.get("MA20", [])[-1]
    ma60 = mas.get("MA60", [])[-1]

    ma_status = "震荡整理"
    if ma5 and ma10 and ma20 and ma60:
        if cur_close > ma5 > ma10 > ma20 > ma60:
            score += 15
            ma_status = "均线多头排列"
            signals.append("均线多头完美排列")
            details.append("MA5/10/20/60 顺向向上发散，典型主升浪形态")
        elif cur_close < ma5 < ma10 < ma20 < ma60:
            score -= 15
            ma_status = "均线空头排列"
            signals.append("均线空头排列破位")
            details.append("MA5/10/20/60 空头向下发散，下行趋势未见扭转")
        elif cur_close >= ma20:
            score += 6
            ma_status = "站上生命线 MA20"
            signals.append("站稳 20 日均线")
        else:
            score -= 6
            ma_status = "跌破生命线 MA20"
            signals.append("跌破 20 日均线")

    # Bound score between 0 and 100
    final_score = max(5.0, min(95.0, round(score, 1)))

    # Determine Rating & Trader Suggestion
    if final_score >= 80.0:
        grade = "强烈买入"
        grade_color = "#f85149"
        action_advice = "技术形态处于极强共振上攻期，多头排列结合量能放大，建议积极做多、持股待涨，回调逢均线低吸。"
    elif final_score >= 65.0:
        grade = "买入看多"
        grade_color = "#ff7b72"
        action_advice = "技术多头占优，技术指标呈现良性修复与支撑，可保持较高仓位，顺势参与反弹行情。"
    elif final_score >= 45.0:
        grade = "中性观望"
        grade_color = "#e3b341"
        action_advice = "多空力量处于平衡拉锯阶段，未见明确方向性单边突破，建议控制仓位（30%~50%），多看少动。"
    elif final_score >= 30.0:
        grade = "偏空防守"
        grade_color = "#7ee787"
        action_advice = "空头占据上风，均线或量价呈现走弱迹象，建议逢反弹降低仓位防守，规避阴跌损耗。"
    else:
        grade = "强烈卖出"
        grade_color = "#00ff88"
        action_advice = "破位杀跌或顶背离风险严峻，空头动能加速宣泄，建议严格执行止损纪律，轻仓或空仓避险。"

    # Support and Resistance levels based on recent swings and MA
    recent_lows = [l for l in lows[-30:] if l > 0]
    recent_highs = [h for h in highs[-30:] if h > 0]

    support_price = round(min(recent_lows), 2) if recent_lows else round(cur_close * 0.95, 2)
    if ma20 and ma20 < cur_close and ma20 > support_price:
        support_price = round(ma20, 2)

    resistance_price = round(max(recent_highs), 2) if recent_highs else round(cur_close * 1.05, 2)
    if ma60 and ma60 > cur_close and ma60 < resistance_price:
        resistance_price = round(ma60, 2)

    return {
        "score": final_score,
        "grade": grade,
        "grade_color": grade_color,
        "action_advice": action_advice,
        "macd_status": macd_status,
        "rsi_status": rsi_status,
        "ma_status": ma_status,
        "signals": signals[:6],
        "details": details,
        "support_price": support_price,
        "resistance_price": resistance_price,
        "current_price": cur_close,
    }


# ==========================================
# 4. Dispatcher: Full Analysis for Stock / Fund
# ==========================================

async def get_asset_technical_analysis(
    user_id: int, code: str, is_fund: bool = False, force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Main entry point for single stock or fund technical analysis.
    Fetches historical bars, computes all indicators, divergences, scores, and constituent breakdown.
    """
    clean_code = re.sub(r"^[a-zA-Z]+", "", code.strip())
    cache_key = f"{clean_code}_{'fund' if is_fund else 'stock'}"

    # Check in-memory cache
    now = datetime.now()
    if not force_refresh and cache_key in _TECH_CACHE:
        item = _TECH_CACHE[cache_key]
        if (now - item["timestamp"]).total_seconds() < TECH_CACHE_TTL:
            return item["data"]

    # 1. Branch by Fund or Stock
    is_etf = clean_code.startswith(("159", "510", "511", "512", "513", "515", "516", "517", "518", "560", "561", "562", "563", "588", "16"))
    
    if is_fund and not is_etf:
        # OTC Mutual Fund
        result = await _analyze_mutual_fund(clean_code)
    else:
        # Stock or ETF
        result = await _analyze_stock_or_etf(clean_code, is_etf=is_etf)

    result["is_fund"] = is_fund
    result["code"] = clean_code

    # Store in cache
    _TECH_CACHE[cache_key] = {"data": result, "timestamp": now}
    return result


async def _analyze_stock_or_etf(stock_code: str, is_etf: bool = False) -> Dict[str, Any]:
    """Analyze stock or ETF using daily K-lines."""
    from services.strategy.stock_data_provider import fetch_stock_history

    try:
        hist_data = await fetch_stock_history(stock_code)
    except Exception as e:
        logger.warning(f"[TechnicalService] fetch_stock_history error for {stock_code}: {e}")
        raise ValueError(f"无法获取股票/ETF {stock_code} 的真实日线历史数据: {str(e)}")

    history = hist_data.get("history", [])
    stock_name = hist_data.get("name") or stock_code

    if not history:
        raise ValueError(f"标的 {stock_code} 历史行情数据为空")

    # Extract series (up to last 200 bars for speed & precision)
    sample = history[-200:]
    dates = [item["date"] for item in sample]
    closes = [_safe_float(item.get("close") or item.get("nav")) for item in sample]
    highs = [_safe_float(item.get("high"), closes[idx]) for idx, item in enumerate(sample)]
    lows = [_safe_float(item.get("low"), closes[idx]) for idx, item in enumerate(sample)]
    opens = [_safe_float(item.get("open"), closes[idx]) for idx, item in enumerate(sample)]
    volumes = [_safe_float(item.get("volume")) for item in sample]

    # Calculate indicators
    mas = calculate_ma(closes, periods=[5, 10, 20, 60])
    difs, deas, macd_bars = calculate_macd(closes)
    rsis = calculate_rsi(closes, periods=[6, 12, 24])
    k_vals, d_vals, j_vals = calculate_kdj(highs, lows, closes)
    boll_mid, boll_upper, boll_lower = calculate_boll(closes)
    vol_metrics = calculate_volume_metrics(volumes, closes)

    # Detect divergences
    rsi6_clean = [r if r is not None else 50.0 for r in rsis["RSI6"]]
    divergence = detect_divergence(
        dates=dates,
        closes=closes,
        highs=highs,
        lows=lows,
        difs=difs,
        macd_bars=macd_bars,
        rsis=rsi6_clean,
        lookback=80,
    )

    # Quantitative scoring
    eval_result = evaluate_technical_posture(
        closes=closes,
        highs=highs,
        lows=lows,
        volumes=volumes,
        difs=difs,
        deas=deas,
        macd_bars=macd_bars,
        rsis=rsis,
        mas=mas,
        vol_metrics=vol_metrics,
        divergence=divergence,
    )

    # Real-time quote & fund flow
    from services.data_provider import GenericDataProvider
    quote_info = {}
    try:
        provider = GenericDataProvider()
        quote_info = await provider.get_stock_detail(stock_code, name=stock_name, is_fund=is_etf)
    except Exception as qe:
        logger.debug(f"[TechnicalService] quote_info error for {stock_code}: {qe}")

    return {
        "code": stock_code,
        "name": quote_info.get("name") or stock_name,
        "asset_type": "etf" if is_etf else "stock",
        "dates": dates,
        "kline_data": [
            [opens[i], closes[i], lows[i], highs[i], volumes[i]]
            for i in range(len(sample))
        ],
        "indicators": {
            "ma": mas,
            "macd": {"dif": difs, "dea": deas, "bar": macd_bars},
            "rsi": rsis,
            "kdj": {"k": k_vals, "d": d_vals, "j": j_vals},
            "boll": {"mid": boll_mid, "upper": boll_upper, "lower": boll_lower},
            "volume": vol_metrics,
        },
        "divergence": divergence,
        "evaluation": eval_result,
        "quote": quote_info or {
            "current": closes[-1],
            "change_pct": round((closes[-1] - closes[-2]) / closes[-2] * 100.0, 2) if len(closes) >= 2 else 0.0,
            "volume_formatted": vol_metrics.get("current_volume", 0),
        },
    }


async def _analyze_mutual_fund(fund_code: str) -> Dict[str, Any]:
    """
    Analyze mutual fund:
    1. Historical NAV series indicators.
    2. Public top 10 constituent stocks extraction & individual technical scoring.
    3. Weighted aggregate constituent technical health score.
    """
    from services.strategy.fund_data_provider import fetch_fund_history
    from services.data_provider import GenericDataProvider

    try:
        f_hist = await fetch_fund_history(fund_code)
    except Exception as e:
        logger.warning(f"[TechnicalService] fetch_fund_history error for {fund_code}: {e}")
        raise ValueError(f"无法获取基金 {fund_code} 的历史净值数据: {str(e)}")

    history = f_hist.get("history", [])
    fund_name = f_hist.get("name") or fund_code

    if not history:
        raise ValueError(f"基金 {fund_code} 净值历史记录为空")

    sample = history[-200:]
    dates = [item["date"] for item in sample]
    navs = [_safe_float(item.get("nav")) for item in sample]
    highs = navs.copy()
    lows = navs.copy()
    volumes = [0.0] * len(navs)

    # Indicators on NAV
    mas = calculate_ma(navs, periods=[5, 10, 20, 60])
    difs, deas, macd_bars = calculate_macd(navs)
    rsis = calculate_rsi(navs, periods=[6, 12, 24])
    boll_mid, boll_upper, boll_lower = calculate_boll(navs)

    vol_metrics = {
        "vol_ma5": volumes,
        "vol_ma10": volumes,
        "current_volume": 0,
        "volume_ratio": 1.0,
        "pattern": "净值平稳",
        "pattern_desc": "场外基金以每日官方净值结算，无日内成交量",
        "signal_bias": "neutral",
    }

    rsi6_clean = [r if r is not None else 50.0 for r in rsis["RSI6"]]
    divergence = detect_divergence(
        dates=dates,
        closes=navs,
        highs=highs,
        lows=lows,
        difs=difs,
        macd_bars=macd_bars,
        rsis=rsi6_clean,
        lookback=80,
    )

    fund_eval = evaluate_technical_posture(
        closes=navs,
        highs=highs,
        lows=lows,
        volumes=volumes,
        difs=difs,
        deas=deas,
        macd_bars=macd_bars,
        rsis=rsis,
        mas=mas,
        vol_metrics=vol_metrics,
        divergence=divergence,
    )

    # 2. Extract Top 10 Constituent Stocks
    provider = GenericDataProvider()
    comp_res = await provider._calculate_fund_flow_from_components(fund_code)
    raw_components = comp_res.get("components", [])

    components_analysis = []
    tot_weight = 0.0
    weighted_score_sum = 0.0

    # Limit to top 10
    top_candidates = raw_components[:10]

    # Concurrently analyze constituent stocks
    async def _analyze_single_comp(c: dict) -> dict:
        scode = c.get("code")
        sname = c.get("name")
        sweight = _safe_float(c.get("weight"), 10.0)

        c_detail = {
            "code": scode,
            "name": sname,
            "weight": sweight,
            "current": 0.0,
            "change_pct": 0.0,
            "macd_status": "正常",
            "rsi_val": 50.0,
            "score": 55.0,
            "bias": "neutral",
        }

        if not scode:
            return c_detail

        try:
            # Lightweight calculation on constituent stock
            s_res = await _analyze_stock_or_etf(scode)
            s_eval = s_res.get("evaluation", {})
            s_quote = s_res.get("quote", {})
            s_rsi6 = s_res.get("indicators", {}).get("rsi", {}).get("RSI6", [])
            last_rsi = s_rsi6[-1] if s_rsi6 and s_rsi6[-1] is not None else 50.0

            c_detail["current"] = s_quote.get("current") or s_eval.get("current_price", 0.0)
            c_detail["change_pct"] = s_quote.get("change_pct", 0.0)
            c_detail["macd_status"] = s_eval.get("macd_status", "正常")
            c_detail["rsi_val"] = last_rsi
            c_detail["score"] = s_eval.get("score", 50.0)
            c_detail["bias"] = "bullish" if c_detail["score"] >= 65 else ("bearish" if c_detail["score"] <= 44 else "neutral")
        except Exception as se:
            logger.debug(f"[TechnicalService] constituent {scode} analysis error: {se}")

        return c_detail

    if top_candidates:
        tasks = [_analyze_single_comp(c) for c in top_candidates]
        components_analysis = await asyncio.gather(*tasks)

        for ca in components_analysis:
            w = ca["weight"]
            tot_weight += w
            weighted_score_sum += ca["score"] * w

    # Calculate weighted penetration score
    weighted_penetration_score = (
        round(weighted_score_sum / tot_weight, 1) if tot_weight > 0 else fund_eval["score"]
    )

    # Penetration summary
    bull_count = sum(1 for c in components_analysis if c.get("bias") == "bullish")
    bear_count = sum(1 for c in components_analysis if c.get("bias") == "bearish")
    penetration_desc = (
        f"前十大重仓股合计权重 {tot_weight:.1f}%，其中 {bull_count} 只处于多头增强态势，{bear_count} 只偏弱防御。"
        f"重仓股加权穿透技术分为 {weighted_penetration_score} 分。"
    )

    # Combine fund NAV score and constituent penetration score (40% NAV + 60% Penetration)
    final_blended_score = round(fund_eval["score"] * 0.35 + weighted_penetration_score * 0.65, 1)
    fund_eval["score"] = final_blended_score
    if final_blended_score >= 75.0:
        fund_eval["grade"] = "强烈看多 (穿透增强)"
        fund_eval["grade_color"] = "#f85149"
    elif final_blended_score >= 60.0:
        fund_eval["grade"] = "稳健看多"
        fund_eval["grade_color"] = "#ff7b72"
    elif final_blended_score <= 40.0:
        fund_eval["grade"] = "偏空规避"
        fund_eval["grade_color"] = "#00ff88"

    # Real-time quote info for fund
    fund_quote = {}
    try:
        fund_quote = await provider.get_stock_detail(fund_code, name=fund_name, is_fund=True)
    except Exception:
        pass

    return {
        "code": fund_code,
        "name": fund_quote.get("name") or fund_name,
        "asset_type": "fund",
        "dates": dates,
        "kline_data": [
            [navs[i], navs[i], navs[i], navs[i], volumes[i]]
            for i in range(len(sample))
        ],
        "indicators": {
            "ma": mas,
            "macd": {"dif": difs, "dea": deas, "bar": macd_bars},
            "rsi": rsis,
            "boll": {"mid": boll_mid, "upper": boll_upper, "lower": boll_lower},
            "volume": vol_metrics,
        },
        "divergence": divergence,
        "evaluation": fund_eval,
        "quote": fund_quote or {
            "current": navs[-1],
            "change_pct": round((navs[-1] - navs[-2]) / navs[-2] * 100.0, 2) if len(navs) >= 2 else 0.0,
            "volume_formatted": "场外申赎",
            "amount_formatted": "净值结算",
        },
        "components_count": len(components_analysis),
        "components_weight_total": round(tot_weight, 1),
        "weighted_penetration_score": weighted_penetration_score,
        "penetration_desc": penetration_desc,
        "components": components_analysis,
    }
