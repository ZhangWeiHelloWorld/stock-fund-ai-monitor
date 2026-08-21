import re
import httpx
from datetime import datetime
from database import get_settings_dict
from services.market_service import get_market_overview
from services.news_service import get_combined_news_context
from services.wxwork_service import send_wxwork_message

DEFAULT_REVIEW_PROMPT = """你是一位专业且严谨的股市宏观与投资分析专家。请根据以下投资者当前的持仓明细和市场数据，结合大盘环境、板块热点与资金流向、近期政治政策局势、以及全球金融市场动态，撰写一份条理清晰、排版美观且分析透彻的收盘复盘报告（适合手机微信直观阅读，内容尽量详尽充实，无需限制字数）。

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
- 请直接使用简洁清晰的文本段落与丰富的 Emoji 表达；
- 切勿在文中输出包含 **粗体**、### 标题、--- 分割线 等 Markdown 语法符号，确保在手机微信客户端阅读时界面干净利落。"""

DEFAULT_NEWS_ANALYSIS_PROMPT = """你是一位顶尖的金融证券分析师与风险控制专家。请结合互联网最新抓取的财经快讯/个股新闻与投资者当前的实际持仓明细，进行深度利好利空分析与风险防范预警。

当前持仓情况：
{holdings_summary}

抓取的互联网最新新闻动态：
{news_summary}

分析要求与架构：
1. 💥【重点新闻利好/利空解读】：精炼解读最新新闻中对投资者持仓品种（包含对应行业板块）有直接或间接影响的关键消息，明确标注利好/利空级别（如：🟢 显著利好 / 🔴 显著利空 / 🟡 中性观望）；
2. 🌊【大盘与板块传导路径】：分析全网大盘快讯及政策/国际市场风向对投资者当前股票与基金资产组合的传导效应；
3. 🛡️【针对性持仓应对策略】：结合持仓盈亏状况与个股/基金占比，给出明确的短中线应对策略（加仓/减仓/观望/止损防范等）。

排版与文本格式要求（极其重要）：
- 请直接使用简洁清晰的段落与 Emoji（如 📰、📊、🟢、🔴、🟡、🛡️、💡），排版力求适合手机微信快速阅读；
- 严禁输出 **粗体**、### 标题、--- 分割线 等 Markdown 符号，保持界面利落清晰。"""


def clean_markdown_for_wechat(text: str) -> str:
    """清理 Markdown 标志（如 **, ###, ---），转换为微信友好呈现的干净纯文本"""
    text = re.sub(r'^[-\*]{3,}\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def format_holdings_summary(overview: dict, session_name: str = "持仓概览") -> str:
    now = datetime.now()
    date_str = now.strftime("%Y/%m/%d")
    time_str = now.strftime("%H:%M")

    summary = overview.get('summary', {})
    total_day_profit = summary.get('total_day_profit', 0.0)
    total_profit = summary.get('total_profit', 0.0)

    lines = [
        f"【持仓概览与市场行情 - {date_str} {time_str} {session_name}】",
        f"💰 今日总盈亏: {total_day_profit:+.2f} 元",
        f"💰 累计总盈亏: {total_profit:+.2f} 元",
        ""
    ]

    stocks = overview.get('stocks', [])
    holding_stocks = [s for s in stocks if s.get('is_holding')]
    if holding_stocks:
        lines.append(f"📈 股票持仓明细 (共 {len(holding_stocks)} 只):")
        for s in holding_stocks:
            name = s.get('name', '未知')
            code = s.get('code', '')
            price = s.get('current_price', 0.0)
            change = s.get('change_pct', 0.0)
            shares = s.get('shares', 0)
            cost = s.get('cost_price', 0.0)
            dp = s.get('day_profit', 0.0)
            tp = s.get('total_profit', 0.0)
            lines.append(
                f"- {name}({code}): 现价 {price:.2f} 元 (涨跌幅 {change:+.2f}%), "
                f"持股 {shares:.0f} 股, 成本 {cost:.2f} 元, 今日盈亏 {dp:+.2f} 元, 累计盈亏 {tp:+.2f} 元"
            )
        lines.append("")
    else:
        lines.append("📈 股票持仓明细: 暂无持仓股票\n")

    funds = overview.get('funds', [])
    holding_funds = [f for f in funds if f.get('is_holding')]
    if holding_funds:
        lines.append(f"📦 基金持仓明细 (共 {len(holding_funds)} 只):")
        for f in holding_funds:
            name = f.get('name', '未知')
            code = f.get('code', '')
            nav = f.get('current_nav', 0.0)
            change = f.get('change_pct', 0.0)
            shares = f.get('shares', 0)
            cost = f.get('cost_nav', 0.0)
            dp = f.get('day_profit', 0.0)
            tp = f.get('total_profit', 0.0)
            is_updated = f.get('is_updated', False)
            nav_tag = "最新净值" if is_updated else "实时估值"
            lines.append(
                f"- {name}({code}): {nav_tag} {nav:.4f} (涨跌幅 {change:+.2f}%), "
                f"持有 {shares:.2f} 份, 成本 {cost:.4f}, 今日盈亏 {dp:+.2f} 元, 累计盈亏 {tp:+.2f} 元"
            )
        lines.append("")
    else:
        lines.append("📦 基金持仓明细: 暂无持仓基金\n")

    return "\n".join(lines).strip()


async def call_llm_chat(
    prompt: str,
    system_prompt: str = "你是一位专业的金融证券分析师及资产配置专家，擅长结合宏观、行业板块与政治金融大局深入分析市场，分析内容详尽充实、条理清晰，不受字数限制，排版适合微信直观阅读。",
    user_id: int = 1,
    temperature: float = 0.7,
    max_tokens: int = 4000
) -> tuple[bool, str]:
    """
    独立通用的 LLM 基础模型调用逻辑，读取用户设定的 API Key、Base URL、Model 等配置。
    支持 DeepSeek、OpenAI、Qwen、Moonshot 等任何兼容 OpenAI Chat Completions 规范的服务端点。
    """
    settings = get_settings_dict(user_id=user_id)

    api_key = settings.get("deepseek_api_key", "").strip()
    if not api_key:
        return False, "⚠️ AI 大模型 API Key 未配置，请先在系统设置中配置 DeepSeek / LLM API Key"

    raw_api_url = settings.get("deepseek_api_url", "https://api.deepseek.com").strip().rstrip("/")
    model = settings.get("deepseek_model", "deepseek-chat").strip() or "deepseek-chat"

    # 规范化 Endpoint
    if "/chat/completions" in raw_api_url:
        endpoint = raw_api_url
    elif raw_api_url.endswith("/v1"):
        endpoint = f"{raw_api_url}/chat/completions"
    else:
        endpoint = f"{raw_api_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            res_data = response.json()
            ai_content = res_data["choices"][0]["message"]["content"].strip()
            ai_content = clean_markdown_for_wechat(ai_content)
            return True, ai_content
    except httpx.HTTPStatusError as e:
        err_detail = e.response.text if e.response else str(e)
        return False, f"LLM API 请求失败 [{e.response.status_code}]: {err_detail}"
    except Exception as e:
        return False, f"LLM API 调用异常: {str(e)}"


async def run_deepseek_review(session_name: str = "收盘复盘", push_to_wx: bool = True, user_id: int = 1) -> tuple[bool, str]:
    """交易日午盘/收盘自动复盘功能"""
    settings = get_settings_dict(user_id=user_id)
    prompt_template = settings.get("deepseek_prompt_template", "").strip() or DEFAULT_REVIEW_PROMPT

    try:
        overview = await get_market_overview(user_id=user_id)
        holdings_summary = format_holdings_summary(overview, session_name)
    except Exception as e:
        return False, f"获取持仓及行情数据失败: {str(e)}"

    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")

    prompt = prompt_template.replace("{holdings_summary}", holdings_summary)
    prompt = prompt.replace("{session_name}", session_name)
    prompt = prompt.replace("{date_str}", now_str)

    if holdings_summary not in prompt:
        prompt += f"\n\n【补充当前持仓及数据】:\n{holdings_summary}"

    success, ai_content = await call_llm_chat(prompt=prompt, user_id=user_id)
    if not success:
        return False, ai_content

    formatted_msg = (
        f"🤖 DeepSeek AI {session_name}\n"
        f"⏰ 时间：{now_str}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{ai_content}"
    )

    if push_to_wx:
        push_success, push_detail = send_wxwork_message(formatted_msg, user_id=user_id)
        if not push_success:
            return False, f"AI复盘生成成功，但推送企业微信失败: {push_detail}"

    return True, formatted_msg


async def run_ai_news_analysis(push_to_wx: bool = True, user_id: int = 1) -> tuple[bool, str]:
    """AI 互联网实时新闻持仓影响分析功能"""
    settings = get_settings_dict(user_id=user_id)
    prompt_template = settings.get("ai_news_prompt_template", "").strip() or DEFAULT_NEWS_ANALYSIS_PROMPT

    try:
        overview = await get_market_overview(user_id=user_id)
        holdings_summary = format_holdings_summary(overview, "新闻影响分析")
        
        stocks = overview.get('stocks', [])
        funds = overview.get('funds', [])
        holding_stocks = [s for s in stocks if s.get('is_holding')]
        holding_funds = [f for f in funds if f.get('is_holding')]

        news_summary = await get_combined_news_context(holding_stocks, holding_funds)
    except Exception as e:
        return False, f"获取持仓或新闻数据异常: {str(e)}"

    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")

    prompt = prompt_template.replace("{holdings_summary}", holdings_summary)
    prompt = prompt.replace("{news_summary}", news_summary)
    prompt = prompt.replace("{date_str}", now_str)

    if holdings_summary not in prompt:
        prompt += f"\n\n【补充持仓明细】:\n{holdings_summary}"
    if news_summary not in prompt:
        prompt += f"\n\n【补充抓取的新闻】:\n{news_summary}"

    success, ai_content = await call_llm_chat(
        prompt=prompt,
        system_prompt="你是一位资深的证券分析师，擅长结合互联网最新新闻分析对股票基金持仓的影响，分析专业严谨、排版清爽适合微信阅读。",
        user_id=user_id
    )
    if not success:
        return False, ai_content

    formatted_msg = (
        f"📰 DeepSeek AI 实时持仓新闻影响分析\n"
        f"⏰ 分析时间：{now_str}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{ai_content}"
    )

    if push_to_wx:
        push_success, push_detail = send_wxwork_message(formatted_msg, user_id=user_id)
        if not push_success:
            return False, f"AI新闻分析完成，但推送企业微信失败: {push_detail}"

    return True, formatted_msg
