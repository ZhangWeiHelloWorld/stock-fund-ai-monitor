import httpx
import re
import json
from datetime import datetime
from typing import List, Dict

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn/"
}

async def fetch_7x24_market_news(limit: int = 15) -> List[Dict[str, str]]:
    """
    Fetch real-time 7x24 global & A-share financial market live news.
    Sources: Sina 7x24 Live Feed with fallback to Eastmoney 7x24.
    """
    news_items = []

    # 1. Fetch from Sina 7x24
    try:
        url = f"https://zhibo.sina.com.cn/api/zhibo/feed?page=1&page_size={limit}&zhibo_id=152"
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                feed_data = data.get("result", {}).get("data", {}).get("feed", {})
                
                raw_list = []
                if isinstance(feed_data, dict):
                    raw_list = feed_data.get("list", list(feed_data.values()))
                elif isinstance(feed_data, list):
                    raw_list = feed_data

                for item in raw_list:
                    if isinstance(item, dict):
                        txt = item.get("rich_text", "") or item.get("docurl", "")
                        txt = re.sub(r'<[^>]+>', '', txt).strip()
                        c_time = item.get("create_time", "") or item.get("created_at", "")
                        if txt:
                            news_items.append({
                                "source": "新浪7x24",
                                "time": c_time,
                                "content": txt
                            })
    except Exception as e:
        print(f"[NewsService] Error fetching Sina 7x24 news: {e}")

    # 2. Fallback or augment with Eastmoney FastNews if needed
    if len(news_items) < 5:
        try:
            em_url = f"https://fastnews-api.eastmoney.com/News/GetFastNewsList?pageSize={limit}&pageIndex=1"
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(em_url, headers=HEADERS)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("FastNewsList", [])
                    for item in items:
                        title = item.get("title") or item.get("digest") or item.get("summary") or ""
                        show_time = item.get("showTime") or ""
                        if title:
                            news_items.append({
                                "source": "东方财富7x24",
                                "time": show_time,
                                "content": title.strip()
                            })
        except Exception as e:
            print(f"[NewsService] Error fetching Eastmoney FastNews: {e}")

    return news_items[:limit]


async def fetch_holding_item_news(keyword: str, limit: int = 3) -> List[Dict[str, str]]:
    """
    Search Eastmoney news API for news articles related to a specific stock/fund keyword.
    """
    items = []
    if not keyword:
        return items

    clean_kw = re.sub(r'[^\w\u4e00-\u9fa5]', '', keyword)
    if not clean_kw:
        return items

    try:
        url = (
            f"https://search-api-web.eastmoney.com/search/jsonp?cb=jQuery&param="
            f"%7B%22uid%22%3A%22%22%2C%22keyword%22%3A%22{clean_kw}%22%2C%22type%22%3A%5B%22cmsArticleWebOld%22%5D%2C"
            f"%22client%22%3A%22web%22%2C%22clientType%22%3A%22web%22%2C%22clientVersion%22%3A%22curr%22%2C"
            f"%22param%22%3A%7B%22cmsArticleWebOld%22%3A%7B%22searchScope%22%3A%22default%22%2C%22sort%22%3A%22default%22%2C"
            f"%22pageIndex%22%3A1%2C%22pageSize%22%3A{limit}%7D%7D%7D"
        )
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=HEADERS)
            if resp.status_code == 200:
                text = resp.text
                if "jQuery(" in text:
                    text = text[text.find("(")+1 : text.rfind(")")]
                data = json.loads(text)
                articles = data.get("result", {}).get("cmsArticleWebOld", [])
                for a in articles:
                    title = re.sub(r'<[^>]+>', '', a.get("title", "")).strip()
                    date_str = a.get("date", "")
                    if title:
                        items.append({
                            "keyword": clean_kw,
                            "time": date_str,
                            "title": title
                        })
    except Exception as e:
        print(f"[NewsService] Error searching news for '{clean_kw}': {e}")

    return items[:limit]


async def get_combined_news_context(holding_stocks: list = None, holding_funds: list = None) -> str:
    """
    Fetch both 7x24 macro market news and targeted stock/fund holding news,
    formatting them into a cohesive text block for LLM prompt context.
    """
    lines = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines.append(f"【互联网最新大盘与持仓新闻汇总 - 采集时间 {now_str}】")
    lines.append("")

    # 1. 7x24 Market Live Stream
    market_news = await fetch_7x24_market_news(limit=12)
    if market_news:
        lines.append("📰 【全网 7x24 实时财经大盘快讯】:")
        for idx, item in enumerate(market_news, 1):
            time_str = item.get("time", "")
            src = item.get("source", "财经快讯")
            cnt = item.get("content", "")
            lines.append(f"{idx}. [{time_str}] ({src}) {cnt}")
        lines.append("")
    else:
        lines.append("📰 【全网 7x24 实时财经大盘快讯】: 暂未检索到最新快讯动态\n")

    # 2. Holding Specific Items News
    keywords = []
    if holding_stocks:
        for s in holding_stocks:
            name = s.get("name", "")
            if name and name != "未知" and len(name) >= 2:
                keywords.append(name)
    if holding_funds:
        for f in holding_funds:
            name = f.get("name", "")
            if name and name != "未知" and len(name) >= 2:
                short_name = re.sub(r'\(.*?\)', '', name).strip()
                if short_name and len(short_name) >= 2:
                    keywords.append(short_name[:8])

    unique_keywords = list(dict.fromkeys(keywords))[:6]

    if unique_keywords:
        lines.append("🎯 【持仓相关品种最新抓取新闻】:")
        item_news_found = False
        for kw in unique_keywords:
            knews = await fetch_holding_item_news(kw, limit=2)
            if knews:
                item_news_found = True
                for kn in knews:
                    lines.append(f"- [{kn['keyword']}] ({kn['time']}): {kn['title']}")
        if not item_news_found:
            lines.append("- 针对当前持仓品种近 24 小时未搜寻到重大突发个股/基金公告新闻。")
        lines.append("")

    return "\n".join(lines).strip()
