from datetime import datetime, time, date

# Simplified A-share holidays (YYYY-MM-DD format) for 2024, 2025, 2026
HOLIDAYS = {
    # 2024
    "2024-01-01", "2024-02-09", "2024-02-12", "2024-02-13", "2024-02-14", "2024-02-15", "2024-02-16",
    "2024-04-04", "2024-04-05", "2024-05-01", "2024-05-02", "2024-05-03", "2024-06-10", "2024-09-16",
    "2024-09-17", "2024-10-01", "2024-10-02", "2024-10-03", "2024-10-04", "2024-10-07",
    
    # 2025 (Estimates based on typical schedule)
    "2025-01-01", "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31", "2025-02-03", "2025-02-04",
    "2025-04-04", "2025-05-01", "2025-05-02", "2025-06-02", "2025-10-01", "2025-10-02", "2025-10-03", "2025-10-06", "2025-10-07",
    
    # 2026 (Estimates)
    "2026-01-01", "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20",
    "2026-04-06", "2026-05-01", "2026-06-22", "2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07"
}

def is_trading_day(dt: datetime = None) -> bool:
    if dt is None:
        dt = datetime.now()
    if dt.weekday() >= 5:  # Saturday or Sunday
        return False
    dt_str = dt.strftime("%Y-%m-%d")
    if dt_str in HOLIDAYS:
        return False
    return True

def is_trading_time(dt: datetime = None) -> bool:
    if dt is None:
        dt = datetime.now()
    if not is_trading_day(dt):
        return False
    
    current_time = dt.time()
    
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

