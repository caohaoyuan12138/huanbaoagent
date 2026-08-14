"""
数据导入模块 — CSV/Excel 批量导入
支持设备监测数据和环保标准数据的导入
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import io
import pandas as pd
from datetime import datetime

from app.db.database import get_db
from app.db.models import DeviceReading, Standard, PollutionFactor, PollutionLimit

router = APIRouter()


# ── 设备读数导入 ─────────────────────────────────────────────────────────────

@router.post("/device-readings")
async def import_device_readings(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    上传 CSV/Excel 批量导入设备监测数据。
    期望列: device_id, factor, value, unit, timestamp
    """
    content = await file.read()
    df = _read_file(content, file.filename)

    required_cols = {"device_id", "factor", "value", "unit", "timestamp"}
    actual_cols = {c.strip().lower() for c in df.columns}
    missing = required_cols - actual_cols
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"缺少必要列: {', '.join(missing)}。期望列: {', '.join(required_cols)}",
        )

    df.columns = [c.strip().lower() for c in df.columns]
    imported = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            device_id = int(row["device_id"])
            factor = str(row["factor"]).strip()
            value = float(row["value"])
            unit = str(row["unit"]).strip()
            ts = _parse_timestamp(row["timestamp"])

            if device_id <= 0:
                errors.append(f"行 {idx + 2}: device_id 无效 ({row['device_id']})")
                continue
            if factor and value is not None:
                reading = DeviceReading(
                    device_id=device_id,
                    factor=factor,
                    value=value,
                    unit=unit,
                    timestamp=ts,
                    status="normal",
                )
                db.add(reading)
                imported += 1
        except (ValueError, TypeError) as e:
            errors.append(f"行 {idx + 2}: {str(e)}")

    db.commit()
    return {
        "imported": imported,
        "errors": errors[:20],
        "error_count": len(errors),
    }


# ── 标准数据导入 ──────────────────────────────────────────────────────────────

@router.post("/standards")
async def import_standards(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    上传 CSV/Excel 批量导入环保标准数据。
    期望列: title, standard_type, industry, category, sub_category,
            pollution_factors, publish_date, implement_date, source_url, status
    """
    content = await file.read()
    df = _read_file(content, file.filename)

    required_cols = {"title", "standard_type", "pollution_factors", "publish_date"}
    actual_cols = {c.strip().lower() for c in df.columns}
    missing = required_cols - actual_cols
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"缺少必要列: {', '.join(missing)}。期望列: {', '.join(required_cols)}",
        )

    df.columns = [c.strip().lower() for c in df.columns]
    imported = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            title = str(row["title"]).strip()
            if not title:
                errors.append(f"行 {idx + 2}: title 不能为空")
                continue

            existing = db.query(Standard).filter(Standard.title == title).first()
            if existing:
                errors.append(f"行 {idx + 2}: 标准已存在 — {title}")
                continue

            publish_date = _parse_date(row["publish_date"])
            implement_date = _parse_date(row.get("implement_date")) if pd.notna(row.get("implement_date")) else None
            factors_raw = row.get("pollution_factors", "")
            factors_list = _parse_factors_list(factors_raw)

            std = Standard(
                title=title,
                standard_type=str(row["standard_type"]).strip(),
                industry=str(row.get("industry", "general")).strip() if pd.notna(row.get("industry")) else "general",
                category=str(row.get("category", "")).strip() if pd.notna(row.get("category")) else "",
                sub_category=str(row.get("sub_category", "")).strip() if pd.notna(row.get("sub_category")) else "",
                pollution_factors=factors_list,
                publish_date=publish_date,
                implement_date=implement_date,
                source_url=str(row.get("source_url", "")).strip() if pd.notna(row.get("source_url")) else None,
                status=str(row.get("status", "active")).strip() if pd.notna(row.get("status")) else "active",
            )
            db.add(std)
            db.flush()

            import_limits_for_standard(db, std, factors_list)
            imported += 1
        except Exception as e:
            errors.append(f"行 {idx + 2}: {str(e)}")

    db.commit()
    return {
        "imported": imported,
        "errors": errors[:20],
        "error_count": len(errors),
    }


# ── 辅助函数 ──────────────────────────────────────────────────────────────────

def _read_file(content: bytes, filename: str) -> pd.DataFrame:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "csv":
        return pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    elif ext in ("xlsx", "xls"):
        return pd.read_excel(io.BytesIO(content))
    else:
        raise HTTPException(status_code=422, detail="仅支持 CSV 和 Excel (.xlsx/.xls) 文件")


def _parse_timestamp(val) -> datetime:
    if isinstance(val, datetime):
        return val
    parsed = pd.to_datetime(val, errors="coerce")
    if pd.isna(parsed):
        return datetime.now()
    return parsed.to_pydatetime()


def _parse_date(val) -> Optional[datetime]:
    if pd.isna(val):
        return None
    if isinstance(val, datetime):
        return val
    parsed = pd.to_datetime(val, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _parse_factors_list(raw) -> list:
    if pd.isna(raw):
        return []
    if isinstance(raw, list):
        return raw
    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            import json
            return json.loads(text)
        except Exception:
            pass
    return [f.strip() for f in text.split(",") if f.strip()]


def import_limits_for_standard(db: Session, std: Standard, factors: list):
    """为导入的标准创建 PollutionFactor 和 PollutionLimit 记录（占位）"""
    pass
