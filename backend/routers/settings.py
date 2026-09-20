from fastapi import APIRouter, Depends
from models import SettingsUpdate
from database import get_settings_dict, update_settings_dict
from services.wxwork_service import send_wxwork_message
from routers.auth import get_current_user

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("")
def get_settings(current_user: dict = Depends(get_current_user)):
    return get_settings_dict(user_id=current_user['id'])

@router.put("")
def update_settings(settings: SettingsUpdate, current_user: dict = Depends(get_current_user)):
    updates = settings.model_dump(exclude_unset=True)
    if updates:
        update_settings_dict(current_user['id'], updates)
        # 如果更新了数据源配置或分析相关参数，立即清除数据分析缓存
        if any(k in updates for k in ('data_source_provider', 'mx_api_key', 'data_analysis_max_panels')):
            from services.data_analysis_service import clear_user_analysis_cache
            clear_user_analysis_cache(current_user['id'])
    return get_settings_dict(user_id=current_user['id'])

@router.post("/test-push")
def test_push(current_user: dict = Depends(get_current_user)):
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"✅ 股票基金监控系统 测试推送 ({current_user['username']})\n发送时间：{now}\n企业微信配置正常，推送功能运行中。"
    user_settings = get_settings_dict(current_user['id'])
    success, detail = send_wxwork_message(msg, settings_override=user_settings)
    return {"success": success, "message": detail}

@router.post("/test-format-push")
async def test_format_push(current_user: dict = Depends(get_current_user)):
    from services.scheduler import format_and_push_message
    try:
        success, detail = await format_and_push_message(user_id=current_user['id'])
        return {"success": success, "message": detail}
    except Exception as e:
        print(f"[test-format-push] Error: {e}")
        return {"success": False, "message": f"生成推送快报异常: {str(e)}"}

@router.post("/test-deepseek-review")
async def test_deepseek_review(current_user: dict = Depends(get_current_user)):
    from services.ai_service import run_deepseek_review
    try:
        success, message = await run_deepseek_review(session_name="测试复盘", push_to_wx=True, user_id=current_user['id'])
        return {"success": success, "message": message}
    except Exception as e:
        print(f"[test-deepseek-review] Error: {e}")
        return {"success": False, "message": f"DeepSeek 复盘测试异常: {str(e)}"}

@router.post("/test-ai-news-analysis")
async def test_ai_news_analysis(current_user: dict = Depends(get_current_user)):
    from services.ai_service import run_ai_news_analysis
    try:
        success, message = await run_ai_news_analysis(push_to_wx=True, user_id=current_user['id'])
        return {"success": success, "message": message}
    except Exception as e:
        print(f"[test-ai-news-analysis] Error: {e}")
        return {"success": False, "message": f"AI 新闻分析测试异常: {str(e)}"}

@router.post("/test-alert-push")
async def test_alert_push(current_user: dict = Depends(get_current_user)):
    from services.alert_service import simulate_test_alert
    try:
        success, message = await simulate_test_alert(user_id=current_user['id'])
        return {"success": success, "message": message}
    except Exception as e:
        print(f"[test-alert-push] Error: {e}")
        return {"success": False, "message": f"股票异动预警测试异常: {str(e)}"}



