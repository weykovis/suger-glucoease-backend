from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.models.meal import Meal, MealFood
from app.models.user import User
from app.schemas.record import (
    MealCreate, MealResponse, MealListResponse, MealFoodResponse
)
from app.dependencies import get_current_user_id

router = APIRouter(prefix="/api/meal", tags=["Meal"])


@router.post("", response_model=MealResponse)
async def create_meal(
    data: MealCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    
    meal = Meal(
        user_id=user_id,
        meal_type=data.meal_type.value,
        recorded_at=data.recorded_at or datetime.now(),
        total_carbs=data.total_carbs,
        note=data.note
    )
    db.add(meal)
    await db.flush()
    
    for food_data in data.foods:
        meal_food = MealFood(
            meal_id=meal.id,
            food_name=food_data.food_name,
            amount=food_data.amount,
            carbs=food_data.carbs,
            calories=food_data.calories
        )
        db.add(meal_food)
    
    await db.commit()
    await db.refresh(meal)
    
    result = await db.execute(
        select(Meal).options(selectinload(Meal.foods)).where(Meal.id == meal.id)
    )
    meal = result.scalar_one()
    
    return meal


@router.get("", response_model=MealListResponse)
async def list_meals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    query = select(Meal).options(selectinload(Meal.foods)).where(Meal.user_id == user_id)
    
    if start_date:
        query = query.where(Meal.recorded_at >= start_date)
    if end_date:
        query = query.where(Meal.recorded_at <= end_date)
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.order_by(desc(Meal.recorded_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    return MealListResponse(
        items=[MealResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/latest", response_model=MealResponse)
async def get_latest_meal(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    query = select(Meal).options(selectinload(Meal.foods)).where(Meal.user_id == user_id)
    query = query.order_by(desc(Meal.recorded_at)).limit(1)
    
    result = await db.execute(query)
    meal = result.scalar_one_or_none()
    
    if not meal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="暂无饮食记录")
    
    return meal


@router.get("/{meal_id}", response_model=MealResponse)
async def get_meal(
    meal_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Meal).options(selectinload(Meal.foods)).where(
            Meal.id == meal_id,
            Meal.user_id == user_id
        )
    )
    meal = result.scalar_one_or_none()
    
    if not meal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    
    return meal


@router.delete("/{meal_id}")
async def delete_meal(
    meal_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Meal).where(
            Meal.id == meal_id,
            Meal.user_id == user_id
        )
    )
    meal = result.scalar_one_or_none()
    
    if not meal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    
    await db.delete(meal)
    await db.commit()
    
    return {"success": True, "message": "删除成功"}
