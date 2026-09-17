import asyncio
import time
from datetime import datetime, time as dt_time, timedelta
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.market_service import (
    _determine_fund_quote,
    _is_fund_cache_valid,
    _fund_cache,
    fetch_fund_data
)
from services.trading_calendar import is_trading_day


def test_determine_fund_quote_premarket():
    """
    Test Bug 2: At 09:15 / 09:25 before market opens, fund MUST NOT use yesterday's intraday estimate.
    Base NAV must be yesterday's official NAV. Today's change is 0.00% and day profit is 0.00.
    """
    # Simulate today is trading day 2026-09-17 at 09:15 AM
    now = datetime(2026, 9, 17, 9, 15, 0)
    quote = _determine_fund_quote(
        code="519674",
        name="银河创新混合A",
        official_nav=11.8891,
        official_prev_nav=11.4354,
        official_date="2026-09-16",
        est_nav=11.9166,       # Yesterday's stale estimate from Sina fu_
        est_change_pct=0.23,   # Yesterday's stale estimate change
        est_time="15:00:00",
        fu_date="2026-09-16",
        now=now
    )
    assert quote["current_nav"] == 11.8891, f"Expected 11.8891, got {quote['current_nav']}"
    assert quote["prev_nav"] == 11.8891, f"Expected 11.8891, got {quote['prev_nav']}"
    assert quote["change_pct"] == 0.0, f"Expected 0.0, got {quote['change_pct']}"
    assert quote["is_updated"] is True, f"Expected is_updated=True, got {quote['is_updated']}"
    assert quote["nav_type"] == "官方净值", f"Expected '官方净值', got {quote['nav_type']}"
    assert quote["update_time"] == "2026-09-16", f"Expected 2026-09-16, got {quote['update_time']}"
    print("✓ test_determine_fund_quote_premarket (09:15) passed")

    # Simulate today at 09:25 AM
    now_25 = datetime(2026, 9, 17, 9, 25, 0)
    quote_25 = _determine_fund_quote(
        code="519674",
        name="银河创新混合A",
        official_nav=11.8891,
        official_prev_nav=11.4354,
        official_date="2026-09-16",
        est_nav=11.9166,
        est_change_pct=0.23,
        est_time="15:00:00",
        fu_date="2026-09-16",
        now=now_25
    )
    assert quote_25["current_nav"] == 11.8891
    assert quote_25["change_pct"] == 0.0
    assert quote_25["is_updated"] is True
    print("✓ test_determine_fund_quote_premarket (09:25) passed")


def test_determine_fund_quote_trading():
    """Test intraday trading: should use today's estimate."""
    now = datetime(2026, 9, 17, 10, 30, 0)
    quote = _determine_fund_quote(
        code="519674",
        name="银河创新混合A",
        official_nav=11.8891,
        official_prev_nav=11.4354,
        official_date="2026-09-16",
        est_nav=11.9500,
        est_change_pct=0.51,
        est_time="10:30:00",
        fu_date="2026-09-17",
        now=now
    )
    assert quote["current_nav"] == 11.9500
    assert quote["prev_nav"] == 11.8891
    assert quote["change_pct"] == 0.51
    assert quote["is_updated"] is False
    assert quote["nav_type"] == "实时估值"
    assert quote["update_time"] == "10:30:00"
    print("✓ test_determine_fund_quote_trading passed")


def test_determine_fund_quote_post_close_unupdated():
    """
    Test Bug 1: After 20:00, if today's official NAV has not been updated yet,
    maintain 15:00 closing estimate with '实时估值' and is_updated=False.
    """
    now = datetime(2026, 9, 17, 20, 15, 0)
    quote = _determine_fund_quote(
        code="519674",
        name="银河创新混合A",
        official_nav=11.8891,
        official_prev_nav=11.4354,
        official_date="2026-09-16", # Still yesterday
        est_nav=11.9166,
        est_change_pct=0.23,
        est_time="15:00:00",
        fu_date="2026-09-17",
        now=now
    )
    assert quote["current_nav"] == 11.9166
    assert quote["prev_nav"] == 11.8891
    assert quote["change_pct"] == 0.23
    assert quote["is_updated"] is False
    assert quote["nav_type"] == "实时估值"
    assert quote["is_final"] is False
    print("✓ test_determine_fund_quote_post_close_unupdated (20:15) passed")


def test_determine_fund_quote_post_close_updated():
    """
    Test Bug 1: After 20:00, when today's official NAV is updated,
    update to official NAV, status '官方净值', is_updated=True, is_final=True.
    """
    now = datetime(2026, 9, 17, 20, 45, 0)
    quote = _determine_fund_quote(
        code="519674",
        name="银河创新混合A",
        official_nav=11.9500,
        official_prev_nav=11.8891,
        official_date="2026-09-17", # Today!
        est_nav=11.9166,
        est_change_pct=0.23,
        est_time="15:00:00",
        fu_date="2026-09-17",
        now=now
    )
    assert quote["current_nav"] == 11.9500
    assert quote["prev_nav"] == 11.8891
    expected_pct = (11.9500 - 11.8891) / 11.8891 * 100
    assert abs(quote["change_pct"] - expected_pct) < 1e-6
    assert quote["is_updated"] is True
    assert quote["nav_type"] == "官方净值"
    assert quote["is_final"] is True
    assert quote["update_time"] == "2026-09-17"
    print("✓ test_determine_fund_quote_post_close_updated (20:45) passed")


def test_determine_fund_quote_weekend():
    """Test non-trading day (weekend)."""
    now = datetime(2026, 9, 19, 14, 0, 0) # Saturday
    quote = _determine_fund_quote(
        code="519674",
        name="银河创新混合A",
        official_nav=11.9500,
        official_prev_nav=11.8891,
        official_date="2026-09-17",
        est_nav=11.9166,
        est_change_pct=0.23,
        est_time="15:00:00",
        fu_date="2026-09-17",
        now=now
    )
    assert quote["current_nav"] == 11.9500
    assert quote["is_updated"] is True
    assert quote["nav_type"] == "官方净值"
    assert quote["is_final"] is True
    print("✓ test_determine_fund_quote_weekend passed")


def test_fund_cache_and_rate_limiting():
    """
    Test rate limiting and caching:
    - is_final=True is never re-queried today.
    - unconfirmed cache within 30s is served from memory.
    """
    now = datetime(2026, 9, 17, 20, 20, 0)
    today_str = "2026-09-17"

    _fund_cache.clear()

    # 1. Finalized fund
    _fund_cache["test_code_1"] = {
        "data": {"name": "银河创新", "current_nav": 11.95, "last_nav": 11.88, "prev_nav": 11.88, "change_pct": 0.5, "update_time": "2026-09-17", "is_updated": True, "nav_type": "官方净值", "is_final": True},
        "fetched_at": time.time() - 3600, # 1 hour ago
        "date": today_str,
        "is_final": True
    }
    assert _is_fund_cache_valid("test_code_1", now, force_refresh=False) is True
    assert _is_fund_cache_valid("test_code_1", now, force_refresh=True) is True # Finalized never re-queried!
    print("✓ test_fund_cache_finalized passed")

    # 2. Un-updated fund within 30s after 20:00
    _fund_cache["test_code_2"] = {
        "data": {"name": "金信稳健", "current_nav": 3.61, "last_nav": 3.59, "prev_nav": 3.59, "change_pct": 0.2, "update_time": "15:00:00", "is_updated": False, "nav_type": "实时估值", "is_final": False},
        "fetched_at": time.time() - 10, # 10 seconds ago
        "date": today_str,
        "is_final": False
    }
    # Within 30s -> valid
    assert _is_fund_cache_valid("test_code_2", now, force_refresh=False) is True
    # Expired (> 30s) -> invalid, allows fresh query
    _fund_cache["test_code_2"]["fetched_at"] = time.time() - 35
    assert _is_fund_cache_valid("test_code_2", now, force_refresh=False) is False
    print("✓ test_fund_cache_unupdated_rate_limiting passed")

    _fund_cache.clear()


async def test_live_fetch_fund_data():
    """Test actual live call to fetch_fund_data and verify caching."""
    _fund_cache.clear()
    codes = ["519674", "007872", "017811"]
    
    t0 = time.time()
    res1 = await fetch_fund_data(codes, force_refresh=True)
    t1 = time.time()
    network_duration = t1 - t0
    print(f"✓ Live fetch took {network_duration:.3f}s")
    
    for c in codes:
        assert c in res1, f"Missing {c} in response"
        f = res1[c]
        assert f["current_nav"] > 0, f"Invalid current_nav for {c}"
        assert f["name"], f"Missing name for {c}"
        assert "update_time" in f, f"Missing update_time for {c}"
        print(f"  Fund {c}: name='{f['name']}', nav={f['current_nav']}, status='{f['nav_type']}', is_updated={f['is_updated']}, time='{f['update_time']}'")

    # Second call should hit cache immediately (< 10ms)
    t2 = time.time()
    res2 = await fetch_fund_data(codes, force_refresh=False)
    t3 = time.time()
    cached_duration = t3 - t2
    print(f"✓ Cached fetch took {cached_duration:.4f}s (Speedup: {network_duration/max(cached_duration, 1e-6):.1f}x)")
    assert cached_duration < 0.05, f"Cache fetch should be instant, took {cached_duration}"
    for c in codes:
        assert res2[c]["current_nav"] == res1[c]["current_nav"]
        assert res2[c]["update_time"] == res1[c]["update_time"]


def main():
    test_determine_fund_quote_premarket()
    test_determine_fund_quote_trading()
    test_determine_fund_quote_post_close_unupdated()
    test_determine_fund_quote_post_close_updated()
    test_determine_fund_quote_weekend()
    test_fund_cache_and_rate_limiting()
    asyncio.run(test_live_fetch_fund_data())
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
