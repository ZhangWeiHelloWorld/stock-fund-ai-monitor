import sqlite3
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from database import DB_PATH, hash_password, init_user_default_settings, update_admin_config_file, get_admin_config
from routers.auth import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])

class UserCreate(BaseModel):
    username: str
    password: str
    role: Optional[str] = "user"

class PasswordReset(BaseModel):
    new_password: str

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: str

@router.get("/users", response_model=List[UserResponse])
def list_users(admin: dict = Depends(get_current_admin)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, created_at FROM users ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@router.post("/users", response_model=UserResponse)
def create_user(req: UserCreate, admin: dict = Depends(get_current_admin)):
    username = req.username.strip()
    password = req.password.strip()
    role = req.role.strip() if req.role else "user"

    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    if role not in ("admin", "user"):
        role = "user"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="用户名已存在")

    now_iso = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO users (username, password_hash, role, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (username, hash_password(password), role, now_iso, now_iso))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Initialize user default settings
    init_user_default_settings(user_id)

    return {
        "id": user_id,
        "username": username,
        "role": role,
        "created_at": now_iso
    }

@router.put("/users/{user_id}/password")
def reset_password(user_id: int, req: PasswordReset, admin: dict = Depends(get_current_admin)):
    new_password = req.new_password.strip()
    if not new_password:
        raise HTTPException(status_code=400, detail="新密码不能为空")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    target_user = cursor.fetchone()
    if not target_user:
        conn.close()
        raise HTTPException(status_code=404, detail="指定用户不存在")

    target_dict = dict(target_user)
    now_iso = datetime.now().isoformat()
    cursor.execute("UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                   (hash_password(new_password), now_iso, user_id))
    conn.commit()
    conn.close()

    # If updating admin user's password, also update admin_config.json
    admin_cfg = get_admin_config()
    if target_dict['username'] == admin_cfg.get("username", "admin") or target_dict['role'] == 'admin':
        update_admin_config_file(target_dict['username'], new_password)

    return {"message": f"用户 {target_dict['username']} 密码修改成功"}

@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin: dict = Depends(get_current_admin)):
    if user_id == admin['id']:
        raise HTTPException(status_code=400, detail="无法删除当前登录的管理员账号")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    target_user = cursor.fetchone()
    if not target_user:
        conn.close()
        raise HTTPException(status_code=404, detail="指定用户不存在")

    target_dict = dict(target_user)
    if target_dict['role'] == 'admin':
        conn.close()
        raise HTTPException(status_code=400, detail="禁止删除主管理员账号")

    # Delete user's stocks, funds, user_settings, and user record
    cursor.execute("DELETE FROM stocks WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM funds WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_settings WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    return {"message": f"用户 {target_dict['username']} 及其相关持仓数据已成功删除"}
