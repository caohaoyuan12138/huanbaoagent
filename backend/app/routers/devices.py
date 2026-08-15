"""
设备数据接入模块
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import json
import re
import logging

from app.db.database import get_db
from app.db.models import Device, DeviceReading, PollutionLimit
from app.websocket_service import get_ws_service
from app.device_health import get_health_monitor

router = APIRouter()
logger = logging.getLogger(__name__)

# IP 地址安全白名单：仅允许内网地址
SAFE_IP_PATTERN = re.compile(r'^(127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})$')


def _validate_modbus_ip(ip: str) -> bool:
    """验证 Modbus 设备 IP 是否在安全范围内"""
    return bool(SAFE_IP_PATTERN.match(ip))


@router.get("/devices")
def list_devices(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    return [{"id": d.id, "name": d.name, "factor": d.factor, "unit": d.unit,
             "location": d.location, "protocol": d.protocol, "topic": d.topic,
             "status": d.status, "created_at": str(d.created_at)} for d in devices]


@router.post("/devices")
def create_device(device: dict, db: Session = Depends(get_db)):
    # 支持 modbus_hj212 协议
    if device.get("protocol") == "modbus_hj212":
        required = ["mn", "ip_address"]
        for field in required:
            if not device.get(field):
                raise HTTPException(status_code=400, detail=f"modbus_hj212 协议需要字段: {field}")
    db_obj = Device(**device)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.put("/devices/{device_id}")
def update_device(device_id: int, device: dict, db: Session = Depends(get_db)):
    existing = db.query(Device).filter(Device.id == device_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="设备不存在")
    for key, value in device.items():
        if hasattr(existing, key):
            setattr(existing, key, value)
    db.commit()
    db.refresh(existing)
    return existing


@router.delete("/devices/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    # 删除相关数据
    db.query(DeviceReading).filter(DeviceReading.device_id == device_id).delete()
    db.delete(device)
    db.commit()
    return {"message": "删除成功"}


@router.post("/devices/{device_id}/readings")
def add_reading(device_id: int, reading: dict, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    reading["device_id"] = device_id
    db_obj = DeviceReading(**reading)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.post("/devices/{device_id}/readings/batch")
def batch_add_readings(device_id: int, readings: list = Body(...), db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    for r in readings:
        r["device_id"] = device_id
        db.add(DeviceReading(**r))
    db.commit()
    return {"message": f"已添加 {len(readings)} 条数据"}


@router.get("/devices/{device_id}/readings")
def get_readings(
    device_id: int,
    factor: Optional[str] = None,
    hours: int = 24,
    limit: int = 1000,
    db: Session = Depends(get_db),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    since = datetime.now() - timedelta(hours=hours)
    query = db.query(DeviceReading).filter(
        DeviceReading.device_id == device_id,
        DeviceReading.timestamp >= since,
    )
    if factor:
        query = query.filter(DeviceReading.factor == factor)

    readings = query.order_by(DeviceReading.timestamp.desc()).limit(limit).all()
    return [
        {
            "device_id": r.device_id,
            "factor": r.factor,
            "value": r.value,
            "unit": r.unit,
            "timestamp": r.timestamp,
            "status": r.status,
        }
        for r in readings
    ]


@router.get("/devices/{device_id}/analysis")
def analyze_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    since = datetime.now() - timedelta(hours=24)
    readings = db.query(DeviceReading).filter(
        DeviceReading.device_id == device_id,
        DeviceReading.timestamp >= since,
    ).all()

    if not readings:
        return {"device_id": device_id, "message": "暂无数据"}

    values = [r.value for r in readings]
    exceed_count = sum(1 for r in readings if r.status == "exceed")
    total = len(values)

    # 限值对比 — 通过 PollutionFactor 表匹配 symbol
    factor_obj = db.query(PollutionFactor).filter(PollutionFactor.symbol == device.factor).first()
    limits = []
    if factor_obj:
        limits = db.query(PollutionLimit).filter(PollutionLimit.factor_id == factor_obj.id).all()
    limit_values = [l.limit_value for l in limits]
    current_limit = limit_values[0] if limit_values else None

    # 简单统计
    avg_value = sum(values) / len(values) if values else 0
    max_value = max(values) if values else 0
    min_value = min(values) if values else 0

    # 趋势判断
    recent = values[-24:] if len(values) >= 24 else values
    older = values[:-24] if len(values) > 24 else []
    recent_avg = sum(recent) / len(recent) if recent else 0
    trend = "上升" if older and recent_avg > sum(older) / len(older) * 1.05 else \
            "下降" if older and recent_avg < sum(older) / len(older) * 0.95 else "稳定"

    # AI建议生成
    suggestions = []
    if current_limit and max_value > current_limit:
        suggestions.append(f"⚠️ 最大值 {max_value}{device.unit} 已超过限值 {current_limit}{device.unit}，请立即排查原因")
    if recent_avg > avg_value * 1.1:
        suggestions.append("📈 近期排放呈上升趋势，建议检查治理设施运行状态")
    if exceed_count > 0:
        suggestions.append(f"📊 过去24小时内有 {exceed_count}/{total} 次数据超标，需关注")
    if not suggestions:
        suggestions.append("✅ 当前排放数据正常，建议继续保持现有运维模式")

    return {
        "device_id": device_id,
        "device_name": device.name,
        "factor": device.factor,
        "statistics": {
            "avg": round(avg_value, 2),
            "max": round(max_value, 2),
            "min": round(min_value, 2),
            "recent_avg": round(recent_avg, 2),
            "trend": trend,
            "total_readings": total,
            "exceed_count": exceed_count,
        },
        "limit": current_limit,
        "suggestions": suggestions,
        "data_points": [
            {"timestamp": r.timestamp.isoformat(), "value": r.value, "status": r.status}
            for r in readings[-100:]
        ],
    }


@router.post("/seed")
def seed_devices(db: Session = Depends(get_db)):
    devices = [
        Device(
            name="废气排气筒DA001",
            factor="VOCs",
            unit="mg/m³",
            location="厂区北侧排气筒",
            protocol="mqtt",
            topic="factory/emission/da001",
            status="online",
        ),
        Device(
            name="废水总排口COD在线仪",
            factor="COD",
            unit="mg/L",
            location="厂区总排口",
            protocol="opc_ua",
            topic="factory/wastewater/cod",
            status="online",
        ),
        Device(
            name="RTO蓄热焚烧炉出口",
            factor="VOCs",
            unit="mg/m³",
            location="废气治理设施出口",
            protocol="modbus",
            topic="factory/rto/outlet",
            status="online",
        ),
        Device(
            name="废水总排口氨氮在线仪",
            factor="NH₃-N",
            unit="mg/L",
            location="厂区总排口",
            protocol="mqtt",
            topic="factory/wastewater/nh3n",
            status="online",
        ),
    ]
    for d in devices:
        existing = db.query(Device).filter(Device.name == d.name).first()
        if not existing:
            db.add(d)
    db.commit()
    return {"message": f"已初始化 {len(devices)} 个设备"}


# ==================== Modbus HJ212 端点 ====================

@router.post("/devices/modbus/connect")
def modbus_connect(body: dict = Body(...), db: Session = Depends(get_db)):
    """测试 Modbus 连接，发送 HJ212 命令读取数据"""
    from app.modbus_device import ModbusDevice

    mn = body.get("mn", "")
    ip = body.get("ip", "")
    port = body.get("port", 8000)
    timeout = body.get("timeout", 5.0)

    if not mn or not ip:
        raise HTTPException(status_code=400, detail="mn 和 ip 为必填项")

    if not _validate_modbus_ip(ip):
        raise HTTPException(status_code=403, detail="仅允许内网 IP 地址 (192.168.x.x / 10.x.x.x / 127.x.x.x)")

    device = ModbusDevice(mn, ip, port, timeout)
    try:
        connected = device.connect()
        if not connected:
            raise HTTPException(status_code=503, detail=f"无法连接到 {ip}:{port}")

        result = device.read_all_data()
        return {
            "success": result["success"],
            "mn": result["mn"],
            "data": result["data"],
            "raw_response": result.get("raw_response"),
            "timestamp": result["timestamp"].isoformat(),
        }
    finally:
        device.close()


@router.post("/devices/{device_id}/read")
def modbus_read_device(device_id: int, db: Session = Depends(get_db)):
    """从指定设备读取 Modbus 数据"""
    from app.modbus_device import ModbusDevice

    device_db = db.query(Device).filter(Device.id == device_id).first()
    if not device_db:
        raise HTTPException(status_code=404, detail="设备不存在")

    if device_db.protocol not in ("modbus", "modbus_hj212"):
        raise HTTPException(status_code=400, detail=f"设备协议不支持: {device_db.protocol}")

    ip = device_db.ip_address or "127.0.0.1"
    port = device_db.port or 8000
    timeout = device_db.timeout or 5.0
    mn = device_db.mn or "UNKNOWN"

    if not _validate_modbus_ip(ip):
        raise HTTPException(status_code=403, detail="仅允许内网 IP 地址")

    modbus_device = ModbusDevice(mn, ip, port, timeout)
    try:
        result = modbus_device.read_all_data()

        if result["success"]:
            now = datetime.now()
            for key, value in result["data"].items():
                if isinstance(value, (int, float)):
                    reading = DeviceReading(
                        device_id=device_id,
                        factor=key,
                        value=float(value),
                        unit=device_db.unit,
                        timestamp=now,
                        status="normal",
                        raw_data=result.get("raw_response", ""),
                        data_type="hj212_parsed",
                    )
                    db.add(reading)
            db.commit()

        return {
            "device_id": device_id,
            "mn": mn,
            "success": result["success"],
            "data": result["data"],
            "timestamp": result["timestamp"].isoformat(),
        }
    finally:
        modbus_device.close()


@router.get("/devices/modbus/discover")
def modbus_discover(subnet: str = "192.168.1", db: Session = Depends(get_db)):
    """扫描子网中的 Modbus 设备（基础扫描）"""
    import socket
    from app.modbus_device import ModbusDevice

    found = []
    for i in range(1, 255):
        ip = f"{subnet}.{i}"
        if not _validate_modbus_ip(ip):
            continue
        device = ModbusDevice("SCAN", ip, 8000, timeout=1.0)
        try:
            if device.connect():
                status = device.check_device_status()
                if status["success"]:
                    found.append({
                        "ip": ip,
                        "port": 8000,
                        "mn": status.get("status", {}).get("MN", "unknown"),
                        "device_status": status,
                    })
        except Exception:
            pass
        finally:
            device.close()

    return {"subnet": subnet, "found_count": len(found), "devices": found}


@router.post("/devices/modbus/batch-read")
def modbus_batch_read(devices: list = Body(...), db: Session = Depends(get_db)):
    """批量读取多个 Modbus 设备数据"""
    from app.modbus_device import ModbusDevice

    results = []
    for dev in devices:
        mn = dev.get("mn", "")
        ip = dev.get("ip", "")
        port = dev.get("port", 8000)
        timeout = dev.get("timeout", 5.0)

        if not mn or not ip:
            results.append({"mn": mn, "ip": ip, "success": False, "error": "缺少 mn 或 ip"})
            continue

        if not _validate_modbus_ip(ip):
            results.append({"mn": mn, "ip": ip, "success": False, "error": "仅允许内网 IP"})
            continue

        device = ModbusDevice(mn, ip, port, timeout)
        try:
            result = device.read_all_data()
            results.append({
                "mn": mn,
                "ip": ip,
                "success": result["success"],
                "data": result["data"],
                "timestamp": result["timestamp"].isoformat(),
            })
        except Exception as e:
            results.append({"mn": mn, "ip": ip, "success": False, "error": str(e)})
        finally:
            device.close()

    return {"results": results, "total": len(results), "success_count": sum(1 for r in results if r["success"])}
