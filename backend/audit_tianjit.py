"""Reproducible local-cache audit. No orders or account changes."""
import json
from pathlib import Path

from services.strategy.strategy_templates import get_preset_template
from services.strategy.tianjit_strategy import run_tianjit_backtest


HOLDINGS = [
    ("600460", "士兰微", "stock", 2500, 30.34, 25.87),
    ("002466", "天齐锂业", "stock", 900, 45.35, 34.60),
    ("600703", "三安光电", "stock", 11400, 13.23, 15.36),
    ("519674", "银河创新混合A", "fund", 5273.58, 11.6316, 6.5476),
    ("007872", "金信稳健策略混合A", "fund", 33950, 3.3041, 1.7500),
    ("017811", "东方人工智能主题混合C", "fund", 112286, 3.0817, 1.0599),
]


def main():
    settings = {"calendar_bazi_day_master": "辛金", "calendar_bazi_year": "壬申", "calendar_bazi_day": "辛未"}
    result = {"source": "User screenshot dated 2026-09-04 and unverified local historical caches",
              "holdings": [], "backtests": [], "scenarios": []}
    for code, name, kind, shares, price, cost in HOLDINGS:
        result["holdings"].append({"code": code, "name": name, "value": round(shares * price, 2),
                                   "cost": round(shares * cost, 2), "unrealized": round(shares * (price - cost), 2)})
        data = json.loads((Path(__file__).parent / "cache" / f"{kind}_history" / f"{code}.json").read_text())
        for start in ("2025-01-01", "2026-01-01"):
            history = [row for row in data["history"] if start <= row["date"] <= "2026-09-04"]
            cfg = dict(get_preset_template("tianjit", kind)["default_config"])
            cfg["allow_additional_capital"] = False
            fees = {"subscription_rate": 0.0 if code == "017811" else 0.001} if kind == "fund" else None
            test = run_tianjit_backtest(history, cfg, settings, fees, is_stock=kind == "stock", asset_type=kind)
            result["backtests"].append({"code": code, "start": history[0]["date"], "end": history[-1]["date"],
                                        "metrics": test["metrics"]})
    total = sum(item["value"] for item in result["holdings"])
    result["total_value"] = round(total, 2)
    result["total_cost"] = round(sum(item["cost"] for item in result["holdings"]), 2)
    result["screenshot_total_difference"] = round(787033.13 - total, 2)
    for item in result["holdings"]:
        item["weight_pct"] = round(item["value"] / total * 100, 2)
    # Sensitivity only: constant monthly shocks, no probabilistic forecast or historical fitting.
    for i, month in enumerate(("2026-09", "2026-10", "2026-11", "2026-12", "2027-01", "2027-02", "2027-03"), 1):
        row = {"month": month}
        for label, rate in (("down_5pct", -0.05), ("flat", 0), ("up_5pct", 0.05)):
            row[label] = {"month_pnl": round(total * (1 + rate) ** (i - 1) * rate, 2),
                          "cumulative_pnl": round(total * ((1 + rate) ** i - 1), 2)}
        result["scenarios"].append(row)
    output = Path(__file__).parent.parent / "reports" / "tianjit-audit-2026-09-06.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
