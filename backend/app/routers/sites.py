"""
站点管理路由 — 多级站点/厂区管理
支持层级结构: 集团 -> 工厂 -> 车间 -> 监测点
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.db.database import get_db
from app.db.models import Site, Device
from sqlalchemy import func

router = APIRouter()


@router.get("/sites")
def list_sites(tenant_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Site)
    if tenant_id is not None:
        query = query.filter(Site.tenant_id == tenant_id)
    sites = query.all()
    # 附带每个站点的设备统计
    result = []
    for s in sites:
        dev_count = db.query(Device).filter(Device.site_id == s.id).count()
        online_count = db.query(Device).filter(
            Device.site_id == s.id, Device.status == "online"
        ).count()
        result.append({
            "id": s.id, "name": s.name, "code": s.code,
            "address": s.address, "parent_id": s.parent_id,
            "contact_name": s.contact_name, "contact_phone": s.contact_phone,
            "status": s.status, "created_at": str(s.created_at),
            "device_count": dev_count, "online_count": online_count,
        })
    return result


@router.post("/sites")
def create_site(site: dict, db: Session = Depends(get_db)):
    db_obj = Site(**site)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.put("/sites/{site_id}")
def update_site(site_id: int, site: dict, db: Session = Depends(get_db)):
    existing = db.query(Site).filter(Site.id == site_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="站点不存在")
    for key, value in site.items():
        if hasattr(existing, key):
            setattr(existing, key, value)
    db.commit()
    db.refresh(existing)
    return existing


@router.delete("/sites/{site_id}")
def delete_site(site_id: int, db: Session = Depends(get_db)):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")
    # 检查是否有子站点
    children = db.query(Site).filter(Site.parent_id == site_id).all()
    if children:
        raise HTTPException(status_code=400, detail="该站点下还有子站点，请先删除子站点")
    db.delete(site)
    db.commit()
    return {"message": "删除成功"}


@router.get("/sites/{site_id}/devices")
def get_site_devices(site_id: int, db: Session = Depends(get_db)):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")
    devices = db.query(Device).filter(Device.site_id == site_id).all()
    return [{"id": d.id, "name": d.name, "factor": d.factor, "unit": d.unit,
             "location": d.location, "protocol": d.protocol,
             "status": d.status, "mn": d.mn, "ip_address": d.ip_address}
            for d in devices]
