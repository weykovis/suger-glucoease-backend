from functools import lru_cache
import json
import redis
from app.config import settings

_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client

class CacheService:
    def __init__(self):
        self.client = get_redis_client()

    def get(self, key: str) -> str | None:
        return self.client.get(key)

    def set(self, key: str, value: str, expire: int = 300) -> None:
        self.client.setex(key, expire, value)

    def delete(self, key: str) -> None:
        self.client.delete(key)

    def get_json(self, key: str):
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None

    def set_json(self, key: str, value: dict, expire: int = 300):
        self.client.setex(key, expire, json.dumps(value, ensure_ascii=False))

    def cache_key(self, prefix: str, *args) -> str:
        return f"{prefix}:{':'.join(str(arg) for arg in args)}"

cache_service = CacheService()
