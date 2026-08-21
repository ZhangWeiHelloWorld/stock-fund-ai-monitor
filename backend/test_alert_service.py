import unittest
from datetime import datetime, timedelta
import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.alert_service import (
    evaluate_stock_alerts,
    evaluate_fund_alerts,
    format_alert_message,
    format_fund_alert_message,
    record_stock_price,
    record_fund_nav,
    reset_daily_state_if_needed,
    _price_history,
    _alert_cooldowns,
    _daily_high_alerted,
    _daily_low_alerted
)

class TestAlertService(unittest.TestCase):

    def setUp(self):
        # Clear in-memory history before each test
        _price_history.clear()
        _alert_cooldowns.clear()
        _daily_high_alerted.clear()
        _daily_low_alerted.clear()

    def test_rise_and_fall_alerts(self):
        settings = {
            'alert_enabled': True,
            'alert_rise_enabled': True,
            'alert_rise_pct': 5.0,
            'alert_fall_enabled': True,
            'alert_fall_pct': -5.0,
            'alert_cooldown_minutes': 15
        }
        now = datetime(2026, 8, 11, 10, 0, 0)

        # Test Rise trigger
        stock_rise = {
            'code': '600519',
            'name': '贵州茅台',
            'current': 1680.0,
            'prev_close': 1600.0,
            'change_pct': 5.0,
            'high': 1680.0,
            'low': 1590.0,
            'open': 1605.0
        }
        alerts = evaluate_stock_alerts(stock_rise, settings, user_id=1, now=now)
        types = [a['type'] for a in alerts]
        self.assertIn('rise', types, "Should trigger rise alert when change_pct >= 5.0%")

        # Test Fall trigger
        stock_fall = {
            'code': '000001',
            'name': '平安银行',
            'current': 9.5,
            'prev_close': 10.0,
            'change_pct': -5.0,
            'high': 10.1,
            'low': 9.5,
            'open': 10.0
        }
        alerts_fall = evaluate_stock_alerts(stock_fall, settings, user_id=1, now=now)
        types_fall = [a['type'] for a in alerts_fall]
        self.assertIn('fall', types_fall, "Should trigger fall alert when change_pct <= -5.0%")

    def test_short_term_swing_alert(self):
        settings = {
            'alert_enabled': True,
            'alert_swing_enabled': True,
            'alert_swing_minutes': 5,
            'alert_swing_pct': 3.0,
            'alert_cooldown_minutes': 15
        }
        code = 'sh600519'
        prev_close = 100.0
        base_time = datetime(2026, 8, 11, 10, 0, 0)

        # Record price 4 minutes ago: 100.0
        record_stock_price(code, 100.0, 0.0, 100.5, 99.8, prev_close, now=base_time - timedelta(minutes=4))
        # Record price 2 minutes ago: 101.5
        record_stock_price(code, 101.5, 1.5, 101.5, 99.8, prev_close, now=base_time - timedelta(minutes=2))

        # Current tick: jumped to 103.5 (+3.5% swing in 4 mins)
        stock_info = {
            'code': '600519',
            'name': '贵州茅台',
            'current': 103.5,
            'prev_close': prev_close,
            'change_pct': 3.5,
            'high': 103.5,
            'low': 99.8,
            'open': 100.0
        }

        alerts = evaluate_stock_alerts(stock_info, settings, user_id=1, now=base_time)
        types = [a['type'] for a in alerts]
        self.assertIn('swing', types, "Should trigger swing alert when price surges > 3.0% within 5 mins")

        msg = format_alert_message(stock_info, alerts[0], now=base_time)
        self.assertIn("贵州茅台", msg)
        self.assertIn("短时间剧烈波动", msg)

    def test_cooldown_deduplication(self):
        settings = {
            'alert_enabled': True,
            'alert_rise_enabled': True,
            'alert_rise_pct': 5.0,
            'alert_cooldown_minutes': 15
        }
        stock = {
            'code': '600519',
            'name': '贵州茅台',
            'current': 1680.0,
            'prev_close': 1600.0,
            'change_pct': 5.0,
            'high': 1680.0,
            'low': 1590.0,
            'open': 1605.0
        }
        t1 = datetime(2026, 8, 11, 10, 0, 0)
        alerts1 = evaluate_stock_alerts(stock, settings, user_id=1, now=t1)
        self.assertTrue(len(alerts1) > 0, "First trigger should succeed")

        # 5 minutes later, still over 5.0%, should be suppressed by 15min cooldown
        t2 = datetime(2026, 8, 11, 10, 5, 0)
        alerts2 = evaluate_stock_alerts(stock, settings, user_id=1, now=t2)
        self.assertEqual(len(alerts2), 0, "Second trigger within cooldown period should be suppressed")

        # 16 minutes later, should trigger again
        t3 = datetime(2026, 8, 11, 10, 16, 0)
        alerts3 = evaluate_stock_alerts(stock, settings, user_id=1, now=t3)
        self.assertTrue(len(alerts3) > 0, "After cooldown expires, should trigger alert again")

    def test_daily_high_low_alerts(self):
        settings = {
            'alert_enabled': True,
            'alert_reach_high_enabled': True,
            'alert_reach_low_enabled': True,
            'alert_cooldown_minutes': 15
        }
        t1 = datetime(2026, 8, 11, 10, 0, 0)
        stock_high = {
            'code': '600519',
            'name': '贵州茅台',
            'current': 1700.0,
            'prev_close': 1650.0,
            'change_pct': 3.03,
            'high': 1700.0,
            'low': 1640.0,
            'open': 1655.0
        }
        alerts = evaluate_stock_alerts(stock_high, settings, user_id=1, now=t1)
        types = [a['type'] for a in alerts]
        self.assertIn('reach_high', types, "Should trigger reach_high alert")

    def test_fund_valuation_alerts(self):
        settings = {
            'alert_funds_enabled': True,
            'alert_fund_rise_enabled': True,
            'alert_fund_rise_pct': 2.0,
            'alert_fund_fall_enabled': True,
            'alert_fund_fall_pct': -2.0,
            'alert_fund_swing_enabled': True,
            'alert_fund_swing_minutes': 15,
            'alert_fund_swing_pct': 1.5,
            'alert_cooldown_minutes': 15
        }
        base_time = datetime(2026, 8, 11, 14, 0, 0)

        # 1. Fund Rise alert
        fund_rise = {
            'code': '161725',
            'name': '招商中证白酒指数A',
            'current_nav': 1.2500,
            'prev_nav': 1.2200,
            'change_pct': 2.46,
            'nav_type': '实时估值'
        }
        alerts_rise = evaluate_fund_alerts(fund_rise, settings, user_id=1, now=base_time)
        types_rise = [a['type'] for a in alerts_rise]
        self.assertIn('fund_rise', types_rise, "Should trigger fund_rise alert when估值涨幅 >= 2.0%")

        msg = format_fund_alert_message(fund_rise, alerts_rise[0], now=base_time)
        self.assertIn("招商中证白酒指数A", msg)
        self.assertIn("实时估值", msg)

        # 2. Fund Fall alert
        fund_fall = {
            'code': '110011',
            'name': '易方达中小盘',
            'current_nav': 2.0000,
            'prev_nav': 2.0500,
            'change_pct': -2.44,
            'nav_type': '实时估值'
        }
        alerts_fall = evaluate_fund_alerts(fund_fall, settings, user_id=1, now=base_time)
        types_fall = [a['type'] for a in alerts_fall]
        self.assertIn('fund_fall', types_fall, "Should trigger fund_fall alert when估值跌幅 <= -2.0%")

        # 3. Fund Swing alert
        f_code = '005827'
        record_fund_nav(f_code, 1.0000, 0.0, 1.0000, now=base_time - timedelta(minutes=10))
        fund_swing = {
            'code': f_code,
            'name': '易方达蓝筹精选',
            'current_nav': 1.0180,
            'prev_nav': 1.0000,
            'change_pct': 1.80,
            'nav_type': '实时估值'
        }
        alerts_swing = evaluate_fund_alerts(fund_swing, settings, user_id=1, now=base_time)
        types_swing = [a['type'] for a in alerts_swing]
        self.assertIn('fund_swing', types_swing, "Should trigger fund_swing alert when 15min swing >= 1.5%")

if __name__ == '__main__':
    unittest.main()
