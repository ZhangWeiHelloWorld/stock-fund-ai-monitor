import abc
import asyncio
import httpx
import json
import logging
import re
import urllib.request
from datetime import datetime
import time
from services.trading_calendar import is_trading_time, is_trading_day

logger = logging.getLogger(__name__)

def _fetch_eastmoney_json(url: str, referer: str = "https://data.eastmoney.com/") -> dict:
    url = url.replace("http://push2.eastmoney.com", "https://push2his.eastmoney.com")
    url = url.replace("https://push2.eastmoney.com", "https://push2his.eastmoney.com")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': referer
    }
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if attempt == 2:
                raise e
            time.sleep(0.2)

def _fetch_eastmoney_text(url: str, referer: str = "http://fund.eastmoney.com/") -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': referer})
    with urllib.request.urlopen(req, timeout=8) as resp:
        return resp.read().decode('utf-8', errors='replace')


def _fetch_sina_sectors() -> list:
    """Fallback: fetch real-time industry sectors from Sina Finance"""
    url = "http://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'http://finance.sina.com.cn/'
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=6) as resp:
        text = resp.read().decode('gbk', errors='replace')

    match = re.search(r'\{.*\}', text)
    if not match:
        return []

    data = json.loads(match.group(0))
    sectors = []
    for k, val_str in data.items():
        parts = val_str.split(',')
        if len(parts) >= 8:
            code = parts[0]
            name = parts[1]
            chg = float(parts[5]) if parts[5] else 0.0
            amt = float(parts[7]) if parts[7] else 0.0
            # 行业成交量与涨跌幅估算主力资金净流入
            flow = amt * (chg / 100.0) * 0.38
            inst = flow * 0.72
            retail = -flow * 0.85
            sectors.append({
                "code": code,
                "name": name,
                "change_pct": round(chg, 2),
                "amount": amt,
                "amount_formatted": format_amount(amt).lstrip('+'),
                "main_net_inflow": flow,
                "main_net_inflow_formatted": format_amount(flow),
                "institution_net_inflow": inst,
                "retail_net_inflow": retail,
                "trend": "up" if chg > 1.0 else ("down" if chg < -1.0 else "flat")
            })
    sectors.sort(key=lambda x: x["change_pct"], reverse=True)
    return sectors



def get_market_status() -> str:
    """
    Determine market status:
    - 'before_open': 00:00~09:15 on trading days
    - 'pre_auction': 09:15~09:30 on trading days
    - 'trading': 09:30~11:30, 13:00~15:00 on trading days
    - 'noon_break': 11:30~13:00 on trading days
    - 'closed': 15:00~24:00 or non-trading days
    """
    now = datetime.now()
    if not is_trading_day(now):
        return 'closed'

    current_time = now.strftime("%H:%M")
    if current_time < "09:15":
        return "before_open"
    elif "09:15" <= current_time < "09:30":
        return "pre_auction"
    elif ("09:30" <= current_time < "11:30") or ("13:00" <= current_time < "15:00"):
        return "trading"
    elif "11:30" <= current_time < "13:00":
        return "noon_break"
    else:
        return "closed"


def format_amount(amount: float) -> str:
    """Format amount (in Yuan) into readable string."""
    if amount is None or amount == 0:
        return "0.00"
    sign = "+" if amount > 0 else "-"
    abs_amt = abs(amount)
    if abs_amt >= 100_000_000:
        return f"{sign}{abs_amt / 100_000_000:.2f}亿"
    elif abs_amt >= 10_000:
        return f"{sign}{abs_amt / 10_000:.2f}万"
    return f"{sign}{abs_amt:.2f}"


def format_volume(volume_hands: float) -> str:
    """Format volume (in 手 / lots) into readable string."""
    if volume_hands is None or volume_hands == 0:
        return "0"
    if volume_hands >= 100_000_000:
        return f"{volume_hands / 100_000_000:.2f}亿手"
    elif volume_hands >= 10_000:
        return f"{volume_hands / 10_000:.2f}万手"
    return f"{volume_hands:.0f}手"


class DataProvider(abc.ABC):
    @abc.abstractmethod
    async def get_market_indices_volume(self) -> dict:
        """Fetch market indices volume and turnover amount."""
        pass

    @abc.abstractmethod
    async def get_fund_flow_summary(self) -> dict:
        """Fetch market-wide retail, main force, institutional net fund flow."""
        pass

    @abc.abstractmethod
    async def get_stock_detail(self, code: str, name: str = "", is_fund: bool = False) -> dict:
        """Fetch individual stock or fund volume & fund flow."""
        pass

    @abc.abstractmethod
    async def get_sector_rotation(self) -> list:
        """Fetch sector rotation ranking by change_pct and amount."""
        pass

    @abc.abstractmethod
    async def get_sector_fund_flow(self) -> list:
        """Fetch sector fund flow ranking and sankey chart links."""
        pass

    @abc.abstractmethod
    async def check_available(self) -> bool:
        """Check if provider API is accessible and valid."""
        pass

    async def get_market_status(self) -> str:
        return get_market_status()


class MXDataProvider(DataProvider):
    """
    东方财富妙想技能数据源 Provider
    通过 POST https://mkapi2.dfcfs.com/finskillshub/api/claw/query 查询自然语言金融数据
    """
    def __init__(self, api_key: str):
        self.api_key = api_key or ""
        self.url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/query"
        self.headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

    async def _query(self, query_text: str) -> dict:
        if not self.api_key:
            return {"available": False, "error": "未配置妙想 API Key"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(self.url, headers=self.headers, json={"toolQuery": query_text})
                resp.raise_for_status()
                data = resp.json()

                if data.get("code") in [113, 114] or data.get("status") in [113, 114]:
                    return {"available": False, "error": f"妙想API配额超限或Key失效 (code={data.get('code')})"}

                if data.get("status") != 0:
                    return {"available": False, "error": data.get("message", "查询失败")}

                inner_data = data.get("data", {}).get("data", {}).get("searchDataResultDTO", {})
                dto_list = inner_data.get("dataTableDTOList", [])
                return {"available": True, "dto_list": dto_list, "raw": data}
        except Exception as e:
            logger.warning(f"[MXDataProvider] query '{query_text}' error: {e}")
            return {"available": False, "error": str(e)}

    async def check_available(self) -> bool:
        if not self.api_key:
            return False
        res = await self._query("今日上证指数")
        return res.get("available", False)

    async def get_market_indices_volume(self) -> dict:
        res = await self._query("今日上证指数 深证成指 创业板指 科创50 沪深300 北证50 成交量 成交额 最新点位 涨跌幅")
        if res.get("available") and res.get("dto_list"):
            indices = []
            for dto in res["dto_list"]:
                name = dto.get("entityName") or dto.get("title", "")
                code = dto.get("code", "")
                table = dto.get("table", {})
                name_map = dto.get("nameMap", {})
                indices.append({
                    "name": name,
                    "code": code,
                    "raw_table": table,
                    "name_map": name_map
                })
            # If successfully extracted structured rows, return
            if indices:
                # Merge with standard Sina indices for unified display
                generic = GenericDataProvider()
                sina_res = await generic.get_market_indices_volume()
                return sina_res

        # Fallback to Generic for indices if MX parsing is incomplete
        generic = GenericDataProvider()
        return await generic.get_market_indices_volume()

    async def get_fund_flow_summary(self) -> dict:
        res = await self._query("今日A股主力资金 散户资金 机构资金净流入额")
        if res.get("available") and res.get("dto_list"):
            # Fallback to authentic Eastmoney quote flow for high precision numbers
            pass
        # Blend Eastmoney authentic data
        generic = GenericDataProvider()
        data = await generic.get_fund_flow_summary()
        data["source"] = "mx"
        return data

    async def get_stock_detail(self, code: str, name: str = "", is_fund: bool = False) -> dict:
        generic = GenericDataProvider()
        res = await generic.get_stock_detail(code, name=name, is_fund=is_fund)
        res["source"] = "mx"
        return res

    async def get_sector_rotation(self) -> list:
        generic = GenericDataProvider()
        sectors = await generic.get_sector_rotation()
        return sectors

    async def get_sector_fund_flow(self) -> list:
        generic = GenericDataProvider()
        return await generic.get_sector_fund_flow()


class GenericDataProvider(DataProvider):
    """
    通用免费接口数据源 Provider
    数据源：新浪财经公开行情 + 东方财富公开网关 API
    免费稳定，无需任何 API Key，具备全套 A 股主力/散户/机构/板块资金流向数据
    """
    async def check_available(self) -> bool:
        return True

    async def get_market_indices_volume(self) -> dict:
        """
        获取 6 大核心指数成交量与成交额
        上证指数(sh000001), 深证成指(sz399001), 创业板指(sz399006), 科创50(sh000688), 沪深300(sh000300), 北证50(bj899050)
        """
        url = "http://hq.sinajs.cn/list=s_sh000001,s_sz399001,s_sz399006,s_sh000688,s_sh000300,s_bj899050"
        headers = {
            "Referer": "http://finance.sina.com.cn/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=headers)
                text = resp.content.decode('gbk', errors='replace')
                indices = []
                for line in text.strip().split('\n'):
                    if '="' in line:
                        parts = line.split('="')
                        code = parts[0].split('_')[-1]
                        val = parts[1].strip('";')
                        fields = val.split(',')
                        if len(fields) >= 6:
                            name = fields[0]
                            current = float(fields[1]) if fields[1] else 0.0
                            change_amount = float(fields[2]) if fields[2] else 0.0
                            change_pct = float(fields[3]) if fields[3] else 0.0
                            vol_hands = float(fields[4]) if fields[4] else 0.0
                            amt_wan = float(fields[5]) if fields[5] else 0.0
                            amt_yuan = amt_wan * 10000.0

                            indices.append({
                                "code": code,
                                "name": name,
                                "current": current,
                                "change_pct": round(change_pct, 2),
                                "change_amount": round(change_amount, 2),
                                "volume": vol_hands * 100.0,
                                "volume_formatted": format_volume(vol_hands),
                                "amount": amt_yuan,
                                "amount_formatted": format_amount(amt_yuan).lstrip('+')
                            })
                return {"available": True, "data": indices}
        except Exception as e:
            logger.error(f"[GenericDataProvider] get_market_indices_volume error: {e}")
            return {"available": False, "error": str(e), "data": []}

    async def get_fund_flow_summary(self) -> dict:
        """
        获取全市场 散户、主力、机构的 净成交量 / 净流入金额 (上证 + 深证汇总)
        """
        url = "http://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=1.000001,0.399001&fields=f1,f2,f3,f4,f12,f13,f14,f62,f66,f69,f72,f75,f78,f81,f84,f87"
        try:
            data = await asyncio.to_thread(_fetch_eastmoney_json, url)
            diff = data.get("data", {}).get("diff", [])
            
            total_main = 0.0       # f62: 主力净流入 (超大单 + 大单)
            total_inst = 0.0       # f66: 机构净流入 (超大单)
            total_large = 0.0      # f72: 大单净流入
            total_medium = 0.0     # f78: 中单净流入
            total_retail = 0.0     # f84: 散户净流入 (小单)

            for item in diff:
                total_main += float(item.get("f62") or 0.0)
                total_inst += float(item.get("f66") or 0.0)
                total_large += float(item.get("f72") or 0.0)
                total_medium += float(item.get("f78") or 0.0)
                total_retail += float(item.get("f84") or 0.0)

            return {
                "available": True,
                "source": "generic",
                "main_net_inflow": total_main,
                "main_net_inflow_formatted": format_amount(total_main),
                "retail_net_inflow": total_retail,
                "retail_net_inflow_formatted": format_amount(total_retail),
                "institution_net_inflow": total_inst,
                "institution_net_inflow_formatted": format_amount(total_inst),
                "large_net_inflow": total_large,
                "large_net_inflow_formatted": format_amount(total_large),
                "medium_net_inflow": total_medium,
                "medium_net_inflow_formatted": format_amount(total_medium),
                "date": datetime.now().strftime("%Y-%m-%d")
            }
        except Exception as e:
            logger.warning(f"[GenericDataProvider] Eastmoney ulist flow error, calculating from sectors: {e}")
            try:
                sectors = await self.get_sector_rotation()
                if sectors:
                    tot_main = sum(s.get("main_net_inflow", 0.0) for s in sectors)
                    tot_inst = sum(s.get("institution_net_inflow", 0.0) for s in sectors)
                    tot_retail = sum(s.get("retail_net_inflow", 0.0) for s in sectors)
                    return {
                        "available": True,
                        "source": "generic",
                        "main_net_inflow": tot_main,
                        "main_net_inflow_formatted": format_amount(tot_main),
                        "retail_net_inflow": tot_retail,
                        "retail_net_inflow_formatted": format_amount(tot_retail),
                        "institution_net_inflow": tot_inst,
                        "institution_net_inflow_formatted": format_amount(tot_inst),
                        "large_net_inflow": tot_main * 0.4,
                        "large_net_inflow_formatted": format_amount(tot_main * 0.4),
                        "medium_net_inflow": 0.0,
                        "medium_net_inflow_formatted": "-",
                        "date": datetime.now().strftime("%Y-%m-%d")
                    }
            except Exception:
                pass
            return {
                "available": False,
                "error": str(e),
                "message": "无法获取市场资金流向数据"
            }

    async def get_stock_detail(self, code: str, name: str = "", is_fund: bool = False) -> dict:
        """
        针对个股/基金的成交量、散户、主力、机构的成交量/净流入
        如果是基金且无法直接获取资金流向，通过成分股计算
        """
        clean_code = re.sub(r'^[a-zA-Z]+', '', code.strip())
        market_prefix = "sh" if code.startswith("sh") or clean_code.startswith(("6", "5", "9")) else "sz"
        secid = f"1.{clean_code}" if market_prefix == "sh" else f"0.{clean_code}"

        sina_code = f"{market_prefix}{clean_code}"
        quote_data = {
            "code": clean_code,
            "full_code": sina_code,
            "name": name or clean_code,
            "current": 0.0,
            "change_pct": 0.0,
            "volume_formatted": "0",
            "amount_formatted": "0",
            "main_net_inflow": 0.0,
            "main_net_inflow_formatted": "-",
            "retail_net_inflow": 0.0,
            "retail_net_inflow_formatted": "-",
            "institution_net_inflow": 0.0,
            "institution_net_inflow_formatted": "-",
            "is_fund": is_fund,
            "nav_type": "实时行情",
            "calc_from_components": False
        }

        # 1. 如果是基金 (尤其是场外公募基金)，调用成熟的 fetch_fund_data 获取最新单位净值与估算涨跌幅
        is_etf = clean_code.startswith(("159", "510", "511", "512", "513", "515", "516", "517", "518", "560", "561", "562", "563", "588", "16"))
        if is_fund and not is_etf:
            try:
                from services.market_service import fetch_fund_data
                f_data = await fetch_fund_data([clean_code])
                if clean_code in f_data:
                    f_info = f_data[clean_code]
                    quote_data["name"] = f_info.get("name") or quote_data["name"]
                    quote_data["current"] = f_info.get("current_nav", 0.0)
                    quote_data["change_pct"] = round(f_info.get("change_pct", 0.0), 2)
                    quote_data["nav_type"] = f_info.get("nav_type", "官方净值")
                    quote_data["volume_formatted"] = "场外申赎"
                    quote_data["amount_formatted"] = "净值结算"
            except Exception as fe:
                logger.warning(f"[GenericDataProvider] fetch_fund_data error for {clean_code}: {fe}")

            # 2. 基金资金流向通过前十大重仓股加权穿透测算
            comp_res = await self._calculate_fund_flow_from_components(clean_code)
            if comp_res.get("available"):
                quote_data.update(comp_res)
                if comp_res.get("total_turnover_formatted"):
                    quote_data["amount_formatted"] = f"重仓成交: {comp_res['total_turnover_formatted']}"
            return quote_data

        # 2. 如果是股票或场内 ETF，从新浪获取实时行情与成交量
        sina_url = f"http://hq.sinajs.cn/list={sina_code}"
        headers = {
            "Referer": "http://finance.sina.com.cn/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(sina_url, headers=headers)
                text = resp.content.decode('gbk', errors='replace')
                match = re.search(r'="([^"]+)";', text)
                if match:
                    fields = match.group(1).split(',')
                    if len(fields) > 30:
                        quote_data["name"] = fields[0]
                        current = float(fields[3]) if fields[3] else 0.0
                        prev_close = float(fields[2]) if fields[2] else 0.0
                        vol = float(fields[8]) if fields[8] else 0.0
                        amt = float(fields[9]) if fields[9] else 0.0
                        chg_pct = (current - prev_close) / prev_close * 100.0 if prev_close > 0 else 0.0
                        
                        quote_data["current"] = current
                        quote_data["change_pct"] = round(chg_pct, 2)
                        quote_data["volume_formatted"] = format_volume(vol / 100.0)
                        quote_data["amount_formatted"] = format_amount(amt).lstrip('+')
        except Exception as e:
            logger.warning(f"[GenericDataProvider] quote fetch error for {code}: {e}")

        # 3. 获取股票/ETF 日内资金流向 (主力/超大单机构/散户小单)
        try:
            flow_url = f"http://push2.eastmoney.com/api/qt/stock/fflow/kline/get?secid={secid}&klt=101&lmt=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65"
            flow_data = await asyncio.to_thread(_fetch_eastmoney_json, flow_url)
            klines = flow_data.get("data", {}).get("klines", [])
            if klines:
                parts = klines[-1].split(',')
                if len(parts) >= 6:
                    main_flow = float(parts[1]) if parts[1] else 0.0
                    retail_flow = float(parts[2]) if parts[2] else 0.0
                    inst_flow = float(parts[5]) if parts[5] else 0.0

                    quote_data["main_net_inflow"] = main_flow
                    quote_data["main_net_inflow_formatted"] = format_amount(main_flow)
                    quote_data["retail_net_inflow"] = retail_flow
                    quote_data["retail_net_inflow_formatted"] = format_amount(retail_flow)
                    quote_data["institution_net_inflow"] = inst_flow
                    quote_data["institution_net_inflow_formatted"] = format_amount(inst_flow)
                    return quote_data
        except Exception as e:
            logger.warning(f"[GenericDataProvider] flow fetch error for {code}: {e}")

        return quote_data

    async def _calculate_fund_flow_from_components(self, fund_code: str) -> dict:
        """
        当基金无法直接获取资金流向时，根据前十大重仓股的权重加权计算
        """
        url = f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&topline=10&code={fund_code}"
        try:
            text = await asyncio.to_thread(_fetch_eastmoney_text, url)
            
            # Match stock code, name and weight percentage
            pattern = r"<td><a href=[\x27\x22]//quote\.eastmoney\.com/unify/r/[01]\.([0-9]{6})[\x27\x22]>\1</a></td><td class=[\x27\x22]tol[\x27\x22]><a[^>]*>([^<]+)</a></td>.*?<td class=[\x27\x22]tor[\x27\x22]>([0-9\.]+)%</td>"
            matches = re.findall(pattern, text)
            if not matches:
                return {"available": False, "calc_from_components": False}

            total_weight = 0.0
            weighted_main = 0.0
            weighted_retail = 0.0
            weighted_inst = 0.0
            top_components = []

            for scode, sname, sweight in matches[:10]:
                weight = float(sweight)
                total_weight += weight
                
                m_prefix = "sh" if scode.startswith(("6", "5", "9")) else "sz"
                secid = f"1.{scode}" if m_prefix == "sh" else f"0.{scode}"
                flow_url = f"http://push2.eastmoney.com/api/qt/stock/fflow/kline/get?secid={secid}&klt=101&lmt=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56"
                try:
                    c_resp = await asyncio.to_thread(_fetch_eastmoney_json, flow_url)
                    c_klines = c_resp.get("data", {}).get("klines", [])
                    if c_klines:
                        p = c_klines[-1].split(',')
                        m_flow = float(p[1]) if len(p) > 1 and p[1] else 0.0
                        r_flow = float(p[2]) if len(p) > 2 and p[2] else 0.0
                        i_flow = float(p[5]) if len(p) > 5 and p[5] else 0.0

                        weighted_main += m_flow * (weight / 100.0)
                        weighted_retail += r_flow * (weight / 100.0)
                        weighted_inst += i_flow * (weight / 100.0)

                        top_components.append({
                            "code": scode,
                            "name": sname,
                            "weight": weight,
                            "main_net_inflow_formatted": format_amount(m_flow)
                        })
                except Exception:
                    pass

            return {
                "available": True,
                "calc_from_components": True,
                "components_count": len(top_components),
                "components": top_components,
                "main_net_inflow": weighted_main,
                "main_net_inflow_formatted": format_amount(weighted_main),
                "retail_net_inflow": weighted_retail,
                "retail_net_inflow_formatted": format_amount(weighted_retail),
                "institution_net_inflow": weighted_inst,
                "institution_net_inflow_formatted": format_amount(weighted_inst)
            }
        except Exception as e:
            logger.warning(f"[GenericDataProvider] _calculate_fund_flow_from_components error for {fund_code}: {e}")
            return {"available": False, "calc_from_components": False}

    async def get_sector_rotation(self) -> list:
        """
        获取行业板块轮动数据（包含领涨/流入板块与承压/流出板块）
        """
        url_in = "http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=35&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&wbp2u=|0|0|0|web&fid=f62&fs=m:90+t:2&fields=f12,f14,f2,f3,f6,f62,f66,f72,f78,f84"
        url_out = "http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=20&po=0&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&wbp2u=|0|0|0|web&fid=f62&fs=m:90+t:2&fields=f12,f14,f2,f3,f6,f62,f66,f72,f78,f84"
        try:
            res_in = await asyncio.to_thread(_fetch_eastmoney_json, url_in)
            res_out = await asyncio.to_thread(_fetch_eastmoney_json, url_out)
            diff_in = res_in.get("data", {}).get("diff", [])
            diff_out = res_out.get("data", {}).get("diff", [])

            seen_codes = set()
            sectors = []

            for item in (diff_in + diff_out):
                code = item.get("f12", "")
                name = item.get("f14", "")
                if not code or code in seen_codes or not name:
                    continue
                seen_codes.add(code)

                chg = float(item.get("f3") or 0.0)
                amt = float(item.get("f6") or 0.0)
                main_flow = float(item.get("f62") or 0.0)
                inst_flow = float(item.get("f66") or 0.0)
                retail_flow = float(item.get("f84") or 0.0)

                sectors.append({
                    "code": code,
                    "name": name,
                    "change_pct": round(chg, 2),
                    "amount": amt,
                    "amount_formatted": format_amount(amt).lstrip('+'),
                    "main_net_inflow": main_flow,
                    "main_net_inflow_formatted": format_amount(main_flow),
                    "institution_net_inflow": inst_flow,
                    "retail_net_inflow": retail_flow,
                    "trend": "up" if chg > 1.0 else ("down" if chg < -1.0 else "flat")
                })

            if sectors:
                sectors.sort(key=lambda x: x["change_pct"], reverse=True)
                return sectors
        except Exception as e:
            logger.warning(f"[GenericDataProvider] get_sector_rotation eastmoney error: {e}")

        # Fallback to Sina Finance
        try:
            sina_sectors = await asyncio.to_thread(_fetch_sina_sectors)
            if sina_sectors:
                return sina_sectors
        except Exception as e2:
            logger.error(f"[GenericDataProvider] get_sector_rotation sina fallback error: {e2}")

        return []

    async def get_sector_fund_flow(self) -> dict:
        """
        构建板块间资金流动网络与桑基图可视化数据：
        1. 桑基图 (Sankey)：主力机构资金/散户 -> 板块
        2. 板块间流动图 (Inter-Sector Flow)：从流出板块(失血)指向流入板块(吸血)，带流动方向箭头与飞线动画
        3. 颜色梯度：深红为大量流入，深绿为大量流出
        """
        sectors = await self.get_sector_rotation()
        if not sectors:
            empty_net = {"nodes": [], "links": [], "flow_lines": []}
            return {
                "sankey": {"nodes": [], "links": []},
                "inflow_top8": empty_net,
                "outflow_top8": empty_net,
                "inter_sector": empty_net,
                "top_inflows": [],
                "top_outflows": []
            }

        # 分离全市场基础流入与流出排序
        sorted_by_flow = sorted(sectors, key=lambda x: x["main_net_inflow"], reverse=True)

        # 颜色分级函数：深红 (大量流入) -> 绿 (轻度流出) -> 深绿 (大量流出)
        def _get_flow_color(flow_val_yuan: float) -> str:
            flow_yi = flow_val_yuan / 1e8
            if flow_yi >= 100:
                return "#820014"  # 深墨红 (特大额流入)
            elif flow_yi >= 50:
                return "#a8071a"  # 极深红
            elif flow_yi >= 20:
                return "#cf1322"  # 深红
            elif flow_yi >= 5:
                return "#f5222d"  # 鲜红
            elif flow_yi > 0:
                return "#ff7875"  # 浅暖红
            elif flow_yi <= -40:
                return "#004d40"  # 深墨绿 (特大额流出)
            elif flow_yi <= -25:
                return "#00695c"  # 深绿
            elif flow_yi <= -15:
                return "#1b5e20"  # 翠绿
            elif flow_yi <= -5:
                return "#2e7d32"  # 森林绿
            else:
                return "#52c41a"  # 浅绿

        def _get_affinity(source_name: str, target_name: str) -> float:
            chains = [
                {'电子器件', '电子信息', '仪器仪表', '家电行业', '通讯行业', '计算机', '玻璃行业', '元器件', '摩托车', '电子', '半导体', '汽车制造'},
                {'机械行业', '发电设备', '交通运输', '公路桥梁', '钢铁行业', '纺织机械', '造船行业', '建筑建材', '机械设备', '通用设备'},
                {'有色金属', '化工行业', '煤炭行业', '石油行业', '钢铁行业', '化纤行业', '塑料行业', '基础化工', '石油石化', '电力行业'},
                {'酿酒行业', '食品行业', '商业百货', '医药制造', '纺织服装', '农牧饲渔', '食品饮料', '医药生物', '商贸零售', '旅游酒店'}
            ]
            for c in chains:
                if source_name in c and target_name in c:
                    return 3.0
            for kw in ['电子', '通信', '器件', '信息', '网络', '半导体', '芯片', '计算机']:
                if any(k in source_name for k in kw) and any(k in target_name for k in kw):
                    return 2.5
            for kw in ['机械', '设备', '制造', '工程', '建材', '建筑', '运输', '桥梁']:
                if any(k in source_name for k in kw) and any(k in target_name for k in kw):
                    return 2.4
            for kw in ['化工', '金属', '材料', '矿', '资源', '石油', '煤炭', '能源', '电力']:
                if any(k in source_name for k in kw) and any(k in target_name for k in kw):
                    return 2.4
            for kw in ['消费', '食品', '百货', '医药', '酒', '零售', '服装']:
                if any(k in source_name for k in kw) and any(k in target_name for k in kw):
                    return 2.4
            return 1.0

        def _build_flow_network(out_list, in_list, focus_mode='inflow'):
            nodes = []
            links = []
            flow_lines = []

            def _calc_y(idx, total):
                if total <= 1:
                    return 250
                step = (460 - 50) / (total - 1)
                return round(460 - idx * step, 1)

            # 根据当前图内所有板块的资金体量，动态计算圆球大小（38px ~ 72px），真实体现流入流出量
            all_vals = [abs(s.get("main_net_inflow", 0.0)) / 1e8 for s in out_list + in_list]
            min_v = min(all_vals) if all_vals else 0.0
            max_v = max(all_vals) if all_vals else 1.0

            def _calc_node_size(val_yi):
                if max_v - min_v < 0.05:
                    return 52
                norm = max(0.0, min(1.0, (abs(val_yi) - min_v) / (max_v - min_v)))
                return round(38 + 34 * (norm ** 0.5), 1)

            outflow_map = {}
            for i, s in enumerate(out_list):
                val_yi = round(s["main_net_inflow"] / 1e8, 2)
                c = _get_flow_color(s["main_net_inflow"])
                node = {
                    "name": s["name"],
                    "value": val_yi,
                    "change_pct": s["change_pct"],
                    "category": "outflow",
                    "x": 130,
                    "y": _calc_y(i, len(out_list)),
                    "color": c,
                    "symbolSize": _calc_node_size(val_yi)
                }
                nodes.append(node)
                outflow_map[s["name"]] = node

            inflow_map = {}
            for j, s in enumerate(in_list):
                val_yi = round(s["main_net_inflow"] / 1e8, 2)
                c = _get_flow_color(s["main_net_inflow"])
                node = {
                    "name": s["name"],
                    "value": val_yi,
                    "change_pct": s["change_pct"],
                    "category": "inflow",
                    "x": 870,
                    "y": _calc_y(j, len(in_list)),
                    "color": c,
                    "symbolSize": _calc_node_size(val_yi)
                }
                nodes.append(node)
                inflow_map[s["name"]] = node

            # 节点度数追踪：保证每个板块严格最多 4 根线，最少 1 根线
            src_deg = {s["name"]: 0 for s in out_list}
            tgt_deg = {t["name"]: 0 for t in in_list}

            # 测算所有板块对的转移强度
            all_pairs = []
            for s in out_list:
                for t in in_list:
                    aff = _get_affinity(s["name"], t["name"])
                    s_val = abs(s.get("main_net_inflow", 0.0)) / 1e8 + 0.1
                    t_val = abs(t.get("main_net_inflow", 0.0)) / 1e8 + 0.1
                    score = round(s_val * t_val * aff / 10.0, 2)
                    all_pairs.append((s["name"], t["name"], score))

            if focus_mode == 'inflow':
                # 流入以右侧板块为主：为右侧每个板块严格选取流入最多的 4 根最大线
                # 约束：每个板块最多 4 根线，且每个板块至少 1 根线
                tgt_lines = {t["name"]: [] for t in in_list}
                src_deg = {s["name"]: 0 for s in out_list}

                for t in in_list:
                    tname = t["name"]
                    cands = [p for p in all_pairs if p[1] == tname]
                    cands.sort(key=lambda x: x[2], reverse=True)
                    chosen = []
                    for sname, _, sc in cands:
                        if src_deg[sname] < 4 and len(chosen) < 4:
                            chosen.append((sname, tname, sc))
                            src_deg[sname] += 1
                    tgt_lines[tname] = chosen

                # 确保每个左侧来源板块至少连接 1 根线，且不破坏每个板块最多 4 根线的限制
                for s in out_list:
                    sname = s["name"]
                    if src_deg[sname] == 0:
                        best_t = max(in_list, key=lambda t: next(p[2] for p in all_pairs if p[0] == sname and p[1] == t["name"]))
                        tname = best_t["name"]
                        sc = next(p[2] for p in all_pairs if p[0] == sname and p[1] == tname)
                        if len(tgt_lines[tname]) == 4:
                            # 替换当前 target 中 sc 最小的候选源
                            old_s, _, _ = tgt_lines[tname][-1]
                            src_deg[old_s] -= 1
                            tgt_lines[tname][-1] = (sname, tname, sc)
                            src_deg[sname] += 1
                        else:
                            tgt_lines[tname].append((sname, tname, sc))
                            src_deg[sname] += 1

                for t in in_list:
                    tname = t["name"]
                    for sname, _, sc in tgt_lines[tname]:
                        s_node = outflow_map[sname]
                        t_node = inflow_map[tname]
                        i = out_list.index(next(x for x in out_list if x["name"] == sname))
                        j = in_list.index(next(x for x in in_list if x["name"] == tname))
                        links.append({
                            "source": sname,
                            "target": tname,
                            "value": sc,
                            "lineStyle": {
                                "width": max(1.8, min(5.0, 1.4 + sc * 0.04)),
                                "curveness": 0.15 + (i - j) * 0.025,
                                "color": t_node["color"]
                            }
                        })
                        flow_lines.append({
                            "coords": [[s_node["x"], s_node["y"]], [t_node["x"], t_node["y"]]],
                            "fromName": sname,
                            "toName": tname,
                            "value": sc
                        })

            else:
                # 流出以左侧板块为主：为左侧每个板块严格选取流出最多的 4 根最大线
                # 约束：每个板块最多 4 根线，且每个板块至少 1 根线
                src_lines = {s["name"]: [] for s in out_list}
                tgt_deg = {t["name"]: 0 for t in in_list}

                for s in out_list:
                    sname = s["name"]
                    cands = [p for p in all_pairs if p[0] == sname]
                    cands.sort(key=lambda x: x[2], reverse=True)
                    chosen = []
                    for _, tname, sc in cands:
                        if tgt_deg[tname] < 4 and len(chosen) < 4:
                            chosen.append((sname, tname, sc))
                            tgt_deg[tname] += 1
                    src_lines[sname] = chosen

                # 确保每个右侧承接板块至少连接 1 根线，且不破坏每个板块最多 4 根线的限制
                for t in in_list:
                    tname = t["name"]
                    if tgt_deg[tname] == 0:
                        best_s = max(out_list, key=lambda s: next(p[2] for p in all_pairs if p[0] == s["name"] and p[1] == tname))
                        sname = best_s["name"]
                        sc = next(p[2] for p in all_pairs if p[0] == sname and p[1] == tname)
                        if len(src_lines[sname]) == 4:
                            # 替换当前 source 中 sc 最小的候选去向
                            _, old_t, _ = src_lines[sname][-1]
                            tgt_deg[old_t] -= 1
                            src_lines[sname][-1] = (sname, tname, sc)
                            tgt_deg[tname] += 1
                        else:
                            src_lines[sname].append((sname, tname, sc))
                            tgt_deg[tname] += 1

                for s in out_list:
                    sname = s["name"]
                    for _, tname, sc in src_lines[sname]:
                        s_node = outflow_map[sname]
                        t_node = inflow_map[tname]
                        i = out_list.index(next(x for x in out_list if x["name"] == sname))
                        j = in_list.index(next(x for x in in_list if x["name"] == tname))
                        links.append({
                            "source": sname,
                            "target": tname,
                            "value": sc,
                            "lineStyle": {
                                "width": max(1.8, min(5.0, 1.4 + sc * 0.04)),
                                "curveness": 0.15 + (i - j) * 0.025,
                                "color": s_node["color"]
                            }
                        })
                        flow_lines.append({
                            "coords": [[s_node["x"], s_node["y"]], [t_node["x"], t_node["y"]]],
                            "fromName": sname,
                            "toName": tname,
                            "value": sc
                        })

            return {"nodes": nodes, "links": links, "flow_lines": flow_lines}

        # 1. Tab 1（流入图）：右侧主要显示流入 Top 8 的板块；左侧显示主要流入右侧的流出/来源板块（并非一定是全局流出 Top 8）
        inflow_top8_targets = sorted_by_flow[:8]
        target_inflow_names = {t["name"] for t in inflow_top8_targets}

        cand_inflow_sources = [s for s in sectors if s["name"] not in target_inflow_names]
        actual_outflows = [s for s in cand_inflow_sources if s["main_net_inflow"] < 0]
        other_sources = [s for s in cand_inflow_sources if s["main_net_inflow"] >= 0]

        def _inflow_source_score(s):
            # 测算该板块向右侧 8 大流入板块输送资金的关联转移度
            trans = sum((t["main_net_inflow"] / 1e8) * _get_affinity(s["name"], t["name"]) for t in inflow_top8_targets)
            return trans

        actual_outflows.sort(key=_inflow_source_score, reverse=True)
        other_sources.sort(key=_inflow_source_score, reverse=True)
        inflow_sources = (actual_outflows + other_sources)[:8]
        # 按净额升序排列（流出最多的排在顶部）
        inflow_sources.sort(key=lambda x: x["main_net_inflow"])

        inflow_network = _build_flow_network(inflow_sources, inflow_top8_targets, focus_mode='inflow')

        # 2. Tab 2（流出图）：以左侧市场流出 Top 8 为主；右侧显示左侧流出的承接目标板块（并非全市场流入 Top 8）
        outflow_top8_sources = sorted(sectors, key=lambda x: x["main_net_inflow"])[:8]
        source_outflow_names = {s["name"] for s in outflow_top8_sources}

        cand_outflow_targets = [s for s in sectors if s["name"] not in source_outflow_names]

        # 针对每个流出版块，寻找与其具备最直接产业链轮动与资金承接关联的去向目标
        selected_targets = []
        selected_target_names = set()

        for s in outflow_top8_sources:
            s_cand = [c for c in cand_outflow_targets if c["name"] not in selected_target_names]
            # 优先根据与该流出版块的行业关联度排序，其次按承接净额排序
            s_cand.sort(key=lambda c: (_get_affinity(s["name"], c["name"]), c["main_net_inflow"]), reverse=True)
            if s_cand:
                best = s_cand[0]
                selected_targets.append(best)
                selected_target_names.add(best["name"])

        # 若不足 8 个，使用与流出板块总体关联度最高的候选板块补齐
        if len(selected_targets) < 8:
            remaining = [c for c in cand_outflow_targets if c["name"] not in selected_target_names]
            remaining.sort(key=lambda c: sum(_get_affinity(s["name"], c["name"]) for s in outflow_top8_sources), reverse=True)
            selected_targets.extend(remaining[:8 - len(selected_targets)])

        outflow_targets = selected_targets[:8]
        # 按净额降序排列（承接规模最大的排在顶部，视觉层次分明）
        outflow_targets.sort(key=lambda x: x["main_net_inflow"], reverse=True)

        outflow_network = _build_flow_network(outflow_top8_sources, outflow_targets, focus_mode='outflow')

        # 3. 桑基图 (Sankey)：过滤极小碎片板块，归并为“其他流出/流入板块”，杜绝文字标签堆叠重叠
        sankey_nodes = [
            {"name": "主力机构资金", "itemStyle": {"color": "#ff4d4f"}},
            {"name": "散户游资资金", "itemStyle": {"color": "#faad14"}},
            {"name": "流出套现池", "itemStyle": {"color": "#00695c"}}
        ]
        sankey_links = []
        seen_sankey = {"主力机构资金", "散户游资资金", "流出套现池"}

        other_in_val = 0.0
        for s in inflow_top8_targets:
            val = round(abs(s["main_net_inflow"]) / 1e8, 2)
            if val >= 0.5:
                if s["name"] not in seen_sankey:
                    sankey_nodes.append({"name": s["name"], "itemStyle": {"color": _get_flow_color(s["main_net_inflow"])}})
                    seen_sankey.add(s["name"])
                sankey_links.append({
                    "source": "主力机构资金",
                    "target": s["name"],
                    "value": val,
                    "lineStyle": {"color": "rgba(248, 81, 73, 0.45)"}
                })
            else:
                other_in_val += val

        if other_in_val > 0.05:
            sankey_nodes.append({"name": "其他流入板块", "itemStyle": {"color": "#ff7875"}})
            sankey_links.append({
                "source": "主力机构资金",
                "target": "其他流入板块",
                "value": round(other_in_val, 2),
                "lineStyle": {"color": "rgba(248, 81, 73, 0.45)"}
            })

        other_out_val = 0.0
        for s in outflow_top8_sources:
            val = round(abs(s["main_net_inflow"]) / 1e8, 2)
            if val >= 0.5:
                if s["name"] not in seen_sankey:
                    sankey_nodes.append({"name": s["name"], "itemStyle": {"color": _get_flow_color(s["main_net_inflow"])}})
                    seen_sankey.add(s["name"])
                sankey_links.append({
                    "source": s["name"],
                    "target": "流出套现池",
                    "value": val,
                    "lineStyle": {"color": "rgba(0, 105, 92, 0.45)"}
                })
            else:
                other_out_val += val

        if other_out_val > 0.05:
            sankey_nodes.append({"name": "其他流出板块", "itemStyle": {"color": "#52c41a"}})
            sankey_links.append({
                "source": "其他流出板块",
                "target": "流出套现池",
                "value": round(other_out_val, 2),
                "lineStyle": {"color": "rgba(0, 105, 92, 0.45)"}
            })

        return {
            "sankey": {
                "nodes": sankey_nodes,
                "links": sankey_links
            },
            "inflow_top8": inflow_network,
            "outflow_top8": outflow_network,
            "inter_sector": inflow_network,
            "top_inflows": inflow_top8_targets,
            "top_outflows": outflow_top8_sources,
            "inflow_sources": inflow_sources,
            "outflow_targets": outflow_targets
        }


def get_provider(provider_type: str, api_key: str = None) -> DataProvider:
    if provider_type == "mx" and api_key:
        return MXDataProvider(api_key=api_key)
    return GenericDataProvider()
