from typing import List, Optional, Dict, Any
from app.schemas.ai import AIChatRequest, AIChatResponse, Intent, Entity, ActionResult
import httpx
import json
import re
from datetime import datetime
from app.config import get_settings
from app.services.dialect_service import dialect_service
from app.services.food_matching_service import food_matching_service
from app.services.emotion_learning_service import emotion_learning_service, EmotionalState

settings = get_settings()


class AIService:
    """
    AI服务 - 整合方言支持、食物匹配、情感学习
    """

    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.DEEPSEEK_MODEL

    async def chat(self, request: AIChatRequest, user_id: int, db) -> AIChatResponse:
        """处理用户对话请求"""
        dialect = request.dialect or "mandarin"

        dialect_service.set_dialect(dialect)

        intent = await self._recognize_intent(request.message)
        entities = await self._extract_entities(request.message, dialect)

        food_result = self._check_food_query(request.message, dialect)

        emotion = emotion_learning_service.analyze_emotion(request.message, user_id)

        emotion_learning_service.record_interaction(
            user_id=user_id,
            message=request.message,
            emotion=emotion,
            intent=intent.type if intent else None
        )

        context = await self._retrieve_context(request.message, dialect)

        emotion_state = emotion_learning_service.assess_blood_glucose_stage(user_id, [])

        prompt = self._build_prompt(
            message=request.message,
            dialect=dialect,
            diabetes_type=request.diabetes_type or "type2",
            target_low=request.target_low or 3.9,
            target_high=request.target_high or 7.0,
            conversation_history=request.conversation_history or [],
            context=context,
            intent=intent,
            entities=entities,
            emotion=emotion,
            blood_glucose_stage=emotion_state
        )

        response_text = await self._call_llm(prompt)

        if food_result:
            response_text = f"{response_text}\n\n{food_result}"

        action = await self._execute_action(intent, entities, user_id, db)

        return AIChatResponse(
            text=response_text,
            intent=intent,
            entities=entities,
            action=action
        )

    async def _recognize_intent(self, message: str) -> Intent:
        """识别用户意图"""
        intent_prompt = f"""请识别用户输入的意图，只返回一个词：

用户输入：{message}

可选意图：
- record_blood_sugar: 记录血糖
- record_meal: 记录饮食
- query_blood_sugar: 查询血糖
- query_nutrition: 查询营养
- predict_effect: 预测影响
- emotional_support: 情感支持
- health_advice: 健康建议
- greeting: 问候
- other: 其他

只返回一个词，不要其他内容。"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": intent_prompt}],
                        "max_tokens": 50,
                        "temperature": 0.1
                    },
                    timeout=30.0
                )

                result = response.json()
                intent_text = result["choices"][0]["message"]["content"].strip().lower()

                valid_intents = {
                    "record_blood_sugar", "record_meal", "query_blood_sugar",
                    "query_nutrition", "predict_effect", "emotional_support",
                    "health_advice", "greeting", "other"
                }

                if intent_text not in valid_intents:
                    intent_text = "other"

                return Intent(type=intent_text, confidence=0.9)
        except Exception as e:
            print(f"[AI] Intent recognition error: {e}")
            return Intent(type="other", confidence=0.5)

    async def _extract_entities(self, message: str, dialect: str = "mandarin") -> List[Entity]:
        """提取实体信息"""
        entity_prompt = f"""从用户输入中提取实体信息，以 JSON 数组格式返回：

用户输入：{message}

实体类型：
- blood_sugar_value: 血糖值（数字）
- blood_sugar_unit: 血糖单位（mmol/L 或 mg/dL）
- food_name: 食物名称
- food_amount: 食物份量（如"二两"、"一碗"）
- time_reference: 时间参照（如"刚才"、"昨天"）
- meal_type: 餐次类型（早餐、午餐、晚餐、零食）

请以 JSON 数组格式返回，例如：
[{{"type": "blood_sugar_value", "value": "8.5"}}, {{"type": "food_name", "value": "面条"}}]

只返回 JSON，不要其他内容。如果没有实体，返回空数组 []。"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": entity_prompt}],
                        "max_tokens": 200,
                        "temperature": 0.1
                    },
                    timeout=30.0
                )

                result = response.json()
                entity_text = result["choices"][0]["message"]["content"].strip()

                entity_text = re.sub(r'```json\s*', '', entity_text)
                entity_text = re.sub(r'```\s*$', '', entity_text)
                entity_text = entity_text.strip()

                try:
                    entities_data = json.loads(entity_text)

                    for entity in entities_data:
                        if entity.get("type") == "food_name":
                            matched = food_matching_service.fuzzy_match(entity["value"], dialect)
                            if matched:
                                entity["matched_food"] = matched.get("food")
                                entity["gi"] = matched.get("gi")

                    return [Entity(**e) for e in entities_data if isinstance(e, dict)]
                except json.JSONDecodeError:
                    return []
        except Exception as e:
            print(f"[AI] Entity extraction error: {e}")
            return []

    def _check_food_query(self, message: str, dialect: str = "mandarin") -> Optional[str]:
        """检查是否是食物查询"""
        food_keywords = ["gi", "血糖生成指数", "碳水", "能不能吃", "可以吃", "吃什么", "食物"]

        has_food_query = any(keyword in message for keyword in food_keywords)

        if has_food_query:
            words = message.replace("?", " ").replace("！", " ").replace(",", " ").split()
            for word in words:
                if len(word) >= 2:
                    matched = food_matching_service.fuzzy_match(word, dialect)
                    if matched:
                        return f"🍽️ {matched['food']}的营养信息：\nGI值：{matched.get('gi', 'N/A')}\n碳水：{matched.get('carbs', 'N/A')}\n{matched.get('suggestion', '')}"

        return None

    async def _retrieve_context(self, query: str, dialect: str = "mandarin") -> str:
        """从知识库检索相关内容"""
        knowledge_base = self._get_knowledge_base()
        return self._semantic_search(query, knowledge_base, dialect)

    def _get_knowledge_base(self) -> dict:
        """获取知识库"""
        return {
            "food_gi": {
                "米饭": {"gi": 72, "carbs": "25g/100g", "advice": "建议搭配蔬菜和蛋白质"},
                "面条": {"gi": 55, "carbs": "25g/100g", "advice": "选择全麦面条更健康"},
                "馒头": {"gi": 85, "carbs": "45g/100g", "advice": "高 GI，建议控制量"},
                "面包": {"gi": 75, "carbs": "50g/100g", "advice": "选择全麦面包"},
                "红薯": {"gi": 54, "carbs": "20g/100g", "advice": "比白米饭更健康"},
                "南瓜": {"gi": 75, "carbs": "5g/100g", "advice": "虽然 GI 高但碳水低"},
                "西瓜": {"gi": 72, "carbs": "5g/100g", "advice": "GI 高但适量食用可以"},
                "苹果": {"gi": 36, "carbs": "13g/100g", "advice": "低 GI 水果推荐"},
                "香蕉": {"gi": 51, "carbs": "22g/100g", "advice": "熟香蕉 GI 更高"},
                "奶茶": {"gi": 67, "carbs": "30g/杯", "advice": "含糖量高，建议少喝"}
            },
            "dietary_guidelines": {
                "主食": "每餐拳头大小的主食（生重约50g）",
                "蔬菜": "每餐至少一捧蔬菜（煮熟后约200g）",
                "蛋白质": "每餐一掌心大小的蛋白质（约50g）",
                "水果": "每天一个拳头大小的水果",
                "饮水": "每天1500-2000ml水"
            },
            "blood_sugar_targets": {
                "空腹": {"min": 4.4, "max": 7.0},
                "餐后2小时": {"min": 4.4, "max": 10.0}
            },
            "low_blood_sugar_advice": "血糖偏低时，建议立即补充15-20g快速碳水化合物，如3-4块糖果、半杯果汁、半罐可乐。"
        }

    def _semantic_search(self, query: str, knowledge_base: dict, dialect: str = "mandarin") -> str:
        """语义搜索"""
        context_parts = []
        query_lower = query.lower()

        normalized_query = dialect_service.normalize_food_name(query_lower, dialect)

        for food, info in knowledge_base["food_gi"].items():
            if food in query_lower or food in normalized_query or normalized_query in food:
                context_parts.append(
                    f"食物【{food}】：GI值 {info['gi']}，碳水化合物 {info['carbs']}，建议：{info['advice']}"
                )

        if any(word in query_lower for word in ["血糖", "控制", "正常", "范围"]):
            context_parts.append(
                f"血糖控制目标：空腹 {knowledge_base['blood_sugar_targets']['空腹']['min']}-{knowledge_base['blood_sugar_targets']['空腹']['max']} mmol/L，"
                f"餐后2小时 {knowledge_base['blood_sugar_targets']['餐后2小时']['min']}-{knowledge_base['blood_sugar_targets']['餐后2小时']['max']} mmol/L"
            )

        if any(word in query_lower for word in ["低血糖", "偏低", "饿了", "心慌"]):
            context_parts.append(f"低血糖处理：{knowledge_base['low_blood_sugar_advice']}")

        if any(word in query_lower for word in ["饮食", "吃", "食谱", "建议"]):
            context_parts.append(
                f"饮食原则：{knowledge_base['dietary_guidelines']['主食']}；"
                f"{knowledge_base['dietary_guidelines']['蔬菜']}；"
                f"{knowledge_base['dietary_guidelines']['蛋白质']}"
            )

        if not context_parts:
            context_parts = [
                "没有找到直接相关的知识，请根据一般原则给出建议。",
                "血糖控制建议：规律饮食、适量运动、按时服药、定期监测。"
            ]

        return "\n\n".join(context_parts[:5])

    def _build_prompt(
        self,
        message: str,
        dialect: str,
        diabetes_type: str,
        target_low: float,
        target_high: float,
        conversation_history: List[Dict],
        context: str,
        intent: Intent,
        entities: List[Entity],
        emotion: EmotionalState,
        blood_glucose_stage: Dict
    ) -> str:
        """构建Prompt"""
        dialect_names = {
            "mandarin": "普通话",
            "cantonese": "粤语",
            "sichuan": "四川话"
        }
        dialect_name = dialect_names.get(dialect, "普通话")

        dialect_greeting = dialect_service.get_dialect_expression("greeting", dialect)
        dialect_encourage = dialect_service.get_dialect_expression("encourage", dialect)
        dialect_concern = dialect_service.get_dialect_expression("concern", dialect)

        diabetes_names = {
            "type1": "1型糖尿病",
            "type2": "2型糖尿病",
            "gestational": "妊娠糖尿病",
            "other": "其他类型"
        }
        diabetes_name = diabetes_names.get(diabetes_type, "2型糖尿病")

        history_text = ""
        if conversation_history:
            for msg in conversation_history[-5:]:
                history_text += f"{msg.get('role', 'user')}: {msg.get('content', '')}\n"

        entities_text = "\n".join([f"- {e.type}: {e.value}" for e in entities]) if entities else "（无实体）"

        emotion_tone = emotion.value if emotion else "neutral"

        stage_info = ""
        if blood_glucose_stage and blood_glucose_stage.get("stage") != "unknown":
            stage_info = f"\n用户当前血糖状态：{blood_glucose_stage.get('description', '')}"

        prompt = f"""你是蓝诺，一位温暖的糖尿病管理助手，用{dialect_name}与用户交流。

用户信息：
- 糖尿病类型：{diabetes_name}
- 目标血糖范围：{target_low} - {target_high} mmol/L
- 当前情绪状态：{emotion_tone}{stage_info}

对话历史：
{history_text if history_text else "（无历史记录）"}

当前输入识别结果：
- 意图：{intent.type if intent else 'other'}
- 实体：
{entities_text}

相关知识：
{context}

用户新输入：{message}

回复要求：
1. 像朋友一样关心，别说教
2. 鼓励正向行为，不批评
3. 回答简洁，口语化表达
4. 如果用户情绪低落，给予安慰和鼓励
5. 融入{dialect_name}的表达习惯"""

        return prompt

    async def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "你是一位温暖的糖尿病管理助手蓝诺。"},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 500,
                        "temperature": 0.8
                    },
                    timeout=60.0
                )

                result = response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[AI] LLM call error: {e}")
            return "抱歉，我遇到了一点问题，请稍后再试。"

    async def _execute_action(
        self,
        intent: Intent,
        entities: List[Entity],
        user_id: int,
        db
    ) -> Optional[ActionResult]:
        """执行动作"""
        from app.models.blood_sugar import BloodSugar
        from app.models.meal import Meal, MealFood
        from sqlalchemy import select

        if intent.type == "record_blood_sugar":
            value = None
            for e in entities:
                if e.type == "blood_sugar_value":
                    try:
                        value = float(re.sub(r'[^\d.]', '', e.value))
                    except:
                        pass
                    break

            if value:
                blood_sugar = BloodSugar(
                    user_id=user_id,
                    value=value,
                    unit="mmol/L",
                    record_type="other",
                    recorded_at=datetime.now(),
                    source="voice"
                )
                db.add(blood_sugar)
                await db.commit()
                return ActionResult(type="blood_sugar_recorded", data={"value": value})

        elif intent.type == "record_meal":
            food_name = None
            food_amount = None

            for e in entities:
                if e.type == "food_name":
                    matched = getattr(e, "matched_food", None)
                    food_name = matched or e.value
                elif e.type == "food_amount":
                    food_amount = e.value

            if food_name:
                meal = Meal(
                    user_id=user_id,
                    meal_type="other",
                    recorded_at=datetime.now()
                )
                db.add(meal)
                await db.flush()

                meal_food = MealFood(
                    meal_id=meal.id,
                    food_name=food_name,
                    amount=food_amount or "适量"
                )
                db.add(meal_food)
                await db.commit()
                return ActionResult(type="meal_recorded", data={"food": food_name})

        return None


ai_service = AIService()