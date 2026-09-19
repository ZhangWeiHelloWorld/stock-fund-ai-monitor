import sqlite3
import asyncio
import json
import logging
from datetime import datetime
from database import DB_PATH, get_settings_dict
from services.data_provider import get_provider, MXDataProvider, GenericDataProvider, get_market_status
from services.trading_calendar import is_trading_time, is_trading_day

logger = logging.getLogger(__name__)

# In-memory runtime cache
_analysis_cache = {}


def get_provider_for_user(user_id: int):
    """
    Get configured DataProvider for the user.
    Reads user settings: data_source_provider ('mx' or 'generic') and mx_api_key.
    Falls back to GenericDataProvider if MX is selected but unavailable.
    """
    settings = get_settings_dict(user_id=user_id)
    provider_type = settings.get('data_source_provider', 'generic')
    mx_api_key = settings.get('mx_api_key', '').strip()
    
    is_degraded = False
    provider = None

    if provider_type == 'mx':
        if mx_api_key:
            provider = MXDataProvider(api_key=mx_api_key)
        else:
            provider = GenericDataProvider()
            is_degraded = True
    else:
        provider = GenericDataProvider()

    return provider, provider_type, is_degraded


def _get_user_cache(user_id: int):
    if user_id not in _analysis_cache:
        _analysis_cache[user_id] = {
            'overview': {'data': None, 'updated_at': None},
            'sector_rotation': {'data': None, 'updated_at': None},
            'sector_flow': {'data': None, 'updated_at': None},
            'stock_detail': {},
        }
        # Try loading initial cache from SQLite DB if exists
        _load_cache_from_db(user_id)
    return _analysis_cache[user_id]


def _load_cache_from_db(user_id: int):
    """Load latest cache from SQLite database if memory cache is empty."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT cache_key, data, updated_at FROM data_analysis_cache WHERE user_id = ?",
                (user_id,)
            )
            rows = cursor.fetchall()
            for key, data_json, updated_at_str in rows:
                try:
                    data = json.loads(data_json)
                    dt = datetime.fromisoformat(updated_at_str) if updated_at_str else None
                    if key in _analysis_cache[user_id]:
                        _analysis_cache[user_id][key] = {'data': data, 'updated_at': dt}
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"[DataAnalysisService] load cache from DB error: {e}")


def _save_cache_to_db(user_id: int, key: str, data: any, updated_at: datetime):
    """Persist cache entry to SQLite database."""
    try:
        now_str = updated_at.isoformat()
        m_status = data.get("market_status", "") if isinstance(data, dict) else ""
        p_type = data.get("provider_type", "") if isinstance(data, dict) else ""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO data_analysis_cache (user_id, cache_key, data, market_status, provider_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, cache_key) DO UPDATE SET
                    data = excluded.data,
                    market_status = excluded.market_status,
                    provider_type = excluded.provider_type,
                    updated_at = excluded.updated_at
            ''', (
                user_id, key, json.dumps(data, ensure_ascii=False),
                m_status, p_type,
                now_str, now_str
            ))
            conn.commit()
    except Exception as e:
        logger.warning(f"[DataAnalysisService] save cache to DB error: {e}")


def _is_cache_valid(updated_at: datetime, max_age_seconds: int = None) -> bool:
    if not updated_at:
        return False
    now = datetime.now()
    age = (now - updated_at).total_seconds()
    if max_age_seconds is not None:
        return age < max_age_seconds
    # Default expiry: 60s in trading hours, 300s in non-trading
    return age < (60 if is_trading_time() else 300)


def _determine_status_and_label():
    """
    Returns (market_status, data_label)
    market_status: before_open | pre_auction | trading | noon_break | closed
    data_label: yesterday | realtime | closed
    """
    now = datetime.now()
    if not is_trading_day(now):
        return "closed", "yesterday"

    cur_time = now.strftime("%H:%M")
    if cur_time < "09:15":
        return "before_open", "yesterday"
    elif "09:15" <= cur_time < "09:30":
        return "pre_auction", "yesterday"
    elif ("09:30" <= cur_time < "11:30") or ("13:00" <= cur_time < "15:00"):
        return "trading", "realtime"
    elif "11:30" <= cur_time < "13:00":
        return "noon_break", "realtime"
    else:
        return "closed", "closed"


async def get_analysis_overview(user_id: int, force_refresh: bool = False):
    """
    Overview endpoint:
    Returns market indices volume + market fund flow summary + status labels
    """
    user_cache = _get_user_cache(user_id)
    cached = user_cache['overview']

    market_status, data_label = _determine_status_and_label()

    if not force_refresh and cached['data'] and _is_cache_valid(cached['updated_at']):
        data = cached['data']
        data['market_status'] = market_status
        data['data_label'] = data_label
        return data

    provider, provider_type, is_degraded = get_provider_for_user(user_id)

    indices_res = await provider.get_market_indices_volume()
    flow_res = await provider.get_fund_flow_summary()

    now = datetime.now()
    response_data = {
        'indices': indices_res.get('data', []),
        'indices_available': indices_res.get('available', True),
        'fund_flow': flow_res,
        'market_status': market_status,
        'data_label': data_label,
        'provider_type': provider_type,
        'is_degraded': is_degraded,
        'last_updated': now.strftime("%Y-%m-%d %H:%M:%S")
    }

    user_cache['overview'] = {
        'data': response_data,
        'updated_at': now
    }
    _save_cache_to_db(user_id, 'overview', response_data, now)

    return response_data


async def get_sector_rotation_data(user_id: int, force_refresh: bool = False):
    """Returns sector rotation rankings."""
    user_cache = _get_user_cache(user_id)
    cached = user_cache['sector_rotation']

    if not force_refresh and cached['data'] and _is_cache_valid(cached['updated_at']):
        return cached['data']

    provider, _, _ = get_provider_for_user(user_id)
    sectors = await provider.get_sector_rotation()

    now = datetime.now()
    user_cache['sector_rotation'] = {
        'data': sectors,
        'updated_at': now
    }
    _save_cache_to_db(user_id, 'sector_rotation', sectors, now)
    return sectors


async def get_sector_flow_data(user_id: int, force_refresh: bool = False):
    """Returns sector fund flow data with Sankey chart structure."""
    user_cache = _get_user_cache(user_id)
    cached = user_cache['sector_flow']

    if not force_refresh and cached['data'] and _is_cache_valid(cached['updated_at']):
        return cached['data']

    provider, _, _ = get_provider_for_user(user_id)
    sankey_data = await provider.get_sector_fund_flow()

    now = datetime.now()
    user_cache['sector_flow'] = {
        'data': sankey_data,
        'updated_at': now
    }
    _save_cache_to_db(user_id, 'sector_flow', sankey_data, now)
    return sankey_data


async def get_user_holdings_list(user_id: int):
    """
    Query all user's holding stocks and funds from database
    """
    holdings = []
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Stocks
        cursor.execute("SELECT code, name, is_holding FROM stocks WHERE user_id = ? ORDER BY is_holding DESC, id ASC", (user_id,))
        for row in cursor.fetchall():
            holdings.append({
                "code": row[0],
                "name": row[1] or row[0],
                "type": "stock",
                "is_holding": bool(row[2])
            })
        # Funds
        cursor.execute("SELECT code, name, is_holding FROM funds WHERE user_id = ? ORDER BY is_holding DESC, id ASC", (user_id,))
        for row in cursor.fetchall():
            holdings.append({
                "code": row[0],
                "name": row[1] or row[0],
                "type": "fund",
                "is_holding": bool(row[2])
            })
    return holdings


async def get_stock_analysis(user_id: int, code: str, name: str = "", is_fund: bool = False):
    """Get single stock or fund volume and fund flow analysis."""
    provider, _, _ = get_provider_for_user(user_id)
    return await provider.get_stock_detail(code, name=name, is_fund=is_fund)


async def get_holdings_analysis_data(user_id: int, items: list):
    """
    Batch analyze multiple stocks and funds.
    items: list of {"code": str, "name": str, "type": "stock"|"fund"}
    """
    provider, _, _ = get_provider_for_user(user_id)
    tasks = []
    for item in items:
        code = item.get("code")
        name = item.get("name", "")
        is_fund = item.get("type") == "fund"
        tasks.append(provider.get_stock_detail(code, name=name, is_fund=is_fund))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = []
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            out.append({
                "code": items[i].get("code"),
                "name": items[i].get("name"),
                "type": items[i].get("type"),
                "error": str(res)
            })
        else:
            res["type"] = items[i].get("type")
            out.append(res)
    return out


async def refresh_analysis_data(user_id: int):
    """Manual refresh triggered by user or timer."""
    try:
        if user_id in _analysis_cache:
            _analysis_cache[user_id]['overview'] = {'data': None, 'updated_at': None}
            _analysis_cache[user_id]['sector_rotation'] = {'data': None, 'updated_at': None}
            _analysis_cache[user_id]['sector_flow'] = {'data': None, 'updated_at': None}
            _analysis_cache[user_id]['stock_detail'] = {}

        await get_analysis_overview(user_id, force_refresh=True)
        await get_sector_rotation_data(user_id, force_refresh=True)
        await get_sector_flow_data(user_id, force_refresh=True)
        return {"success": True, "message": "数据分析已更新完成"}
    except Exception as e:
        logger.error(f"[DataAnalysisService] refresh error: {e}")
        return {"success": False, "message": f"刷新失败: {str(e)}"}


async def auto_refresh_all_users():
    """Active auto-refresh scheduled at 09:15 and 20:30 daily."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users")
            users = cursor.fetchall()

        for (user_id,) in users:
            try:
                await refresh_analysis_data(user_id)
                logger.info(f"[DataAnalysisService] Auto-refreshed analysis for user {user_id}")
            except Exception as ue:
                logger.warning(f"[DataAnalysisService] Auto-refresh user {user_id} error: {ue}")
    except Exception as e:
        logger.error(f"[DataAnalysisService] auto_refresh_all_users error: {e}")


def get_analysis_status(user_id: int):
    user_cache = _get_user_cache(user_id)
    cached = user_cache['overview']
    updated_at = cached.get('updated_at')
    
    age_seconds = 0
    if updated_at:
        age_seconds = (datetime.now() - updated_at).total_seconds()

    settings = get_settings_dict(user_id=user_id)
    provider_type = settings.get('data_source_provider', 'generic')
    max_panels = int(settings.get('data_analysis_max_panels', 6))

    market_status, data_label = _determine_status_and_label()

    return {
        'last_refresh_time': updated_at.strftime("%Y-%m-%d %H:%M:%S") if updated_at else None,
        'provider_type': provider_type,
        'max_panels': max_panels,
        'market_status': market_status,
        'data_label': data_label,
        'cache_age_seconds': int(age_seconds)
    }
