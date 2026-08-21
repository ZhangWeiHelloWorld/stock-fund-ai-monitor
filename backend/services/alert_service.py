import sqlite3
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import asyncio

from database import DB_PATH, get_settings_dict
from services.market_service import fetch_stock_data, fetch_fund_data, format_stock_code
from services.wxwork_service import send_wxwork_message
from services.trading_calendar import is_trading_time, is_trading_day

# In-memory sliding price/nav history:
# { "sh600519": deque([...]), "fund_161725": deque([...]) }
_price_history: Dict[str, deque] = {}

# Alert cooldown tracking: { (user_id, target_code, alert_type): last_alert_datetime }
_alert_cooldowns: Dict[Tuple[int, str, str], datetime] = {}

# Last recorded day for resetting daily states
_last_reset_day: Optional[str] = None

# Track highest and lowest alerted values for each stock on current day to avoid duplicate low/high pings
_daily_high_alerted: Dict[Tuple[int, str], float] = {}
_daily_low_alerted: Dict[Tuple[int, str], float] = {}


def _clean_old_history(key: str, now: datetime, max_minutes: int = 120):
    """Purge history older than max_minutes."""
    if key in _price_history:
        cutoff = now - timedelta(minutes=max_minutes)
        dq = _price_history[key]
        while dq and dq[0]['time'] < cutoff:
            dq.popleft()


def record_stock_price(
    code: str,
    price: float,
    change_pct: float,
    high: float,
    low: float,
    prev_close: float,
    now: datetime = None
):
    """Record current stock tick data into sliding window."""
    if now is None:
        now = datetime.now()

    if code not in _price_history:
        _price_history[code] = deque(maxlen=600)

    _price_history[code].append({
        'time': now,
        'price': price,
        'change_pct': change_pct,
        'high': high,
        'low': low,
        'prev_close': prev_close
    })

    _clean_old_history(code, now)


def record_fund_nav(
    code: str,
    nav: float,
    change_pct: float,
    prev_nav: float,
    now: datetime = None
):
    """Record current fund estimated NAV into sliding window."""
    if now is None:
        now = datetime.now()

    key = f"fund_{code}"
    if key not in _price_history:
        _price_history[key] = deque(maxlen=600)

    _price_history[key].append({
        'time': now,
        'price': nav,
        'change_pct': change_pct,
        'high': nav,
        'low': nav,
        'prev_close': prev_nav
    })

    _clean_old_history(key, now)


def reset_daily_state_if_needed(now: datetime = None):
    """Reset daily state when entering a new calendar day."""
    global _last_reset_day, _daily_high_alerted, _daily_low_alerted
    if now is None:
        now = datetime.now()

    today_str = now.strftime("%Y-%m-%d")
    if _last_reset_day != today_str:
        _last_reset_day = today_str
        _daily_high_alerted.clear()
        _daily_low_alerted.clear()
        _alert_cooldowns.clear()
        print(f"[AlertService] New day {today_str}: Cleared daily alert state and cooldowns.")


def evaluate_stock_alerts(
    stock_info: dict,
    settings: dict,
    user_id: int,
    now: datetime = None
) -> List[dict]:
    """
    Evaluate all alert conditions for a stock against user settings.
    Returns a list of triggered alert dictionaries.
    """
    if now is None:
        now = datetime.now()

    code = stock_info.get('code', '')
    formatted_code = format_stock_code(code)
    name = stock_info.get('name') or code
    current_price = stock_info.get('current', 0.0) or stock_info.get('current_price', 0.0)
    prev_close = stock_info.get('prev_close', 0.0)
    change_pct = stock_info.get('change_pct', 0.0)
    high = stock_info.get('high', 0.0)
    low = stock_info.get('low', 0.0)
    open_price = stock_info.get('open', 0.0)

    if current_price <= 0 or prev_close <= 0:
        return []

    # Record current price into memory history
    record_stock_price(formatted_code, current_price, change_pct, high, low, prev_close, now)

    triggered_alerts = []
    cooldown_mins = int(settings.get('alert_cooldown_minutes', 15) or 15)

    def is_cooling_down(alert_type: str) -> bool:
        key = (user_id, formatted_code, alert_type)
        last_time = _alert_cooldowns.get(key)
        if last_time and (now - last_time).total_seconds() < cooldown_mins * 60:
            return True
        return False

    def mark_triggered(alert_type: str):
        key = (user_id, formatted_code, alert_type)
        _alert_cooldowns[key] = now

    # 1. 短时间剧烈波动 / 振幅预警 (Rapid Swing Alert)
    if settings.get('alert_swing_enabled', True):
        try:
            swing_mins = int(settings.get('alert_swing_minutes', 5) or 5)
            swing_threshold = float(settings.get('alert_swing_pct', 3.0) or 3.0)
        except (ValueError, TypeError):
            swing_mins = 5
            swing_threshold = 3.0

        if not is_cooling_down('swing') and formatted_code in _price_history:
            cutoff = now - timedelta(minutes=swing_mins)
            recent_points = [p for p in _price_history[formatted_code] if p['time'] >= cutoff]
            if len(recent_points) >= 2:
                prices = [p['price'] for p in recent_points]
                min_p = min(prices)
                max_p = max(prices)
                first_p = recent_points[0]['price']
                last_p = recent_points[-1]['price']

                amplitude_pct = (max_p - min_p) / prev_close * 100
                direct_change_pct = (last_p - first_p) / prev_close * 100

                if amplitude_pct >= swing_threshold:
                    if direct_change_pct >= swing_threshold:
                        action_desc = f"⚡ {swing_mins}分钟内急速拉升 +{direct_change_pct:.2f}% (振幅 {amplitude_pct:.2f}%)"
                    elif direct_change_pct <= -swing_threshold:
                        action_desc = f"⚡ {swing_mins}分钟内急速跳水 {direct_change_pct:.2f}% (振幅 {amplitude_pct:.2f}%)"
                    else:
                        action_desc = f"⚡ {swing_mins}分钟内剧烈震荡 振幅达 {amplitude_pct:.2f}% (最低 {min_p:.2f} / 最高 {max_p:.2f})"

                    mark_triggered('swing')
                    triggered_alerts.append({
                        'type': 'swing',
                        'title': '⚡ 短时间剧烈波动预警',
                        'reason': action_desc,
                        'details': f"统计窗口: {swing_mins}分钟 | 阈值: {swing_threshold:.1f}% | 现价: {current_price:.2f}"
                    })

    # 2. 涨幅达到预警阈值 (Rise Alert)
    if settings.get('alert_rise_enabled', True):
        try:
            rise_threshold = float(settings.get('alert_rise_pct', 5.0) or 5.0)
        except (ValueError, TypeError):
            rise_threshold = 5.0

        if change_pct >= rise_threshold and not is_cooling_down('rise'):
            mark_triggered('rise')
            triggered_alerts.append({
                'type': 'rise',
                'title': '📈 股价大幅上涨预警',
                'reason': f"当日涨幅已达 {change_pct:+.2f}% (触发阈值: +{rise_threshold:.2f}%)",
                'details': f"现价: {current_price:.2f} | 较昨收上涨: {(current_price - prev_close):+.2f}元"
            })

    # 3. 跌幅达到预警阈值 (Fall Alert)
    if settings.get('alert_fall_enabled', True):
        try:
            fall_threshold = float(settings.get('alert_fall_pct', -5.0) or -5.0)
            if fall_threshold > 0:
                fall_threshold = -fall_threshold
        except (ValueError, TypeError):
            fall_threshold = -5.0

        if change_pct <= fall_threshold and not is_cooling_down('fall'):
            mark_triggered('fall')
            triggered_alerts.append({
                'type': 'fall',
                'title': '📉 股价大幅下跌预警',
                'reason': f"当日跌幅已达 {change_pct:+.2f}% (触发阈值: {fall_threshold:.2f}%)",
                'details': f"现价: {current_price:.2f} | 较昨收下跌: {(current_price - prev_close):+.2f}元"
            })

    # 4. 触及 / 刷新日内最高值 (Intraday High Alert)
    if settings.get('alert_reach_high_enabled', True):
        if high > 0 and current_price >= high and current_price > prev_close:
            last_high = _daily_high_alerted.get((user_id, formatted_code), 0.0)
            if not is_cooling_down('reach_high') and (last_high == 0.0 or current_price > last_high * 1.003):
                _daily_high_alerted[(user_id, formatted_code)] = current_price
                mark_triggered('reach_high')
                triggered_alerts.append({
                    'type': 'reach_high',
                    'title': '🚀 触及/突破日内最高价',
                    'reason': f"现价 {current_price:.2f} 触及/创出日内新高 (今日最高: {high:.2f}, 涨幅 {change_pct:+.2f}%)",
                    'details': f"今开: {open_price:.2f} | 昨收: {prev_close:.2f}"
                })

    # 5. 触及 / 跌破日内最低值 (Intraday Low Alert)
    if settings.get('alert_reach_low_enabled', True):
        if low > 0 and current_price <= low and current_price < prev_close:
            last_low = _daily_low_alerted.get((user_id, formatted_code), 0.0)
            if not is_cooling_down('reach_low') and (last_low == 0.0 or current_price < last_low * 0.997):
                _daily_low_alerted[(user_id, formatted_code)] = current_price
                mark_triggered('reach_low')
                triggered_alerts.append({
                    'type': 'reach_low',
                    'title': '⚠️ 触及/跌破日内最低价',
                    'reason': f"现价 {current_price:.2f} 触及/创出日内新低 (今日最低: {low:.2f}, 跌幅 {change_pct:+.2f}%)",
                    'details': f"今开: {open_price:.2f} | 昨收: {prev_close:.2f}"
                })

    return triggered_alerts


def evaluate_fund_alerts(
    fund_info: dict,
    settings: dict,
    user_id: int,
    now: datetime = None
) -> List[dict]:
    """
    Evaluate alert conditions for a fund (estimated NAV & valuation change %) against user settings.
    Returns a list of triggered alert dictionaries.
    """
    if now is None:
        now = datetime.now()

    code = fund_info.get('code', '')
    name = fund_info.get('name') or code
    current_nav = fund_info.get('current_nav', 0.0)
    prev_nav = fund_info.get('prev_nav', 0.0) or fund_info.get('last_nav', 0.0) or current_nav
    change_pct = fund_info.get('change_pct', 0.0)
    nav_type = fund_info.get('nav_type', '实时估值')

    if current_nav <= 0 or prev_nav <= 0:
        return []

    # Record current fund NAV into memory history
    record_fund_nav(code, current_nav, change_pct, prev_nav, now)

    triggered_alerts = []
    cooldown_mins = int(settings.get('alert_cooldown_minutes', 15) or 15)
    fund_key = f"fund_{code}"

    def is_cooling_down(alert_type: str) -> bool:
        key = (user_id, fund_key, alert_type)
        last_time = _alert_cooldowns.get(key)
        if last_time and (now - last_time).total_seconds() < cooldown_mins * 60:
            return True
        return False

    def mark_triggered(alert_type: str):
        key = (user_id, fund_key, alert_type)
        _alert_cooldowns[key] = now

    # 1. 基金估值大幅上涨预警 (Fund Rise Alert)
    if settings.get('alert_fund_rise_enabled', True):
        try:
            rise_threshold = float(settings.get('alert_fund_rise_pct', 2.0) or 2.0)
        except (ValueError, TypeError):
            rise_threshold = 2.0

        if change_pct >= rise_threshold and not is_cooling_down('fund_rise'):
            mark_triggered('fund_rise')
            triggered_alerts.append({
                'type': 'fund_rise',
                'title': '📈 基金估值大幅上涨预警',
                'reason': f"当前{nav_type}涨幅已达 {change_pct:+.2f}% (触发阈值: +{rise_threshold:.2f}%)",
                'details': f"实时估值: {current_nav:.4f} | 昨收净值: {prev_nav:.4f} ({nav_type})"
            })

    # 2. 基金估值大幅下跌预警 (Fund Fall Alert)
    if settings.get('alert_fund_fall_enabled', True):
        try:
            fall_threshold = float(settings.get('alert_fund_fall_pct', -2.0) or -2.0)
            if fall_threshold > 0:
                fall_threshold = -fall_threshold
        except (ValueError, TypeError):
            fall_threshold = -2.0

        if change_pct <= fall_threshold and not is_cooling_down('fund_fall'):
            mark_triggered('fund_fall')
            triggered_alerts.append({
                'type': 'fund_fall',
                'title': '📉 基金估值大幅下跌预警',
                'reason': f"当前{nav_type}跌幅已达 {change_pct:+.2f}% (触发阈值: {fall_threshold:.2f}%)",
                'details': f"实时估值: {current_nav:.4f} | 昨收净值: {prev_nav:.4f} ({nav_type})"
            })

    # 3. 基金短时间剧烈波动 / 估值异动 (Fund Swing Alert)
    if settings.get('alert_fund_swing_enabled', True):
        try:
            swing_mins = int(settings.get('alert_fund_swing_minutes', 15) or 15)
            swing_threshold = float(settings.get('alert_fund_swing_pct', 1.5) or 1.5)
        except (ValueError, TypeError):
            swing_mins = 15
            swing_threshold = 1.5

        if not is_cooling_down('fund_swing') and fund_key in _price_history:
            cutoff = now - timedelta(minutes=swing_mins)
            recent_points = [p for p in _price_history[fund_key] if p['time'] >= cutoff]
            if len(recent_points) >= 2:
                navs = [p['price'] for p in recent_points]
                min_n = min(navs)
                max_n = max(navs)
                first_n = recent_points[0]['price']
                last_n = recent_points[-1]['price']

                amplitude_pct = (max_n - min_n) / prev_nav * 100
                direct_change_pct = (last_n - first_n) / prev_nav * 100

                if amplitude_pct >= swing_threshold:
                    if direct_change_pct >= swing_threshold:
                        action_desc = f"⚡ {swing_mins}分钟内估值急速拉升 +{direct_change_pct:.2f}% (波动 {amplitude_pct:.2f}%)"
                    elif direct_change_pct <= -swing_threshold:
                        action_desc = f"⚡ {swing_mins}分钟内估值急速跳水 {direct_change_pct:.2f}% (波动 {amplitude_pct:.2f}%)"
                    else:
                        action_desc = f"⚡ {swing_mins}分钟内估值异动 波动达 {amplitude_pct:.2f}%"

                    mark_triggered('fund_swing')
                    triggered_alerts.append({
                        'type': 'fund_swing',
                        'title': '⚡ 基金估值异动波动预警',
                        'reason': action_desc,
                        'details': f"统计窗口: {swing_mins}分钟 | 阈值: {swing_threshold:.1f}% | 现估值: {current_nav:.4f}"
                    })

    return triggered_alerts


def format_alert_message(stock_info: dict, alert: dict, now: datetime = None) -> str:
    """Format stock alert message for Enterprise WeChat push."""
    if now is None:
        now = datetime.now()

    name = stock_info.get('name') or stock_info.get('code')
    code = stock_info.get('code')
    current_price = stock_info.get('current', 0.0) or stock_info.get('current_price', 0.0)
    change_pct = stock_info.get('change_pct', 0.0)
    high = stock_info.get('high', 0.0)
    low = stock_info.get('low', 0.0)
    prev_close = stock_info.get('prev_close', 0.0)

    date_time_str = now.strftime("%Y/%m/%d %H:%M:%S")

    lines = [
        f"{alert['title']}",
        "━━━━━━━━━━━━━━━━",
        f"📌 股票: {name} ({code})",
        f"💰 现价: {current_price:.2f} ({change_pct:+.2f}%)",
        f"🚨 触发原因: {alert['reason']}",
    ]
    if alert.get('details'):
        lines.append(f"ℹ️ 详细说明: {alert['details']}")
    if high > 0 and low > 0:
        lines.append(f"📊 今日最高: {high:.2f} | 今日最低: {low:.2f}")
    if prev_close > 0:
        lines.append(f"📈 昨收价: {prev_close:.2f}")
    lines.append(f"⏰ 预警时间: {date_time_str}")

    return "\n".join(lines)


def format_fund_alert_message(fund_info: dict, alert: dict, now: datetime = None) -> str:
    """Format fund alert message for Enterprise WeChat push."""
    if now is None:
        now = datetime.now()

    name = fund_info.get('name') or fund_info.get('code')
    code = fund_info.get('code')
    current_nav = fund_info.get('current_nav', 0.0)
    change_pct = fund_info.get('change_pct', 0.0)
    prev_nav = fund_info.get('prev_nav', 0.0) or fund_info.get('last_nav', 0.0) or current_nav
    nav_type = fund_info.get('nav_type', '实时估值')

    date_time_str = now.strftime("%Y/%m/%d %H:%M:%S")

    lines = [
        f"{alert['title']}",
        "━━━━━━━━━━━━━━━━",
        f"📦 基金: {name} ({code})",
        f"💰 {nav_type}: {current_nav:.4f} ({change_pct:+.2f}%)",
        f"🚨 触发原因: {alert['reason']}",
    ]
    if alert.get('details'):
        lines.append(f"ℹ️ 详细说明: {alert['details']}")
    if prev_nav > 0:
        lines.append(f"📊 昨收净值: {prev_nav:.4f}")
    lines.append(f"⏰ 预警时间: {date_time_str}")

    return "\n".join(lines)


async def check_and_trigger_stock_alerts():
    """
    Main background job called by scheduler during trading hours.
    Checks stock and fund price movements for all users and pushes alerts.
    """
    now = datetime.now()
    reset_daily_state_if_needed(now)

    if not is_trading_time(now):
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users")
    users = cursor.fetchall()

    for u in users:
        user_id = u['id']
        settings = get_settings_dict(user_id=user_id)

        # 1. 检查股票波动预警
        if settings.get('alert_enabled', True):
            cursor.execute("SELECT * FROM stocks WHERE user_id = ?", (user_id,))
            stocks = [dict(row) for row in cursor.fetchall()]
            if stocks:
                selected_codes_str = (settings.get('alert_monitored_stock_codes') or '').strip()
                if selected_codes_str:
                    selected_codes = [c.strip() for c in selected_codes_str.split(',') if c.strip()]
                    monitored_stocks = [
                        s for s in stocks
                        if s['code'] in selected_codes or s['code'].lstrip('shsz') in selected_codes
                    ]
                else:
                    monitored_stocks = [s for s in stocks if s.get('is_holding')]

                if monitored_stocks:
                    sina_codes = [format_stock_code(s['code']) for s in monitored_stocks]
                    market_data = await fetch_stock_data(sina_codes)

                    for s in monitored_stocks:
                        f_code = format_stock_code(s['code'])
                        s_data = market_data.get(f_code)
                        if not s_data:
                            continue

                        stock_info = {
                            'code': s['code'],
                            'name': s_data.get('name') or s.get('name') or s['code'],
                            'current': s_data['current'],
                            'prev_close': s_data['prev_close'],
                            'change_pct': s_data['change_pct'],
                            'high': s_data['high'],
                            'low': s_data['low'],
                            'open': s_data['open']
                        }

                        triggered_alerts = evaluate_stock_alerts(stock_info, settings, user_id, now)
                        for alert in triggered_alerts:
                            msg = format_alert_message(stock_info, alert, now)
                            print(f"[AlertService] User {user_id} triggered stock alert: {alert['title']} - {stock_info['name']}")
                            success, push_msg = send_wxwork_message(msg, user_id=user_id)
                            if not success:
                                print(f"[AlertService] Push failed: {push_msg}")

        # 2. 检查基金估值预警
        if settings.get('alert_funds_enabled', True):
            cursor.execute("SELECT * FROM funds WHERE user_id = ?", (user_id,))
            funds = [dict(row) for row in cursor.fetchall()]
            if funds:
                selected_fund_str = (settings.get('alert_monitored_fund_codes') or '').strip()
                if selected_fund_str:
                    selected_codes = [c.strip() for c in selected_fund_str.split(',') if c.strip()]
                    monitored_funds = [f for f in funds if f['code'] in selected_codes]
                else:
                    monitored_funds = [f for f in funds if f.get('is_holding')]

                if monitored_funds:
                    fund_codes = [f['code'] for f in monitored_funds]
                    fund_market_data = await fetch_fund_data(fund_codes)

                    for f in monitored_funds:
                        c = f['code']
                        f_data = fund_market_data.get(c)
                        if not f_data:
                            continue

                        fund_info = {
                            'code': c,
                            'name': f_data.get('name') or f.get('name') or c,
                            'current_nav': f_data.get('current_nav', 0.0),
                            'prev_nav': f_data.get('prev_nav', 0.0),
                            'change_pct': f_data.get('change_pct', 0.0),
                            'nav_type': f_data.get('nav_type', '实时估值')
                        }

                        triggered_fund_alerts = evaluate_fund_alerts(fund_info, settings, user_id, now)
                        for alert in triggered_fund_alerts:
                            msg = format_fund_alert_message(fund_info, alert, now)
                            print(f"[AlertService] User {user_id} triggered fund alert: {alert['title']} - {fund_info['name']}")
                            success, push_msg = send_wxwork_message(msg, user_id=user_id)
                            if not success:
                                print(f"[AlertService] Fund Push failed: {push_msg}")

    conn.close()


async def simulate_test_alert(user_id: int = 1) -> Tuple[bool, str]:
    """
    Simulate an alert push for UI testing.
    Pushes simulated alerts for both stock and fund to prove full capability.
    """
    now = datetime.now()
    settings = get_settings_dict(user_id=user_id)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stocks WHERE user_id = ? AND is_holding = 1 LIMIT 1", (user_id,))
    stock = cursor.fetchone()
    if not stock:
        cursor.execute("SELECT * FROM stocks WHERE user_id = ? LIMIT 1", (user_id,))
        stock = cursor.fetchone()

    cursor.execute("SELECT * FROM funds WHERE user_id = ? AND is_holding = 1 LIMIT 1", (user_id,))
    fund = cursor.fetchone()
    if not fund:
        cursor.execute("SELECT * FROM funds WHERE user_id = ? LIMIT 1", (user_id,))
        fund = cursor.fetchone()
    conn.close()

    # Prepare Stock info
    if stock:
        code = stock['code']
        name = stock['name'] or code
        f_code = format_stock_code(code)
        market_dict = await fetch_stock_data([f_code])
        m_data = market_dict.get(f_code, {})
        curr = m_data.get('current') or stock['cost_price'] or 100.0
        prev = m_data.get('prev_close') or (curr * 0.95)
        high = m_data.get('high') or (curr * 1.02)
        low = m_data.get('low') or (curr * 0.98)
        change_pct = m_data.get('change_pct') or 5.26
    else:
        code = "600519"
        name = "贵州茅台"
        curr = 1680.00
        prev = 1600.00
        high = 1688.00
        low = 1595.00
        change_pct = 5.00

    stock_info = {
        'code': code,
        'name': name,
        'current': curr,
        'prev_close': prev,
        'change_pct': change_pct,
        'high': high,
        'low': low,
        'open': prev * 1.01
    }

    swing_mins = int(settings.get('alert_swing_minutes', 5) or 5)
    swing_pct = float(settings.get('alert_swing_pct', 3.0) or 3.0)

    test_alert = {
        'type': 'test',
        'title': '🧪【测试】股票价格与异动预警通知',
        'reason': f"⚡ 模拟触发：{swing_mins}分钟内急速拉升 +{swing_pct + 0.8:.2f}% (振幅 {swing_pct + 1.2:.2f}%) / 涨幅超 +{settings.get('alert_rise_pct', 5.0)}%",
        'details': f"已成功连接企业微信消息通道，预警监控引擎与冷却机制运行正常。"
    }

    stock_msg = format_alert_message(stock_info, test_alert, now)

    # Prepare Fund info
    if fund:
        fcode = fund['code']
        fname = fund['name'] or fcode
        f_dict = await fetch_fund_data([fcode])
        fdata = f_dict.get(fcode, {})
        fcurr = fdata.get('current_nav') or fund['cost_nav'] or 1.2500
        fprev = fdata.get('prev_nav') or (fcurr * 0.98)
        fchange = fdata.get('change_pct') or 2.15
        ftype = fdata.get('nav_type') or '实时估值'
    else:
        fcode = "161725"
        fname = "招商中证白酒指数A"
        fcurr = 1.2345
        fprev = 1.2050
        fchange = 2.45
        ftype = "实时估值"

    fund_info = {
        'code': fcode,
        'name': fname,
        'current_nav': fcurr,
        'prev_nav': fprev,
        'change_pct': fchange,
        'nav_type': ftype
    }

    fund_alert = {
        'type': 'test',
        'title': '🧪【测试】基金实时估值异动预警通知',
        'reason': f"📈 模拟触发：今日{ftype}涨幅达 +{fchange:.2f}% (触发阈值: +{settings.get('alert_fund_rise_pct', 2.0)}%)",
        'details': f"基金实时估值监控通道正常，支持估值涨跌幅与短时间异动预警。"
    }

    fund_msg = format_fund_alert_message(fund_info, fund_alert, now)

    combined_msg = f"{stock_msg}\n\n════════════════\n\n{fund_msg}"
    success, detail = send_wxwork_message(combined_msg, user_id=user_id)
    return success, f"推送结果: {detail}\n\n已发送内容预览:\n{combined_msg}"
