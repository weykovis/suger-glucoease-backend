from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal

from app.database import get_db
from app.models.blood_sugar import BloodSugar
from app.models.user import User
from app.schemas.record import (
    BloodSugarCreate, BloodSugarResponse, BloodSugarListResponse,
    BloodSugarTrendResponse, BloodSugarTrendPoint, BloodSugarStats
)
from app.dependencies import get_current_user_id

router = APIRouter(prefix="/api/blood-sugar", tags=["BloodSugar"])


@router.post("", response_model=BloodSugarResponse)
async def create_blood_sugar(
    data: BloodSugarCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    
    blood_sugar = BloodSugar(
        user_id=user_id,
        value=data.value,
        unit=data.unit,
        record_type=data.record_type.value,
        recorded_at=data.recorded_at or datetime.now(),
        source=data.source.value,
        meal_id=data.meal_id,
        note=data.note
    )
    db.add(blood_sugar)
    await db.commit()
    await db.refresh(blood_sugar)
    
    return blood_sugar


@router.get("", response_model=BloodSugarListResponse)
async def list_blood_sugars(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    query = select(BloodSugar).where(BloodSugar.user_id == user_id)
    
    if start_date:
        query = query.where(BloodSugar.recorded_at >= start_date)
    if end_date:
        query = query.where(BloodSugar.recorded_at <= end_date)
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.order_by(desc(BloodSugar.recorded_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    return BloodSugarListResponse(
        items=[BloodSugarResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/latest", response_model=BloodSugarResponse)
async def get_latest_blood_sugar(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    query = select(BloodSugar).where(BloodSugar.user_id == user_id)
    query = query.order_by(desc(BloodSugar.recorded_at)).limit(1)
    
    result = await db.execute(query)
    blood_sugar = result.scalar_one_or_none()
    
    if not blood_sugar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="暂无血糖记录")
    
    return blood_sugar


@router.get("/{record_id}", response_model=BloodSugarResponse)
async def get_blood_sugar(
    record_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(BloodSugar).where(
            BloodSugar.id == record_id,
            BloodSugar.user_id == user_id
        )
    )
    blood_sugar = result.scalar_one_or_none()
    
    if not blood_sugar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    
    return blood_sugar


@router.delete("/{record_id}")
async def delete_blood_sugar(
    record_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(BloodSugar).where(
            BloodSugar.id == record_id,
            BloodSugar.user_id == user_id
        )
    )
    blood_sugar = result.scalar_one_or_none()
    
    if not blood_sugar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    
    await db.delete(blood_sugar)
    await db.commit()
    
    return {"success": True, "message": "删除成功"}


@router.get("/trend/overview", response_model=BloodSugarTrendResponse)
async def get_blood_sugar_trend(
    days: int = Query(7, ge=1, le=90, description="查询天数"),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    result = await db.execute(
        select(BloodSugar).where(
            and_(
                BloodSugar.user_id == user_id,
                BloodSugar.recorded_at >= start_date,
                BloodSugar.recorded_at <= end_date
            )
        ).order_by(BloodSugar.recorded_at)
    )
    records = result.scalars().all()
    
    daily_data = {}
    for record in records:
        date_str = record.recorded_at.strftime("%Y-%m-%d")
        if date_str not in daily_data:
            daily_data[date_str] = []
        daily_data[date_str].append(float(record.value))
    
    points = []
    all_values = []
    in_range_count = 0
    
    for i in range(days):
        date = (end_date - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        if date in daily_data:
            values = daily_data[date]
            points.append(BloodSugarTrendPoint(
                date=date,
                avg_value=round(sum(values) / len(values), 1),
                min_value=round(min(values), 1),
                max_value=round(max(values), 1),
                count=len(values)
            ))
            all_values.extend(values)
            in_range_count += sum(1 for v in values if 3.9 <= v <= 10.0)
        else:
            points.append(BloodSugarTrendPoint(
                date=date,
                avg_value=0,
                min_value=0,
                max_value=0,
                count=0
            ))
    
    stats = BloodSugarStats(
        avg_value=round(sum(all_values) / len(all_values), 1) if all_values else 0,
        min_value=round(min(all_values), 1) if all_values else 0,
        max_value=round(max(all_values), 1) if all_values else 0,
        in_range_count=in_range_count,
        in_range_rate=round(in_range_count / len(all_values) * 100, 1) if all_values else 0,
        total_count=len(all_values)
    )
    
    return BloodSugarTrendResponse(
        points=points,
        stats=stats,
        start_date=start_date,
        end_date=end_date
    )
