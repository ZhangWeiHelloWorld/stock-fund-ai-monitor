from fastapi import APIRouter, Depends
from services.market_service import get_market_overview, fetch_market_indices
from routers.auth import get_current_user

router = APIRouter(prefix="/api/market", tags=["market"])

@router.get("/indices")
async def market_indices(current_user: dict = Depends(get_current_user)):
    indices = await fetch_market_indices()
    return indices

@router.get("/overview")
async def market_overview(current_user: dict = Depends(get_current_user)):
    overview = await get_market_overview(user_id=current_user['id'], force_refresh=False)
    return overview

@router.get("/refresh")
async def market_refresh(current_user: dict = Depends(get_current_user)):
    overview = await get_market_overview(user_id=current_user['id'], force_refresh=True)
    return overview


import sqlite3
from database import DB_PATH
from datetime import datetime, timedelta

@router.get("/history")
async def market_history(days: int = 30, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    cursor.execute('''
        SELECT date, stock_profit, fund_profit, total_profit, stock_asset, fund_asset, total_asset 
        FROM history_profits 
        WHERE user_id = ? AND date >= ?
        ORDER BY date ASC
    ''', (current_user['id'], start_date))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]
