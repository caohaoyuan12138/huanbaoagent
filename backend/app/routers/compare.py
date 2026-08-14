"""
标准对比分析模块
支持多标准限值对比、因子限值汇总、差异分析
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.db.models import PollutionFactor, PollutionLimit, Standard

router = APIRouter()


@router.get("/factors")
def list_factors_with_limits(db: Session = Depends(get_db)):
    """
    获取所有污染因子及其在各个标准下的限值，按 standard_type 分组展示。
    """
    factors = db.query(PollutionFactor).all()
    result = []
    for f in factors:
        limits = db.query(PollutionLimit).filter(
            PollutionLimit.factor_id == f.id
        ).all()

        grouped: dict = {}
        for lim in limits:
            st = lim.standard_type or "unknown"
            if st not in grouped:
                grouped[st] = []
            grouped[st].append({
                "standard_title": lim.standard_title,
                "limit_value": lim.limit_value,
                "unit": lim.unit,
                "description": lim.description,
            })

        result.append({
            "id": f.id,
            "name": f.name,
            "symbol": f.symbol,
            "unit": f.unit,
            "limits_by_standard": grouped,
            "limit_count": len(limits),
        })

    return result


@router.post("/limits")
def compare_limits(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """
    对比指定因子 ID 在不同标准下的限值差异，返回 diff 分析。
    请求体: {"factor_ids": [1, 2, ...]}
    """
    factor_ids: List[int] = payload.get("factor_ids", [])
    if not factor_ids:
        raise HTTPException(status_code=422, detail="factor_ids 不能为空")

    results = []
    for fid in factor_ids:
        factor = db.query(PollutionFactor).filter(PollutionFactor.id == fid).first()
        if not factor:
            continue

        limits = db.query(PollutionLimit).filter(
            PollutionLimit.factor_id == fid
        ).order_by(PollutionLimit.standard_type).all()

        if not limits:
            continue

        grouped: dict = {}
        for lim in limits:
            st = lim.standard_type or "unknown"
            if st not in grouped:
                grouped[st] = []
            grouped[st].append({
                "standard_title": lim.standard_title,
                "limit_value": lim.limit_value,
                "unit": lim.unit,
                "description": lim.description,
            })

        values_by_standard = {
            st: entries[0]["limit_value"] if entries else None
            for st, entries in grouped.items()
        }

        diff_analysis = _compute_diff(values_by_standard, factor.unit)

        results.append({
            "factor_id": factor.id,
            "factor_name": factor.name,
            "symbol": factor.symbol,
            "unit": factor.unit,
            "standards": grouped,
            "value_by_standard": values_by_standard,
            "diff": diff_analysis,
        })

    return {
        "compared_factors": len(results),
        "results": results,
    }


def _compute_diff(
    values_by_standard: dict,
    unit: str,
) -> dict:
    """计算限值差异分析"""
    present = {k: v for k, v in values_by_standard.items() if v is not None}
    if len(present) < 2:
        return {
            "has_variation": False,
            "strictest": None,
            "loosest": None,
            "difference": None,
            "max_ratio": None,
        }

    strictest_key = min(present, key=present.__getitem__)
    loosest_key = max(present, key=present.__getitem__)
    strictest_val = present[strictest_key]
    loosest_val = present[loosest_key]
    diff_val = round(loosest_val - strictest_val, 4)
    max_ratio = round(loosest_val / strictest_val, 4) if strictest_val != 0 else None

    return {
        "has_variation": diff_val != 0,
        "strictest": {
            "standard_type": strictest_key,
            "limit_value": strictest_val,
        },
        "loosest": {
            "standard_type": loosest_key,
            "limit_value": loosest_val,
        },
        "difference": {
            "value": diff_val,
            "unit": unit,
            "ratio": max_ratio,
        },
    }
