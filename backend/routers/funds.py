from fastapi import APIRouter, Depends, HTTPException
import sqlite3
from typing import List
from models import Fund, FundCreate, FundUpdate
from database import DB_PATH
from datetime import datetime
from routers.auth import get_current_user

from services.market_service import fetch_fund_data

router = APIRouter(prefix="/api/funds", tags=["funds"])

@router.get("/lookup/{code}")
async def lookup_fund(code: str, current_user: dict = Depends(get_current_user)):
    data = await fetch_fund_data([code])
    res = data.get(code, {})
    return {
        "code": code,
        "name": res.get("name", ""),
        "current_nav": res.get("current_nav", 0)
    }

@router.get("", response_model=List[Fund])
def list_funds(current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM funds WHERE user_id = ? ORDER BY id DESC", (current_user['id'],))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@router.post("", response_model=Fund)
async def create_fund(fund: FundCreate, current_user: dict = Depends(get_current_user)):
    name = (fund.name or "").strip()
    if not name or name == fund.code:
        f_data = await fetch_fund_data([fund.code])
        fetched_name = f_data.get(fund.code, {}).get("name")
        if fetched_name:
            name = fetched_name
        elif not name:
            name = fund.code

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO funds (code, name, shares, cost_nav, is_holding, note, created_at, updated_at, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (fund.code, name, fund.shares, fund.cost_nav, fund.is_holding, fund.note, now, now, current_user['id']))
    fund_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM funds WHERE id = ?", (fund_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))
    raise HTTPException(status_code=500, detail="Creation failed")

@router.put("/{fund_id}", response_model=Fund)
async def update_fund(fund_id: int, fund: FundUpdate, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM funds WHERE id = ? AND user_id = ?", (fund_id, current_user['id']))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Fund not found")
        
    update_data = fund.model_dump(exclude_unset=True)
    if not update_data:
        columns = [column[0] for column in cursor.description]
        conn.close()
        return dict(zip(columns, row))

    if 'name' in update_data:
        cur_code = update_data.get('code') or dict(row)['code']
        cur_name = (update_data['name'] or '').strip()
        if not cur_name or cur_name == cur_code:
            f_data = await fetch_fund_data([cur_code])
            fetched_name = f_data.get(cur_code, {}).get("name")
            if fetched_name:
                update_data['name'] = fetched_name
        
    update_data['updated_at'] = datetime.now().isoformat()
    
    set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
    values = list(update_data.values()) + [fund_id, current_user['id']]
    
    cursor.execute(f"UPDATE funds SET {set_clause} WHERE id = ? AND user_id = ?", values)
    conn.commit()
    
    cursor.execute("SELECT * FROM funds WHERE id = ?", (fund_id,))
    row = cursor.fetchone()
    columns = [column[0] for column in cursor.description]
    conn.close()
    
    return dict(zip(columns, row))

@router.delete("/{fund_id}")
def delete_fund(fund_id: int, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM funds WHERE id = ? AND user_id = ?", (fund_id, current_user['id']))
    conn.commit()
    conn.close()
    return {"success": True}

