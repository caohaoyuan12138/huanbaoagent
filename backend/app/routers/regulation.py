"""
公约条款查询路由 — 结构化环保公约知识检索
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.db.models import RegulationClause
from sqlalchemy import func

router = APIRouter()


@router.get("/clauses")
def list_clauses(
    chapter: Optional[str] = Query("", description="章节筛选"),
    keyword: Optional[str] = Query("", description="关键词全文搜索"),
    action_type: Optional[str] = Query("", description="按要求类型筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(RegulationClause)

    if chapter:
        query = query.filter(RegulationClause.chapter.contains(chapter))
    if keyword:
        query = query.filter(
            RegulationClause.content.contains(keyword) |
            RegulationClause.article_title.contains(keyword) |
            RegulationClause.source.contains(keyword)
        )
    if action_type:
        query = query.filter(RegulationClause.action_required.isnot(None))

    total = query.count()
    clauses = (
        query.order_by(RegulationClause.article_no.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "clauses": [
            {
                "id": c.id,
                "source": c.source,
                "chapter": c.chapter,
                "article_no": c.article_no,
                "article_title": c.article_title,
                "content": c.content,
                "keywords": c.keywords or [],
                "action_required": c.action_required,
                "platform_url": c.platform_url,
            }
            for c in clauses
        ],
    }


@router.get("/clauses/search")
def search_clauses(
    q: str = Query(..., description="搜索关键词"),
    top_k: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """关键词检索公约条款"""
    kw_lower = q.lower()
    clauses = (
        db.query(RegulationClause)
        .filter(
            (RegulationClause.content.contains(q)) |
            (RegulationClause.article_title.contains(q)) |
            (RegulationClause.source.contains(q)) |
            (RegulationClause.keywords.contains(q))
        )
        .limit(top_k)
        .all()
    )

    results = []
    for c in clauses:
        score = 0
        if c.article_title and q in c.article_title:
            score += 10
        if c.content and q in c.content:
            score += 5
        if c.keywords and any(q.lower() in k.lower() for k in c.keywords):
            score += 3
        results.append({
            "id": c.id,
            "source": c.source,
            "chapter": c.chapter,
            "article_no": c.article_no,
            "article_title": c.article_title,
            "content": c.content,
            "keywords": c.keywords or [],
            "action_required": c.action_required,
            "platform_url": c.platform_url,
            "score": score,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return {"query": q, "count": len(results), "clauses": results[:top_k]}


@router.get("/clauses/{clause_id}")
def get_clause(clause_id: int, db: Session = Depends(get_db)):
    clause = db.query(RegulationClause).filter(RegulationClause.id == clause_id).first()
    if not clause:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="条款不存在")
    return {
        "id": clause.id,
        "source": clause.source,
        "chapter": clause.chapter,
        "article_no": clause.article_no,
        "article_title": clause.article_title,
        "content": clause.content,
        "keywords": clause.keywords or [],
        "action_required": clause.action_required,
        "platform_url": clause.platform_url,
    }


@router.get("/clauses/stats")
def clause_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(RegulationClause.id)).scalar() or 0
    chapters = (
        db.query(RegulationClause.chapter, func.count(RegulationClause.id))
        .filter(RegulationClause.chapter != "")
        .group_by(RegulationClause.chapter)
        .all()
    )
    with_action = (
        db.query(func.count(RegulationClause.id))
        .filter(RegulationClause.action_required.isnot(None))
        .scalar() or 0
    )
    return {
        "total_clauses": total,
        "chapters_with_clauses": len(chapters),
        "clauses_with_action_required": with_action,
        "chapter_breakdown": [{"chapter": c[0], "count": c[1]} for c in chapters],
    }


@router.post("/seed")
def seed_regulations(db: Session = Depends(get_db)):
    """种子数据初始化"""
    from scripts.seed_regulations import seed_regulations as _seed
    return _seed(db)
