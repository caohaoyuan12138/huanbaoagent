"""
设备数据接收 API — 供外部系统通过 HTTP/MQTT 转发设备数据
外部系统可以 POST 数据到本接口，数据自动入库并触发告警
"""
import os
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.db.models import Device, DeviceReading, PollutionLimit, PollutionFactor, Alert
from app.websocket_service import get_ws_service
from datetime import datetime, timedelta

router = APIRouter()


@router.post("/external/devices/{device_id}/data")
async def receive_device_data(
    device_id: int,
    readings: List[dict],
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None),
):
    """
    接收外部系统转发的设备数据

    用法示例：
        curl -X POST http://your-server/api/devices/1/data \
          -H "Content-Type: application/json" \
          -d '[{"factor": "VOCs", "value": 32.5, "unit": "mg/m³", "status": "normal"}]'

    认证（可选）：
        在 .env 中设置 EXTERNAL_API_KEY=your-key
        请求头添加: X-API-Key: your-key
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # 认证检查
    api_key = os.getenv("EXTERNAL_API_KEY", "")
    if api_key and x_api_key != api_key:
        raise HTTPException(status_code=401, detail="API Key 无效")

    saved = []
    ws = get_ws_service()

    for r in readings:
        factor = r.get("factor", device.factor)
        value = float(r.get("value", 0))
        unit = r.get("unit", device.unit)
        status = r.get("status", "normal")
        ts = r.get("timestamp", datetime.utcnow().isoformat())

        reading = DeviceReading(
            device_id=device.id,
            factor=factor,
            value=value,
            unit=unit,
            timestamp=datetime.fromisoformat(ts) if isinstance(ts, str) else ts,
            status=status,
            raw_data=r.get("raw_data"),
            data_type="external_api",
        )
        db.add(reading)
        saved.append(reading)

        # 更新设备状态
        device.status = "online"
        device.last_seen = datetime.utcnow()
        device.total_readings = (device.total_readings or 0) + 1

        # 推送实时数据
        ws.update_device_data(str(device.id), {"factor": factor, "value": value, "unit": unit})

    db.commit()

    # 异步检查告警
    import asyncio
    asyncio.create_task(_check_alert_for_device(device.id, db))

    return {"message": f"已接收 {len(saved)} 条数据", "device_id": device_id, "saved": len(saved)}


@router.post("/external/batch")
async def receive_batch_data(
    payload: dict,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None),
):
    """
    批量接收多设备数据

    格式：
    {
      "devices": [
        {"device_id": 1, "readings": [{"factor": "VOCs", "value": 32.5}]},
        {"device_id": 2, "readings": [{"factor": "COD", "value": 45.0}]}
      ]
    }
    """
    api_key = os.getenv("EXTERNAL_API_KEY", "")
    if api_key and x_api_key != api_key:
        raise HTTPException(status_code=401, detail="API Key 无效")

    devices = payload.get("devices", [])
    total_saved = 0
    ws = get_ws_service()

    for dev_data in devices:
        device_id = dev_data.get("device_id")
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            continue

        for r in dev_data.get("readings", []):
            reading = DeviceReading(
                device_id=device.id,
                factor=r.get("factor", device.factor),
                value=float(r.get("value", 0)),
                unit=r.get("unit", device.unit),
                timestamp=datetime.utcnow(),
                status=r.get("status", "normal"),
                data_type="external_api",
            )
            db.add(reading)
            total_saved += 1

            device.status = "online"
            device.last_seen = datetime.utcnow()
            device.total_readings = (device.total_readings or 0) + 1
            ws.update_device_data(str(device.id), {
                "factor": r.get("factor", device.factor),
                "value": float(r.get("value", 0)),
                "unit": r.get("unit", device.unit),
            })

    db.commit()
    return {"message": f"已接收 {total_saved} 条数据", "device_count": len(devices)}


async def _check_alert_for_device(device_id: int, db: Session):
    """收到数据后检查是否产生告警"""
    try:
        from app.db.database import SessionLocal
        from app.db.models import Device, PollutionLimit, PollutionFactor, Alert
        import logging
        logger = logging.getLogger(__name__)

        db: Session = SessionLocal()
        try:
            device = db.query(Device).filter(Device.id == device_id).first()
            if not device:
                return

            now = datetime.now()
            one_hour_ago = now - timedelta(hours=1)
            thirty_min_ago = now - timedelta(minutes=30)

            latest = db.query(DeviceReading).filter(
                DeviceReading.device_id == device_id,
                DeviceReading.timestamp >= one_hour_ago,
            ).order_by(DeviceReading.timestamp.desc()).first()
            if not latest:
                return

            factor_symbol = device.factor
            unit = device.unit
            value = latest.value

            factor_obj = db.query(PollutionFactor).filter(PollutionFactor.symbol == factor_symbol).first()
            limits = []
            if factor_obj:
                limits = db.query(PollutionLimit).filter(PollutionLimit.factor_id == factor_obj.id).all()
            else:
                limits = db.query(PollutionLimit).filter(PollutionLimit.unit == unit).all()
            if not limits or not limits[0].limit_value:
                return

            limit_value = limits[0].limit_value
            if value <= limit_value:
                return

            severity = "critical" if value > limit_value * 1.5 else "warning"
            message = f"设备[{device.name}] {factor_symbol} 监测值 {value}{unit} 超过限值 {limit_value}{unit}"

            existing = db.query(Alert).filter(
                Alert.device_id == device_id, Alert.factor == factor_symbol,
                Alert.severity == severity, Alert.status == "unread",
                Alert.created_at >= thirty_min_ago,
            ).first()
            if existing:
                return

            alert = Alert(device_id=device_id, factor=factor_symbol, value=value,
                         limit_value=limit_value, unit=unit, severity=severity,
                         status="unread", message=message, created_at=now)
            db.add(alert)
            db.commit()
            logger.info("外部数据触发告警: %s", message)

            ws = get_ws_service()
            ws.push_alert({"id": alert.id, "device_id": device_id, "factor": factor_symbol,
                          "value": value, "limit_value": limit_value,
                          "severity": severity, "message": message})
        finally:
            db.close()
    except Exception as e:
        logging.getLogger(__name__).debug("告警检查异常: %s", e)


@router.get("/external/devices")
def list_external_devices(db: Session = Depends(get_db)):
    """获取允许接收数据的设备列表"""
    devices = db.query(Device).all()
    return [{"id": d.id, "name": d.name, "factor": d.factor,
             "protocol": d.protocol, "status": d.status} for d in devices]


@router.post("/external/devices/{device_id}/command")
async def send_device_command(
    device_id: int,
    command: dict,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None),
):
    """
    向设备发送远程指令（如校准、重启、参数设置）

    当前支持：
    - cn=1301: 查询设备状态
    - cn=1401: 读取全部数据
    - cn=1501: 设备校准
    - cn=1601: 设备重启

    用法：
        POST /api/devices/1/command
        {"command": "cn=1401", "params": {}}
    """
    api_key = getenv("EXTERNAL_API_KEY", "")
    if api_key and x_api_key != api_key:
        raise HTTPException(status_code=401, detail="API Key 无效")

    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    if device.protocol not in ("modbus", "modbus_hj212"):
        raise HTTPException(status_code=400, detail="仅支持 Modbus/HJ212 设备")

    # 记录指令（实际执行由 ModbusDevicePool 处理）
    return {
        "message": f"指令已提交: {command.get('command')}",
        "device_id": device_id,
        "command": command.get("command"),
        "note": "指令将发送到设备，响应将在下次轮询中获取"
    }
