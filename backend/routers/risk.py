import json
import sqlite3
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query

from database import DB_PATH
from models import (
    RiskModelCreate,
    RiskModelUpdate,
    AnalyzeManualNewsRequest,
    AnalyzeCrawlNewsRequest,
    DailyRiskSnapshotRequest,
    DailyRiskSyncCloseRequest,
    DailyRiskRecordUpdate
)
from routers.auth import get_current_user
from services.om_stw_service import (
    analyze_news_with_model,
    fetch_official_media_macro_news,
    get_dynamic_market_context,
    format_risk_alert_wx_message,
    record_daily_pre_market_risk,
    record_daily_market_close,
    get_daily_risk_market_records,
    update_daily_risk_market_record,
    get_daily_risk_analytics_summary
)
from services.wxwork_service import send_wxwork_message

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("/models")
def get_risk_models(current_user: dict = Depends(get_current_user)):
    """List all configured risk analysis models."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM risk_models ORDER BY is_default DESC, id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/models")
def create_risk_model(model_in: RiskModelCreate, current_user: dict = Depends(get_current_user)):
    """Add a new analysis model."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    try:
        cursor.execute('''
            INSERT INTO risk_models (
                model_id, name, version, description, category,
                system_prompt, prompt_template, alert_threshold,
                is_enabled, is_default, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            model_in.model_id.strip(),
            model_in.name.strip(),
            model_in.version or "v1.0",
            model_in.description or "",
            model_in.category or "top_warning",
            model_in.system_prompt or "",
            model_in.prompt_template,
            model_in.alert_threshold or 60,
            1 if model_in.is_enabled else 0,
            1 if model_in.is_default else 0,
            now_str,
            now_str
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail=f"模型 ID '{model_in.model_id}' 已存在")
    finally:
        conn.close()

    return {"message": "模型创建成功", "model_id": model_in.model_id}


@router.put("/models/{model_id}")
def update_risk_model(
    model_id: str,
    updates: RiskModelUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing model's prompt, rules, or settings."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM risk_models WHERE model_id = ?", (model_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail=f"未找到模型 '{model_id}'")

    update_dict = updates.model_dump(exclude_unset=True)
    if not update_dict:
        conn.close()
        return {"message": "无更新字段"}

    fields = []
    values = []
    for k, v in update_dict.items():
        if k in ("is_enabled", "is_default"):
            v = 1 if v else 0
        fields.append(f"{k} = ?")
        values.append(v)

    fields.append("updated_at = ?")
    values.append(datetime.now().isoformat())
    values.append(model_id)

    cursor.execute(f"UPDATE risk_models SET {', '.join(fields)} WHERE model_id = ?", tuple(values))
    conn.commit()
    conn.close()

    return {"message": "模型配置已更新", "model_id": model_id}


@router.delete("/models/{model_id}")
def delete_risk_model(model_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a custom risk model (default model 'om_stw' cannot be deleted)."""
    if model_id == "om_stw":
        raise HTTPException(status_code=400, detail="默认核心模型 'om_stw' 禁止删除")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM risk_models WHERE model_id = ?", (model_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail=f"未找到模型 '{model_id}'")
    conn.commit()
    conn.close()

    return {"message": "模型已删除", "model_id": model_id}


@router.get("/market-context")
async def get_market_context_api(current_user: dict = Depends(get_current_user)):
    """Get live market historical metrics used by risk models."""
    return await get_dynamic_market_context()


@router.get("/official-news")
async def get_official_news_list(
    limit: int = Query(15, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Fetch recent official media macro news items (noise-filtered)."""
    return await fetch_official_media_macro_news(limit=limit)


@router.post("/analyze/manual")
async def analyze_manual_news(
    req: AnalyzeManualNewsRequest,
    current_user: dict = Depends(get_current_user)
):
    """Execute AI risk analysis on manually inputted news."""
    res = await analyze_news_with_model(
        news_title=req.news_title.strip(),
        news_source=req.news_source or "央视《新闻联播》",
        news_time=req.news_time,
        news_content=req.news_content or "",
        model_id=req.model_id or "om_stw",
        user_id=current_user["id"],
        trigger_type="manual_input",
        push_to_wx=bool(req.push_to_wx)
    )
    return res


@router.post("/analyze/crawl")
async def analyze_crawled_news(
    req: AnalyzeCrawlNewsRequest,
    current_user: dict = Depends(get_current_user)
):
    """Crawl internet official media news and analyze the top macro event."""
    news_items = await fetch_official_media_macro_news(limit=req.limit or 10)
    if not news_items:
        raise HTTPException(status_code=404, detail="未抓取到当期中央官媒宏观新闻")

    top_news = news_items[0]
    res = await analyze_news_with_model(
        news_title=top_news["title"],
        news_source=top_news.get("source", "权威官媒"),
        news_time=top_news.get("time"),
        news_content=top_news.get("content", top_news["title"]),
        model_id=req.model_id or "om_stw",
        user_id=current_user["id"],
        trigger_type="manual_crawl",
        push_to_wx=bool(req.push_to_wx)
    )
    res["crawled_pool_count"] = len(news_items)
    return res


@router.get("/records")
def get_risk_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    level: Optional[str] = None,
    model_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get paginated risk analysis records for current user."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM risk_analysis_records WHERE user_id = ?"
    params: List[Any] = [current_user["id"]]

    if level:
        query += " AND level = ?"
        params.append(level)
    if model_id:
        query += " AND model_id = ?"
        params.append(model_id)

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    offset = (page - 1) * page_size
    params.extend([page_size, offset])

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()

    # Total count
    count_query = "SELECT COUNT(*) FROM risk_analysis_records WHERE user_id = ?"
    count_params: List[Any] = [current_user["id"]]
    if level:
        count_query += " AND level = ?"
        count_params.append(level)
    if model_id:
        count_query += " AND model_id = ?"
        count_params.append(model_id)
    cursor.execute(count_query, tuple(count_params))
    total = cursor.fetchone()[0]

    conn.close()

    items = []
    for r in rows:
        d = dict(r)
        if d.get("action_guide"):
            try:
                d["action_guide"] = json.loads(d["action_guide"])
            except Exception:
                pass
        if d.get("breakdown"):
            try:
                d["breakdown"] = json.loads(d["breakdown"])
            except Exception:
                pass
        items.append(d)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/records/latest")
def get_latest_risk_record(current_user: dict = Depends(get_current_user)):
    """Get the most recent risk analysis record."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM risk_analysis_records WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (current_user["id"],)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    d = dict(row)
    if d.get("action_guide"):
        try:
            d["action_guide"] = json.loads(d["action_guide"])
        except Exception:
            pass
    if d.get("breakdown"):
        try:
            d["breakdown"] = json.loads(d["breakdown"])
        except Exception:
            pass
    return d


@router.get("/records/{record_id}")
def get_risk_record_detail(record_id: int, current_user: dict = Depends(get_current_user)):
    """Get single record detail."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM risk_analysis_records WHERE id = ? AND user_id = ?", (record_id, current_user["id"]))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="未找到该分析记录")

    d = dict(row)
    if d.get("action_guide"):
        try:
            d["action_guide"] = json.loads(d["action_guide"])
        except Exception:
            pass
    if d.get("breakdown"):
        try:
            d["breakdown"] = json.loads(d["breakdown"])
        except Exception:
            pass
    return d


@router.delete("/records/{record_id}")
def delete_risk_record(record_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a risk analysis record."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM risk_analysis_records WHERE id = ? AND user_id = ?", (record_id, current_user["id"]))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="未找到该分析记录")
    conn.commit()
    conn.close()
    return {"message": "记录已删除"}


@router.post("/records/{record_id}/push-wx")
def push_record_to_wx(record_id: int, current_user: dict = Depends(get_current_user)):
    """Re-push an existing analysis record to Enterprise WeChat."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM risk_analysis_records WHERE id = ? AND user_id = ?", (record_id, current_user["id"]))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="未找到该分析记录")

    rec = dict(row)
    wx_msg = format_risk_alert_wx_message(rec)
    success, detail = send_wxwork_message(wx_msg, user_id=current_user["id"])

    if success:
        cursor.execute("UPDATE risk_analysis_records SET pushed_to_wx = 1 WHERE id = ?", (record_id,))
        conn.commit()

    conn.close()
    return {"success": success, "message": detail}


@router.get("/daily-records")
async def get_daily_risk_records_api(
    limit: int = Query(100, ge=1, le=500),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get historical daily pre-market risk warnings and day-close indices points tracking.
    """
    return await get_daily_risk_market_records(
        user_id=current_user["id"],
        limit=limit,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/daily-records/analytics")
async def get_daily_risk_analytics_api(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get quantitative analytics (Pearson correlation, win rate, tier returns, attribution counts).
    """
    return await get_daily_risk_analytics_summary(
        user_id=current_user["id"],
        start_date=start_date,
        end_date=end_date
    )


@router.post("/daily-records/snapshot-premarket")
async def snapshot_premarket_risk_api(
    req: DailyRiskSnapshotRequest = DailyRiskSnapshotRequest(),
    current_user: dict = Depends(get_current_user)
):
    """
    Manually take a pre-market risk evaluation snapshot for a trading day (defaults to today).
    """
    record = await record_daily_pre_market_risk(
        user_id=current_user["id"],
        trade_date=req.trade_date,
        risk_record_id=req.risk_record_id
    )
    return {"message": "开盘前风险快照已记录", "data": record}


@router.post("/daily-records/sync-close")
async def sync_close_indices_api(
    req: DailyRiskSyncCloseRequest = DailyRiskSyncCloseRequest(),
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch and sync today's/specified date's market closing points for indices (上证, 深成, 创业板, 科创50等).
    """
    records = await record_daily_market_close(
        trade_date=req.trade_date,
        user_id=current_user["id"]
    )
    return {"message": "各大指数收盘点数已同步回填", "data": records[0] if records else None}


@router.put("/daily-records/{record_id}")
def update_daily_record_api(
    record_id: int,
    updates: DailyRiskRecordUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update or adjust a daily record.
    """
    update_dict = updates.model_dump(exclude_unset=True)
    try:
        updated = update_daily_risk_market_record(
            record_id=record_id,
            user_id=current_user["id"],
            updates=update_dict
        )
        return {"message": "记录已更新", "data": updated}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

