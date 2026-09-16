import unittest
import asyncio
import sys
import os
from datetime import date
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.bazi_calculator import calculate_full_bazi
from services.strategy.tianjit_strategy import resolve_tianjit_action, run_tianjit_backtest, compute_monthly_regime



class TianjitRegressionTests(unittest.TestCase):
    def decision(self, **overrides):
        params = dict(today=date(2026, 9, 3), today_bazi={"signal_level": "S", "score": 90,
                      "ten_god": "比肩", "shensha_names": [], "ganzhi": "庚辰"},
                      t1_signal={}, monthly_regime={"max_position_ratio": 1},
                      day_change_pct=0, cur_shares=1000, cur_nav=10, avg_cost=10,
                      last_buy_index=-999, last_sell_index=-999, cur_day_index=0, cfg={})
        params.update(overrides)
        return resolve_tianjit_action(**params)

    def test_stop_loss_bypasses_discretionary_cooldown(self):
        action = self.decision(cur_nav=8, last_sell_index=0, cfg={"sell_cooldown_days": 10})
        self.assertEqual(action[:3], ("SELL", 0, 1))

    def test_rise_take_profit_before_buy(self):
        self.assertEqual(self.decision(day_change_pct=6)[0], "SELL")

    def test_position_limit_reduces_existing_position(self):
        action = self.decision(cfg={"max_position_limit": 5000})
        self.assertEqual(action[:3], ("SELL", 0, 0.5))

    def test_solar_term_boundary(self):
        self.assertEqual(compute_monthly_regime(2026, 10, {}, {}, date(2026, 10, 1))["month_branch"], "酉")
        self.assertEqual(compute_monthly_regime(2026, 10, {}, {}, date(2026, 10, 20))["month_branch"], "戌")

    def test_birthplace_and_lunar_date(self):
        bazi = calculate_full_bazi("1992-05-24", "07:00", province="河南省", city="固始县", calendar_type="lunar")
        self.assertEqual(bazi["solar_date"], "1992-06-24")
        self.assertEqual(bazi["day_pillar"], "辛未")
        self.assertEqual(bazi["longitude"], 115.68)
        self.assertEqual(bazi["hour_pillar"], "辛卯")

    def history(self):
        return [{"date": f"2026-09-0{i}", "nav": 10, "change_pct": 0} for i in (1, 2, 3)]

    def test_initial_stock_cash_conservation(self):
        with patch("services.strategy.tianjit_strategy.resolve_tianjit_action", return_value=(None, 0, 0, "")):
            result = run_tianjit_backtest(self.history(), {"initial_capital": 10001}, {}, is_stock=True)
        metrics = result["metrics"]
        self.assertAlmostEqual(metrics["final_assets"] + metrics["total_fees_paid"], 10001, places=2)
        self.assertGreaterEqual(metrics["final_cash"], 0)

    def test_insufficient_stock_capital(self):
        self.assertFalse(run_tianjit_backtest(self.history(), {"initial_capital": 600}, {}, is_stock=True)["success"])

    def test_fund_contributions_include_fee_and_signal_is_lagged(self):
        with patch("services.strategy.tianjit_strategy.resolve_tianjit_action", return_value=("BUY", 1000, 0, "test")) as resolve:
            result = run_tianjit_backtest(self.history(), {"initial_capital": 10000, "allow_additional_capital": True}, {}, {"subscription_rate": 0.01})
        self.assertEqual(result["metrics"]["total_invested"], 12000)
        self.assertEqual(resolve.call_args_list[0].kwargs["today"], date(2026, 9, 1))
        self.assertAlmostEqual(result["metrics"]["final_assets"] + result["metrics"]["total_fees_paid"], 12000, delta=0.02)

    def test_default_has_no_implicit_contributions(self):
        with patch("services.strategy.tianjit_strategy.resolve_tianjit_action", return_value=("BUY", 1000, 0, "test")):
            result = run_tianjit_backtest(self.history(), {"initial_capital": 10000}, {})
        self.assertEqual(result["metrics"]["total_invested"], 10000)
        self.assertEqual(result["metrics"]["buy_trades"], 1)

    def test_network_failure_does_not_generate_prices(self):
        from services.strategy.stock_data_provider import fetch_stock_history
        with patch("services.strategy.stock_data_provider.httpx.AsyncClient") as client:
            client.return_value.__aenter__ = AsyncMock(side_effect=RuntimeError("offline"))
            with self.assertRaisesRegex(ValueError, "真实股票历史行情"):
                asyncio.run(fetch_stock_history("600460", force_refresh=True))

    def test_duplicate_dates_rejected(self):
        with self.assertRaises(ValueError):
            run_tianjit_backtest([self.history()[0]] * 2, {}, {})

    def test_monthly_filter_can_be_disabled(self):
        self.assertEqual(compute_monthly_regime(2026, 10, {}, {"monthly_regime_enabled": False})["max_position_ratio"], 1)


if __name__ == "__main__":
    unittest.main()
