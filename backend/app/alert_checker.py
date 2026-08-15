"""
实时告警检查器 — 后台异步任务
每5分钟检查所有在线设备的最近读数，与限值对比生成告警
"""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import (
    Device, DeviceReading, PollutionLimit, Alert, PollutionFactor
)

logger = logging.getLogger(__name__)


async def _check_alerts():
    """核心告警检查逻辑"""
    db: Session = SessionLocal()
    try:
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        thirty_min_ago = now - timedelta(minutes=30)

        online_devices = db.query(Device).filter(Device.status == "online").all()
        if not online_devices:
            logger.debug("暂无在线设备，跳过告警检查")
            return

        for device in online_devices:
            readings = db.query(DeviceReading).filter(
                DeviceReading.device_id == device.id,
                DeviceReading.timestamp >= one_hour_ago,
            ).order_by(DeviceReading.timestamp.desc()).all()

            if not readings:
                continue

            latest = readings[0]
            factor_symbol = device.factor
            unit = device.unit
            value = latest.value

            factor_obj = db.query(PollutionFactor).filter(
                PollutionFactor.symbol == factor_symbol
            ).first()

            limits: list[PollutionLimit] = []
            if factor_obj:
                limits = db.query(PollutionLimit).filter(
                    PollutionLimit.factor_id == factor_obj.id
                ).all()
            else:
                limits = db.query(PollutionLimit).filter(
                    PollutionLimit.unit == unit
                ).all()

            if not limits:
                continue

            limit_value = limits[0].limit_value
            if limit_value is None or limit_value <= 0:
                continue

            severity = "critical" if value > limit_value * 1.5 else "warning"
            message = (
                f"设备[{device.name}] {factor_symbol} 监测值 {value}{unit} "
                f"超过限值 {limit_value}{unit}"
            )

            existing = db.query(Alert).filter(
                Alert.device_id == device.id,
                Alert.factor == factor_symbol,
                Alert.severity == severity,
                Alert.status == "unread",
                Alert.created_at >= thirty_min_ago,
            ).first()

            if existing:
                continue

            alert = Alert(
                device_id=device.id,
                factor=factor_symbol,
                value=value,
                limit_value=limit_value,
                unit=unit,
                severity=severity,
                status="unread",
                message=message,
                created_at=now,
            )
            db.add(alert)
            db.commit()
            logger.info("告警已生成: device=%s factor=%s value=%s severity=%s",
                        device.name, factor_symbol, value, severity)

            # 异步推送飞书 + WebSocket，不阻塞主循环
            asyncio.create_task(_push_to_feishu(
                device.name, factor_symbol, value, limit_value,
                unit, severity, message,
            ))
            asyncio.create_task(_push_alert_to_ws({
                "id": alert.id,
                "device_id": device.id,
                "factor": factor_symbol,
                "value": value,
                "limit_value": limit_value,
                "severity": severity,
                "message": message,
            }))

    except Exception as e:
        logger.error("告警检查失败: %s", str(e))
    finally:
        db.close()


async def _push_to_feishu(device_name, factor, value, limit, unit, severity, message):
    """推送到飞书（异步执行避免阻塞主循环）"""
    try:
        from app.feishu_notify import send_feishu_alert
        send_feishu_alert(
            device_name=device_name,
            factor=factor,
            value=value,
            limit_value=limit,
            severity=severity,
            message=message,
        )
    except Exception as e:
        logger.warning(f"飞书推送失败: {e}")


async def _push_alert_to_ws(alert_data):
    """推送告警到 WebSocket"""
    try:
        from app.websocket_service import get_ws_service
        ws = get_ws_service()
        ws.push_alert(alert_data)
    except Exception as e:
        logger.debug(f"WebSocket告警推送失败: {e}")


async def run_alert_checker():
    """每5分钟执行一次告警检查的后台循环"""
    while True:
        try:
            await _check_alerts()
        except Exception as e:
            logger.error("告警检查循环异常: %s", str(e))
        await asyncio.sleep(300)
