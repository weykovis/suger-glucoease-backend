from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class DiabetesType(str, Enum):
    type1 = "type1"
    type2 = "type2"
    gestational = "gestational"
    other = "other"


class DialectType(str, Enum):
    mandarin = "mandarin"
    cantonese = "cantonese"
    sichuan = "sichuan"


class UserBase(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="手机号")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    diabetes_type: DiabetesType = Field(DiabetesType.type2, description="糖尿病类型")
    target_low: float = Field(3.9, ge=2.0, le=10.0, description="目标血糖下限")
    target_high: float = Field(7.0, ge=4.0, le=15.0, description="目标血糖上限")
    dialect: DialectType = Field(DialectType.mandarin, description="偏好语言")


class UserCreate(UserBase):
    password: Optional[str] = Field(None, min_length=6, max_length=50, description="密码")


class UserUpdate(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50)
    diabetes_type: Optional[DiabetesType] = None
    target_low: Optional[float] = Field(None, ge=2.0, le=10.0)
    target_high: Optional[float] = Field(None, ge=4.0, le=15.0)
    dialect: Optional[DialectType] = None


class UserResponse(UserBase):
    id: int
    has_cgm: bool = False
    cgm_device: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SendCodeRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="手机号")


class SendCodeResponse(BaseModel):
    success: bool
    message: str


class LoginRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="手机号")
    code: str = Field(..., min_length=6, max_length=6, description="验证码")


class LoginPasswordRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="手机号")
    password: str = Field(..., min_length=6, max_length=50, description="密码")


class LoginResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class TokenData(BaseModel):
    user_id: int
    exp: datetime


class SetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=6, max_length=50, description="密码")


class SetPasswordResponse(BaseModel):
    success: bool
    message: str
