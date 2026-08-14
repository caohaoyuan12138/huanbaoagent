"""
环保法律法规知识库模块
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.db.models import Standard, PollutionFactor, EnterpriseStandard, PollutionLimit, NewsItem, Device, CrawlLog

router = APIRouter()


def _to_dict(obj):
    if obj is None:
        return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def _list_to_dict(items):
    return [_to_dict(item) for item in items]


@router.get("/standards")
def list_standards(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    keyword: str = Query("", description="关键字搜索（标准号/名称/行业）"),
    standard_type: str = Query("", description="分类筛选：all/综合标准/行业标准/地方标准/团体标准"),
    category: str = Query("", description="污染类别：all/废气/废水/固废/噪声/土壤/地下水/环境空气"),
):
    db = next(get_db())
    try:
        query = db.query(Standard)
        if keyword:
            query = query.filter(
                Standard.title.contains(keyword) |
                Standard.standard_type.contains(keyword) |
                Standard.industry.contains(keyword)
            )
        if standard_type and standard_type != "all":
            query = query.filter(Standard.standard_type == standard_type)
        if category and category != "all":
            query = query.filter(Standard.category == category)
        total = query.count()
        rows = (
            query.order_by(Standard.publish_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return _list_to_dict(rows), total
    finally:
        db.close()


@router.get("/standards/{standard_id}")
def get_standard(standard_id: int, db: Session = Depends(get_db)):
    standard = db.query(Standard).filter(Standard.id == standard_id).first()
    if not standard:
        raise HTTPException(status_code=404, detail="标准不存在")
    return _to_dict(standard)


@router.post("/standards")
def create_standard(
    standard: dict,
    db: Session = Depends(get_db),
):
    db_obj = Standard(**standard)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return _to_dict(db_obj)


@router.delete("/standards/{standard_id}")
def delete_standard(standard_id: int, db: Session = Depends(get_db)):
    standard = db.query(Standard).filter(Standard.id == standard_id).first()
    if not standard:
        raise HTTPException(status_code=404, detail="标准不存在")
    db.delete(standard)
    db.commit()
    return {"message": "删除成功"}


@router.get("/pollution-factors")
def list_pollution_factors(db: Session = Depends(get_db)):
    factors = db.query(PollutionFactor).all()
    result = []
    for f in factors:
        limits = db.query(PollutionLimit).filter(
            PollutionLimit.factor_id == f.id
        ).all()
        result.append({
            "id": f.id,
            "name": f.name,
            "symbol": f.symbol,
            "unit": f.unit,
            "limits": [
                {
                    "standard_title": limit.standard_title,
                    "limit_value": limit.limit_value,
                    "standard_type": limit.standard_type,
                }
                for limit in limits
            ],
        })
    return result


@router.get("/standards/{standard_id}/limits")
def get_standard_limits(standard_id: int, db: Session = Depends(get_db)):
    """按标准ID查询该标准下所有污染因子排放限值"""
    standard = db.query(Standard).filter(Standard.id == standard_id).first()
    if not standard:
        raise HTTPException(status_code=404, detail="标准不存在")
    limits = db.query(PollutionLimit).filter(
        PollutionLimit.standard_title == standard.title
    ).all()
    result = []
    for limit in limits:
        factor = db.query(PollutionFactor).filter(PollutionFactor.id == limit.factor_id).first()
        result.append({
            "id": limit.id,
            "factor_id": limit.factor_id,
            "factor_name": factor.name if factor else "",
            "factor_symbol": factor.symbol if factor else "",
            "limit_value": limit.limit_value,
            "unit": limit.unit,
            "standard_type": limit.standard_type,
            "description": limit.description,
        })
    return {"standard": _to_dict(standard), "limits": result}


@router.get("/limits")
def list_limits(
    factor_id: Optional[int] = None,
    standard_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(PollutionLimit)
    if factor_id:
        query = query.filter(PollutionLimit.factor_id == factor_id)
    if standard_type:
        query = query.filter(PollutionLimit.standard_type == standard_type)
    return _list_to_dict(query.all())


@router.get("/enterprise-standards")
def list_enterprise_standards(db: Session = Depends(get_db)):
    return _list_to_dict(db.query(EnterpriseStandard).all())


@router.post("/enterprise-standards")
def create_enterprise_standard(
    standard: dict,
    db: Session = Depends(get_db),
):
    db_obj = EnterpriseStandard(**standard)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return _to_dict(db_obj)


@router.get("/knowledge/search")
def search_knowledge(
    q: str,
    db: Session = Depends(get_db),
):
    results = {
        "standards": [],
        "factors": [],
        "enterprise": [],
    }
    kw = q
    results["standards"] = [
        {"id": s.id, "title": s.title, "standard_type": s.standard_type, "category": s.category}
        for s in db.query(Standard).filter(
            Standard.title.contains(kw) | Standard.content.contains(kw)
        ).limit(10).all()
    ]
    results["factors"] = [
        {"id": f.id, "name": f.name, "symbol": f.symbol}
        for f in db.query(PollutionFactor).filter(
            PollutionFactor.name.contains(kw) | PollutionFactor.symbol.contains(kw)
        ).all()
    ]
    results["enterprise"] = [
        {"id": e.id, "name": e.name, "industry": e.industry}
        for e in db.query(EnterpriseStandard).filter(
            EnterpriseStandard.name.contains(kw)
        ).all()
    ]
    return results


@router.post("/seed")
def seed_initial_data(db: Session = Depends(get_db)):
    """初始化示例数据"""
    factors = [
        PollutionFactor(name="化学需氧量", symbol="COD", unit="mg/L"),
        PollutionFactor(name="氨氮", symbol="NH₃-N", unit="mg/L"),
        PollutionFactor(name="挥发性有机物", symbol="VOCs", unit="mg/m³"),
        PollutionFactor(name="二氧化硫", symbol="SO₂", unit="mg/m³"),
        PollutionFactor(name="氮氧化物", symbol="NOx", unit="mg/m³"),
        PollutionFactor(name="颗粒物", symbol="PM", unit="mg/m³"),
        PollutionFactor(name="总汞", symbol="Hg", unit="μg/m³"),
        PollutionFactor(name="苯系物", symbol="BTEX", unit="mg/m³"),
    ]
    for f in factors:
        existing = db.query(PollutionFactor).filter(PollutionFactor.symbol == f.symbol).first()
        if not existing:
            db.add(f)
    db.commit()

    return {"message": "基础因子初始化完成", "factors": len(factors)}


@router.get("/stats")
def knowledge_stats(db: Session = Depends(get_db)):
    """知识库统计"""
    standards = db.query(func.count(Standard.id)).scalar() or 0
    factors = db.query(func.count(PollutionFactor.id)).scalar() or 0
    limits = db.query(func.count(PollutionLimit.id)).scalar() or 0
    news = db.query(func.count(NewsItem.id)).scalar() or 0
    devices = db.query(func.count(Device.id)).scalar() or 0
    enterprise = db.query(func.count(EnterpriseStandard.id)).scalar() or 0
    category_stats = (
        db.query(Standard.category, func.count(Standard.id))
        .filter(Standard.status == "active")
        .group_by(Standard.category)
        .all()
    )
    return {
        "standards": standards,
        "factors": factors,
        "limits": limits,
        "news": news,
        "devices": devices,
        "enterprise_standards": enterprise,
        "category_stats": [{"category": r[0], "count": r[1]} for r in category_stats if r[0]],
    }


@router.get("/search/web")
async def web_search(query: str = Query(..., description="搜索关键词"), max_results: int = Query(5, ge=1, le=10)):
    """网络搜索 — 调用 AnySearch / Tavily 搜索最新环保资讯"""
    from app.search_engine import SearchEngine
    engine = SearchEngine()
    return await engine.search(query, max_results)


@router.get("/search/status")
def search_status():
    """搜索引擎状态"""
    from app.search_engine import SearchEngine
    engine = SearchEngine()
    return engine.get_status()
