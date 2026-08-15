"""
WebSocket 路由 — 设备实时数据流 + 告警推送
前端通过 WebSocket 订阅实时设备数据和告警
"""
import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

from app.websocket_service import get_ws_service
from app.device_health import get_health_monitor
from app.db.database import SessionLocal
from app.db.models import Device, Alert, DeviceReading
from sqlalchemy import desc

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/devices")
async def device_websocket(
    websocket: WebSocket,
    device_id: Optional[str] = Query(None, description="订阅特定设备ID，不传则订阅全部"),
):
    """
    设备实时数据 WebSocket

    消息格式:
    - 服务端推送: {"type": "device_data"|"alert"|"device_status"|"ping", ...}
    - 客户端订阅: {"type": "subscribe", "device_id": "1"}
    - 客户端取消: {"type": "unsubscribe", "device_id": "1"}
    """
    await websocket.accept()
    ws_service = get_ws_service()
    client_id = await ws_service.connect(websocket)

    # 订阅指定设备或全部
    if device_id:
        await ws_service.subscribe_device(client_id, device_id)
        # 推送当前数据快照
        data = ws_service.get_device_data(device_id)
        if data:
            await websocket.send_json({
                "type": "device_data",
                "device_id": device_id,
                **data,
            })
    else:
        # 推送所有设备快照
        all_data = ws_service.get_all_device_data()
        for did, ddata in all_data.items():
            await websocket.send_json({
                "type": "device_data",
                "device_id": did,
                **ddata,
            })

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "subscribe" and data.get("device_id"):
                await ws_service.subscribe_device(client_id, data["device_id"])
            elif data.get("type") == "unsubscribe" and data.get("device_id"):
                await ws_service.unsubscribe_device(client_id, data["device_id"])
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await ws_service.disconnect(client_id)
    except Exception as e:
        logger.error("WebSocket 异常: %s", str(e))
        await ws_service.disconnect(client_id)


@router.websocket("/ws/alerts")
async def alert_websocket(websocket: WebSocket):
    """告警实时推送 WebSocket"""
    await websocket.accept()
    ws_service = get_ws_service()
    client_id = await ws_service.connect(websocket)

    # 推送最近10条未读告警
    db = SessionLocal()
    try:
        recent_alerts = db.query(Alert).filter(
            Alert.status == "unread"
        ).order_by(desc(Alert.created_at)).limit(10).all()
        for alert in recent_alerts:
            await websocket.send_json({
                "type": "alert",
                "id": alert.id,
                "device_id": alert.device_id,
                "factor": alert.factor,
                "value": alert.value,
                "limit_value": alert.limit_value,
                "severity": alert.severity,
                "message": alert.message,
                "created_at": alert.created_at.isoformat(),
            })
    finally:
        db.close()

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await ws_service.disconnect(client_id)
    except Exception as e:
        logger.error("告警WebSocket异常: %s", str(e))
        await ws_service.disconnect(client_id)


@router.get("/ws/stats")
def ws_stats():
    """查询 WebSocket 服务统计"""
    ws = get_ws_service()
    health = get_health_monitor()
    return {
        **ws.get_stats(),
        "device_health": health.get_all_health(),
    }
