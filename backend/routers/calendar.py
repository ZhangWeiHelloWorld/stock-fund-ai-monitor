from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime, date
from typing import Optional

from routers.auth import get_current_user
from models import VerifyAdviceRequest, GenerateAiAdviceRequest, CalculateBaziRequest
from services.bazi_calculator import calculate_full_bazi, CITY_LONGITUDES
from services.calendar_service import (
    get_month_calendar_data,
    get_day_detail,
    generate_calendar_ai_advice,
    verify_ai_advice
)

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

@router.get("/cities")
async def get_cities_list(current_user: dict = Depends(get_current_user)):
    """返回全国主要省市与经度配置，供出生地点选择及真太阳时换算"""
    return {
        "cities": CITY_LONGITUDES
    }

@router.post("/calculate-bazi")
async def calculate_bazi_endpoint(
    req: CalculateBaziRequest,
    current_user: dict = Depends(get_current_user)
):
    """根据输入的出生日期、时间、性别、出生地自动测算八字四柱、日主、五行旺衰与喜忌神"""
    try:
        res = calculate_full_bazi(
            birth_date_str=req.birth_date,
            birth_time_str=req.birth_time or "12:00",
            gender=req.gender or "male",
            province=req.province or "北京市",
            city=req.city or "北京市",
            calendar_type=req.calendar_type or "solar",
            is_leap_month=bool(req.is_leap_month),
            lunar_year=req.lunar_year,
            lunar_month=req.lunar_month,
            lunar_day=req.lunar_day
        )
        return res
    except Exception as e:
        print(f"[CalendarRouter] Error in calculate_bazi: {e}")
        raise HTTPException(status_code=400, detail=f"八字测算异常: {str(e)}")

@router.get("/month")
async def calendar_month(
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    today = date.today()
    target_year = year or today.year
    target_month = month or today.month

    if target_month < 1 or target_month > 12:
        raise HTTPException(status_code=400, detail="月份必须在 1 到 12 之间")

    try:
        data = await get_month_calendar_data(target_year, target_month, user_id=current_user['id'])
        return data
    except Exception as e:
        print(f"[CalendarRouter] Error in calendar_month: {e}")
        raise HTTPException(status_code=500, detail=f"获取月度日历数据异常: {str(e)}")


@router.get("/day/{target_date}")
async def calendar_day(
    target_date: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        # Validate date string
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    try:
        detail = await get_day_detail(target_date, user_id=current_user['id'])
        return detail
    except Exception as e:
        print(f"[CalendarRouter] Error in calendar_day: {e}")
        raise HTTPException(status_code=500, detail=f"获取日期详情异常: {str(e)}")


@router.post("/ai-advice")
async def create_ai_advice(
    req: GenerateAiAdviceRequest = None,
    current_user: dict = Depends(get_current_user)
):
    date_str = req.date if req else None
    if date_str:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    try:
        result = await generate_calendar_ai_advice(date_str=date_str, user_id=current_user['id'])
        return result
    except Exception as e:
        print(f"[CalendarRouter] Error generating ai advice: {e}")
        return {"success": False, "message": f"AI建议生成失败: {str(e)}"}


@router.put("/ai-advice/{target_date}/verify")
async def update_advice_verification(
    target_date: str,
    req: VerifyAdviceRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    valid_statuses = ('pending', 'accurate', 'partial', 'divergent')
    if req.verified_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"核验状态必须为: {', '.join(valid_statuses)}")

    try:
        result = verify_ai_advice(
            date_str=target_date,
            verified_status=req.verified_status,
            verified_notes=req.verified_notes or "",
            user_id=current_user['id']
        )
        return result
    except Exception as e:
        print(f"[CalendarRouter] Error updating verification: {e}")
        raise HTTPException(status_code=500, detail=f"更新核验结果异常: {str(e)}")
