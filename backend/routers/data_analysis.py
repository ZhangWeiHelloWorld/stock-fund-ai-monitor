from fastapi import APIRouter, Depends, Body
from typing import List, Dict, Any
from routers.auth import get_current_user

router = APIRouter(prefix="/api/data-analysis", tags=["data-analysis"])

@router.get("/overview")
async def get_overview(current_user: dict = Depends(get_current_user)):
    from services.data_analysis_service import get_analysis_overview
    return await get_analysis_overview(current_user['id'])

@router.get("/stock/{code}")
async def get_stock_detail(code: str, is_fund: bool = False, current_user: dict = Depends(get_current_user)):
    from services.data_analysis_service import get_stock_analysis
    return await get_stock_analysis(current_user['id'], code, is_fund=is_fund)

@router.get("/sector-rotation")
async def get_sector_rotation(current_user: dict = Depends(get_current_user)):
    from services.data_analysis_service import get_sector_rotation_data
    return await get_sector_rotation_data(current_user['id'])

@router.get("/sector-flow")
async def get_sector_flow(current_user: dict = Depends(get_current_user)):
    from services.data_analysis_service import get_sector_flow_data
    return await get_sector_flow_data(current_user['id'])

@router.get("/holdings")
async def get_holdings(current_user: dict = Depends(get_current_user)):
    from services.data_analysis_service import get_user_holdings_list
    return await get_user_holdings_list(current_user['id'])

@router.post("/holdings-analysis")
async def get_holdings_analysis(items: List[Dict[str, Any]] = Body(...), current_user: dict = Depends(get_current_user)):
    from services.data_analysis_service import get_holdings_analysis_data
    return await get_holdings_analysis_data(current_user['id'], items)

@router.post("/refresh")
async def refresh_data(current_user: dict = Depends(get_current_user)):
    from services.data_analysis_service import refresh_analysis_data
    return await refresh_analysis_data(current_user['id'])

@router.get("/status")
async def get_status(current_user: dict = Depends(get_current_user)):
    from services.data_analysis_service import get_analysis_status
    return get_analysis_status(current_user['id'])
