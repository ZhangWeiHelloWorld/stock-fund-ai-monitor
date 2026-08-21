from fastapi import APIRouter, Depends, HTTPException
import sqlite3
from typing import List
from models import Stock, StockCreate, StockUpdate
from database import DB_PATH
from datetime import datetime
from routers.auth import get_current_user

from services.market_service import fetch_stock_data, format_stock_code

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

@router.get("/lookup/{code}")
async def lookup_stock(code: str, current_user: dict = Depends(get_current_user)):
    formatted = format_stock_code(code)
    data = await fetch_stock_data([formatted])
    res = data.get(formatted, {})
    return {
        "code": code,
        "name": res.get("name", ""),
        "current": res.get("current", 0)
    }

@router.get("", response_model=List[Stock])
def list_stocks(current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stocks WHERE user_id = ? ORDER BY id DESC", (current_user['id'],))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@router.post("", response_model=Stock)
async def create_stock(stock: StockCreate, current_user: dict = Depends(get_current_user)):
    name = (stock.name or "").strip()
    if not name:
        formatted = format_stock_code(stock.code)
        s_data = await fetch_stock_data([formatted])
        name = s_data.get(formatted, {}).get("name") or stock.code

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO stocks (code, name, shares, cost_price, is_holding, note, created_at, updated_at, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (stock.code, name, stock.shares, stock.cost_price, stock.is_holding, stock.note, now, now, current_user['id']))
    stock_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM stocks WHERE id = ?", (stock_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))
    raise HTTPException(status_code=500, detail="Creation failed")

@router.put("/{stock_id}", response_model=Stock)
async def update_stock(stock_id: int, stock: StockUpdate, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM stocks WHERE id = ? AND user_id = ?", (stock_id, current_user['id']))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Stock not found")
        
    update_data = stock.model_dump(exclude_unset=True)
    if not update_data:
        columns = [column[0] for column in cursor.description]
        conn.close()
        return dict(zip(columns, row))

    if 'name' in update_data and not (update_data['name'] or '').strip():
        code = update_data.get('code') or dict(row)['code']
        formatted = format_stock_code(code)
        s_data = await fetch_stock_data([formatted])
        update_data['name'] = s_data.get(formatted, {}).get("name") or code
        
    update_data['updated_at'] = datetime.now().isoformat()
    
    set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
    values = list(update_data.values()) + [stock_id, current_user['id']]
    
    cursor.execute(f"UPDATE stocks SET {set_clause} WHERE id = ? AND user_id = ?", values)
    conn.commit()
    
    cursor.execute("SELECT * FROM stocks WHERE id = ?", (stock_id,))
    row = cursor.fetchone()
    columns = [column[0] for column in cursor.description]
    conn.close()
    
    return dict(zip(columns, row))

@router.delete("/{stock_id}")
def delete_stock(stock_id: int, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stocks WHERE id = ? AND user_id = ?", (stock_id, current_user['id']))
    conn.commit()
    conn.close()
    return {"success": True}

