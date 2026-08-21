import httpx
import re
import json
import sqlite3
import datetime as dt
from database import DB_PATH
from datetime import datetime
from services.trading_calendar import is_trading_time, is_trading_day


def format_stock_code(code: str) -> str:
    """Add sh/sz prefix for Sina Finance API."""
    code = code.strip()
    if code.startswith(("6", "5", "9")):
        return f"sh{code}"
    return f"sz{code}"


async def fetch_stock_data(codes: list) -> dict:
    """Fetch real-time stock data from Sina Finance."""
    if not codes:
        return {}

    url = f"http://hq.sinajs.cn/list={','.join(codes)}"
    headers = {
        "Referer": "http://finance.sina.com.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            text = resp.content.decode('gbk', errors='replace')

            result = {}
            for line in text.strip().split('\n'):
                match = re.search(r'var hq_str_(.*?)="(.*?)";', line)
                if match:
                    code = match.group(1)
                    data_str = match.group(2)
                    if not data_str:
                        continue
                    fields = data_str.split(',')
                    if len(fields) > 30:
                        name = fields[0]
                        open_price = float(fields[1]) if fields[1] else 0.0
                        prev_close = float(fields[2]) if fields[2] else 0.0
                        current = float(fields[3]) if fields[3] else 0.0
                        high = float(fields[4]) if fields[4] else 0.0
                        low = float(fields[5]) if fields[5] else 0.0

                        # 针对早盘 9:15-9:25 集合竞价或尚未成交（current == 0）时的现价回退与涨跌幅修正
                        real_current = current
                        if real_current <= 0:
                            if open_price > 0:
                                real_current = open_price
                            elif prev_close > 0:
                                real_current = prev_close

                        # 计算涨跌幅与涨跌额：如果尚未有成交价（current <= 0）
                        if current <= 0 and open_price <= 0:
                            change_pct = 0.0
                            change_amount = 0.0
                        elif current <= 0 and open_price > 0:
                            change_pct = (open_price - prev_close) / prev_close * 100 if prev_close > 0 else 0.0
                            change_amount = open_price - prev_close
                        else:
                            change_pct = (current - prev_close) / prev_close * 100 if prev_close > 0 else 0.0
                            change_amount = current - prev_close

                        result[code] = {
                            "name": name,
                            "open": open_price,
                            "prev_close": prev_close,
                            "current": real_current,
                            "raw_current": current,
                            "high": high,
                            "low": low,
                            "change_pct": change_pct,
                            "change_amount": change_amount
                        }
            return result
    except Exception as e:
        print(f"[MarketService] Error fetching stock data: {e}")
        return {}


def _determine_fund_nav_status(update_time: str, now: datetime = None) -> tuple:
    """
    Determine whether fund data is official NAV ('官方净值') or real-time estimate ('实时估值').

    Rules:
    1. On non-trading days (weekends/holidays), it is official NAV ('官方净值').
    2. On trading days:
       - Before 18:00 (6:00 PM), the market is open / in trading / just closed, and official NAV for today has not been released yet by fund managers. Intraday numbers are estimated NAV ('实时估值').
       - After 18:00 (6:00 PM), if update_time matches today's date, official NAV has been released ('官方净值'); otherwise it is still estimated ('实时估值').
    """
    if now is None:
        now = datetime.now()

    if not is_trading_day(now):
        return True, "官方净值"

    today_str = now.strftime("%Y-%m-%d")
    update_date = update_time.split()[0] if update_time else ''

    if now.time() < dt.time(18, 0):
        return False, "实时估值"
    else:
        is_updated = (update_date == today_str)
        return is_updated, "官方净值" if is_updated else "实时估值"


async def fetch_fund_data(codes: list) -> dict:
    """Fetch fund estimated and official NAV from Sina Finance API with EastMoney fallback."""
    result = {}
    if not codes:
        return result

    sina_codes = []
    for c in codes:
        sina_codes.append(f"fu_{c}")
        sina_codes.append(f"f_{c}")
        
    url = f"http://hq.sinajs.cn/list={','.join(sina_codes)}"
    headers = {
        "Referer": "http://finance.sina.com.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, headers=headers)
            text = resp.content.decode('gbk', errors='replace')
            
            fu_data = {}
            f_data = {}
            for line in text.strip().split('\n'):
                match_fu = re.search(r'var hq_str_fu_(.*?)=\"(.*?)\";', line)
                if match_fu:
                    fu_data[match_fu.group(1)] = match_fu.group(2)
                    continue
                match_f = re.search(r'var hq_str_f_(.*?)=\"(.*?)\";', line)
                if match_f:
                    f_data[match_f.group(1)] = match_f.group(2)
            
            for code in codes:
                if code not in fu_data:
                    continue
                fu_fields = fu_data[code].split(',')
                f_fields = f_data.get(code, "").split(',')
                
                if len(fu_fields) >= 8:
                    name = fu_fields[0]
                    est_nav = float(fu_fields[2]) if fu_fields[2] else 0.0
                    est_change_pct = float(fu_fields[6]) if fu_fields[6] else 0.0
                    est_time = fu_fields[1]
                    
                    official_nav = est_nav
                    official_prev_nav = est_nav
                    official_date = ""
                    
                    if len(f_fields) >= 5:
                        if f_fields[0]: name = f_fields[0]
                        official_nav = float(f_fields[1]) if f_fields[1] else est_nav
                        official_prev_nav = float(f_fields[3]) if f_fields[3] else official_nav
                        official_date = f_fields[4]
                    
                    if not is_trading_day(now):
                        is_updated = True
                    else:
                        is_updated = (official_date == today_str)

                    if is_updated:
                        nav_type = "官方净值"
                        current_nav = official_nav
                        prev_nav = official_prev_nav
                        change_pct = (current_nav - prev_nav) / prev_nav * 100 if prev_nav > 0 else 0.0
                        update_time = official_date
                    else:
                        nav_type = "实时估值"
                        current_nav = est_nav
                        prev_nav = official_nav if official_nav > 0 else est_nav
                        change_pct = est_change_pct
                        update_time = est_time
                    
                    result[code] = {
                        "name": name,
                        "current_nav": current_nav,
                        "last_nav": prev_nav,
                        "change_pct": change_pct,
                        "prev_nav": prev_nav,
                        "update_time": update_time,
                        "is_updated": is_updated,
                        "nav_type": nav_type
                    }
        except Exception as e:
            print(f"[MarketService] Error fetching Sina fund batch data: {e}")

        # Fallback for codes missing in Sina or missing name
        for code in codes:
            if code not in result or not result[code].get("name"):
                try:
                    em_url = f"https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx?m=1&key={code}"
                    em_resp = await client.get(em_url)
                    em_json = em_resp.json()
                    datas = em_json.get("Datas", [])
                    target = None
                    for d in datas:
                        if d.get("CODE") == code:
                            target = d
                            break
                    if not target and datas:
                        target = datas[0]
                    if target:
                        name = target.get("NAME") or target.get("SHORTNAME") or ""
                        base_info = target.get("FundBaseInfo") or {}
                        last_nav = float(base_info.get("DWJZ") or 0.0)
                        current_nav = last_nav
                        prev_nav = last_nav
                        update_time = base_info.get("FSRQ") or ""
                        is_updated, nav_type = _determine_fund_nav_status(update_time, now)
                        result[code] = {
                            "name": name,
                            "current_nav": current_nav,
                            "last_nav": last_nav,
                            "change_pct": 0.0,
                            "prev_nav": prev_nav,
                            "update_time": update_time,
                            "is_updated": is_updated,
                            "nav_type": nav_type
                        }
                except Exception as e:
                    print(f"[MarketService] Eastmoney fallback error for fund {code}: {e}")

    return result


async def auto_fix_fund_names_in_db():
    """Auto-repair existing database funds where name is code or missing."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM funds WHERE name = code OR name IS NULL OR TRIM(name) = ''")
        rows = cursor.fetchall()
        if rows:
            codes = [row['code'] for row in rows]
            f_data = await fetch_fund_data(codes)
            for row in rows:
                c = row['code']
                real_name = f_data.get(c, {}).get("name")
                if real_name and real_name != c:
                    cursor.execute("UPDATE funds SET name = ? WHERE id = ?", (real_name, row['id']))
            conn.commit()
            print(f"[MarketService] Auto-repaired {len(rows)} fund names in database.")
        conn.close()
    except Exception as e:
        print(f"[MarketService] Error auto repairing fund names: {e}")


def _get_market_status() -> str:
    now = datetime.now()
    if not is_trading_day(now):
        return "非交易日"
    t = now.time()
    if t < dt.time(9, 15):
        return "待开盘"
    if is_trading_time(now):
        return "交易中"
    if t < dt.time(13, 0):
        return "午间休市"
    return "已收盘"


async def get_market_overview(user_id: int = 1) -> dict:
    """Get full market overview with P&L for all stocks and funds of a user."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM stocks WHERE user_id = ? ORDER BY id DESC", (user_id,))
    stocks = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT * FROM funds WHERE user_id = ? ORDER BY id DESC", (user_id,))
    funds = [dict(row) for row in cursor.fetchall()]

    conn.close()

    # Fetch market data
    sina_codes = [format_stock_code(s['code']) for s in stocks]
    stock_market_data = await fetch_stock_data(sina_codes)

    fund_codes = [f['code'] for f in funds]
    fund_market_data = await fetch_fund_data(fund_codes)

    total_day_profit = 0.0
    total_profit = 0.0

    # Enrich stocks
    enriched_stocks = []
    for s in stocks:
        sina_code = format_stock_code(s['code'])
        s_data = stock_market_data.get(sina_code)
        if s_data:
            current_price = s_data['current']
            prev_close = s_data['prev_close']
            day_profit_val = (current_price - prev_close) * s['shares']
            total_profit_val = (current_price - s['cost_price']) * s['shares']
            total_profit_pct = (current_price - s['cost_price']) / s['cost_price'] * 100 if s['cost_price'] else 0

            s['current_price'] = current_price
            s['prev_close'] = prev_close
            s['change_pct'] = s_data['change_pct']
            s['change_amount'] = s_data['change_amount']
            s['high'] = s_data['high']
            s['low'] = s_data['low']
            s['day_profit'] = day_profit_val
            s['total_profit'] = total_profit_val
            s['total_profit_pct'] = total_profit_pct
            if not s.get('name') and s_data.get('name'):
                s['name'] = s_data['name']

            if s['is_holding']:
                total_day_profit += day_profit_val
                total_profit += total_profit_val
        else:
            cost = s.get('cost_price', 0)
            s['current_price'] = cost
            s['prev_close'] = cost
            s['change_pct'] = 0.0
            s['change_amount'] = 0.0
            s['high'] = cost
            s['low'] = cost
            s['day_profit'] = 0.0
            s['total_profit'] = 0.0
            s['total_profit_pct'] = 0.0
        enriched_stocks.append(s)

    # Enrich funds
    enriched_funds = []
    for f in funds:
        f_data = fund_market_data.get(f['code'])
        if f_data:
            current_nav = f_data['current_nav']
            prev_nav = f_data['prev_nav']
            day_profit_val = (current_nav - prev_nav) * f['shares']
            total_profit_val = (current_nav - f['cost_nav']) * f['shares']
            total_profit_pct = (current_nav - f['cost_nav']) / f['cost_nav'] * 100 if f['cost_nav'] else 0

            f['current_nav'] = current_nav
            f['prev_nav'] = prev_nav
            f['change_pct'] = f_data['change_pct']
            f['day_profit'] = day_profit_val
            f['total_profit'] = total_profit_val
            f['total_profit_pct'] = total_profit_pct
            f['update_time'] = f_data.get('update_time', '')
            f['is_updated'] = f_data.get('is_updated', False)
            f['nav_type'] = f_data.get('nav_type', '实时估值')

            if (not f.get('name') or f.get('name') == f.get('code')) and f_data.get('name'):
                f['name'] = f_data['name']

            if f['is_holding']:
                total_day_profit += day_profit_val
                total_profit += total_profit_val
        else:
            cost_nav = f.get('cost_nav', 0)
            f['current_nav'] = cost_nav
            f['prev_nav'] = cost_nav
            f['change_pct'] = 0.0
            f['day_profit'] = 0.0
            f['total_profit'] = 0.0
            f['total_profit_pct'] = 0.0
            f['update_time'] = ''
            f['is_updated'] = False
            f['nav_type'] = '实时估值'
        enriched_funds.append(f)

    # Calculate holding assets and return rates
    stock_asset = sum(s['current_price'] * s['shares'] for s in enriched_stocks if s['is_holding'])
    stock_cost = sum(s['cost_price'] * s['shares'] for s in enriched_stocks if s['is_holding'])
    stock_profit = sum(s['total_profit'] for s in enriched_stocks if s['is_holding'])
    stock_day_profit = sum(s['day_profit'] for s in enriched_stocks if s['is_holding'])
    stock_profit_pct = (stock_profit / stock_cost * 100) if stock_cost > 0 else 0.0

    fund_asset = sum(f['current_nav'] * f['shares'] for f in enriched_funds if f['is_holding'])
    fund_cost = sum(f['cost_nav'] * f['shares'] for f in enriched_funds if f['is_holding'])
    fund_profit = sum(f['total_profit'] for f in enriched_funds if f['is_holding'])
    fund_day_profit = sum(f['day_profit'] for f in enriched_funds if f['is_holding'])
    fund_profit_pct = (fund_profit / fund_cost * 100) if fund_cost > 0 else 0.0

    total_asset = stock_asset + fund_asset
    total_cost = stock_cost + fund_cost
    total_profit_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0.0


    # Save today snapshot
    today_str = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO history_profits (user_id, date, stock_profit, fund_profit, total_profit, stock_asset, fund_asset, total_asset)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, date) DO UPDATE SET
        stock_profit=excluded.stock_profit,
        fund_profit=excluded.fund_profit,
        total_profit=excluded.total_profit,
        stock_asset=excluded.stock_asset,
        fund_asset=excluded.fund_asset,
        total_asset=excluded.total_asset
    ''', (user_id, today_str, stock_profit, fund_profit, total_profit, stock_asset, fund_asset, total_asset))
    conn.commit()
    conn.close()

    return {
        "stocks": enriched_stocks,
        "funds": enriched_funds,
        "summary": {
            "total_day_profit": total_day_profit,
            "total_profit": total_profit,
            "total_asset": total_asset,
            "total_cost": total_cost,
            "total_profit_pct": total_profit_pct,
            "stock_asset": stock_asset,
            "stock_cost": stock_cost,
            "stock_profit": stock_profit,
            "stock_profit_pct": stock_profit_pct,
            "stock_day_profit": stock_day_profit,
            "fund_asset": fund_asset,
            "fund_cost": fund_cost,
            "fund_profit": fund_profit,
            "fund_profit_pct": fund_profit_pct,
            "fund_day_profit": fund_day_profit,
            "market_status": _get_market_status(),
            "last_update": datetime.now().strftime("%H:%M:%S")
        }
    }
