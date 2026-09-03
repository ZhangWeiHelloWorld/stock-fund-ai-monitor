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
- 请使用清晰工整的段落与 Emoji（如 ☯️、📊、🌍、🎯、🔮、🛡️、💡），语言专业有力、逻辑严密、切中要害，便于随时复盘核验。'''
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
- 请使用清晰工整的段落与 Emoji（如 ☯️、📊、🌍、🎯、🔮、🛡️、💡），语言专业有力、逻辑严密、切中要害，便于随时复盘核验。'''
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

