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
last_risk_analysis_date = {}
last_daily_premarket_date = {}
last_daily_close_indices_date = {}

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

async def _trigger_risk_analysis_safe(user_id: int):
    try:
        from services.om_stw_service import run_daily_official_news_analysis
        success, msg = await run_daily_official_news_analysis(user_id=user_id)
        print(f"[Scheduler] 用户 {user_id} 每日官媒舆情风控分析: {msg}")
    except Exception as e:
        print(f"[Scheduler] 用户 {user_id} 每日官媒舆情风控分析异常: {e}")

async def _trigger_daily_premarket_snapshot_safe(user_id: int):
    try:
        from services.om_stw_service import record_daily_pre_market_risk
        res = await record_daily_pre_market_risk(user_id=user_id)
        print(f"[Scheduler] 用户 {user_id} 今日开盘前风险快照记录成功: {res.get('pre_market_level_name')} ({res.get('pre_market_score')}分)")
    except Exception as e:
        print(f"[Scheduler] 用户 {user_id} 记录开盘前风险快照异常: {e}")

async def _trigger_daily_close_indices_safe(user_id: int):
    try:
        from services.om_stw_service import record_daily_market_close
        res = await record_daily_market_close(user_id=user_id)
        print(f"[Scheduler] 用户 {user_id} 今日各指数收盘点数回填成功: {len(res)} 条")
    except Exception as e:
        print(f"[Scheduler] 用户 {user_id} 回填收盘点数异常: {e}")


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

        # 1. 检查交易日开盘前风险快照、收盘点数回填及 DeepSeek 复盘
        if is_trading_day(now):
            today_str = now.strftime("%Y-%m-%d")
            # 1.1 开盘前 09:15 自动记录风险快照
            if now.hour == 9 and now.minute == 15:
                # Data Analysis auto-refresh at 9:15
                if globals().get(f'_data_analysis_915_done_{uid}') != today_str:
                    globals()[f'_data_analysis_915_done_{uid}'] = today_str
                    try:
                        from services.data_analysis_service import auto_refresh_all_users
                        await auto_refresh_all_users()
                        print(f"[Scheduler] Data analysis auto-refreshed at 09:15")
                    except Exception as e:
                        print(f"[Scheduler] Data analysis refresh error: {e}")

                if last_daily_premarket_date.get(uid) != today_str:
                    last_daily_premarket_date[uid] = today_str
                    print(f"[Scheduler] 用户 {uid} 自动触发交易日 09:15 开盘前风险快照记录...")
                    asyncio.create_task(_trigger_daily_premarket_snapshot_safe(user_id=uid))
            # 1.2 收盘后 15:05 自动回填当天各指数收盘点数
            elif now.hour == 15 and now.minute == 5:
                if last_daily_close_indices_date.get(uid) != today_str:
                    last_daily_close_indices_date[uid] = today_str
                    print(f"[Scheduler] 用户 {uid} 自动触发交易日 15:05 各指数收盘点数回填...")
                    asyncio.create_task(_trigger_daily_close_indices_safe(user_id=uid))

            # 1.3 检查 DeepSeek 交易日复盘 (11:35 午盘复盘, 15:05 收盘复盘)
            if settings.get('deepseek_review_enabled', True):
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

        # 3. 检查每日官媒舆情风控定时分析 (默认 20:30，可配置时分)
        if settings.get('risk_cron_enabled', True):
            cron_time_str = settings.get('risk_cron_time', '20:30') or '20:30'
            try:
                parts = cron_time_str.split(':')
                cron_hour = int(parts[0])
                cron_minute = int(parts[1])
            except Exception:
                cron_hour, cron_minute = 20, 30

            today_str = now.strftime("%Y-%m-%d")
            if now.hour == cron_hour and now.minute == cron_minute:
                if last_risk_analysis_date.get(uid) != today_str:
                    last_risk_analysis_date[uid] = today_str
                    print(f"[Scheduler] 用户 {uid} 自动触发每日 {cron_time_str} 官媒舆情风控分析与预警...")
                    asyncio.create_task(_trigger_risk_analysis_safe(user_id=uid))

        # Data Analysis auto-refresh at 20:30
        if now.hour == 20 and now.minute == 30:
            today_str = now.strftime("%Y-%m-%d")
            if globals().get(f'_data_analysis_2030_done_{uid}') != today_str:
                globals()[f'_data_analysis_2030_done_{uid}'] = today_str
                try:
                    from services.data_analysis_service import auto_refresh_all_users
                    await auto_refresh_all_users()
                    print(f"[Scheduler] Data analysis auto-refreshed at 20:30")
                except Exception as e:
                    print(f"[Scheduler] Data analysis refresh error: {e}")

        # 4. 检查普通定时行情快报推送
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


async def check_and_notify_strategy_signals():
    now = datetime.now()
    if not is_trading_day(now):
        return
    try:
        from services.strategy.strategy_service import scan_strategy_signals
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users")
        user_rows = cursor.fetchall()
        conn.close()

        for urow in user_rows:
            uid = urow[0]
            sigs = await scan_strategy_signals(user_id=uid)
            if sigs and now.hour == 14 and now.minute in (30, 45):
                settings = get_settings_dict(user_id=uid)
                if settings.get('push_enabled', True):
                    msg_lines = ["⚡【基金策略买卖信号提醒】", "━━━━━━━━━━━━━━━━", f"📅 时间: {now.strftime('%H:%M:%S')}"]
                    for s in sigs:
                        msg_lines.append(f"• {s['target_name']}({s['target_code']})")
                        msg_lines.append(f"  {s['reason']}")
                    msg_lines.append("\n💡 提示：基金 15:00 前申赎按今日收盘净值确认，请及时在支付宝或平台操作。")
                    send_wxwork_message("\n".join(msg_lines), user_id=uid)
    except Exception as e:
        print(f"[Scheduler] Error checking strategy signals: {e}")


def start_scheduler():
    scheduler.add_job(check_and_push, 'cron', minute='*')
    scheduler.add_job(check_and_trigger_stock_alerts, 'interval', seconds=30)
    scheduler.add_job(check_and_notify_strategy_signals, 'cron', minute='*/5')
    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()

