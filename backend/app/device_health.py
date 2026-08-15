"""
设备健康监控器 — 主动检测设备连接状态，维护在线/离线/故障状态
对比现有轮询方式，提供更精确的设备健康指标
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Device, DeviceReading
from app.modbus_device import ModbusDevicePool
from app.websocket_service import get_ws_service

logger = logging.getLogger(__name__)


class DeviceHealthMonitor:
    """
    设备健康监控器

    功能:
    1. 每30秒 ping 所有 Modbus 设备，检测连接状态
    2. 记录 last_seen 时间，超时自动标记离线
    3. 计算设备 uptime / 可用率
    4. 通过 WebSocket 推送状态变更
    """

    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._device_latencies: Dict[int, float] = {}  # device_id -> last latency (ms)
        self._device_last_seen: Dict[int, datetime] = {}  # device_id -> last seen time
        self._device_success_count: Dict[int, int] = {}  # device_id -> success count
        self._device_fail_count: Dict[int, int] = {}  # device_id -> fail count

    async def start(self):
        """启动健康监控"""
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("设备健康监控已启动，检查间隔: %ds", self.check_interval)

    async def stop(self):
        """停止健康监控"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("设备健康监控已停止")

    async def _monitor_loop(self):
        """主监控循环"""
        while self._running:
            try:
                await self._check_all_devices()
            except Exception as e:
                logger.error("健康监控循环异常: %s", str(e))
            await asyncio.sleep(self.check_interval)

    async def _check_all_devices(self):
        """检查所有 Modbus 设备的连接状态"""
        db: Session = SessionLocal()
        try:
            modbus_devices = db.query(Device).filter(
                Device.protocol.in_(["modbus", "modbus_hj212"])
            ).all()

            ws = get_ws_service()
            pool = ModbusDevicePool()

            for device in modbus_devices:
                await self._check_device(db, device, pool, ws)

            # 检查离线超时
            await self._check_offline_devices(db, ws)

        except Exception as e:
            logger.error("健康检查异常: %s", str(e))
        finally:
            db.close()

    async def _check_device(self, db: Session, device: Device, pool, ws):
        """检查单个设备"""
        mn = device.mn or ""
        ip = device.ip_address or ""
        if not mn or not ip:
            return

        start_time = datetime.utcnow()
        try:
            modbus_dev = pool.get_device(mn)
            if modbus_dev and modbus_dev.connected:
                latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                self._device_latencies[device.id] = latency_ms
                self._device_last_seen[device.id] = datetime.utcnow()
                self._device_success_count[device.id] = \
                    self._device_success_count.get(device.id, 0) + 1

                if device.status != "online":
                    device.status = "online"
                    db.commit()
                    ws.push_device_status(str(device.id), "online",
                                          self._device_last_seen[device.id].isoformat())
                    logger.info("设备上线: %s (%s)", device.name, ip)
            else:
                # 尝试重连
                modbus_dev = pool.add_device(mn, ip, device.port or 8000, device.timeout or 5.0)
                if modbus_dev.connect():
                    latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                    self._device_latencies[device.id] = latency_ms
                    self._device_last_seen[device.id] = datetime.utcnow()
                    self._device_success_count[device.id] = \
                        self._device_success_count.get(device.id, 0) + 1
                    if device.status != "online":
                        device.status = "online"
                        db.commit()
                        ws.push_device_status(str(device.id), "online",
                                              self._device_last_seen[device.id].isoformat())
                        logger.info("设备重连成功: %s (%s)", device.name, ip)
                else:
                    self._device_fail_count[device.id] = \
                        self._device_fail_count.get(device.id, 0) + 1
                    if device.status != "offline":
                        device.status = "offline"
                        db.commit()
                        ws.push_device_status(str(device.id), "offline")
                        logger.warning("设备离线: %s (%s)", device.name, ip)
        except Exception as e:
            logger.debug("设备 %s 检查异常: %s", device.name, str(e))
            self._device_fail_count[device.id] = \
                self._device_fail_count.get(device.id, 0) + 1
            if device.status != "offline":
                device.status = "offline"
                db.commit()
                ws.push_device_status(str(device.id), "offline")

    async def _check_offline_devices(self, db: Session, ws):
        """检查超时应离线的设备"""
        timeout = timedelta(seconds=self.check_interval * 3)
        now = datetime.utcnow()

        for device_id, last_seen in list(self._device_last_seen.items()):
            if last_seen < now - timeout:
                if device_id not in self._device_fail_count:
                    self._device_fail_count[device_id] = 0
                self._device_fail_count[device_id] += 1

                # 连续3次未检测到才标记离线
                if self._device_fail_count.get(device_id, 0) >= 3:
                    device = db.query(Device).filter(Device.id == device_id).first()
                    if device and device.status != "offline":
                        device.status = "offline"
                        db.commit()
                        ws.push_device_status(str(device_id), "offline")
                        logger.info("设备超时离线: id=%s", device_id)

    def get_device_health(self, device_id: int) -> Dict:
        """获取单台设备健康指标"""
        return {
            "device_id": device_id,
            "latency_ms": round(self._device_latencies.get(device_id, 0), 1),
            "last_seen": self._device_last_seen.get(device_id).isoformat()
                if device_id in self._device_last_seen else None,
            "success_count": self._device_success_count.get(device_id, 0),
            "fail_count": self._device_fail_count.get(device_id, 0),
            "availability": self._calc_availability(device_id),
        }

    def _calc_availability(self, device_id: int) -> float:
        """计算可用率（成功/总尝试）"""
        success = self._device_success_count.get(device_id, 0)
        fails = self._device_fail_count.get(device_id, 0)
        total = success + fails
        if total == 0:
            return 100.0
        return round(success / total * 100, 1)

    def get_all_health(self) -> Dict[int, Dict]:
        """获取所有设备健康指标"""
        result = {}
        for device_id in set(list(self._device_latencies.keys()) +
                             list(self._device_last_seen.keys()) +
                             list(self._device_success_count.keys()) +
                             list(self._device_fail_count.keys())):
            result[device_id] = self.get_device_health(device_id)
        return result

    def record_reading(self, device_id: int, value: float):
        """记录一次成功读取（由轮询任务调用）"""
        self._device_last_seen[device_id] = datetime.utcnow()
        self._device_success_count[device_id] = \
            self._device_success_count.get(device_id, 0) + 1
        if device_id in self._device_fail_count:
            del self._device_fail_count[device_id]


# 全局单例
_health_monitor: Optional[DeviceHealthMonitor] = None


def get_health_monitor() -> DeviceHealthMonitor:
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = DeviceHealthMonitor()
    return _health_monitor


def reset_health_monitor():
    global _health_monitor
    _health_monitor = None
