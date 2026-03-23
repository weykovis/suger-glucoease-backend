from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from app.config import get_settings

settings = get_settings()


class EmotionalState(Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    ANXIOUS = "anxious"
    FRUSTRATED = "frustrated"
    HOPEFUL = "hopeful"


class CareStrategy:
    """关怀策略"""

    STRATEGIES = {
        EmotionalState.POSITIVE: {
            "tone": "鼓励强化",
            "responses": [
                "继续保持！你做得很好！",
                "看到你的进步真开心！",
                "坚持下去，一定会越来越好的！"
            ],
            "action": "positive_reinforcement"
        },
        EmotionalState.NEUTRAL: {
            "tone": "温和询问",
            "responses": [
                "今天感觉怎么样？",
                "有什么想和我聊聊的吗？",
                "记得照顾好自己哦"
            ],
            "action": "gentle_inquiry"
        },
        EmotionalState.NEGATIVE: {
            "tone": "共情安慰",
            "responses": [
                "我理解你的感受，这确实不容易",
                "不要太责怪自己，我们一起慢慢来",
                "一时的波动不代表什么，你已经很努力了"
            ],
            "action": "empathetic_support"
        },
        EmotionalState.ANXIOUS: {
            "tone": "舒缓情绪",
            "responses": [
                "深呼吸，慢慢来，不用着急",
                "我在这里陪着你",
                "先放下担心，我们一起想办法"
            ],
            "action": "calming_support"
        },
        EmotionalState.FRUSTRATED: {
            "tone": "耐心倾听",
            "responses": [
                "我能感受到你的沮丧",
                "说出来会好受一些吗？",
                "不要放弃，我们换个方式试试"
            ],
            "action": "patient_listening"
        },
        EmotionalState.HOPEFUL: {
            "tone": "积极肯定",
            "responses": [
                "你对未来充满信心，这很好！",
                "继续保持这个状态！",
                "你正在做正确的选择"
            ],
            "action": "positive_affirmation"
        }
    }


class EmotionLearningService:
    """
    AI情感支持学习服务
    通过分析用户日常使用数据、健康记录及对话内容
    准确判断用户当前的血糖阶段，提供个性化的鼓励与支持
    """

    EMOTION_KEYWORDS = {
        EmotionalState.POSITIVE: ["好开心", "太好了", "谢谢", "不错", "加油", "棒", "进步", "开心"],
        EmotionalState.NEGATIVE: ["难过", "沮丧", "烦", "累", "担心", "害怕", "焦虑", "心情不好"],
        EmotionalState.ANXIOUS: ["紧张", "害怕", "不安", "慌", "担心", "压力", "怎么办"],
        EmotionalState.FRUSTRATED: ["气", "烦", "恼火", "怎么没用", "没用", "放弃", "受够了"],
        EmotionalState.HOPEFUL: ["希望", "加油", "努力", "会好的", "一起", "慢慢来", "坚持"]
    }

    def __init__(self):
        self.user_models: Dict[int, Dict] = {}
        self.conversation_history: Dict[int, List[Dict]] = {}

    def load_user_model(self, user_id: int, db) -> Dict:
        """加载用户模型"""
        from app.models.user import User
        from sqlalchemy import select

        result = db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return self._create_default_model(user_id)

        model = {
            "user_id": user_id,
            "diabetes_type": user.diabetes_type,
            "target_low": user.target_low,
            "target_high": user.target_high,
            "emotion_history": [],
            "preferences": {
                "encouragement_style": "gentle",
                "preferred_topics": [],
                "sensitive_topics": []
            },
            "interaction_patterns": {
                "avg_session_length": 0,
                "preferred_time": [],
                "common_intents": []
            },
            "health_trends": {
                "recent_avg": None,
                "trend_direction": "stable",
                "outlier_days": []
            }
        }

        self.user_models[user_id] = model
        return model

    def _create_default_model(self, user_id: int) -> Dict:
        """创建默认用户模型"""
        return {
            "user_id": user_id,
            "diabetes_type": "type2",
            "target_low": 3.9,
            "target_high": 7.0,
            "emotion_history": [],
            "preferences": {
                "encouragement_style": "gentle",
                "preferred_topics": [],
                "sensitive_topics": []
            },
            "interaction_patterns": {
                "avg_session_length": 0,
                "preferred_time": [],
                "common_intents": []
            },
            "health_trends": {
                "recent_avg": None,
                "trend_direction": "stable",
                "outlier_days": []
            }
        }

    def analyze_emotion(self, message: str, user_id: int) -> EmotionalState:
        """分析用户情绪状态"""
        message_lower = message.lower()
        emotion_scores: Dict[EmotionalState, int] = {
            EmotionalState.POSITIVE: 0,
            EmotionalState.NEUTRAL: 0,
            EmotionalState.NEGATIVE: 0,
            EmotionalState.ANXIOUS: 0,
            EmotionalState.FRUSTRATED: 0,
            EmotionalState.HOPEFUL: 0
        }

        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    emotion_scores[emotion] += 1

        if user_id in self.user_models:
            model = self.user_models[user_id]
            recent_emotions = [e["emotion"] for e in model.get("emotion_history", [])[-5:]]
            if recent_emotions:
                most_common = max(set(recent_emotions), key=recent_emotions.count)
                emotion_scores[EmotionalState[most_common.upper()]] += 2

        max_score = max(emotion_scores.values())
        if max_score == 0:
            return EmotionalState.NEUTRAL

        for emotion, score in emotion_scores.items():
            if score == max_score:
                return emotion

        return EmotionalState.NEUTRAL

    def record_interaction(
        self,
        user_id: int,
        message: str,
        emotion: EmotionalState,
        blood_sugar_value: Optional[float] = None,
        intent: Optional[str] = None
    ) -> None:
        """记录交互用于学习"""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []

        interaction = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "emotion": emotion.value,
            "blood_sugar_value": blood_sugar_value,
            "intent": intent
        }

        self.conversation_history[user_id].append(interaction)

        if len(self.conversation_history[user_id]) > 100:
            self.conversation_history[user_id] = self.conversation_history[user_id][-100:]

        self._update_user_model(user_id, interaction)

    def _update_user_model(self, user_id: int, interaction: Dict) -> None:
        """更新用户模型"""
        if user_id not in self.user_models:
            self.user_models[user_id] = self._create_default_model(user_id)

        model = self.user_models[user_id]

        emotion_history = model.get("emotion_history", [])
        emotion_history.append({
            "emotion": interaction["emotion"],
            "timestamp": interaction["timestamp"]
        })
        emotion_history = emotion_history[-20:]
        model["emotion_history"] = emotion_history

        if interaction.get("blood_sugar_value"):
            health_trends = model.get("health_trends", {})
            recent_values = [e["blood_sugar_value"] for e in emotion_history if e.get("blood_sugar_value")]
            if recent_values:
                health_trends["recent_avg"] = sum(recent_values) / len(recent_values)

        if interaction.get("intent"):
            patterns = model.get("interaction_patterns", {})
            common_intents = patterns.get("common_intents", [])
            common_intents.append(interaction["intent"])
            common_intents = common_intents[-20:]
            patterns["common_intents"] = common_intents

    def generate_emotional_response(
        self,
        user_id: int,
        emotion: EmotionalState,
        blood_sugar_status: Optional[Dict] = None
    ) -> str:
        """生成情感支持回复"""
        strategy = CareStrategy.STRATEGIES.get(emotion, CareStrategy.STRATEGIES[EmotionalState.NEUTRAL])

        if user_id in self.user_models:
            model = self.user_models[user_id]
            style = model.get("preferences", {}).get("encouragement_style", "gentle")
            if style == "direct":
                strategy = CareStrategy.STRATEGIES.get(emotion, CareStrategy.STRATEGIES[EmotionalState.NEUTRAL])

        response = strategy["responses"][0]

        if blood_sugar_status:
            response = self._integrate_health_status(response, blood_sugar_status)

        return response

    def _integrate_health_status(self, response: str, status: Dict) -> str:
        """整合健康状态到回复中"""
        if status.get("is_high"):
            response = f"{response} 最近血糖有点高，记得多注意饮食哦。"
        elif status.get("is_low"):
            response = f"{response} 最近血糖偏低，要小心低血糖风险。"
        elif status.get("is_improving"):
            response = f"{response} 看到你的血糖在改善，真的很棒！"

        return response

    def assess_blood_glucose_stage(self, user_id: int, recent_records: List[Dict]) -> Dict:
        """
        评估用户当前血糖阶段
        返回: {stage: str, description: str, recommendations: List[str]}
        """
        if not recent_records:
            return {
                "stage": "unknown",
                "description": "暂无足够数据进行分析",
                "recommendations": ["坚持记录血糖，我会更好地帮助你"]
            }

        values = [r.get("value", 0) for r in recent_records if r.get("value")]
        if not values:
            return {
                "stage": "unknown",
                "description": "暂无足够数据进行分析",
                "recommendations": ["坚持记录血糖，我会更好地帮助你"]
            }

        avg_value = sum(values) / len(values)
        high_count = sum(1 for v in values if v > 10.0)
        low_count = sum(1 for v in values if v < 3.9)
        in_range_count = sum(1 for v in values if 3.9 <= v <= 7.0)

        in_range_rate = in_range_count / len(values) * 100

        if in_range_rate >= 70:
            stage = "controlled"
            description = "血糖控制良好"
            recommendations = ["继续保持当前的生活方式"]
        elif in_range_rate >= 50:
            stage = "improving"
            description = "血糖控制有改善空间"
            recommendations = ["注意餐后血糖监测", "减少高GI食物摄入"]
        else:
            stage = "needs_attention"
            description = "血糖波动较大，需要更多关注"
            recommendations = ["建议咨询医生", "增加血糖监测频率", "注意饮食规律"]

        if low_count > 0:
            stage = "attention_low"
            description = "出现低血糖现象"
            recommendations.insert(0, "警惕低血糖，随身携带糖果")

        return {
            "stage": stage,
            "avg_value": round(avg_value, 1),
            "in_range_rate": round(in_range_rate, 1),
            "description": description,
            "recommendations": recommendations
        }

    def get_personalized_care(self, user_id: int) -> Dict:
        """获取个性化关怀策略"""
        if user_id not in self.user_models:
            return {
                "greeting": "你好！今天感觉怎么样？",
                "care_focus": "general",
                "suggested_topics": ["今天血糖怎么样", "有什么想聊的吗"]
            }

        model = self.user_models[user_id]
        recent_emotions = [e["emotion"] for e in model.get("emotion_history", [])[-5:]]

        if not recent_emotions:
            return {
                "greeting": "你好！好久没聊了，今天怎么样？",
                "care_focus": "general",
                "suggested_topics": ["最近血糖怎么样", "有什么需要帮助的吗"]
            }

        most_common_emotion = max(set(recent_emotions), key=recent_emotions.count)

        care_configs = {
            "positive": {
                "greeting": "看到你这么开心，我也替你高兴！",
                "care_focus": "positive_reinforcement",
                "suggested_topics": ["继续保持", "分享好心情"]
            },
            "negative": {
                "greeting": "我在这里陪你，有什么想说的吗？",
                "care_focus": "emotional_support",
                "suggested_topics": ["聊聊你的感受", "我可以帮你分析"]
            },
            "neutral": {
                "greeting": "今天怎么样？有什么我可以帮你的吗？",
                "care_focus": "general_support",
                "suggested_topics": ["记录血糖", "查询食物GI"]
            },
            "anxious": {
                "greeting": "深呼吸，我在这里。有什么让你担心的事情吗？",
                "care_focus": "anxiety_relief",
                "suggested_topics": ["血糖数据", "健康建议"]
            },
            "frustrated": {
                "greeting": "我理解你的沮丧，让我们一起想办法。",
                "care_focus": "frustration_support",
                "suggested_topics": ["遇到什么困难了", "我可以提供什么帮助"]
            },
            "hopeful": {
                "greeting": "你对未来充满希望，这很好！",
                "care_focus": "hope_enhancement",
                "suggested_topics": ["你的计划是什么", "继续加油"]
            }
        }

        return care_configs.get(
            most_common_emotion,
            care_configs["neutral"]
        )


emotion_learning_service = EmotionLearningService()