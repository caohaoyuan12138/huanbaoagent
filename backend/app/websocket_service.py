"""
WebSocket 实时推送服务 — 设备数据与告警的实时广播
所有连接的客户端（前端页面）可订阅设备实时数据流
"""
import asyncio
import json
import logging
import time
from typing import Dict, Set, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DeviceWebSocket:
    """
    WebSocket 设备实时推送服务

    功能:
    1. 设备实时数据广播（每轮询周期推送最新数据）
    2. 告警实时推送（产生告警时立即推送）
    3. 设备在线状态变更通知
    4. 客户端订阅管理（按设备过滤）
    """

    def __init__(self):
        self._clients: Set = set()
        self._device_subs: Dict[str, Set] = {}  # device_id -> set of clients
        self._device_data: Dict[str, Dict] = {}  # device_id -> latest reading
        self._lock = asyncio.Lock()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

    async def connect(self, ws) -> str:
        """客户端连接，返回 client_id"""
        client_id = f"client_{int(time.time() * 1000)}"
        async with self._lock:
            self._clients.add((client_id, ws))
        logger.info("WebSocket 客户端连接: %s, 总数: %d", client_id, len(self._clients))
        await self._send(client_id, {
            "type": "connected",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        return client_id

    async def disconnect(self, client_id: str):
        """客户端断开"""
        async with self._lock:
            self._clients = {(cid, ws) for cid, ws in self._clients if cid != client_id}
            # 清理订阅
            for dev_id, subs in self._device_subs.items():
                subs.discard(client_id)
        logger.info("WebSocket 客户端断开: %s, 剩余: %d", client_id, len(self._clients))

    async def subscribe_device(self, client_id: str, device_id: str):
        """客户端订阅特定设备"""
        async with self._lock:
            if device_id not in self._device_subs:
                self._device_subs[device_id] = set()
            self._device_subs[device_id].add(client_id)

    async def unsubscribe_device(self, client_id: str, device_id: str):
        """客户端取消订阅"""
        async with self._lock:
            if device_id in self._device_subs:
                self._device_subs[device_id].discard(client_id)
                if not self._device_subs[device_id]:
                    del self._device_subs[device_id]

    def update_device_data(self, device_id: str, data: Dict):
        """更新设备最新数据（由轮询任务调用）"""
        self._device_data[device_id] = {
            **data,
            "updated_at": datetime.utcnow().isoformat(),
        }
        # 广播给订阅了该设备的客户端
        subscribers = self._device_subs.get(device_id, set())
        if subscribers:
            asyncio.create_task(self._broadcast_to(subscribers, {
                "type": "device_data",
                "device_id": device_id,
                **data,
            }))

    def push_alert(self, alert: Dict):
        """推送告警给所有客户端"""
        asyncio.create_task(self._broadcast_all({
            "type": "alert",
            **alert,
            "timestamp": datetime.utcnow().isoformat(),
        }))

    def push_device_status(self, device_id: str, status: str, last_seen: str = None):
        """推送设备状态变更"""
        asyncio.create_task(self._broadcast_all({
            "type": "device_status",
            "device_id": device_id,
            "status": status,
            "last_seen": last_seen or datetime.utcnow().isoformat(),
        }))
        # 同时通知订阅者
        subscribers = self._device_subs.get(device_id, set())
        if subscribers:
            asyncio.create_task(self._broadcast_to(subscribers, {
                "type": "device_status",
                "device_id": device_id,
                "status": status,
                "last_seen": last_seen or datetime.utcnow().isoformat(),
            }))

    async def start_heartbeat(self):
        """启动心跳检测"""
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        """每30秒发送心跳并检测超时客户端"""
        while self._running:
            await asyncio.sleep(30)
            async with self._lock:
                dead = []
                for client_id, ws in self._clients:
                    try:
                        await ws.send(json.dumps({"type": "ping"}))
                    except Exception:
                        dead.append(client_id)
                for cid in dead:
                    await self.disconnect(cid)

    async def stop(self):
        """停止服务"""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        async with self._lock:
            self._clients.clear()
            self._device_subs.clear()

    async def _send(self, client_id: str, message: Dict):
        """发送消息给单个客户端"""
        async with self._lock:
            ws = next((ws for cid, ws in self._clients if cid == client_id), None)
        if ws:
            try:
                await ws.send(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.debug("发送失败 %s: %s", client_id, e)

    async def _broadcast_to(self, clients: Set[str], message: Dict):
        """广播给指定客户端集合"""
        tasks = []
        async with self._lock:
            client_map = {cid: ws for cid, ws in self._clients if cid in clients}
        for cid, ws in client_map.items():
            tasks.append(self._safe_send(ws, message))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _broadcast_all(self, message: Dict):
        """广播给所有客户端"""
        tasks = []
        async with self._lock:
            client_map = dict(self._clients)
        for cid, ws in client_map.items():
            tasks.append(self._safe_send(ws, message))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_send(self, ws, message: Dict):
        try:
            await ws.send(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.debug("广播发送失败: %s", e)

    def get_device_data(self, device_id: str) -> Optional[Dict]:
        """获取设备最新数据快照"""
        return self._device_data.get(device_id)

    def get_all_device_data(self) -> Dict[str, Dict]:
        """获取所有设备最新数据"""
        return dict(self._device_data)

    def get_client_count(self) -> int:
        return len(self._clients)

    def get_stats(self) -> Dict:
        return {
            "connected_clients": len(self._clients),
            "subscribed_devices": len(self._device_subs),
            "device_data_points": len(self._device_data),
        }


# 全局单例
_ws_service: Optional[DeviceWebSocket] = None


def get_ws_service() -> DeviceWebSocket:
    global _ws_service
    if _ws_service is None:
        _ws_service = DeviceWebSocket()
    return _ws_service


def reset_ws_service():
    global _ws_service
    _ws_service = None
