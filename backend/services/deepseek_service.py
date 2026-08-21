"""
Backward compatibility proxy for deepseek_service module.
All core AI logic is now maintained in ai_service.py.
"""
from services.ai_service import (
    clean_markdown_for_wechat,
    format_holdings_summary,
    call_llm_chat,
    run_deepseek_review,
    run_ai_news_analysis
)

__all__ = [
    "clean_markdown_for_wechat",
    "format_holdings_summary",
    "call_llm_chat",
    "run_deepseek_review",
    "run_ai_news_analysis"
]
