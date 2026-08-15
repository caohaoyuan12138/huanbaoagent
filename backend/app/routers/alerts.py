"""
告警管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.db.database import get_db
from app.db.models import Alert, Device, PollutionLimit, PollutionFactor
from sqlalchemy import func
from app.websocket_service import get_ws_service

router = APIRouter()


@router.get("")
def list_alerts(
    device_id: Optional[int] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Alert)
    if device_id is not None:
        query = query.filter(Alert.device_id == device_id)
    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)

    total = query.count()
    alerts = (
        query.order_by(Alert.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "alerts": [
            {
                "id": a.id,
                "device_id": a.device_id,
                "factor": a.factor,
                "value": a.value,
                "limit_value": a.limit_value,
                "unit": a.unit,
                "severity": a.severity,
                "status": a.status,
                "message": a.message,
                "created_at": str(a.created_at),
            }
            for a in alerts
        ],
    }


@router.put("/{alert_id}/read")
def mark_read(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    alert.status = "read"
    db.commit()
    return {"message": "已标记为已读"}


@router.put("/{alert_id}/resolve")
def mark_resolve(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    alert.status = "resolved"
    db.commit()
    return {"message": "已标记为已解决"}


@router.get("/stats")
def alert_stats(db: Session = Depends(get_db)):
    by_severity = (
        db.query(Alert.severity, func.count(Alert.id))
        .group_by(Alert.severity)
        .all()
    )
    by_status = (
        db.query(Alert.status, func.count(Alert.id))
        .group_by(Alert.status)
        .all()
    )
    unread = db.query(Alert).filter(Alert.status == "unread").count()
    unresolved = db.query(Alert).filter(
        Alert.status.in_(["unread", "read"])
    ).count()

    return {
        "unread": unread,
        "unresolved": unresolved,
        "by_severity": {s: c for s, c in by_severity},
        "by_status": {s: c for s, c in by_status},
    }


@router.post("/seed")
def seed_alerts(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    if not devices:
        return {"message": "暂无设备，请先 seeding 设备"}

    created = 0
    for d in devices:
        for severity, value, limit in [("critical", 999.0, 50.0), ("warning", 55.0, 50.0)]:
            existing = db.query(Alert).filter(
                Alert.device_id == d.id,
                Alert.factor == d.factor,
                Alert.status == "unread",
            ).first()
            if existing:
                continue
            alert = Alert(
                device_id=d.id, factor=d.factor, unit=d.unit,
                value=value, limit_value=limit, severity=severity,
                status="unread",
                message=f"[模拟] {d.name} {d.factor} {severity}超标",
                created_at=datetime.now(),
            )
            db.add(alert)
            created += 1

    db.commit()
    return {"message": f"已种子 {created} 条告警"}
