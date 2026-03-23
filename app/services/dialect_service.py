from typing import Dict, List, Optional
from app.config import get_settings

settings = get_settings()


class DialectService:
    """
    方言服务 - 支持多方言识别和适配
    """

    DIALECT_CODE_MAP = {
        "mandarin": "zh-CN",
        "cantonese": "zh-CN",  # 粤语使用中文
        "sichuan": "zh-CN",    # 四川话使用中文
        "hakka": "zh-CN",      # 客家话
        "taiwanese": "zh-CN",  # 台语
        "shanghainese": "zh-CN",  # 上海话
    }

    FOOD_NAME_ALIASES: Dict[str, Dict[str, List[str]]] = {
        "mandarin": {},
        "cantonese": {
            "米饭": ["饭", "白饭", "米"],
            "面条": ["面", "粉"],
            "苹果": ["苹果"],
            "香蕉": ["香蕉仔"],
            "西瓜": ["瓜"],
            "牛奶": ["奶"],
            "鸡蛋": ["鸡仔"],
        },
        "sichuan": {
            "米饭": ["米", "干饭"],
            "面条": ["面", "挂面"],
            "馒头": ["蒸馍"],
            "豆腐": ["豆花"],
        },
        "shanghainese": {
            "米饭": ["饭", "白饭"],
            "面条": ["面", "切面"],
            "馄饨": ["菜包"],
        }
    }

    DIALECT_EXPRESSIONS: Dict[str, Dict[str, List[str]]] = {
        "cantonese": {
            "blood_sugar_high": ["血糖高", "血糖偏高", "糖高"],
            "blood_sugar_low": ["血糖低", "血糖偏低", "糖低"],
            "good": ["好好", "几好", "唔错"],
            "bad": ["唔好", "差", "麻麻地"],
            "record": ["记录", "写低", "登记"],
        },
        "sichuan": {
            "blood_sugar_high": ["血糖高", "偏高"],
            "blood_sugar_low": ["血糖低", "偏低"],
            "good": ["好", "巴适", "安逸"],
            "bad": ["不好", "撇", "恼火"],
            "record": ["记下来", "记一哈"],
        },
        "shanghainese": {
            "blood_sugar_high": ["血糖高"],
            "blood_sugar_low": ["血糖低"],
            "good": ["蛮好", "好个"],
            "bad": ["勿好", "差个"],
            "record": ["记一记", "写下来"],
        }
    }

    DIALECT_RESPONSES: Dict[str, Dict[str, str]] = {
        "cantonese": {
            "greeting": "你好啊！今日血糖点样？",
            "encourage": "做得好好啊！继续加油！",
            "concern": "我理解你嘅感受，唔使太担心。",
            "suggestion": "建议你试下{option}，应该会有帮助。",
            "record_success": "已经帮你登记好了，记得定时测量啊！",
        },
        "sichuan": {
            "greeting": "你好啊！今天血糖咋样？",
            "encourage": "做得巴适！继续加油哈！",
            "concern": "我晓得你嘞感受，莫得啥子，慢慢来。",
            "suggestion": "建议你试哈{option}，应该有帮助。",
            "record_success": "记下来了，记得定时测血糖哈！",
        },
        "shanghainese": {
            "greeting": "你好啊！今早血糖哪能？",
            "encourage": "做得蛮好！继续加油！",
            "concern": "我晓得侬呃感受，勿要太担心。",
            "suggestion": "建议侬试下{option}，应该有帮助。",
            "record_success": "记下来了，记得定时测量啊！",
        }
    }

    def __init__(self):
        self.current_dialect = "mandarin"

    def set_dialect(self, dialect: str) -> None:
        """设置当前方言"""
        if dialect in self.DIALECT_CODE_MAP:
            self.current_dialect = dialect

    def get_dialect_code(self, dialect: Optional[str] = None) -> str:
        """获取火山引擎方言代码"""
        dialect = dialect or self.current_dialect
        return self.DIALECT_CODE_MAP.get(dialect, "zh-CN")

    def normalize_food_name(self, food_name: str, dialect: Optional[str] = None) -> str:
        """
        将方言食物名称转换为标准食物名称
        使用反向映射表
        """
        dialect = dialect or self.current_dialect

        if dialect in self.FOOD_NAME_ALIASES:
            aliases = self.FOOD_NAME_ALIASES[dialect]
            for standard_name, alias_list in aliases.items():
                if food_name in alias_list or food_name == standard_name:
                    return standard_name

        return food_name

    def get_dialect_expression(self, key: str, dialect: Optional[str] = None) -> str:
        """获取方言表达"""
        dialect = dialect or self.current_dialect

        if dialect in self.DIALECT_RESPONSES:
            return self.DIALECT_RESPONSES[dialect].get(key, self.DIALECT_RESPONSES["mandarin"].get(key, ""))

        return key

    def get_dialect_food_aliases(self, standard_food_name: str, dialect: Optional[str] = None) -> List[str]:
        """获取标准食物名称的方言别名"""
        dialect = dialect or self.current_dialect

        if dialect in self.FOOD_NAME_ALIASES:
            return self.FOOD_NAME_ALIASES[dialect].get(standard_food_name, [])

        return []

    def extract_dialect_keywords(self, text: str, dialect: Optional[str] = None) -> Dict[str, bool]:
        """
        从文本中提取方言关键词
        返回检测到的方言特征
        """
        dialect = dialect or self.current_dialect
        result = {}

        if dialect in self.DIALECT_EXPRESSIONS:
            expressions = self.DIALECT_EXPRESSIONS[dialect]
            for category, keywords in expressions.items():
                for keyword in keywords:
                    if keyword in text:
                        result[keyword] = True
                        break

        return result

    def detect_dialect(self, text: str) -> Optional[str]:
        """
        自动检测文本中的方言特征
        返回最可能的方言
        """
        dialect_scores: Dict[str, int] = {
            "cantonese": 0,
            "sichuan": 0,
            "shanghainese": 0,
        }

        for dialect, expressions in self.DIALECT_EXPRESSIONS.items():
            for category, keywords in expressions.items():
                for keyword in keywords:
                    if keyword in text:
                        dialect_scores[dialect] += 1

        max_score = max(dialect_scores.values())
        if max_score > 0:
            for dialect, score in dialect_scores.items():
                if score == max_score:
                    return dialect

        return None

    def build_dialect_prompt(self, base_prompt: str, dialect: Optional[str] = None) -> str:
        """构建带方言风格的Prompt"""
        dialect = dialect or self.current_dialect

        dialect_styles = {
            "mandarin": "使用标准的普通话表达",
            "cantonese": "适当使用粤语常用表达，如'几好'、'唔使担心'等",
            "sichuan": "适当使用四川话常用表达，如'巴适'、'咋样'等",
            "shanghainese": "适当使用上海话常用表达，如'蛮好'、'哪能'等",
        }

        style_hint = dialect_styles.get(dialect, dialect_styles["mandarin"])
        return f"{base_prompt}\n\n风格要求：{style_hint}"


dialect_service = DialectService()