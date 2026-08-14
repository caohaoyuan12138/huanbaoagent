"""
租户管理路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.db.models import Tenant, Device, Alert, ReportInstance

router = APIRouter()


@router.get("/tenants")
def list_tenants(db: Session = Depends(get_db)):
    tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "code": t.code,
            "contact_name": t.contact_name,
            "contact_phone": t.contact_phone,
            "contact_email": t.contact_email,
            "address": t.address,
            "status": t.status,
            "created_at": str(t.created_at),
        }
        for t in tenants
    ]


@router.post("/tenants")
def create_tenant(tenant: dict, db: Session = Depends(get_db)):
    if db.query(Tenant).filter(Tenant.code == tenant.get("code")).first():
        raise HTTPException(status_code=400, detail="租户编码已存在")
    db_obj = Tenant(**tenant)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.get("/tenants/{tenant_id}")
def get_tenant(tenant_id: int, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    device_count = db.query(Device).filter(Device.tenant_id == tenant_id).count()
    alert_count = db.query(Alert).filter(Alert.tenant_id == tenant_id).count()
    report_count = db.query(ReportInstance).filter(ReportInstance.tenant_id == tenant_id).count()
    return {
        "id": tenant.id,
        "name": tenant.name,
        "code": tenant.code,
        "contact_name": tenant.contact_name,
        "contact_phone": tenant.contact_phone,
        "contact_email": tenant.contact_email,
        "address": tenant.address,
        "status": tenant.status,
        "created_at": str(tenant.created_at),
        "device_count": device_count,
        "alert_count": alert_count,
        "report_count": report_count,
    }


@router.put("/tenants/{tenant_id}")
def update_tenant(tenant_id: int, tenant_data: dict, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    if "code" in tenant_data and tenant_data["code"] != tenant.code:
        if db.query(Tenant).filter(Tenant.code == tenant_data["code"]).first():
            raise HTTPException(status_code=400, detail="租户编码已存在")
    for key, value in tenant_data.items():
        if hasattr(tenant, key):
            setattr(tenant, key, value)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.delete("/tenants/{tenant_id}")
def delete_tenant(tenant_id: int, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    db.query(Device).filter(Device.tenant_id == tenant_id).delete()
    db.query(Alert).filter(Alert.tenant_id == tenant_id).delete()
    db.query(ReportInstance).filter(ReportInstance.tenant_id == tenant_id).delete()
    db.delete(tenant)
    db.commit()
    return {"message": "删除成功"}


@router.post("/tenants/seed")
def seed_tenants(db: Session = Depends(get_db)):
    seed_data = [
        {
            "name": "华星化工集团",
            "code": "tenant001",
            "contact_name": "张明",
            "contact_phone": "13800138001",
            "contact_email": "zhangming@huaxing.com",
            "address": "江苏省南京市栖霞区化工园",
            "status": "active",
        },
        {
            "name": "绿源环保科技",
            "code": "tenant002",
            "contact_name": "李华",
            "contact_phone": "13900139002",
            "contact_email": "lihua@lvyuan.com",
            "address": "浙江省杭州市滨江区科技园",
            "status": "active",
        },
        {
            "name": "蓝天材料有限",
            "code": "tenant003",
            "contact_name": "王强",
            "contact_phone": "13700137003",
            "contact_email": "wangqiang@lantian.com",
            "address": "山东省青岛市黄岛区工业园",
            "status": "active",
        },
        {
            "name": "瑞丰精细化工",
            "code": "tenant004",
            "contact_name": "陈静",
            "contact_phone": "13600136004",
            "contact_email": "chenjing@ruifeng.com",
            "address": "广东省东莞市松山湖高新区",
            "status": "suspended",
        },
    ]
    created = 0
    for data in seed_data:
        existing = db.query(Tenant).filter(Tenant.code == data["code"]).first()
        if not existing:
            db.add(Tenant(**data))
            created += 1
    db.commit()
    return {"message": f"已种子 {created} 个租户"}
