from datetime import datetime, time, date, timedelta
from typing import Union, Optional, Dict, Any

# Simplified A-share holidays (YYYY-MM-DD format) for 2023, 2024, 2025, 2026, 2027
HOLIDAYS = {
    # 2023
    "2023-01-02", "2023-01-23", "2023-01-24", "2023-01-25", "2023-01-26", "2023-01-27",
    "2023-04-05", "2023-05-01", "2023-05-02", "2023-05-03", "2023-06-22", "2023-06-23",
    "2023-09-29", "2023-10-02", "2023-10-03", "2023-10-04", "2023-10-05", "2023-10-06",

    # 2024
    "2024-01-01", "2024-02-09", "2024-02-12", "2024-02-13", "2024-02-14", "2024-02-15", "2024-02-16",
    "2024-04-04", "2024-04-05", "2024-05-01", "2024-05-02", "2024-05-03", "2024-06-10", "2024-09-16",
    "2024-09-17", "2024-10-01", "2024-10-02", "2024-10-03", "2024-10-04", "2024-10-07",
    
    # 2025 (Estimates based on typical schedule)
    "2025-01-01", "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31", "2025-02-03", "2025-02-04",
    "2025-04-04", "2025-05-01", "2025-05-02", "2025-06-02", "2025-10-01", "2025-10-02", "2025-10-03", "2025-10-06", "2025-10-07",
    
    # 2026 (Estimates)
    "2026-01-01", "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20",
    "2026-04-06", "2026-05-01", "2026-06-22", "2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07",

    # 2027 (Estimates)
    "2027-01-01", "2027-02-05", "2027-02-08", "2027-02-09", "2027-02-10", "2027-02-11", "2027-02-12",
    "2027-04-05", "2027-05-03", "2027-06-09", "2027-10-01", "2027-10-04", "2027-10-05", "2027-10-06", "2027-10-07"
}

def is_trading_day(dt: Union[datetime, date, None] = None) -> bool:
    if dt is None:
        dt = datetime.now()
    if dt.weekday() >= 5:  # Saturday or Sunday
        return False
    dt_str = dt.strftime("%Y-%m-%d")
    if dt_str in HOLIDAYS:
        return False
    return True

def is_trading_time(dt: Union[datetime, date, None] = None) -> bool:
    if dt is None:
        dt = datetime.now()
    if not is_trading_day(dt):
        return False
    
    current_time = dt.time() if isinstance(dt, datetime) else time(10, 0)
    
    # Pre-market prepare: 9:15
    # Morning: 9:30 - 11:30
    # Afternoon: 13:00 - 15:00
    
    # Start checking from 9:15 (for pre-market prep) to 11:40 (allow 10 mins after morning close for review)
    if time(9, 15) <= current_time <= time(11, 40):
        return True
        
    # 13:00 to 15:10 (allow 10 mins after close for final updates and review)
    if time(13, 0) <= current_time <= time(15, 10):
        return True
        
    return False


WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

def get_next_trading_day(dt: Union[date, datetime] = None, max_lookahead: int = 20) -> Optional[date]:
    """获取指定日期之后的下一个实际交易日（自动跳过周末与法定休市日）"""
    if dt is None:
        dt = date.today()
    elif isinstance(dt, datetime):
        dt = dt.date()
    
    candidate = dt + timedelta(days=1)
    for _ in range(max_lookahead):
        if is_trading_day(candidate):
            return candidate
        candidate += timedelta(days=1)
    return None

def get_next_trading_day_info(dt: Union[date, datetime] = None, max_lookahead: int = 20) -> Dict[str, Any]:
    """
    推导下一个交易日的详细结构化信息，包括星期、是否跳过周末、友好文案标签等。
    """
    if dt is None:
        dt = date.today()
    elif isinstance(dt, datetime):
        dt = dt.date()

    next_day = get_next_trading_day(dt, max_lookahead=max_lookahead)
    if not next_day:
        return {
            "target_date": dt.isoformat(),
            "next_trading_date": None,
            "days_ahead": 0,
            "is_natural_tomorrow": False,
            "is_weekend_skipped": False,
            "weekday_cn": "",
            "display_label": "未知交易日",
            "skip_reason": "无法在指定窗口内定位下一交易日"
        }

    days_ahead = (next_day - dt).days
    is_natural_tomorrow = (days_ahead == 1)
    target_weekday = dt.weekday()
    next_weekday = next_day.weekday()
    next_weekday_cn = WEEKDAY_NAMES[next_weekday]
    date_short = next_day.strftime("%m-%d")

    is_weekend_skipped = False
    skip_reasons = []

    if target_weekday == 4 and next_weekday == 0 and days_ahead == 3:
        is_weekend_skipped = True
        skip_reasons.append("已跳过周末双休")
        display_label = f"下周一 ({date_short})"
    elif days_ahead > 1:
        if days_ahead >= 3 and any((dt + timedelta(days=i)).weekday() >= 5 for i in range(1, days_ahead)):
            is_weekend_skipped = True
            skip_reasons.append("跳过周末")
        if any((dt + timedelta(days=i)).strftime("%Y-%m-%d") in HOLIDAYS for i in range(1, days_ahead)):
            skip_reasons.append("跳过法定节假日休市")
        display_label = f"下一交易日 ({next_weekday_cn} {date_short})"
    else:
        display_label = f"明日 ({next_weekday_cn} {date_short})"

    return {
        "target_date": dt.isoformat(),
        "next_trading_date": next_day.isoformat(),
        "days_ahead": days_ahead,
        "is_natural_tomorrow": is_natural_tomorrow,
        "is_weekend_skipped": is_weekend_skipped,
        "weekday_cn": next_weekday_cn,
        "display_label": display_label,
        "skip_reason": "；".join(skip_reasons) if skip_reasons else "正常次日开盘"
    }


