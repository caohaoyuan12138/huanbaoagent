"""
知识图谱 API 路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.db.models import Standard, PollutionFactor, PollutionLimit

router = APIRouter()


def _to_dict(obj):
    if obj is None:
        return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def _list_to_dict(items):
    return [_to_dict(item) for item in items]


@router.get("/graph/factors")
def graph_factors(
    standard_type: Optional[str] = Query("", description="按标准类型筛选"),
    keyword: Optional[str] = Query("", description="关键字搜索"),
    db: Session = Depends(get_db),
):
    factors = db.query(PollutionFactor).all()
    if keyword:
        factors = [
            f for f in factors
            if keyword.lower() in f.name.lower() or keyword.lower() in f.symbol.lower()
        ]

    nodes = []
    edges = []
    seen_limits = set()

    for f in factors:
        factor_node_id = f"factor_{f.id}"
        nodes.append({
            "id": factor_node_id,
            "label": f.name,
            "symbol": f.symbol,
            "type": "factor",
            "unit": f.unit,
            "description": f.name,
            "standard_type": standard_type or "all",
        })

        limits = db.query(PollutionLimit).filter(
            PollutionLimit.factor_id == f.id
        ).all()

        if standard_type and standard_type != "all":
            limits = [l for l in limits if l.standard_type == standard_type]

        for limit in limits:
            limit_key = f"limit_{limit.id}"
            if limit_key in seen_limits:
                continue
            seen_limits.add(limit_key)
            nodes.append({
                "id": limit_key,
                "label": f"≤{limit.limit_value} {limit.unit}",
                "type": "limit",
                "standard": limit.standard_title,
                "standard_type": limit.standard_type,
                "limit_value": limit.limit_value,
                "unit": limit.unit,
                "description": limit.description or "",
            })
            edges.append({
                "source": factor_node_id,
                "target": limit_key,
                "relation": "limit_of",
                "standard": limit.standard_title,
            })

    return {"nodes": nodes, "edges": edges}


@router.get("/graph/standards")
def graph_standards(
    industry: Optional[str] = Query("", description="按行业筛选"),
    keyword: Optional[str] = Query("", description="关键字搜索"),
    db: Session = Depends(get_db),
):
    standards = db.query(Standard).filter(Standard.status == "active").all()
    if industry and industry != "all":
        standards = [s for s in standards if industry in s.industry]
    if keyword:
        standards = [
            s for s in standards
            if keyword.lower() in s.title.lower() or keyword.lower() in s.standard_type.lower()
        ]

    nodes = []
    edges = []
    factor_ids_seen = set()

    for s in standards:
        std_node_id = f"std_{s.id}"
        nodes.append({
            "id": std_node_id,
            "label": s.title,
            "type": "standard",
            "standard_type": s.standard_type,
            "industry": s.industry,
            "category": s.category,
            "description": s.content[:100] if s.content else "",
        })

        pollution_factors = s.pollution_factors or []
        for factor_entry in pollution_factors:
            if isinstance(factor_entry, dict):
                symbol = factor_entry.get("symbol", "")
                name = factor_entry.get("name", "")
            elif isinstance(factor_entry, str):
                symbol = factor_entry
                name = factor_entry
            else:
                continue

            factor_node_id = f"factor_{symbol}"
            if factor_node_id not in factor_ids_seen:
                factor_ids_seen.add(factor_node_id)
                nodes.append({
                    "id": factor_node_id,
                    "label": name or symbol,
                    "symbol": symbol,
                    "type": "factor",
                })
            edges.append({
                "source": std_node_id,
                "target": factor_node_id,
                "relation": "covers",
            })

    return {"nodes": nodes, "edges": edges}


@router.get("/graph/industry/{industry}")
def graph_industry(
    industry: str,
    db: Session = Depends(get_db),
):
    standards = db.query(Standard).filter(
        Standard.industry.contains(industry),
        Standard.status == "active",
    ).all()

    nodes = []
    edges = []
    factor_ids_seen = set()

    for s in standards:
        std_node_id = f"std_{s.id}"
        nodes.append({
            "id": std_node_id,
            "label": s.title,
            "type": "standard",
            "standard_type": s.standard_type,
            "industry": s.industry,
            "category": s.category,
            "description": s.content[:100] if s.content else "",
        })

        pollution_factors = s.pollution_factors or []
        for factor_entry in pollution_factors:
            if isinstance(factor_entry, dict):
                symbol = factor_entry.get("symbol", "")
                name = factor_entry.get("name", "")
            elif isinstance(factor_entry, str):
                symbol = factor_entry
                name = factor_entry
            else:
                continue

            factor_node_id = f"factor_{symbol}"
            if factor_node_id not in factor_ids_seen:
                factor_ids_seen.add(factor_node_id)
                nodes.append({
                    "id": factor_node_id,
                    "label": name or symbol,
                    "symbol": symbol,
                    "type": "factor",
                })
            edges.append({
                "source": std_node_id,
                "target": factor_node_id,
                "relation": "covers",
            })

        for limit in db.query(PollutionLimit).filter(
            PollutionLimit.standard_title.like(f"%{s.title[:30]}%")
        ).all():
            factor_id = f"factor_{limit.unit}"
            limit_node_id = f"limit_{limit.id}"
            if limit_node_id not in [n["id"] for n in nodes]:
                nodes.append({
                    "id": limit_node_id,
                    "label": f"≤{limit.limit_value} {limit.unit}",
                    "type": "limit",
                    "standard": limit.standard_title,
                    "limit_value": limit.limit_value,
                    "unit": limit.unit,
                })
            edges.append({
                "source": factor_id,
                "target": limit_node_id,
                "relation": "limit_of",
            })

    return {"nodes": nodes, "edges": edges}
