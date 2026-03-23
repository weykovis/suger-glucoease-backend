from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class RecordType(str, Enum):
    fasting = "fasting"
    breakfast_after = "breakfast_after"
    lunch_after = "lunch_after"
    dinner_after = "dinner_after"
    bedtime = "bedtime"
    other = "other"


class SourceType(str, Enum):
    manual = "manual"
    cgm = "cgm"
    voice = "voice"


class BloodSugarCreate(BaseModel):
    value: float = Field(..., ge=1.0, le=35.0, description="血糖值")
    unit: str = Field("mmol/L", description="单位")
    record_type: RecordType = Field(RecordType.other, description="记录类型")
    recorded_at: Optional[datetime] = Field(None, description="记录时间")
    source: SourceType = Field(SourceType.manual, description="来源")
    meal_id: Optional[int] = Field(None, description="关联饮食ID")
    note: Optional[str] = Field(None, max_length=255, description="备注")


class BloodSugarResponse(BaseModel):
    id: int
    user_id: int
    value: float
    unit: str
    record_type: str
    recorded_at: datetime
    source: str
    meal_id: Optional[int]
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class BloodSugarListResponse(BaseModel):
    items: List[BloodSugarResponse]
    total: int
    page: int
    page_size: int


class MealType(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"
    other = "other"


class MealFoodCreate(BaseModel):
    food_name: str = Field(..., max_length=100, description="食物名称")
    amount: Optional[str] = Field(None, max_length=50, description="份量")
    carbs: Optional[float] = Field(None, ge=0, description="碳水化合物(g)")
    calories: Optional[float] = Field(None, ge=0, description="热量(kcal)")


class MealFoodResponse(BaseModel):
    id: int
    meal_id: int
    food_name: str
    amount: Optional[str]
    carbs: Optional[float]
    calories: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class MealCreate(BaseModel):
    meal_type: MealType = Field(MealType.other, description="餐次类型")
    recorded_at: Optional[datetime] = Field(None, description="记录时间")
    foods: List[MealFoodCreate] = Field(default_factory=list, description="食物列表")
    total_carbs: Optional[float] = Field(None, ge=0, description="总碳水化合物(g)")
    note: Optional[str] = Field(None, max_length=255, description="备注")


class MealResponse(BaseModel):
    id: int
    user_id: int
    meal_type: str
    recorded_at: datetime
    total_carbs: Optional[float]
    note: Optional[str]
    foods: List[MealFoodResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class MealListResponse(BaseModel):
    items: List[MealResponse]
    total: int
    page: int
    page_size: int


class BloodSugarTrendPoint(BaseModel):
    date: str
    avg_value: float
    min_value: float
    max_value: float
    count: int


class BloodSugarStats(BaseModel):
    avg_value: float
    min_value: float
    max_value: float
    in_range_count: int
    in_range_rate: float
    total_count: int


class BloodSugarTrendResponse(BaseModel):
    points: List[BloodSugarTrendPoint]
    stats: BloodSugarStats
    start_date: datetime
    end_date: datetime
