"""
合规检查路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.database import get_db
from app.db.models import (
    ComplianceCheck, Device, DeviceReading,
    PollutionLimit, PollutionFactor, Standard,
)
from sqlalchemy import func

router = APIRouter()


@router.post("/check")
def start_compliance_check(
    payload: dict,
    db: Session = Depends(get_db),
):
    device_ids: list = payload.get("device_ids", [])
    standard_ids: list = payload.get("standard_ids", [])
    name: str = payload.get("name", "合规检查")

    if not device_ids:
        raise HTTPException(status_code=422, detail="device_ids 不能为空")

    check = ComplianceCheck(
        name=name,
        device_ids=device_ids,
        standard_ids=standard_ids,
        status="running",
        created_at=datetime.now(),
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return {"id": check.id, "status": check.status}


@router.get("/checks")
def list_checks(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(ComplianceCheck)
    if status:
        query = query.filter(ComplianceCheck.status == status)
    total = query.count()
    checks = (
        query.order_by(ComplianceCheck.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "checks": [
            {
                "id": c.id,
                "name": c.name,
                "device_ids": c.device_ids,
                "standard_ids": c.standard_ids,
                "status": c.status,
                "passed_count": c.passed_count,
                "failed_count": c.failed_count,
                "warning_count": c.warning_count,
                "result_summary": c.result_summary,
                "created_at": str(c.created_at),
                "completed_at": str(c.completed_at) if c.completed_at else None,
            }
            for c in checks
        ],
    }


@router.post("/seed")
def seed_checks(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    if not devices:
        return {"message": "暂无设备，请先 seeding 设备"}

    check = ComplianceCheck(
        name="示例合规检查",
        device_ids=[d.id for d in devices],
        standard_ids=[],
        status="completed",
        passed_count=len(devices),
        failed_count=0,
        warning_count=0,
        result_summary=f"检查 {len(devices)} 个设备，全部通过。",
        created_at=datetime.now(),
        completed_at=datetime.now(),
    )
    db.add(check)
    db.commit()
    return {"message": "已种子示例合规检查"}


@router.get("/checks/{check_id}")
def get_check(check_id: int, db: Session = Depends(get_db)):
    check = db.query(ComplianceCheck).filter(ComplianceCheck.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail="合规检查不存在")
    return {
        "id": check.id,
        "name": check.name,
        "device_ids": check.device_ids,
        "standard_ids": check.standard_ids,
        "status": check.status,
        "passed_count": check.passed_count,
        "failed_count": check.failed_count,
        "warning_count": check.warning_count,
        "result_summary": check.result_summary,
        "created_at": str(check.created_at),
        "completed_at": str(check.completed_at) if check.completed_at else None,
    }


@router.post("/checks/{check_id}/results")
def run_compliance_results(
    check_id: int,
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db),
):
    check = db.query(ComplianceCheck).filter(ComplianceCheck.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail="合规检查不存在")

    if check.status == "completed":
        return {
            "check_id": check_id,
            "status": check.status,
            "passed_count": check.passed_count,
            "failed_count": check.failed_count,
            "warning_count": check.warning_count,
            "result_summary": check.result_summary,
        }

    db.query(ComplianceCheck).filter(
        ComplianceCheck.id == check_id
    ).update({"status": "running"})
    db.commit()

    now = datetime.now()
    since = now - timedelta(hours=hours)
    device_ids = check.device_ids or []
    standard_ids = check.standard_ids or []

    passed = 0
    failed = 0
    warnings = 0
    details = []

    for dev_id in device_ids:
        device = db.query(Device).filter(Device.id == dev_id).first()
        if not device:
            continue

        readings = db.query(DeviceReading).filter(
            DeviceReading.device_id == dev_id,
            DeviceReading.timestamp >= since,
        ).order_by(DeviceReading.timestamp.desc()).all()

        if not readings:
            details.append({
                "device_id": dev_id,
                "device_name": device.name,
                "factor": device.factor,
                "status": "no_data",
                "message": "无最近读数数据",
            })
            continue

        latest = readings[0]
        factor_symbol = device.factor
        limit_value = None
        limit_source = None

        factor_obj = db.query(PollutionFactor).filter(
            PollutionFactor.symbol == factor_symbol
        ).first()
        if factor_obj:
            limits = db.query(PollutionLimit).filter(
                PollutionLimit.factor_id == factor_obj.id
            ).all()
            if standard_ids:
                limits = [l for l in limits if l.standard_title in standard_ids]
            if limits:
                limit_value = limits[0].limit_value
                limit_source = limits[0].standard_title

        if limit_value is None:
            details.append({
                "device_id": dev_id,
                "device_name": device.name,
                "factor": factor_symbol,
                "status": "no_limit",
                "message": f"未找到 {factor_symbol} 的适用限值",
            })
            continue

        value = latest.value
        if value > limit_value * 1.5:
            status = "failed"
            failed += 1
            msg = f"{factor_symbol}: {value}{device.unit} 超过限值 {limit_value}{device.unit} 的1.5倍（严重超标）"
        elif value > limit_value:
            status = "warning"
            warnings += 1
            msg = f"{factor_symbol}: {value}{device.unit} 超过限值 {limit_value}{device.unit}"
        else:
            status = "passed"
            passed += 1
            msg = f"{factor_symbol}: {value}{device.unit} 符合限值 {limit_value}{device.unit}"

        details.append({
            "device_id": dev_id,
            "device_name": device.name,
            "factor": factor_symbol,
            "status": status,
            "value": value,
            "limit_value": limit_value,
            "unit": device.unit,
            "limit_source": limit_source,
            "message": msg,
        })

    summary = (
        f"检查 {len(device_ids)} 个设备，"
        f"通过 {passed}，警告 {warnings}，不合格 {failed}。"
    )

    db.query(ComplianceCheck).filter(
        ComplianceCheck.id == check_id
    ).update({
        "status": "completed",
        "passed_count": passed,
        "failed_count": failed,
        "warning_count": warnings,
        "result_summary": summary,
        "completed_at": datetime.now(),
    })
    db.commit()

    return {
        "check_id": check_id,
        "status": "completed",
        "passed_count": passed,
        "failed_count": failed,
        "warning_count": warnings,
        "result_summary": summary,
        "details": details,
    }
