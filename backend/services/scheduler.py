import sqlite3
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.trading_calendar import is_trading_time, is_trading_day
from services.market_service import get_market_overview
from services.wxwork_service import send_wxwork_message
from services.ai_service import run_deepseek_review, run_ai_news_analysis
from services.alert_service import check_and_trigger_stock_alerts
from database import DB_PATH, get_settings_dict
from datetime import datetime
import asyncio
import re

import os

scheduler = AsyncIOScheduler(timezone=os.environ.get("TZ", "Asia/Shanghai"))
last_push_time = None
last_morning_review_date = {}
last_afternoon_review_date = {}
last_ai_news_push_time = {}

async def _trigger_review_safe(session_name: str, user_id: int):
    try:
        success, msg = await run_deepseek_review(session_name, user_id=user_id)
        if success:
            print(f"[Scheduler] 用户 {user_id} {session_name} 成功发送")
        else:
            print(f"[Scheduler] 用户 {user_id} {session_name} 发送失败: {msg}")
    except Exception as e:
        print(f"[Scheduler] 用户 {user_id} {session_name} 执行异常: {e}")

async def _trigger_ai_news_safe(user_id: int):
    try:
        success, msg = await run_ai_news_analysis(push_to_wx=True, user_id=user_id)
        if success:
            print(f"[Scheduler] 用户 {user_id} AI 新闻持仓影响分析成功发送")
        else:
            print(f"[Scheduler] 用户 {user_id} AI 新闻持仓影响分析发送失败: {msg}")
    except Exception as e:
        print(f"[Scheduler] 用户 {user_id} AI 新闻持仓影响分析执行异常: {e}")

def parse_interval_minutes(schedule_val: str) -> int:
    """Parse interval minutes from schedule_val string, enforcing a minimum of 3 minutes."""
    try:
        match = re.search(r'\d+', str(schedule_val))
        if match:
            minutes = int(match.group(0))
            return max(3, minutes)
    except Exception as e:
        print(f"[Scheduler] Error parsing schedule_val '{schedule_val}': {e}")
    return 30

async def format_and_push_message(user_id: int = 1):
    settings = get_settings_dict(user_id=user_id)
    if not settings.get('push_enabled', True):
        return False, "推送功能尚未开启，请先开启「启用推送通知」开关"
        
    overview = await get_market_overview(user_id=user_id)
    
    now = datetime.now()
    date_str = now.strftime("%Y/%m/%d")
    time_str = now.strftime("%H:%M:%S")
    
    lines = [f"📊 快报 {date_str} {time_str}", "━━━━━━━━━━━━━━━━"]
    
    # 股票选择过滤逻辑（未选择时默认推送持有的）
    selected_stock_str = settings.get('push_selected_stock_codes', '') or ''
    selected_stock_codes = [c.strip() for c in selected_stock_str.split(',') if c.strip()]
    
    stocks = overview.get('stocks', [])
    if selected_stock_codes:
        display_stocks = [
            s for s in stocks 
            if s.get('code') in selected_stock_codes 
            or s.get('code').lstrip('shsz') in selected_stock_codes
        ]
    else:
        # 没有单独勾选股票时，默认推送持有的股票
        display_stocks = [s for s in stocks if s.get('is_holding')]
    
    if settings.get('push_stocks', True) and display_stocks:
        header_title = "📈 股票持仓" if not selected_stock_codes else "📈 股票列表"
        lines.append(header_title)
        for s in display_stocks:
            name = s.get('name', '未命名')
            code = s.get('code', '')
            price = s.get('current_price', 0)
            change = s.get('change_pct', 0)
            dp = s.get('day_profit', 0)
            tp = s.get('total_profit', 0)
            
            price_str = f"{price:.2f}" if price > 0 else "-"
            change_str = f"{change:+.2f}%"
            if s.get('is_holding'):
                lines.append(f"{name}({code}) {price_str} ({change_str}) | 今日:{dp:+.0f}元 | 总:{tp:+.0f}元")
            else:
                lines.append(f"{name}({code}) {price_str} ({change_str}) [未持仓]")
        lines.append("")
        
    # 基金选择过滤逻辑（未选择时默认推送持有的）
    selected_fund_str = settings.get('push_selected_fund_codes', '') or ''
    selected_fund_codes = [c.strip() for c in selected_fund_str.split(',') if c.strip()]
    
    funds = overview.get('funds', [])
    if selected_fund_codes:
        display_funds = [f for f in funds if f.get('code') in selected_fund_codes]
    else:
        # 没有单独勾选基金时，默认推送持有的基金
        display_funds = [f for f in funds if f.get('is_holding')]

    if settings.get('push_funds', True) and display_funds:
        header_title = "📦 基金持仓" if not selected_fund_codes else "📦 基金列表"
        lines.append(header_title)
        for f in display_funds:
            name = f.get('name', '未命名')
            code = f.get('code', '')
            nav = f.get('current_nav', 0)
            change = f.get('change_pct', 0)
            dp = f.get('day_profit', 0)
            tp = f.get('total_profit', 0)
            
            nav_str = f"{nav:.4f}" if nav > 0 else "-"
            change_str = f"{change:+.2f}%"
            nav_tag = "净值" if f.get('is_updated') else "估值"
            if f.get('is_holding'):
                lines.append(f"{name}({code}) {nav_tag}:{nav_str} ({change_str}) | 今日:{dp:+.0f}元 | 总:{tp:+.0f}元")
            else:
                lines.append(f"{name}({code}) {nav_tag}:{nav_str} ({change_str}) [未持仓]")
        lines.append("")
        
    # 盈亏汇总
    if settings.get('push_pnl', True):
        summary = overview.get('summary', {})
        tdp = summary.get('total_day_profit', 0)
        tp = summary.get('total_profit', 0)
        lines.append(f"💰 今日总盈亏: {tdp:+.0f}元")
        lines.append(f"💰 累计总盈亏: {tp:+.0f}元")
        
    content = "\n".join(lines).strip()
    return send_wxwork_message(content, user_id=user_id)

async def check_and_push():
    global last_push_time, last_morning_review_date, last_afternoon_review_date, last_ai_news_push_time
    now = datetime.now()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users")
    user_rows = cursor.fetchall()
    conn.close()

    for urow in user_rows:
        uid = urow[0]
        settings = get_settings_dict(user_id=uid)

        # 1. 检查 DeepSeek 收盘自动复盘 (11:35 午盘复盘, 15:05 收盘复盘)
        if is_trading_day(now):
            if settings.get('deepseek_review_enabled', True):
                today_str = now.strftime("%Y-%m-%d")
                if now.hour == 11 and now.minute == 35:
                    if last_morning_review_date.get(uid) != today_str:
                        last_morning_review_date[uid] = today_str
                        print(f"[Scheduler] 用户 {uid} 自动触发交易日 11:35 午盘 AI 复盘...")
                        asyncio.create_task(_trigger_review_safe("午盘复盘", user_id=uid))
                elif now.hour == 15 and now.minute == 5:
                    if last_afternoon_review_date.get(uid) != today_str:
                        last_afternoon_review_date[uid] = today_str
                        print(f"[Scheduler] 用户 {uid} 自动触发交易日 15:05 收盘 AI 复盘...")
                        asyncio.create_task(_trigger_review_safe("收盘复盘", user_id=uid))

        # 2. 检查 AI 实时新闻持仓影响分析 (频率可在 30min 到 720min/12小时 调节)
        if settings.get('ai_news_analysis_enabled', True):
            news_schedule_val = settings.get('ai_news_schedule', '60min')
            news_interval = parse_interval_minutes(news_schedule_val)
            last_time = last_ai_news_push_time.get(uid)

            trigger_news = False
            if last_time is None:
                # 初始启动记录时间，防止第一次全员同时推送
                last_ai_news_push_time[uid] = now
            else:
                elapsed = (now - last_time).total_seconds()
                if elapsed >= news_interval * 60 - 5:
                    trigger_news = True

            if trigger_news:
                last_ai_news_push_time[uid] = now
                print(f"[Scheduler] 用户 {uid} 触发 AI 新闻持仓影响分析 (设置频率: {news_schedule_val})...")
                asyncio.create_task(_trigger_ai_news_safe(user_id=uid))

        # 3. 检查普通定时行情快报推送
        if not is_trading_time(now):
            continue

        if not settings.get('push_enabled', True):
            continue

        schedule_val = settings.get('push_schedule', '30min')
        interval_minutes = parse_interval_minutes(schedule_val)
        
        push = False
        
        # Time-based interval push
        if last_push_time is None:
            push = True
        else:
            elapsed = (now - last_push_time).total_seconds()
            if elapsed >= interval_minutes * 60 - 5:
                push = True

        # Check explicit open/close pushes
        if settings.get('push_at_open') and now.hour == 9 and now.minute == 30:
            push = True
            
        if settings.get('push_at_close') and now.hour == 15 and now.minute == 0:
            push = True
            
        if push:
            last_push_time = now
            await format_and_push_message(user_id=uid)


def start_scheduler():
    scheduler.add_job(check_and_push, 'cron', minute='*')
    scheduler.add_job(check_and_trigger_stock_alerts, 'interval', seconds=30)
    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()

