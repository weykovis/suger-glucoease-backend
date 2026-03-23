from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class Intent(BaseModel):
    type: str = Field(..., description="意图类型")
    confidence: float = Field(1.0, description="置信度")


class Entity(BaseModel):
    type: str = Field(..., description="实体类型")
    value: str = Field(..., description="实体值")


class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="用户消息")
    dialect: Optional[str] = Field("mandarin", description="方言")
    diabetes_type: Optional[str] = Field("type2", description="糖尿病类型")
    target_low: Optional[float] = Field(3.9, description="目标血糖下限")
    target_high: Optional[float] = Field(7.0, description="目标血糖上限")
    conversation_history: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="对话历史")


class ActionResult(BaseModel):
    type: str = Field(..., description="操作类型")
    data: Optional[Dict[str, Any]] = Field(None, description="操作数据")


class AIChatResponse(BaseModel):
    text: str = Field(..., description="回复文本")
    intent: Optional[Intent] = Field(None, description="识别的意图")
    entities: List[Entity] = Field(default_factory=list, description="提取的实体")
    action: Optional[ActionResult] = Field(None, description="执行的操作")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
