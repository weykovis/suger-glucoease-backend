from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.database import get_db
from app.dependencies import get_current_user_id

router = APIRouter(prefix="/api/food", tags=["Food"])

# 食物 GI 数据库（MVP 阶段使用内存数据库）
FOOD_GI_DATABASE = {
    "米饭": {
        "gi": 72,
        "carbs": "25g/100g",
        "category": "主食",
        "suggestion": "建议搭配蔬菜和蛋白质，控制份量"
    },
    "面条": {
        "gi": 55,
        "carbs": "25g/100g",
        "category": "主食",
        "suggestion": "选择全麦面条更健康"
    },
    "馒头": {
        "gi": 85,
        "carbs": "45g/100g",
        "category": "主食",
        "suggestion": "高 GI，建议控制量"
    },
    "面包": {
        "gi": 75,
        "carbs": "50g/100g",
        "category": "主食",
        "suggestion": "选择全麦面包"
    },
    "红薯": {
        "gi": 54,
        "carbs": "20g/100g",
        "category": "主食",
        "suggestion": "比白米饭更健康"
    },
    "南瓜": {
        "gi": 75,
        "carbs": "5g/100g",
        "category": "蔬菜",
        "suggestion": "虽然 GI 高但碳水低，可以适量食用"
    },
    "苹果": {
        "gi": 36,
        "carbs": "13g/100g",
        "category": "水果",
        "suggestion": "低 GI，适合作为加餐"
    },
    "香蕉": {
        "gi": 52,
        "carbs": "23g/100g",
        "category": "水果",
        "suggestion": "中等 GI，控制份量"
    },
    "西瓜": {
        "gi": 72,
        "carbs": "8g/100g",
        "category": "水果",
        "suggestion": "高 GI 但碳水低，适量食用"
    },
    "牛奶": {
        "gi": 30,
        "carbs": "5g/100ml",
        "category": "奶制品",
        "suggestion": "低 GI，适合饮用"
    },
    "鸡蛋": {
        "gi": 0,
        "carbs": "0g/个",
        "category": "蛋白质",
        "suggestion": "零 GI，适合食用"
    },
    "鸡肉": {
        "gi": 0,
        "carbs": "0g/100g",
        "category": "蛋白质",
        "suggestion": "零 GI，适合食用"
    },
    "鱼肉": {
        "gi": 0,
        "carbs": "0g/100g",
        "category": "蛋白质",
        "suggestion": "零 GI，适合食用"
    },
    "豆腐": {
        "gi": 15,
        "carbs": "2g/100g",
        "category": "蛋白质",
        "suggestion": "低 GI，适合食用"
    },
    "蔬菜": {
        "gi": 15,
        "carbs": "5g/100g",
        "category": "蔬菜",
        "suggestion": "低 GI，鼓励多吃"
    }
}


@router.get("/gi", response_model=Dict[str, Any])
async def get_food_gi(
    food: str,
    user_id: int = Depends(get_current_user_id)
):
    """查询食物的 GI 值"""
    food = food.strip()
    if not food:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="食物名称不能为空"
        )
    
    # 模糊匹配食物
    matched_food = None
    for food_name in FOOD_GI_DATABASE:
        if food in food_name or food_name in food:
            matched_food = food_name
            break
    
    if not matched_food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到食物 '{food}' 的 GI 数据"
        )
    
    return {
        "food": matched_food,
        "gi": FOOD_GI_DATABASE[matched_food]["gi"],
        "carbs": FOOD_GI_DATABASE[matched_food]["carbs"],
        "category": FOOD_GI_DATABASE[matched_food]["category"],
        "suggestion": FOOD_GI_DATABASE[matched_food]["suggestion"]
    }


@router.get("/nutrition", response_model=Dict[str, Any])
async def get_food_nutrition(
    food: str,
    user_id: int = Depends(get_current_user_id)
):
    """查询食物的营养信息"""
    food = food.strip()
    if not food:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="食物名称不能为空"
        )
    
    # 模糊匹配食物
    matched_food = None
    for food_name in FOOD_GI_DATABASE:
        if food in food_name or food_name in food:
            matched_food = food_name
            break
    
    if not matched_food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到食物 '{food}' 的营养数据"
        )
    
    return {
        "food": matched_food,
        "nutrition": {
            "carbs": FOOD_GI_DATABASE[matched_food]["carbs"],
            "gi": FOOD_GI_DATABASE[matched_food]["gi"],
            "category": FOOD_GI_DATABASE[matched_food]["category"],
            "suggestion": FOOD_GI_DATABASE[matched_food]["suggestion"]
        }
    }


@router.get("/categories", response_model=List[str])
async def get_food_categories(
    user_id: int = Depends(get_current_user_id)
):
    """获取食物分类"""
    categories = set()
    for food in FOOD_GI_DATABASE.values():
        categories.add(food["category"])
    return sorted(list(categories))


@router.get("/list", response_model=List[Dict[str, Any]])
async def get_food_list(
    category: str = None,
    user_id: int = Depends(get_current_user_id)
):
    """获取食物列表"""
    foods = []
    for food_name, food_data in FOOD_GI_DATABASE.items():
        if category and food_data["category"] != category:
            continue
        foods.append({
            "name": food_name,
            "gi": food_data["gi"],
            "carbs": food_data["carbs"],
            "category": food_data["category"]
        })
    return foods