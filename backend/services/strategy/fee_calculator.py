"""
Fund Fee Calculator and Tiered Rules Parser.
Handles:
1. Fetching & parsing fund subscription and redemption fee rates from Eastmoney.
2. Tiered redemption fee calculation based on natural holding days (FIFO).
3. Standard Alipay/Regulatory defaults.
"""

import httpx
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, date

# Standard CSRC regulatory default redemption fee tiers for non-money funds
DEFAULT_REDEMPTION_TIERS = [
    {"min_days": 0, "max_days": 6, "rate": 0.015, "label": "小于7天 (1.50% 惩罚性费率)"},
    {"min_days": 7, "max_days": 29, "rate": 0.005, "label": "7天至29天 (0.50%)"},
    {"min_days": 30, "max_days": 364, "rate": 0.0025, "label": "30天至364天 (0.25%)"},
    {"min_days": 365, "max_days": 999999, "rate": 0.0, "label": "1年及以上 (0.00% 免赎回费)"}
]

# Standard Alipay discount for subscription fee (A-class usually 0.1% ~ 0.15%, C-class 0.0%)
DEFAULT_SUBSCRIPTION_RATE = 0.001  # 0.10% (1折)


async def fetch_fund_fee_structure(fund_code: str) -> Dict[str, Any]:
    """
    Fetch and parse real fee structures for a specific fund from Eastmoney.
    Returns:
    {
        "code": "000001",
        "subscription_rate": 0.0015, # Alipay discount or default
        "original_subscription_rate": 0.015,
        "is_c_share": False,
        "redemption_tiers": [
            {"min_days": 0, "max_days": 6, "rate": 0.015, "label": "小于7天 (1.50%)"},
            ...
        ]
    }
    """
    url = f"https://fundf10.eastmoney.com/jjfl_{fund_code}.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://fund.eastmoney.com/{fund_code}.html"
    }

    sub_rate = DEFAULT_SUBSCRIPTION_RATE
    orig_sub_rate = 0.015
    is_c_share = fund_code.endswith(('C', 'c')) or False
    parsed_redemption_tiers = []

    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            html = resp.content.decode('utf-8', errors='replace')

            # Also check fund basic info JS for discount rate
            js_url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
            js_resp = await client.get(js_url, headers=headers)
            js_text = js_resp.content.decode('utf-8', errors='replace')

            name_match = re.search(r'var fS_name = \"(.*?)\";', js_text)
            fund_name = name_match.group(1) if name_match else ""
            if fund_name and ('C' in fund_name or 'c' in fund_name):
                is_c_share = True

            rate_match = re.search(r'var fund_Rate = \"(.*?)\";', js_text)
            source_rate_match = re.search(r'var fund_sourceRate = \"(.*?)\";', js_text)

            if source_rate_match and source_rate_match.group(1):
                try:
                    orig_sub_rate = float(source_rate_match.group(1).replace('%', '')) / 100.0
                except Exception:
                    pass

            if rate_match and rate_match.group(1):
                try:
                    sub_rate = float(rate_match.group(1).replace('%', '')) / 100.0
                except Exception:
                    pass
            elif is_c_share:
                sub_rate = 0.0
            else:
                # Alipay 1-discount usually 0.1% ~ 0.15%
                sub_rate = min(0.0015, orig_sub_rate * 0.1)

            # Parse Redemption fee table from HTML
            tables = re.findall(r'<table.*?>(.*?)</table>', html, re.DOTALL)
            for t in tables:
                if '赎回费率' in t:
                    rows = re.findall(r'<tr.*?>(.*?)</tr>', t, re.DOTALL)
                    for r in rows:
                        cells = re.findall(r'<t[dh].*?>(.*?)</t[dh]>', r, re.DOTALL)
                        clean_cells = [re.sub(r'<.*?>', '', c).strip() for c in cells]
                        if len(clean_cells) >= 2 and ('天' in clean_cells[0] or '年' in clean_cells[0]):
                            period_str, rate_str = clean_cells[0], clean_cells[1]
                            tier = parse_redemption_period_and_rate(period_str, rate_str)
                            if tier:
                                parsed_redemption_tiers.append(tier)

    except Exception as e:
        print(f"[FeeCalculator] Error fetching fee for fund {fund_code}: {e}")

    # Fallback to standard tiers if parsing returned empty
    if not parsed_redemption_tiers:
        parsed_redemption_tiers = DEFAULT_REDEMPTION_TIERS.copy()
        if is_c_share:
            # C share usually 0% after 7 days
            parsed_redemption_tiers = [
                {"min_days": 0, "max_days": 6, "rate": 0.015, "label": "小于7天 (1.50%)"},
                {"min_days": 7, "max_days": 999999, "rate": 0.0, "label": "大于等于7天 (0.00% 免赎回费)"}
            ]

    # Ensure tiers are sorted by min_days
    parsed_redemption_tiers.sort(key=lambda x: x["min_days"])

    return {
        "code": fund_code,
        "subscription_rate": sub_rate,
        "original_subscription_rate": orig_sub_rate,
        "is_c_share": is_c_share,
        "redemption_tiers": parsed_redemption_tiers
    }


def parse_redemption_period_and_rate(period_str: str, rate_str: str) -> Optional[Dict[str, Any]]:
    """Parse text like '小于7天', '大于等于7天，小于等于29天', '1.50%' into min_days, max_days, rate."""
    try:
        rate_val = float(rate_str.replace('%', '').strip()) / 100.0
    except Exception:
        return None

    min_days = 0
    max_days = 999999

    # Check for days / years
    if '小于7天' in period_str or '小于等于6天' in period_str:
        min_days = 0
        max_days = 6
    elif '大于等于7天' in period_str and ('小于' in period_str or '小于等于' in period_str):
        min_days = 7
        match_max = re.search(r'小于[等于]?(\d+)天', period_str)
        if match_max:
            max_days = int(match_max.group(1))
            if '小于等于' not in period_str and f'小于{max_days}天' in period_str:
                max_days -= 1
        elif re.search(r'小于[等于]?(\d+)年', period_str):
            match_yr = re.search(r'小于[等于]?(\d+)年', period_str)
            if match_yr:
                max_days = int(match_yr.group(1)) * 365
    elif '大于等于30天' in period_str and ('小于' in period_str or '小于等于' in period_str):
        min_days = 30
        match_max = re.search(r'小于[等于]?(\d+)天', period_str)
        if match_max:
            max_days = int(match_max.group(1))
            if '小于等于' not in period_str and f'小于{max_days}天' in period_str:
                max_days -= 1
        else:
            match_yr = re.search(r'小于[等于]?(\d+)年', period_str)
            if match_yr:
                max_days = int(match_yr.group(1)) * 365 - 1
    elif '大于等于' in period_str and '年' in period_str and ('小于' in period_str or '小于等于' in period_str):
        match_min_yr = re.search(r'大于等于(\d+)年', period_str)
        match_max_yr = re.search(r'小于[等于]?(\d+)年', period_str)
        if match_min_yr:
            min_days = int(match_min_yr.group(1)) * 365
        if match_max_yr:
            max_days = int(match_max_yr.group(1)) * 365 - 1
    elif '大于等于' in period_str:
        match_min_day = re.search(r'大于等于(\d+)天', period_str)
        match_min_yr = re.search(r'大于等于(\d+)年', period_str)
        if match_min_day:
            min_days = int(match_min_day.group(1))
        elif match_min_yr:
            min_days = int(match_min_yr.group(1)) * 365
        max_days = 999999
    elif '小于' in period_str:
        match_max_day = re.search(r'小于[等于]?(\d+)天', period_str)
        match_max_yr = re.search(r'小于[等于]?(\d+)年', period_str)
        min_days = 0
        if match_max_day:
            max_days = int(match_max_day.group(1))
        elif match_max_yr:
            max_days = int(match_max_yr.group(1)) * 365
    else:
        return None

    return {
        "min_days": min_days,
        "max_days": max_days,
        "rate": rate_val,
        "label": f"{period_str} ({rate_str})"
    }


def get_redemption_fee_rate(holding_days: int, tiers: List[Dict[str, Any]]) -> float:
    """Find applicable redemption fee rate for given natural holding days."""
    if not tiers:
        tiers = DEFAULT_REDEMPTION_TIERS

    for tier in tiers:
        min_d = tier.get("min_days", 0)
        max_d = tier.get("max_days", 999999)
        if min_d <= holding_days <= max_d:
            return float(tier.get("rate", 0.0))

    return 0.0 if holding_days >= 7 else 0.015


def calculate_holding_days(buy_confirm_date: str, sell_apply_date: str) -> int:
    """Calculate natural holding days between confirmation date and redemption apply date."""
    try:
        d1 = datetime.strptime(buy_confirm_date.split()[0], "%Y-%m-%d").date()
        d2 = datetime.strptime(sell_apply_date.split()[0], "%Y-%m-%d").date()
        return max(0, (d2 - d1).days)
    except Exception:
        return 0


def calculate_subscription(amount: float, nav: float, sub_rate: float) -> Dict[str, float]:
    """
    Standard China Mutual Fund Subscription calculation:
    Net Subscription Amount = Amount / (1 + Sub_Rate)
    Subscription Fee = Amount - Net Subscription Amount
    Confirmed Shares = Net Subscription Amount / NAV
    """
    if amount <= 0 or nav <= 0:
        return {"gross_amount": 0.0, "net_amount": 0.0, "fee": 0.0, "shares": 0.0}

    net_amount = amount / (1.0 + sub_rate)
    fee = amount - net_amount
    shares = round(net_amount / nav, 4)
    return {
        "gross_amount": amount,
        "net_amount": round(net_amount, 2),
        "fee": round(fee, 2),
        "shares": shares
    }


def calculate_redemption(shares: float, nav: float, red_rate: float) -> Dict[str, float]:
    """
    Standard China Mutual Fund Redemption calculation:
    Gross Redemption Amount = Shares * NAV
    Redemption Fee = Gross Redemption Amount * Red_Rate
    Net Redemption Amount = Gross Redemption Amount - Fee
    """
    if shares <= 0 or nav <= 0:
        return {"gross_amount": 0.0, "fee": 0.0, "net_amount": 0.0}

    gross_amount = shares * nav
    fee = gross_amount * red_rate
    net_amount = gross_amount - fee
    return {
        "gross_amount": round(gross_amount, 2),
        "fee": round(fee, 2),
        "net_amount": round(net_amount, 2),
        "rate": red_rate
    }
