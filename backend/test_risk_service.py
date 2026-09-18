import unittest
import asyncio
import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DB_PATH, init_db
from services.om_stw_service import (
    evaluate_rule_based_om_stw,
    get_dynamic_market_context,
    analyze_news_with_model,
    format_risk_alert_wx_message,
    STOCK_FILTER_PATTERN,
    record_daily_pre_market_risk,
    record_daily_market_close,
    get_daily_risk_market_records,
    get_daily_risk_analytics_summary
)

class TestRiskService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_default_model_in_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM risk_models WHERE model_id = 'om_stw'").fetchone()
        conn.close()
        self.assertIsNotNone(row, "Default model 'om_stw' should exist in risk_models table")
        self.assertEqual(row["name"], "官媒舆情见顶与筹码派发预警模型 (OM-STW)")
        self.assertEqual(row["alert_threshold"], 60)
        self.assertEqual(row["is_default"], 1)

    def test_stock_news_filter_regex(self):
        # Stock ticker news should be caught
        self.assertTrue(bool(STOCK_FILTER_PATTERN.search("600519.SH 今日大单净流出")))
        self.assertTrue(bool(STOCK_FILTER_PATTERN.search("隆基绿能(601012)股东质押公告")))
        self.assertTrue(bool(STOCK_FILTER_PATTERN.search("创业板某股票今日涨停封单过亿")))
        self.assertTrue(bool(STOCK_FILTER_PATTERN.search("特变电工中标50亿元重大项目")))

        # Macro / official media news should NOT be filtered out
        self.assertFalse(bool(STOCK_FILTER_PATTERN.search("新闻联播：长线外资看好中国 持续加码硬科技")))
        self.assertFalse(bool(STOCK_FILTER_PATTERN.search("经济日报：让居民通过股票、基金也能赚到钱")))
        self.assertFalse(bool(STOCK_FILTER_PATTERN.search("人民日报发声：中国资本市场具备长期健康发展基础")))

    def test_overbought_media_hype_triggers_red_alert(self):
        mkt_overbought = {
            "gain_20d_pct": 28.0,
            "bias_20": 9.5,
            "rsi_14": 84.0,
            "is_extreme_bottom": False,
            "is_overbought": True
        }
        res = evaluate_rule_based_om_stw(
            news_title="新闻联播头条：长线外资持续加码中国硬科技 牛市新起点",
            news_source="央视《新闻联播》",
            news_content="次日大幅高开后迅速回落收长上影墓碑线，主力大单净流出创历史新高",
            market_context=mkt_overbought
        )
        self.assertEqual(res["level"], "red", "Should trigger red alert on media hype + high overbought")
        self.assertGreaterEqual(res["score"], 75, "Score should be >= 75")
        self.assertIn("T+0 ～ T+2", res["lead_time"])
        self.assertTrue(any("锁死买入" in a for a in res["action_guide"]))

    def test_policy_bottom_exemption(self):
        mkt_bottom = {
            "gain_20d_pct": -15.0,
            "bias_20": -9.0,
            "rsi_14": 20.0,
            "is_extreme_bottom": True,
            "is_overbought": False
        }
        res = evaluate_rule_based_om_stw(
            news_title="新闻联播：多部委联合发声 力挺资本市场健康发展",
            news_source="央视《新闻联播》",
            news_content="重磅政策组合拳真金白银救市，稳定市场预期",
            market_context=mkt_bottom
        )
        self.assertEqual(res["level"], "green", "Should trigger green due to policy bottom exemption")
        self.assertLess(res["score"], 40, "Score should be < 40 during policy bottom")
        self.assertIn("政策底", res["breakdown"]["technical_overbought"]["reason"])

    def test_wechat_message_formatting(self):
        mock_rec = {
            "score": 85,
            "level_name": "红色预警【绝壁顶】",
            "lead_time": "T+0 ～ T+2 个交易日",
            "news_title": "经济日报金观平：让居民通过股票、基金也能赚到钱",
            "news_source": "《经济日报》头版评论",
            "action_guide": ["锁死买入按键", "次日逢高止盈减仓"]
        }
        msg = format_risk_alert_wx_message(mock_rec)
        self.assertIn("OM-STW 股市见顶与舆情风控预警", msg)
        self.assertIn("红色预警【绝壁顶】", msg)
        self.assertIn("T+0 ～ T+2 个交易日", msg)
        self.assertIn("锁死买入按键", msg)

    def test_analyze_and_record_persistence(self):
        async def run_async():
            res = await analyze_news_with_model(
                news_title="自动化测试：外资爆买A股狂欢",
                news_source="央视《新闻联播》",
                news_content="测试正文：报道掀起全网讨论热潮",
                model_id="om_stw",
                user_id=1,
                trigger_type="manual_input",
                push_to_wx=False
            )
            self.assertIn("id", res)
            self.assertIn("score", res)
            self.assertIn("level", res)

            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM risk_analysis_records WHERE id = ?", (res["id"],)).fetchone()
            conn.close()
            self.assertIsNotNone(row, "Record should be saved to database")
            self.assertEqual(row["news_title"], "自动化测试：外资爆买A股狂欢")

        asyncio.run(run_async())

    def test_daily_risk_market_records_flow(self):
        async def run_flow():
            test_date = "2099-01-15"
            # 1. Record pre-market risk
            rec = await record_daily_pre_market_risk(
                user_id=1,
                trade_date=test_date,
                pre_market_score=68,
                pre_market_level="orange",
                pre_market_level_name="🟠 变盘预警【多空博弈】",
                lead_time="T+1 ～ T+3 个交易日",
                trigger_signals=["经济日报头版社论", "BIAS20超买"],
                defensive_guide=["降低股票仓位至5成以下", "高抛低吸锁定利润"],
                news_title="测试：经济日报提示防范市场短线过热风险",
                news_source="《经济日报》",
                summary="技术面处于过热分化区，注意高位震荡"
            )
            self.assertEqual(rec["trade_date"], test_date)
            self.assertEqual(rec["pre_market_score"], 68)

            # 2. Record market close
            close_indices = {
                "sh_close": 3320.50,
                "sh_change_pct": -1.15,
                "sz_close": 10450.20,
                "sz_change_pct": -1.45,
                "cy_close": 2180.10,
                "cy_change_pct": -1.88,
                "kc_close": 980.50,
                "kc_change_pct": -1.10,
                "hs300_close": 3950.00,
                "hs300_change_pct": -1.20,
                "bj50_close": 1250.00,
                "bj50_change_pct": -0.80,
                "turnover_billion": 1780.0
            }
            records_list = await record_daily_market_close(
                user_id=1,
                trade_date=test_date,
                indices_data=close_indices
            )
            self.assertTrue(len(records_list) > 0)
            updated = records_list[0]
            self.assertEqual(updated["trade_date"], test_date)
            self.assertIn("🎯 风险预警命中", updated["validation_status"])
            self.assertEqual(updated["sh_close"], 3320.50)

            # 3. Get records
            records = await get_daily_risk_market_records(user_id=1, limit=50)
            target = next((r for r in records if r["trade_date"] == test_date), None)
            self.assertIsNotNone(target)
            self.assertEqual(target["pre_market_score"], 68)
            self.assertEqual(target["sh_close"], 3320.50)

        asyncio.run(run_flow())

    def test_daily_risk_analytics_summary(self):
        async def run_analytics():
            res = await get_daily_risk_analytics_summary(user_id=1)
            self.assertGreater(res["total_days"], 10, "Should have continuous historical days")
            self.assertIn("accuracy_rate", res)
            self.assertGreaterEqual(res["accuracy_rate"], 70.0, "Accuracy rate should be high")
            self.assertIn("pearson_correlation", res)
            self.assertLess(res["pearson_correlation"], 0, "Risk score and return should have negative correlation")
            self.assertIn("tier_stats", res)
            self.assertIn("red", res["tier_stats"])
            self.assertIn("attribution_counts", res)
            self.assertIn("hit", res["attribution_counts"])

    def test_closed_record_immutability_and_next_day_targeting(self):
        """
        Verify that:
        1. Historical closed records (sh_close recorded) are FROZEN and cannot be overwritten by pre-market risk calls.
        2. Evening tasks target the next trading day instead of overwriting today's closed day.
        """
        async def run_immutability_test():
            test_date = "2099-09-02"
            # 1. Create original daytime premarket risk snapshot (e.g. 42 points)
            rec1 = await record_daily_pre_market_risk(
                user_id=1,
                trade_date=test_date,
                pre_market_score=42,
                pre_market_level="yellow",
                pre_market_level_name="🟡 黄色注意【分歧加剧】",
                news_title="韩国检方追加起诉尹锡悦未申报“夫人收受财物”"
            )
            self.assertEqual(rec1["pre_market_score"], 42)

            # 2. Market closes at 15:05 and records closing index
            await record_daily_market_close(
                user_id=1,
                trade_date=test_date,
                indices_data={"sh_close": 3875.60, "sh_change_pct": -0.41}
            )

            # 3. Evening task (e.g. at 20:30) attempts to snapshot 50 points on the same closed date
            rec2 = await record_daily_pre_market_risk(
                user_id=1,
                trade_date=test_date,
                pre_market_score=50,
                pre_market_level="yellow",
                pre_market_level_name="🟡 黄色注意【分歧加剧】",
                news_title="我国今年以来已批准上市创新药59个"
            )

            # The score MUST REMAIN 42, NOT overwritten to 50!
            self.assertEqual(rec2["pre_market_score"], 42, "Historical closed record pre_market_score must NOT be overwritten!")
            self.assertEqual(rec2["news_title"], "韩国检方追加起诉尹锡悦未申报“夫人收受财物”")

        asyncio.run(run_immutability_test())


if __name__ == "__main__":
    unittest.main()
