import time
import base64
import json
import hmac
import sqlite3
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from typing import Optional

from database import DB_PATH, get_admin_config, hash_password, verify_password, update_admin_config_file

SECRET_KEY = "lh_monitor_system_jwt_secret_key_2026"

def create_access_token(data: dict, expires_in: int = 86400 * 30) -> str:
    payload = data.copy()
    payload['exp'] = int(time.time()) + expires_in
    payload_str = base64.b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8')
    sig = hmac.new(SECRET_KEY.encode('utf-8'), payload_str.encode('utf-8'), 'sha256').hexdigest()
    return f"{payload_str}.{sig}"

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload_str, sig = token.split('.')
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), payload_str.encode('utf-8'), 'sha256').hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(base64.b64decode(payload_str.encode('utf-8')).decode('utf-8'))
        if payload.get('exp', 0) < time.time():
            return None
        return payload
    except Exception:
        return None

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或缺少身份令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.replace("Bearer ", "").strip()
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="身份令牌无效或已过期，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM users WHERE id = ?", (payload.get("user_id"),))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="关联用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return dict(row)

def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(req: LoginRequest):
    username = req.username.strip()
    password = req.password.strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user_row = cursor.fetchone()

    # Check if admin and if admin_config.json was changed manually
    admin_cfg = get_admin_config()
    if username == admin_cfg.get("username", "admin"):
        if password == admin_cfg.get("password"):
            # Update password in DB if it differed
            now_iso = datetime.now().isoformat()
            if not user_row:
                cursor.execute('''
                    INSERT INTO users (username, password_hash, role, created_at, updated_at)
                    VALUES (?, ?, 'admin', ?, ?)
                ''', (username, hash_password(password), now_iso, now_iso))
                conn.commit()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                user_row = cursor.fetchone()
            else:
                cursor.execute("UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                               (hash_password(password), now_iso, user_row['id']))
                conn.commit()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_row['id'],))
                user_row = cursor.fetchone()

    conn.close()

    if not user_row or not verify_password(dict(user_row)['password_hash'], password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    user_dict = dict(user_row)
    token = create_access_token({
        "user_id": user_dict['id'],
        "username": user_dict['username'],
        "role": user_dict['role']
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_dict['id'],
            "username": user_dict['username'],
            "role": user_dict['role']
        }
    }

@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user

@router.post("/logout")
def logout():
    return {"message": "已成功退出登录"}
