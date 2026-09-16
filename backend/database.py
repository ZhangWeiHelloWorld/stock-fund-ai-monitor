import sqlite3
import os
from datetime import datetime
import json
import hashlib

DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(DATA_DIR, "lh.db"))
ADMIN_CONFIG_PATH = os.environ.get("ADMIN_CONFIG_PATH", os.path.join(DATA_DIR, "admin_config.json"))

def hash_password(password: str, salt: bytes = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    elif isinstance(salt, str):
        salt = bytes.fromhex(salt)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + '$' + key.hex()

def verify_password(stored_password_hash: str, provided_password: str) -> bool:
    try:
        salt_hex, key_hex = stored_password_hash.split('$')
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return key.hex() == key_hex
    except Exception:
        return False

def get_admin_config():
    default_username = os.environ.get("ADMIN_USERNAME", "admin")
    default_password = os.environ.get("ADMIN_PASSWORD", "admin123456")
    
    os.makedirs(os.path.dirname(os.path.abspath(ADMIN_CONFIG_PATH)), exist_ok=True)
    if not os.path.exists(ADMIN_CONFIG_PATH):
        config = {
            "username": default_username,
            "password": default_password
        }
        with open(ADMIN_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return config
    try:
        with open(ADMIN_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            if "username" not in config or "password" not in config:
                config = {"username": default_username, "password": default_password}
            return config
    except Exception:
        return {"username": default_username, "password": default_password}

def update_admin_config_file(username: str, password: str):
    os.makedirs(os.path.dirname(os.path.abspath(ADMIN_CONFIG_PATH)), exist_ok=True)
    config = {
        "username": username,
        "password": password
    }
    with open(ADMIN_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def get_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def seed_extended_daily_risk_records(cursor, user_id: int = 1):
    import datetime as dt_mod
    import random
    random.seed(42)

    start_date = dt_mod.date(2026, 6, 1)
    end_date = dt_mod.date(2026, 9, 9)

    cur_sh = 3010.0
    cur_sz = 9200.0
    cur_cy = 1780.0
    cur_kc = 740.0
    cur_hs = 3520.0
    cur_bj = 860.0

    records = []
    cur = start_date

    hype_dates = {'2026-06-18', '2026-07-08', '2026-07-28', '2026-08-14', '2026-08-27'}
    yellow_dates = {'2026-06-11', '2026-06-25', '2026-07-16', '2026-08-05', '2026-08-21', '2026-09-04'}

    while cur <= end_date:
        if cur.weekday() < 5:
            d_str = cur.strftime('%Y-%m-%d')
            if d_str in hype_dates:
                score = random.randint(72, 85)
                level = 'red' if score >= 75 else 'orange'
                level_name = '🔴 红色预警【绝壁顶】' if score >= 75 else '🟠 橙色预警【诱多阶段顶】'
                lead_time = 'T+0 ～ T+2 个交易日'
                news_title = f'主流官媒重磅社论：外资连续净流入 居民资产入市新热潮 ({d_str})'
                news_source = '央视《新闻联播》/经济日报'
                summary = '官媒密集唱多出圈，情绪指标与BIAS20超买高位钝化，主力巨量出逃派发风险极大。'
                guide = ['锁死买入按键，禁止追涨', '次日逢高果断减持7成仓位', '防范主力借利好对倒派发']
                sh_chg = round(random.uniform(-2.4, -0.9), 2)
                val_status = '🎯 风险预警命中 (大盘收跌)'
            elif d_str in yellow_dates:
                score = random.randint(45, 58)
                level = 'yellow'
                level_name = '🟡 黄色注意【分歧加剧】'
                lead_time = 'T+3 ～ T+5 个交易日'
                news_title = f'宏观经济数据解读：结构分化延续 政策工具箱持续发力 ({d_str})'
                news_source = '人民日报/新华社'
                summary = '板块轮动速度加快，多空博弈白热化，量能未能持续放大，谨防冲高回落。'
                guide = ['关注成交量能变化', '适度降低波段仓位', '逢反弹锁定盈利']
                sh_chg = round(random.uniform(-0.9, 0.4), 2)
                val_status = '🎯 风险预警命中 (大盘收跌)' if sh_chg < 0 else '⏳ 变盘观察期 (多空博弈中)'
            else:
                score = random.randint(22, 38)
                level = 'green'
                level_name = '🟢 绿色安全【常态安全】'
                lead_time = '暂无变盘风险'
                news_title = f'央行与发改委统筹推进重点项目 宏观政策平稳发力 ({d_str})'
                news_source = '官方媒体'
                summary = '舆情中性平稳，无大众出圈狂热现象，技术指标处于常态震荡区间。'
                guide = ['保持常态底仓', '跟踪优质个股均线趋势']
                sh_chg = round(random.uniform(-0.6, 1.3), 2)
                if sh_chg <= -1.5:
                    val_status = '⚡ 外部突发超跌'
                elif sh_chg < 0:
                    val_status = '🟡 弱势微调 (风险未超标)'
                else:
                    val_status = '🟢 常态平稳 (符合预期)'

            sz_chg = round(sh_chg * random.uniform(1.05, 1.25), 2)
            cy_chg = round(sh_chg * random.uniform(1.15, 1.45), 2)
            kc_chg = round(sh_chg * random.uniform(1.0, 1.35), 2)
            hs_chg = round(sh_chg * random.uniform(0.9, 1.05), 2)
            bj_chg = round(sh_chg * random.uniform(0.8, 1.4), 2)

            cur_sh = round(cur_sh * (1 + sh_chg / 100.0), 2)
            cur_sz = round(cur_sz * (1 + sz_chg / 100.0), 2)
            cur_cy = round(cur_cy * (1 + cy_chg / 100.0), 2)
            cur_kc = round(cur_kc * (1 + kc_chg / 100.0), 2)
            cur_hs = round(cur_hs * (1 + hs_chg / 100.0), 2)
            cur_bj = round(cur_bj * (1 + bj_chg / 100.0), 2)
            turnover = round(random.uniform(1200.0, 2400.0), 1)

            idx_data = {
                'sh000001': {'name': '上证指数', 'current': cur_sh, 'change_pct': sh_chg},
                'sz399001': {'name': '深证成指', 'current': cur_sz, 'change_pct': sz_chg},
                'sz399006': {'name': '创业板指', 'current': cur_cy, 'change_pct': cy_chg},
                'sh000688': {'name': '科创50', 'current': cur_kc, 'change_pct': kc_chg},
                'sh000300': {'name': '沪深300', 'current': cur_hs, 'change_pct': hs_chg},
                'bj899050': {'name': '北证50', 'current': cur_bj, 'change_pct': bj_chg},
                'turnover_billion': turnover
            }

            records.append((
                user_id, d_str, score, level, level_name, lead_time, news_title, news_source,
                summary, json.dumps(guide, ensure_ascii=False), None,
                f'{d_str}T09:15:00', cur_sh, sh_chg, cur_sz, sz_chg, cur_cy, cy_chg,
                cur_kc, kc_chg, json.dumps(idx_data, ensure_ascii=False), val_status,
                f'{d_str}T15:05:00', f'{d_str}T09:15:00', f'{d_str}T15:05:00'
            ))
        cur += dt_mod.timedelta(days=1)

    cursor.executemany('''
        INSERT OR IGNORE INTO daily_risk_market_records (
            user_id, trade_date, pre_market_score, pre_market_level, pre_market_level_name,
            lead_time, news_title, news_source, summary, action_guide, risk_record_id,
            pre_market_time, sh_close, sh_change_pct, sz_close, sz_change_pct, cy_close,
            cy_change_pct, kc_close, kc_change_pct, indices_data, validation_status,
            close_time, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', records)

def init_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')

    # Read admin_config.json & sync admin account into DB
    admin_cfg = get_admin_config()
    admin_user = admin_cfg.get("username", "admin")
    admin_pass = admin_cfg.get("password", "admin123456")
    now_iso = datetime.now().isoformat()

    cursor.execute("SELECT * FROM users WHERE username = ?", (admin_user,))
    existing_admin = cursor.fetchone()
    if not existing_admin:
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (admin_user, hash_password(admin_pass), 'admin', now_iso, now_iso))
    else:
        # Check if admin_config password differs from DB password hash
        if not verify_password(existing_admin['password_hash'], admin_pass):
            cursor.execute('''
                UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?
            ''', (hash_password(admin_pass), now_iso, existing_admin['id']))

    # 2. Stocks table & migration
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            shares REAL NOT NULL,
            cost_price REAL NOT NULL,
            is_holding BOOLEAN NOT NULL DEFAULT 1,
            note TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    cursor.execute("PRAGMA table_info(stocks)")
    stock_cols = [row[1] for row in cursor.fetchall()]
    if 'user_id' not in stock_cols:
        cursor.execute("ALTER TABLE stocks ADD COLUMN user_id INTEGER DEFAULT 1")

    # 3. Funds table & migration
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS funds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            shares REAL NOT NULL,
            cost_nav REAL NOT NULL,
            is_holding BOOLEAN NOT NULL DEFAULT 1,
            note TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    cursor.execute("PRAGMA table_info(funds)")
    fund_cols = [row[1] for row in cursor.fetchall()]
    if 'user_id' not in fund_cols:
        cursor.execute("ALTER TABLE funds ADD COLUMN user_id INTEGER DEFAULT 1")

    # 4. Settings table & user_settings migration
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            UNIQUE(user_id, key)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history_profits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            stock_profit REAL DEFAULT 0,
            fund_profit REAL DEFAULT 0,
            total_profit REAL DEFAULT 0,
            stock_asset REAL DEFAULT 0,
            fund_asset REAL DEFAULT 0,
            total_asset REAL DEFAULT 0,
            UNIQUE(user_id, date)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calendar_ai_advice (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time_slot TEXT DEFAULT '',
            session_type TEXT DEFAULT 'intraday',
            suggestion TEXT NOT NULL,
            events_summary TEXT,
            bazi_analysis TEXT,
            holdings_snapshot TEXT,
            generated_at TEXT NOT NULL,
            is_final BOOLEAN DEFAULT 0,
            verified_status TEXT DEFAULT 'pending',
            verified_notes TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendar_ai_advice_user_date ON calendar_ai_advice (user_id, date)")

    # 7. Risk Models and Risk Analysis Records tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS risk_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            version TEXT DEFAULT 'v1.0',
            description TEXT,
            category TEXT DEFAULT 'top_warning',
            system_prompt TEXT,
            prompt_template TEXT NOT NULL,
            alert_threshold INTEGER DEFAULT 60,
            is_enabled BOOLEAN DEFAULT 1,
            is_default BOOLEAN DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS risk_analysis_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            trigger_type TEXT NOT NULL,
            model_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            news_title TEXT NOT NULL,
            news_source TEXT,
            news_content TEXT,
            score INTEGER NOT NULL,
            level TEXT NOT NULL,
            level_name TEXT NOT NULL,
            lead_time TEXT,
            action_guide TEXT,
            breakdown TEXT,
            analysis_report TEXT NOT NULL,
            pushed_to_wx BOOLEAN DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_records_user ON risk_analysis_records (user_id, created_at)")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_risk_market_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            trade_date TEXT NOT NULL,
            pre_market_score INTEGER,
            pre_market_level TEXT,
            pre_market_level_name TEXT,
            lead_time TEXT,
            news_title TEXT,
            news_source TEXT,
            summary TEXT,
            action_guide TEXT,
            risk_record_id INTEGER,
            pre_market_time TEXT,
            sh_close REAL,
            sh_change_pct REAL,
            sz_close REAL,
            sz_change_pct REAL,
            cy_close REAL,
            cy_change_pct REAL,
            kc_close REAL,
            kc_change_pct REAL,
            indices_data TEXT,
            validation_status TEXT,
            close_time TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, trade_date)
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_risk_date ON daily_risk_market_records (user_id, trade_date)")

    # Seed initial daily risk market records for user 1 if table is empty
    cursor.execute("SELECT COUNT(*) FROM daily_risk_market_records")
    if cursor.fetchone()[0] == 0:
        seed_records = [
            (1, "2026-09-16", 42, "yellow", "🟡 黄色注意【分歧加剧】", "T+3~T+5", "徐湖平等相关责任人被依规依纪依法处理", "中央纪委国家监委", "严肃监管信号释放，大盘处于常态整理区间，建议控制仓位分歧应对。", '["严格执行止损纪律", "关注盘口承接力", "仓位控制在5成以内"]', 6, "2026-09-16T09:15:00", None, None, None, None, None, None, None, None, None, "⏳ 今日交易中 / 等待收盘归因", None, "2026-09-16T09:15:00", "2026-09-16T09:15:00"),
            (1, "2026-09-15", 35, "green", "🟢 绿色安全【常态安全】", "暂无变盘风险", "央行开展中期借贷并发操作保持流动性充裕", "中国人民银行", "宏观流动性合理宽裕，未见主流官媒出圈唱多信号，市场常态平稳。", '["保持常态化仓位", "关注核心资产均线支撑"]', None, "2026-09-15T09:15:00", 2717.28, -0.48, 7992.25, -0.88, 1533.47, -1.07, 651.98, -0.92, None, "🟢 常态平稳 (符合预期)", "2026-09-15T15:05:00", "2026-09-15T09:15:00", "2026-09-15T15:05:00"),
            (1, "2026-09-14", 38, "green", "🟢 绿色安全【常态安全】", "暂无变盘风险", "8月份宏观经济数据平稳运行 高技术制造业投资增势良好", "国家统计局", "宏观数据平稳披露，官媒常规通报无亢奋出圈迹象，风险偏好中性。", '["遵循个股技术位", "不盲目追高杀跌"]', None, "2026-09-14T09:15:00", 2704.09, -0.48, 7983.55, -0.88, 1535.17, -1.07, 652.88, -0.92, None, "🟢 常态平稳 (符合预期)", "2026-09-14T15:05:00", "2026-09-14T09:15:00", "2026-09-14T15:05:00"),
            (1, "2026-09-11", 60, "orange", "🟠 橙色预警【诱多阶段顶】", "T+0~T+2", "自动化测试：外资爆买A股狂欢，居民存款涌向权益市场", "证券时报", "官媒密集唱多且情绪传播触达末端大众，BIAS20处于高位，主力存在出货诱多可能。", '["禁止开新仓追高", "执行T+1减仓计划", "跌破MA5坚决离场"]', 5, "2026-09-11T09:15:00", 2717.12, -0.17, 8054.24, -0.63, 1551.40, -0.42, 658.12, -0.85, None, "🎯 风险预警命中 (大盘收跌)", "2026-09-11T15:05:00", "2026-09-11T09:15:00", "2026-09-11T15:05:00"),
            (1, "2026-09-10", 45, "yellow", "🟡 黄色注意【分歧加剧】", "T+3~T+5", "测试新闻：经济日报发文活跃资本市场 提高居民财产性收入", "《经济日报》", "政策底信号积极，但高位承接资金尚存分歧，需提防冲高回落。", '["密切跟踪成交量能", "逢高锁定短线利润"]', 2, "2026-09-10T09:15:00", 2721.80, 0.28, 8105.38, 0.22, 1558.93, 0.48, 663.75, 0.35, None, "⏳ 变盘观察期 (多空博弈中)", "2026-09-10T15:05:00", "2026-09-10T09:15:00", "2026-09-10T15:05:00")
        ]
        cursor.executemany('''
            INSERT INTO daily_risk_market_records (
                user_id, trade_date, pre_market_score, pre_market_level, pre_market_level_name,
                lead_time, news_title, news_source, summary, action_guide, risk_record_id,
                pre_market_time, sh_close, sh_change_pct, sz_close, sz_change_pct, cy_close,
                cy_change_pct, kc_close, kc_change_pct, indices_data, validation_status,
                close_time, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', seed_records)

    # Seed extended continuous trading days for user 1 (2026-06 to 2026-09) if dataset is small
    cursor.execute("SELECT COUNT(*) FROM daily_risk_market_records")
    if cursor.fetchone()[0] < 20:
        seed_extended_daily_risk_records(cursor, user_id=1)

    # Insert default OM-STW model if not exists
    cursor.execute("SELECT id FROM risk_models WHERE model_id = 'om_stw'")
    if not cursor.fetchone():
        now_str = datetime.now().isoformat()
        om_stw_prompt = """你是一位资深的证券市场行为金融与宏观风控专家。请基于【OM-STW 官媒舆情见顶与筹码派发预警模型】，对以下输入的新闻事件结合当前A股市场大盘动态历史走势进行深度研判，计算量化风险分值并给出实操避险建议。

【模型核心原理】：
当大盘经过一段上涨或处于中高位时，主流中央官媒（如央视《新闻联播》、《人民日报》、《经济日报》）集中重磅专题报道或普惠性唱多（如“外资爆买”、“让居民通过股票赚钱”、“牛市新起点”），标志着信息传播已触达末端大众层，边际增量买盘枯竭；同时激发的散户一致性亢奋为主力提供了天量接盘流动性，主力借利好出货，市场易在 T+0~T+2（绝壁顶）或 T+3~T+5（诱多顶）迎来深度暴跌。
例外法则：若当前市场处于长周期极度超跌的绝对底部（如2018年2440、2024年初2635点），官媒发声属于“政策底真救市”，触发底部豁免，不作为见顶预警。

【待分析的新闻信息】：
📰 新闻标题：{news_title}
🏛️ 报道媒体/规格：{news_source}
⏰ 报道时间：{news_time}
📄 新闻要点/详细内容：
{news_content}

【当前市场动态历史行情背景】：
{market_context}

【研判评估打分卡（满分100分）】：
1. 媒体出圈度 (Media Tier Index, 权重 30%)：
   - 央视《新闻联播》专题报道（时长>1分钟）：30分
   - 《人民日报》/《经济日报》头版或重磅特评：25分
   - 全网各大财经APP弹窗推送 + 抖音/微博热搜前3：20分
   - 行业主流财经报刊常规报道：10分
2. 技术面位置与拥挤度 (Overbought Index, 权重 30%)：
   - 近20日累计涨幅>25% 且 BIAS20>8%：30分
   - 短期连续大阳拔葱，RSI进入超买区(>80)：25分
   - 中位平台突破，涨幅适中(<10%)：10分
   - 处于历史极限底部、破位超跌区：0分（触发底部豁免）
3. 盘口与资金异动 (Order Flow Index, 权重 25%)：
   - 次日大幅高开后迅速回落，主力资金净流出巨量：25分
   - 全天放天量但K线收假阴线或长上影墓碑线：20分
   - 量价背离（创出新高但成交量明显萎缩）：15分
   - 温和放量上攻且主力净流入：5分
4. 叙事属性与情绪语调 (Narrative Tone, 权重 15%)：
   - 宏大叙事/情绪性造富口号（“外资爆买”、“让居民赚钱”、“牛市新起点”等）：15分
   - 纯产业扶持政策或客观统计数据通报：5分

【预警级别标准】：
- 🔴 红色预警 (75~100分)：【绝壁顶】变盘时间窗 T+0 ~ T+2，锁死买入按键，次日冲高坚决止盈减持7成以上
- 🟠 橙色预警 (60~74分)：【诱多阶段顶】变盘时间窗 T+3 ~ T+5，逢冲高逐步压降总仓位至3成以下
- 🟡 黄色注意 (40~59分)：【分歧加剧】提高警惕，收紧止盈线
- 🟢 绿色安全 (0~39分)：【常态波动/政策底筑底】常态运行，无需恐慌

【输出格式要求（极其重要）】：
必须在回复的最开始严格输出一个 JSON 格式块（由 ```json 和 ``` 包裹），便于系统解析指标，格式如下：
```json
{
  "score": 80,
  "level": "red",
  "level_name": "红色预警【绝壁顶】",
  "lead_time": "T+0 ～ T+2 个交易日",
  "action_guide": [
    "锁死买入按键：坚决禁止追涨任何被报道的热门板块和高位股",
    "次日逢高无条件止盈：利用早盘冲高流动性清仓或减持7成以上高位筹码",
    "警惕主力借利好出逃：谨防大资金利用散户追高流动性大举派发"
  ],
  "breakdown": {
    "media_tier": {"score": 25, "reason": "《经济日报》重磅评论"},
    "technical_overbought": {"score": 25, "reason": "短期拔葱超买"},
    "order_flow": {"score": 15, "reason": "放量滞涨与量价背离"},
    "narrative_tone": {"score": 15, "reason": "出现普惠性造富宏大叙事口号"}
  }
}
```
在 JSON 块之后，请输出适合手机微信直观阅读的详细深度剖析文本（使用清晰段落与丰富 Emoji，勿用 Markdown 粗体与标题符号）。"""
        om_stw_sys = "你是一位资深且敏锐的证券宏观博弈与行为金融风控专家，擅长根据信息传播生命周期理论与市场流动性筹码博弈，识别市场见顶与主力派发出货风险。分析透彻严谨，排版清晰适合手机直观阅读。"
        cursor.execute('''
            INSERT INTO risk_models (
                model_id, name, version, description, category,
                system_prompt, prompt_template, alert_threshold,
                is_enabled, is_default, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
        ''', (
            'om_stw',
            '官媒舆情见顶与筹码派发预警模型 (OM-STW)',
            'v1.0',
            '监控主流官媒集中重磅唱多后引发的社会级出圈、增量买盘衰竭与主力资金借机大举派发出逃风险。',
            'top_warning',
            om_stw_sys,
            om_stw_prompt,
            60,
            now_str,
            now_str
        ))

    # Migrate existing global settings to user_settings for user_id = 1 (admin)
    cursor.execute("SELECT key, value FROM settings")
    old_settings = cursor.fetchall()
    for row in old_settings:
        cursor.execute("INSERT OR IGNORE INTO user_settings (user_id, key, value) VALUES (1, ?, ?)", (row[0], row[1]))

    default_settings = {
        'wxwork_corpid': '',
        'wxwork_agentsecret': '',
        'wxwork_agentid': '1000002',
        'wxwork_touser': '@all',
        'push_enabled': 'true',
        'push_schedule': '30min',
        'push_at_open': 'true',
        'push_at_close': 'true',
        'push_stocks': 'true',
        'push_stocks_only_holding': 'true',
        'push_selected_stock_codes': '',
        'push_funds': 'true',
        'push_funds_only_holding': 'true',
        'push_selected_fund_codes': '',
        'push_pnl': 'true',
        'token': 'messagetoken',
        'encoding_aes_key': 'uFjt1DCRcstr8NGvPFPyPfWUwsaiEeAarzN1GQ12Vmx',
        'deepseek_api_key': '',
        'deepseek_api_url': 'https://api.deepseek.com',
        'deepseek_model': 'deepseek-chat',
        'deepseek_review_enabled': 'true',
        'deepseek_prompt_template': '''你是一位专业且严谨的股市宏观与投资分析专家。请根据以下投资者当前的持仓明细和市场数据，结合大盘环境、板块热点与资金流向、近期政治政策局势、以及全球金融市场动态，撰写一份条理清晰、排版美观且分析透彻的收盘复盘报告（适合手机微信直观阅读，内容尽量详尽充实，无需限制字数）。

当前持仓与市场数据：
{holdings_summary}

复盘与分析要求：
1. 📊【持仓与市场点评】：总结{session_name}持仓的总体盈亏及主要贡献/拉胯品种，结合大盘及核心板块走势分析驱动逻辑；
2. 🌐【宏观与环境分析】：
   - 整体市场环境与大盘走势分析
   - 板块环境与热点资金轮动分析
   - 近期政治局势/宏观政策影响
   - 全球金融市场环境对A股的传导效应
3. 🔮【短中期走势展望】：
   - 短期（未来 7 天）市场走势预测与关键观察点
   - 中期（未来 1 个月）趋势判断与资产配置导向
4. 🎯【操作与风控建议】：针对当前持仓异动与仓位占比，给出具体的后续操作建议（如仓位调整、止盈止损线、加减仓时机等）。

排版与文本格式要求（极其重要）：
- 请直接使用简洁清晰的文本段落与丰富的 Emoji 表达（如 📊、💰、📈、📉、🌐、🔮、🎯、🛡️）；
- 切勿在文中输出包含 **粗体**、### 标题、--- 分割线 等 Markdown 语法符号，确保在手机微信客户端阅读时界面干净利落、直观美观。''',
        'ai_news_analysis_enabled': 'true',
        'ai_news_schedule': '60min',
        'ai_news_prompt_template': '''你是一位顶尖的金融证券分析师与风险控制专家。请结合互联网最新抓取的财经快讯/个股新闻与投资者当前的实际持仓明细，进行深度利好利空分析与风险防范预警。

当前持仓情况：
{holdings_summary}

抓取的互联网最新新闻动态：
{news_summary}

分析要求与架构：
1. 💥【重点新闻利好/利空解读】：精炼解读最新新闻中对投资者持仓品种（包含对应行业板块）有直接或间接影响的关键消息，明确标注利好/利空级别（如：🟢 显著利好 / 🔴 显著利空 / 🟡 中性观望）；
2. 🌊【大盘与板块传导路径】：分析全网大盘快讯及政策/国际市场风向对投资者当前股票与基金资产组合的传导效应；
3. 🛡️【针对性持仓应对策略】：结合持仓盈亏状况与个股/基金占比，给出明确的短中线应对策略（加仓/减仓/观望/止损防范等）。

排版与文本格式要求（极其重要）：
- 请直接使用简洁清晰的段落与 Emoji，排版力求适合手机微信快速阅读；
- 严禁输出 **粗体**、### 标题、--- 分割线 等 Markdown 符号，保持界面利落清晰。''',
        'alert_enabled': 'true',
        'alert_monitored_stock_codes': '',
        'alert_rise_enabled': 'true',
        'alert_rise_pct': '5.0',
        'alert_fall_enabled': 'true',
        'alert_fall_pct': '-5.0',
        'alert_reach_high_enabled': 'true',
        'alert_reach_low_enabled': 'true',
        'alert_swing_enabled': 'true',
        'alert_swing_minutes': '5',
        'alert_swing_pct': '3.0',
        'alert_cooldown_minutes': '15',
        'alert_funds_enabled': 'true',
        'alert_monitored_fund_codes': '',
        'alert_fund_rise_enabled': 'true',
        'alert_fund_rise_pct': '2.0',
        'alert_fund_fall_enabled': 'true',
        'alert_fund_fall_pct': '-2.0',
        'alert_fund_swing_enabled': 'true',
        'alert_fund_swing_minutes': '15',
        'alert_fund_swing_pct': '1.5',
        'calendar_birth_date': '1992-06-25',
        'calendar_birth_time': '07:40',
        'calendar_calendar_type': 'solar',
        'calendar_gender': 'male',
        'calendar_birth_province': '北京市',
        'calendar_birth_city': '北京市',
        'calendar_birth_longitude': '116.4',
        'calendar_true_solar_time': '07:26',
        'calendar_zodiac': '猴',
        'calendar_constellation': '巨蟹座',
        'calendar_wuxing_counts': '{"金": 1, "木": 1, "水": 3, "火": 2, "土": 1}',
        'calendar_bazi_year': '壬申',
        'calendar_bazi_month': '丙午',
        'calendar_bazi_day': '壬辰',
        'calendar_bazi_hour': '甲辰',
        'calendar_bazi_day_master': '壬水',
        'calendar_bazi_favorable': '金, 水, 湿土 (庚辛申酉 / 壬癸亥子 / 辰丑)',
        'calendar_bazi_unfavorable': '燥土, 烈火, 刑冲 (戊未戌 / 丙午 / 寅申冲 / 辰戌冲)',
        'calendar_profit_display_mode': 'amount',
        'calendar_show_metaphysics': 'true',
        'calendar_show_auspicious': 'true',
        'calendar_show_shensha': 'true',
        'calendar_ai_enabled': 'true',
        'calendar_ai_prompt_template': '''你是一位精通中国传统命理易经五行与现代宏观金融投资的顶级资产配置专家。
请根据投资者的生辰八字、今日天干地支五行与易经卦象气场，结合投资者当下的实际股票/基金持仓数据以及今日国内外重大金融财经大事，进行全方位的综合复盘研判，并给出今日最终的专业投资操作建议。

【投资者命理信息】：
{bazi_info}

【今日时空易象】：
{calendar_day_info}

【投资者当前实际持仓】：
{stock_holdings}
{fund_holdings}
{portfolio_summary}

【今日世界与国内金融重大要闻】：
{financial_events}

【分析与建议要求】：
1. ☯️【五行气场与持仓行业共振】：分析今日干支与卦象对投资者日主的生克制化，以及对持仓资产所处行业（半导体科技、新能源/锂电、AI/数字经济等）的五行利弊影响；
2. 🌍【国内外宏观金融要闻传导】：研判全球资本市场风向及国内政策/大盘资金面变动，对持仓品种产生的利好或利空冲击；
3. 🎯【今日终极投资操作建议】：明确给出针对当前持仓的具体操作决策（如：逢高止盈减仓、逆势分批低吸、卧倒坚守、防范刑冲洗盘风险等），并给出仓位控制指引；
4. 🔮【次日/后市关键观察信号】：给出投资者接下来的关键防守位或进攻观察点。

排版要求：
- 请使用清晰工整的段落与 Emoji（如 ☯️、📊、🌍、🎯、🔮、🛡️、💡），语言专业有力、逻辑严密、切中要害，便于随时复盘核验。''',
        'risk_cron_enabled': 'true',
        'risk_cron_time': '20:30',
        'risk_default_model_id': 'om_stw',
        'risk_notify_wx': 'true',
        'risk_alert_threshold': '60'
    }

    cursor.execute("SELECT id FROM users")
    all_users = cursor.fetchall()
    for u in all_users:
        uid = u[0]
        for k, v in default_settings.items():
            cursor.execute("INSERT OR IGNORE INTO user_settings (user_id, key, value) VALUES (?, ?, ?)", (uid, k, v))

    conn.commit()
    conn.close()

    try:
        from services.strategy.strategy_service import init_strategy_tables
        init_strategy_tables()
    except Exception as e:
        print(f"[DB] Error initializing strategy tables: {e}")

def init_user_default_settings(user_id: int):
    default_settings = {
        'wxwork_corpid': '',
        'wxwork_agentsecret': '',
        'wxwork_agentid': '1000002',
        'wxwork_touser': '@all',
        'push_enabled': 'false',
        'push_schedule': '30min',
        'push_at_open': 'true',
        'push_at_close': 'true',
        'push_stocks': 'true',
        'push_stocks_only_holding': 'true',
        'push_selected_stock_codes': '',
        'push_funds': 'true',
        'push_funds_only_holding': 'true',
        'push_selected_fund_codes': '',
        'push_pnl': 'true',
        'token': 'messagetoken',
        'encoding_aes_key': 'uFjt1DCRcstr8NGvPFPyPfWUwsaiEeAarzN1GQ12Vmx',
        'deepseek_api_key': '',
        'deepseek_api_url': 'https://api.deepseek.com',
        'deepseek_model': 'deepseek-chat',
        'deepseek_review_enabled': 'false',
        'deepseek_prompt_template': '''你是一位专业且严谨的股市宏观与投资分析专家。请根据以下投资者当前的持仓明细和市场数据，结合大盘环境、板块热点与资金流向、近期政治政策局势、以及全球金融市场动态，撰写一份条理清晰、排版美观且分析透彻的收盘复盘报告（适合手机微信直观阅读，内容尽量详尽充实，无需限制字数）。

当前持仓与市场数据：
{holdings_summary}

复盘与分析要求：
1. 📊【持仓与市场点评】：总结{session_name}持仓的总体盈亏及主要贡献/拉胯品种，结合大盘及核心板块走势分析驱动逻辑；
2. 🌐【宏观与环境分析】：
   - 整体市场环境与大盘走势分析
   - 板块环境与热点资金轮动分析
   - 近期政治局势/宏观政策影响
   - 全球金融市场环境对A股的传导效应
3. 🔮【短中期走势展望】：
   - 短期（未来 7 天）市场走势预测与关键观察点
   - 中期（未来 1 个月）趋势判断与资产配置导向
4. 🎯【操作与风控建议】：针对当前持仓异动与仓位占比，给出具体的后续操作建议（如仓位调整、止盈止损线、加减仓时机等）。

排版与文本格式要求（极其重要）：
- 请直接使用简洁清晰的文本段落与丰富的 Emoji 表达（如 📊、💰、📈、📉、🌐、🔮、🎯、🛡️）；
- 切勿在文中输出包含 **粗体**、### 标题、--- 分割线 等 Markdown 语法符号，确保在手机微信客户端阅读时界面干净利落、直观美观。''',
        'ai_news_analysis_enabled': 'false',
        'ai_news_schedule': '60min',
        'ai_news_prompt_template': '''你是一位顶尖的金融证券分析师与风险控制专家。请结合互联网最新抓取的财经快讯/个股新闻与投资者当前的实际持仓明细，进行深度利好利空分析与风险防范预警。

当前持仓情况：
{holdings_summary}

抓取的互联网最新新闻动态：
{news_summary}

分析要求与架构：
1. 💥【重点新闻利好/利空解读】：精炼解读最新新闻中对投资者持仓品种（包含对应行业板块）有直接或间接影响的关键消息，明确标注利好/利空级别（如：🟢 显著利好 / 🔴 显著利空 / 🟡 中性观望）；
2. 🌊【大盘与板块传导路径】：分析全网大盘快讯及政策/国际市场风向对投资者当前股票与基金资产组合的传导效应；
3. 🛡️【针对性持仓应对策略】：结合持仓盈亏状况与个股/基金占比，给出明确的短中线应对策略（加仓/减仓/观望/止损防范等）。

排版与文本格式要求（极其重要）：
- 请直接使用简洁清晰的段落与 Emoji，排版力求适合手机微信快速阅读；
- 严禁输出 **粗体**、### 标题、--- 分割线 等 Markdown 符号，保持界面利落清晰。''',
        'alert_enabled': 'false',
        'alert_monitored_stock_codes': '',
        'alert_rise_enabled': 'true',
        'alert_rise_pct': '5.0',
        'alert_fall_enabled': 'true',
        'alert_fall_pct': '-5.0',
        'alert_reach_high_enabled': 'true',
        'alert_reach_low_enabled': 'true',
        'alert_swing_enabled': 'true',
        'alert_swing_minutes': '5',
        'alert_swing_pct': '3.0',
        'alert_cooldown_minutes': '15',
        'alert_funds_enabled': 'true',
        'alert_monitored_fund_codes': '',
        'alert_fund_rise_enabled': 'true',
        'alert_fund_rise_pct': '2.0',
        'alert_fund_fall_enabled': 'true',
        'alert_fund_fall_pct': '-2.0',
        'alert_fund_swing_enabled': 'true',
        'alert_fund_swing_minutes': '15',
        'alert_fund_swing_pct': '1.5',
        'calendar_birth_date': '1992-06-25',
        'calendar_birth_time': '07:40',
        'calendar_calendar_type': 'solar',
        'calendar_gender': 'male',
        'calendar_birth_province': '北京市',
        'calendar_birth_city': '北京市',
        'calendar_birth_longitude': '116.4',
        'calendar_true_solar_time': '07:26',
        'calendar_zodiac': '猴',
        'calendar_constellation': '巨蟹座',
        'calendar_wuxing_counts': '{"金": 1, "木": 1, "水": 3, "火": 2, "土": 1}',
        'calendar_bazi_year': '壬申',
        'calendar_bazi_month': '丙午',
        'calendar_bazi_day': '壬辰',
        'calendar_bazi_hour': '甲辰',
        'calendar_bazi_day_master': '壬水',
        'calendar_bazi_favorable': '金, 水, 湿土 (庚辛申酉 / 壬癸亥子 / 辰丑)',
        'calendar_bazi_unfavorable': '燥土, 烈火, 刑冲 (戊未戌 / 丙午 / 寅申冲 / 辰戌冲)',
        'calendar_profit_display_mode': 'amount',
        'calendar_show_metaphysics': 'true',
        'calendar_show_auspicious': 'true',
        'calendar_ai_enabled': 'true',
        'calendar_ai_prompt_template': '''你是一位精通中国传统命理易经五行与现代宏观金融投资的顶级资产配置专家。
请根据投资者的生辰八字、今日天干地支五行与易经卦象气场，结合投资者当下的实际股票/基金持仓数据以及今日国内外重大金融财经大事，进行全方位的综合复盘研判，并给出今日最终的专业投资操作建议。

【投资者命理信息】：
{bazi_info}

【今日时空易象】：
{calendar_day_info}

【投资者当前实际持仓】：
{stock_holdings}
{fund_holdings}
{portfolio_summary}

【今日世界与国内金融重大要闻】：
{financial_events}

【分析与建议要求】：
1. ☯️【五行气场与持仓行业共振】：分析今日干支与卦象对投资者日主的生克制化，以及对持仓资产所处行业（半导体科技、新能源/锂电、AI/数字经济等）的五行利弊影响；
2. 🌍【国内外宏观金融要闻传导】：研判全球资本市场风向及国内政策/大盘资金面变动，对持仓品种产生的利好或利空冲击；
3. 🎯【今日终极投资操作建议】：明确给出针对当前持仓的具体操作决策（如：逢高止盈减仓、逆势分批低吸、卧倒坚守、防范刑冲洗盘风险等），并给出仓位控制指引；
4. 🔮【次日/后市关键观察信号】：给出投资者接下来的关键防守位或进攻观察点。

排版要求：
- 请使用清晰工整的段落与 Emoji（如 ☯️、📊、🌍、🎯、🔮、🛡️、💡），语言专业有力、逻辑严密、切中要害，便于随时复盘核验。''',
        'risk_cron_enabled': 'true',
        'risk_cron_time': '20:30',
        'risk_default_model_id': 'om_stw',
        'risk_notify_wx': 'true',
        'risk_alert_threshold': '60'
    }
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for k, v in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO user_settings (user_id, key, value) VALUES (?, ?, ?)", (user_id, k, v))
    conn.commit()
    conn.close()

def get_settings_dict(user_id: int = 1):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM user_settings WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    settings = {}
    for row in rows:
        val = row[1]
        if val in ('true', 'false'):
            settings[row[0]] = val == 'true'
        else:
            settings[row[0]] = val
    return settings

def update_settings_dict(user_id: int, updates: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for k, v in updates.items():
        if isinstance(v, bool):
            val = 'true' if v else 'false'
        else:
            val = str(v)
        cursor.execute("UPDATE user_settings SET value = ? WHERE user_id = ? AND key = ?", (val, user_id, k))
        if cursor.rowcount == 0:
            cursor.execute("INSERT INTO user_settings (user_id, key, value) VALUES (?, ?, ?)", (user_id, k, val))
    conn.commit()
    conn.close()

