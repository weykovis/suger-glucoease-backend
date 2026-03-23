from typing import Dict, List, Optional, Tuple
import re
from app.services.dialect_service import dialect_service


class FoodMatchingService:
    """
    食物匹配服务 - 支持模糊匹配、同义词匹配、编辑距离匹配
    目标：方言称呼识别准确率 > 90%，地方特色食物识别准确率 > 85%
    """

    STANDARD_FOOD_DB: Dict[str, Dict] = {
        "米饭": {"gi": 72, "carbs": "25g/100g", "category": "主食", "aliases": ["白米饭", "大米饭", "米"]},
        "面条": {"gi": 55, "carbs": "25g/100g", "category": "主食", "aliases": ["面", "白面条", "挂面"]},
        "馒头": {"gi": 85, "carbs": "45g/100g", "category": "主食", "aliases": ["蒸馍", "白馒头"]},
        "面包": {"gi": 75, "carbs": "50g/100g", "category": "主食", "aliases": ["白面包", "吐司"]},
        "红薯": {"gi": 54, "carbs": "20g/100g", "category": "主食", "aliases": ["红苕", "地瓜"]},
        "南瓜": {"gi": 75, "carbs": "5g/100g", "category": "蔬菜", "aliases": ["倭瓜", "番瓜"]},
        "土豆": {"gi": 62, "carbs": "17g/100g", "category": "蔬菜", "aliases": ["马铃薯", "洋芋"]},
        "玉米": {"gi": 55, "carbs": "22g/100g", "category": "主食", "aliases": ["苞米", "棒子"]},
        "燕麦": {"gi": 55, "carbs": "25g/100g", "category": "主食", "aliases": ["莜麦", "雀麦"]},
        "苹果": {"gi": 36, "carbs": "13g/100g", "category": "水果", "aliases": ["apple"]},
        "香蕉": {"gi": 52, "carbs": "23g/100g", "category": "水果", "aliases": ["banana"]},
        "西瓜": {"gi": 72, "carbs": "8g/100g", "category": "水果", "aliases": ["水瓜"]},
        "葡萄": {"gi": 50, "carbs": "17g/100g", "category": "水果", "aliases": []},
        "橙子": {"gi": 43, "carbs": "11g/100g", "category": "水果", "aliases": ["橙"]},
        "牛奶": {"gi": 30, "carbs": "5g/100ml", "category": "奶制品", "aliases": ["鲜奶", "奶"]},
        "酸奶": {"gi": 35, "carbs": "10g/100ml", "category": "奶制品", "aliases": ["酸牛奶"]},
        "鸡蛋": {"gi": 0, "carbs": "0g/个", "category": "蛋白质", "aliases": ["鸡子", "蛋"]},
        "鸡胸肉": {"gi": 0, "carbs": "0g/100g", "category": "蛋白质", "aliases": ["鸡肉"]},
        "鱼肉": {"gi": 0, "carbs": "0g/100g", "category": "蛋白质", "aliases": ["鱼"]},
        "豆腐": {"gi": 15, "carbs": "2g/100g", "category": "蛋白质", "aliases": ["豆花", "嫩豆腐"]},
        "豆浆": {"gi": 30, "carbs": "3g/100ml", "category": "饮品", "aliases": ["豆奶"]},
        "奶茶": {"gi": 67, "carbs": "30g/杯", "category": "饮品", "aliases": ["奶精", "珍珠奶茶"]},
        "可乐": {"gi": 65, "carbs": "35g/罐", "category": "饮品", "aliases": ["汽水"]},
    }

    REGIONAL_SPECIALTIES: Dict[str, Dict] = {
        "biangbiang面": {"standard": "面条", "region": "陕西", "gi": 55},
        "油泼面": {"standard": "面条", "region": "陕西", "gi": 55},
        "臊子面": {"standard": "面条", "region": "陕西", "gi": 55},
        "兰州拉面": {"standard": "面条", "region": "甘肃", "gi": 55},
        "刀削面": {"standard": "面条", "region": "山西", "gi": 55},
        "热干面": {"standard": "面条", "region": "湖北", "gi": 60},
        "重庆小面": {"standard": "面条", "region": "重庆", "gi": 58},
        "螺蛳粉": {"standard": "面条", "region": "广西", "gi": 65},
        "肠粉": {"standard": "米粉", "region": "广东", "gi": 50},
        "叉烧饭": {"standard": "米饭", "region": "广东", "gi": 72},
        "煲仔饭": {"standard": "米饭", "region": "广东", "gi": 72},
        "炒粿条": {"standard": "面条", "region": "广东", "gi": 60},
        "煎饼果子": {"standard": "面粉制品", "region": "天津", "gi": 70},
        "肉夹馍": {"standard": "馒头", "region": "陕西", "gi": 85},
        "凉皮": {"standard": "面粉制品", "region": "陕西", "gi": 60},
        "锅盔": {"standard": "面粉制品", "region": "四川", "gi": 70},
        "馄饨": {"standard": "面粉制品", "region": "全国", "gi": 55},
        "汤圆": {"standard": "糯米制品", "region": "全国", "gi": 80},
        "粽子": {"standard": "糯米制品", "region": "全国", "gi": 80},
        "元宵": {"standard": "糯米制品", "region": "全国", "gi": 80},
    }

    FOOD_CATEGORIES = ["主食", "水果", "蔬菜", "蛋白质", "奶制品", "饮品"]

    def __init__(self):
        self.food_db = self.STANDARD_FOOD_DB.copy()
        self.food_db.update(self.REGIONAL_SPECIALTIES)
        self.alias_map = self._build_alias_map()
        self.reverse_alias_map = self._build_reverse_alias_map()

    def _build_alias_map(self) -> Dict[str, str]:
        """构建别名到标准名的映射"""
        alias_map = {}
        for food_name, info in self.STANDARD_FOOD_DB.items():
            alias_map[food_name] = food_name
            for alias in info.get("aliases", []):
                alias_map[alias] = food_name
                alias_map[alias.lower()] = food_name
        return alias_map

    def _build_reverse_alias_map(self) -> Dict[str, List[str]]:
        """构建标准名到别名的映射"""
        reverse_map = {}
        for food_name, info in self.STANDARD_FOOD_DB.items():
            reverse_map[food_name] = info.get("aliases", [])
        return reverse_map

    def normalize_input(self, user_input: str) -> str:
        """标准化用户输入"""
        user_input = user_input.strip().lower()
        user_input = re.sub(r'[^\w\s]', '', user_input)
        return user_input

    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算两个字符串的编辑距离"""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def match_by_similarity(self, user_input: str, threshold: float = 0.8) -> List[Tuple[str, float]]:
        """基于编辑距离的相似度匹配"""
        normalized_input = self.normalize_input(user_input)
        results = []

        for food_name in self.food_db.keys():
            normalized_food = self.normalize_input(food_name)
            max_len = max(len(normalized_input), len(normalized_food))

            if max_len == 0:
                continue

            distance = self.levenshtein_distance(normalized_input, normalized_food)
            similarity = 1 - (distance / max_len)

            if similarity >= threshold:
                results.append((food_name, similarity))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def fuzzy_match(self, user_input: str, dialect: Optional[str] = None) -> Optional[Dict]:
        """
        多级模糊匹配算法
        返回匹配的食物信息，如果没有匹配返回None
        """
        normalized_input = self.normalize_input(user_input)

        if not normalized_input:
            return None

        matched_food = None
        match_type = None

        level_1 = self._exact_match(normalized_input, dialect)
        if level_1:
            matched_food = level_1
            match_type = "exact"
        else:
            level_2 = self._alias_match(normalized_input, dialect)
            if level_2:
                matched_food = level_2
                match_type = "alias"
            else:
                level_3 = self._regional_match(normalized_input)
                if level_3:
                    matched_food = level_3
                    match_type = "regional"
                else:
                    level_4 = self._similarity_match(normalized_input)
                    if level_4:
                        matched_food = level_4
                        match_type = "similarity"

        if matched_food:
            result = self.food_db[matched_food].copy()
            result["food"] = matched_food
            result["match_type"] = match_type
            result["confidence"] = self._calculate_confidence(match_type, matched_food, dialect)
            return result

        return None

    def _exact_match(self, normalized_input: str, dialect: Optional[str] = None) -> Optional[str]:
        """第一级：精确匹配"""
        if normalized_input in self.food_db:
            return normalized_input

        for food_name in self.food_db.keys():
            if self.normalize_input(food_name) == normalized_input:
                return food_name

        return None

    def _alias_match(self, normalized_input: str, dialect: Optional[str] = None) -> Optional[str]:
        """第二级：别名匹配"""
        if normalized_input in self.alias_map:
            return self.alias_map[normalized_input]

        for alias, standard in self.alias_map.items():
            if alias == normalized_input:
                return standard

        if dialect:
            dialect_food = dialect_service.normalize_food_name(normalized_input, dialect)
            if dialect_food in self.food_db:
                return dialect_food

        return None

    def _regional_match(self, normalized_input: str) -> Optional[str]:
        """第三级：地方特色食物匹配"""
        for specialty, info in self.REGIONAL_SPECIALTIES.items():
            if self.normalize_input(specialty) == normalized_input:
                return specialty
            if normalized_input in self.normalize_input(specialty):
                return specialty

        return None

    def _similarity_match(self, normalized_input: str) -> Optional[str]:
        """第四级：相似度匹配"""
        matches = self.match_by_similarity(normalized_input, threshold=0.7)
        if matches:
            return matches[0][0]
        return None

    def _calculate_confidence(self, match_type: str, food_name: str, dialect: Optional[str] = None) -> float:
        """计算匹配置信度"""
        confidence_map = {
            "exact": 1.0,
            "alias": 0.95,
            "regional": 0.90,
            "similarity": 0.75
        }

        base_confidence = confidence_map.get(match_type, 0.5)

        if dialect:
            dialect_food = dialect_service.normalize_food_name(food_name, dialect)
            if dialect_food != food_name:
                base_confidence *= 0.9

        return round(base_confidence, 2)

    def search_foods(self, query: str = None, category: str = None, dialect: Optional[str] = None) -> List[Dict]:
        """搜索食物列表"""
        results = []

        for food_name, info in self.food_db.items():
            if category and info.get("category") != category:
                continue

            if query:
                match_result = self.fuzzy_match(query, dialect)
                if not match_result:
                    continue

            result = info.copy()
            result["food"] = food_name
            results.append(result)

        return results

    def get_food_by_name(self, food_name: str, dialect: Optional[str] = None) -> Optional[Dict]:
        """通过名称获取食物信息"""
        return self.fuzzy_match(food_name, dialect)

    def get_categories(self) -> List[str]:
        """获取所有食物分类"""
        categories = set()
        for info in self.food_db.values():
            if "category" in info:
                categories.add(info["category"])
        return sorted(list(categories))

    def add_custom_food(self, food_name: str, food_info: Dict, dialect: Optional[str] = None) -> bool:
        """添加自定义食物"""
        try:
            self.food_db[food_name] = food_info
            for alias in food_info.get("aliases", []):
                self.alias_map[alias] = food_name
                self.alias_map[alias.lower()] = food_name
            return True
        except Exception:
            return False

    def record_miss(self, user_input: str, expected_food: str, dialect: Optional[str] = None) -> None:
        """记录匹配失败案例，用于后续优化"""
        miss_log = {
            "user_input": user_input,
            "expected_food": expected_food,
            "dialect": dialect,
            "timestamp": "now"
        }
        print(f"[FoodMatching] Match miss recorded: {miss_log}")


food_matching_service = FoodMatchingService()