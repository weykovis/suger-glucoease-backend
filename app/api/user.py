from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis
import random
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

from app.database import get_db
from app.config import get_settings
from app.models.user import User
from app.schemas.user import (
    SendCodeRequest, SendCodeResponse,
    LoginRequest, LoginPasswordRequest, LoginResponse,
    UserUpdate, UserResponse,
    SetPasswordRequest, SetPasswordResponse
)
from app.dependencies import get_current_user_id

router = APIRouter(prefix="/api/user", tags=["User"])
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


@router.post("/send-code", response_model=SendCodeResponse)
async def send_verification_code(request: SendCodeRequest):
    rate_key = f"sms:rate:{request.phone}"
    if redis_client.exists(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请60秒后再试"
        )
    
    code = str(random.randint(100000, 999999))
    code_key = f"sms:code:{request.phone}"
    
    redis_client.setex(code_key, 300, code)
    redis_client.setex(rate_key, 60, "1")
    
    print(f"[DEV] 验证码已发送到 {request.phone}: {code}")
    
    return SendCodeResponse(success=True, message="验证码已发送")


@router.post("/login", response_model=LoginResponse)
async def login_with_code(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    code_key = f"sms:code:{request.phone}"
    stored_code = redis_client.get(code_key)
    
    if not stored_code or stored_code != request.code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="验证码错误或已过期"
        )
    
    redis_client.delete(code_key)
    
    result = await db.execute(select(User).where(User.phone == request.phone))
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            phone=request.phone,
            diabetes_type="type2",
            target_low=3.9,
            target_high=7.0,
            dialect="mandarin"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    token = create_access_token(user.id)
    
    return LoginResponse(
        success=True,
        data={
            "token": token,
            "user": UserResponse.model_validate(user).model_dump()
        }
    )


@router.post("/login-password", response_model=LoginResponse)
async def login_with_password(
    request: LoginPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.phone == request.phone))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户未设置密码，请使用验证码登录"
        )
    
    if not pwd_context.verify(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码错误"
        )
    
    token = create_access_token(user.id)
    
    return LoginResponse(
        success=True,
        data={
            "token": token,
            "user": UserResponse.model_validate(user).model_dump()
        }
    )


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return UserResponse.model_validate(user)


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    update_data: UserUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    
    if "target_low" in update_dict and "target_high" in update_dict:
        if update_dict["target_low"] >= update_dict["target_high"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="目标血糖下限必须小于上限"
            )
    
    for key, value in update_dict.items():
        setattr(user, key, value)
    
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.put("/password", response_model=SetPasswordResponse)
async def set_password(
    request: SetPasswordRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    user.password_hash = pwd_context.hash(request.password)
    await db.commit()
    
    return SetPasswordResponse(success=True, message="密码设置成功")


def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"user_id": user_id, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
