from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import asyncio
import json


class SyncStatus(Enum):
    PENDING = "pending"
    SYNCING = "syncing"
    SUCCESS = "success"
    FAILED = "failed"
    CONFLICT = "conflict"


class ConflictResolution(Enum):
    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"
    MERGE = "merge"
    MANUAL = "manual"


class DataSyncService:
    """
    跨平台数据同步服务
    支持：微信小程序、H5、iOS App、Android App
    """

    SYNC_PRIORITY = {
        "blood_sugar": 1,
        "meal": 2,
        "user_profile": 3,
        "settings": 4,
        "chat_history": 5
    }

    def __init__(self):
        self.sync_queue: List[Dict] = []
        self.sync_history: List[Dict] = []
        self.last_sync_time: Dict[str, datetime] = {}
        self.sync_locks: Dict[str, asyncio.Lock] = {}

    async def sync_data(
        self,
        user_id: int,
        data_type: str,
        local_data: Dict,
        server_version: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        执行数据同步
        """
        lock = self.sync_locks.get(f"{user_id}_{data_type}")
        if not lock:
            lock = asyncio.Lock()
            self.sync_locks[f"{user_id}_{data_type}"] = lock

        async with lock:
            sync_result = {
                "status": SyncStatus.PENDING,
                "data_type": data_type,
                "timestamp": datetime.now().isoformat(),
                "local_version": local_data.get("version", 0),
                "server_version": server_version.get("version", 0) if server_version else 0
            }

            try:
                sync_result["status"] = SyncStatus.SYNCING

                if self._need_sync(local_data, server_version):
                    conflict_result = self._check_conflict(local_data, server_version)

                    if conflict_result["has_conflict"]:
                        resolution = await self._resolve_conflict(
                            local_data,
                            server_version,
                            ConflictResolution.MERGE
                        )
                        sync_result["data"] = resolution
                        sync_result["conflict_resolved"] = True
                    else:
                        sync_result["data"] = local_data
                        sync_result["conflict_resolved"] = False

                    sync_result["status"] = SyncStatus.SUCCESS
                else:
                    sync_result["data"] = server_version
                    sync_result["status"] = SyncStatus.SUCCESS
                    sync_result["message"] = "No sync needed"

                self._update_sync_history(sync_result)
                return sync_result

            except Exception as e:
                sync_result["status"] = SyncStatus.FAILED
                sync_result["error"] = str(e)
                return sync_result

    def _need_sync(self, local_data: Optional[Dict], server_data: Optional[Dict]) -> bool:
        """检查是否需要同步"""
        if not server_data:
            return True

        local_version = local_data.get("version", 0)
        server_version = server_data.get("version", 0)

        return local_version > server_version

    def _check_conflict(self, local_data: Optional[Dict], server_data: Optional[Dict]) -> Dict[str, bool]:
        """检查数据冲突"""
        if not server_data:
            return {"has_conflict": False}

        local_updated = local_data.get("updated_at", "")
        server_updated = server_data.get("updated_at", "")

        if local_updated and server_updated:
            local_time = datetime.fromisoformat(local_updated)
            server_time = datetime.fromisoformat(server_updated)
            time_diff = abs((local_time - server_time).total_seconds())

            if time_diff < 60:
                return {"has_conflict": True, "time_diff": time_diff}

        return {"has_conflict": False}

    async def _resolve_conflict(
        self,
        local_data: Dict,
        server_data: Dict,
        resolution: ConflictResolution
    ) -> Dict:
        """解决数据冲突"""
        if resolution == ConflictResolution.SERVER_WINS:
            return server_data

        elif resolution == ConflictResolution.CLIENT_WINS:
            return local_data

        elif resolution == ConflictResolution.MERGE:
            return self._merge_data(local_data, server_data)

        else:
            return self._manual_merge(local_data, server_data)

    def _merge_data(self, local_data: Dict, server_data: Dict) -> Dict:
        """合并数据"""
        merged = server_data.copy()

        for key, value in local_data.items():
            if key not in merged:
                merged[key] = value
            elif isinstance(value, dict) and isinstance(merged[key], dict):
                merged[key] = self._merge_data(value, merged[key])
            elif isinstance(value, list) and isinstance(merged[key], list):
                merged[key] = self._merge_lists(value, merged[key])
            elif key in ["updated_at"]:
                if local_data.get("updated_at", "") > server_data.get("updated_at", ""):
                    merged[key] = value

        merged["version"] = max(
            local_data.get("version", 0),
            server_data.get("version", 0)
        ) + 1
        merged["merged_at"] = datetime.now().isoformat()

        return merged

    def _merge_lists(self, local_list: List, server_list: List) -> List:
        """合并列表数据"""
        result = server_list.copy()
        local_ids = {item.get("id") for item in local_list if isinstance(item, dict)}

        for item in local_list:
            if isinstance(item, dict) and item.get("id") not in local_ids:
                result.append(item)

        return result

    def _manual_merge(self, local_data: Dict, server_data: Dict) -> Dict:
        """手动合并（标记冲突待处理）"""
        return {
            "has_conflict": True,
            "local_data": local_data,
            "server_data": server_data,
            "resolution_required": True
        }

    def _update_sync_history(self, sync_result: Dict) -> None:
        """更新同步历史"""
        self.sync_history.append(sync_result)
        if len(self.sync_history) > 100:
            self.sync_history = self.sync_history[-100:]

    async def get_sync_status(self, user_id: int) -> Dict[str, Any]:
        """获取同步状态"""
        return {
            "last_sync": self.last_sync_time.get(user_id),
            "pending_items": len(self.sync_queue),
            "history": self.sync_history[-10:]
        }

    async def queue_sync(self, user_id: int, data_type: str, data: Dict) -> None:
        """将数据加入同步队列"""
        self.sync_queue.append({
            "user_id": user_id,
            "data_type": data_type,
            "data": data,
            "queued_at": datetime.now().isoformat(),
            "priority": self.SYNC_PRIORITY.get(data_type, 10)
        })

        self.sync_queue.sort(key=lambda x: x["priority"])

    async def process_sync_queue(self) -> None:
        """处理同步队列"""
        while self.sync_queue:
            item = self.sync_queue.pop(0)
            await self.sync_data(
                item["user_id"],
                item["data_type"],
                item["data"]
            )

    def get_encryption_key(self, user_id: int) -> str:
        """获取用户加密密钥（实际应该从密钥服务获取）"""
        return f"user_key_{user_id}"

    def encrypt_data(self, data: Dict, user_id: int) -> str:
        """加密数据（实际应该使用AES等加密算法）"""
        key = self.get_encryption_key(user_id)
        data_str = json.dumps(data)
        return data_str

    def decrypt_data(self, encrypted_data: str, user_id: int) -> Dict:
        """解密数据"""
        key = self.get_encryption_key(user_id)
        return json.loads(encrypted_data)


data_sync_service = DataSyncService()