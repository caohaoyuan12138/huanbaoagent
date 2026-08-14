"""
新闻信息采集模块
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.db.models import NewsItem

router = APIRouter()


@router.get("/news")
def list_news(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(NewsItem)
    if category:
        query = query.filter(NewsItem.category == category)
    if tag:
        query = query.filter(NewsItem.tags.contains(tag))
    if keyword:
        query = query.filter(
            NewsItem.title.contains(keyword) |
            NewsItem.summary.contains(keyword)
        )
    news_list = query.order_by(NewsItem.published_at.desc()).offset(offset).limit(limit).all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "summary": n.summary,
            "source": n.source,
            "url": n.url,
            "published_at": n.published_at,
            "tags": n.tags,
            "category": n.category,
        }
        for n in news_list
    ]


@router.get("/news/{news_id}")
def get_news(news_id: int, db: Session = Depends(get_db)):
    news = db.query(NewsItem).filter(NewsItem.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="新闻不存在")
    return {
        "id": news.id,
        "title": news.title,
        "summary": news.summary,
        "source": news.source,
        "url": news.url,
        "published_at": news.published_at,
        "tags": news.tags,
        "category": news.category,
        "content": news.content,
    }


@router.post("/news")
def create_news(news: dict, db: Session = Depends(get_db)):
    db_obj = NewsItem(**news)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return {"id": db_obj.id, "title": db_obj.title, "source": db_obj.source}


@router.post("/news/seed")
def seed_news(db: Session = Depends(get_db)):
    """初始化示例新闻数据"""
    news_items = [
        NewsItem(
            title="生态环境部发布《挥发性有机物无组织排放控制标准》征求意见",
            summary="为进一步加强挥发性有机物(VOCs)无组织排放控制，生态环境部近日发布了《挥发性有机物无组织排放控制标准（征求意见稿）》，向社会公开征求意见。",
            source="生态环境部官网",
            url="https://www.mee.gov.cn/",
            published_at=datetime(2025, 7, 10, 9, 0),
            tags=["VOCs", "标准", "政策"],
            category="policy",
            content="（新闻正文内容占位...）",
        ),
        NewsItem(
            title="2025年化工行业环保改造投资规模预计超2000亿元",
            summary="据行业研究机构预测，2025年我国化工行业环保改造投资规模将突破2000亿元，其中VOCs治理和废水处理升级是投资重点方向。",
            source="化工新闻",
            url="https://example.com/",
            published_at=datetime(2025, 7, 8, 14, 30),
            tags=["化工", "投资", "VOCs"],
            category="industry",
            content="（新闻正文内容占位...）",
        ),
        NewsItem(
            title="江苏省发布地方标准DB32/ 3816-2025《大气污染物综合排放标准》",
            summary="江苏省生态环境厅发布《大气污染物综合排放标准》（DB32/ 3816-2025），将于2025年10月1日起实施，对重点污染物排放限值提出更严格要求。",
            source="江苏省生态环境厅",
            url="https://h.jsepg.cn/",
            published_at=datetime(2025, 7, 5, 10, 0),
            tags=["江苏", "地标", "VOCs", "标准"],
            category="standard",
            content="（新闻正文内容占位...）",
        ),
        NewsItem(
            title="RTO蓄热式燃烧技术在化工行业应用案例分享",
            summary="某大型石化企业通过改造RTO蓄热式焚烧炉，VOCs去除效率提升至99%以上，排放浓度稳定低于30mg/m³，达到行业领先水平。",
            source="环保在线",
            url="https://www.hbzxb.com/",
            published_at=datetime(2025, 7, 3, 16, 0),
            tags=["RTO", "VOCs", "治理技术"],
            category="news",
            content="（新闻正文内容占位...）",
        ),
        NewsItem(
            title="生态环境部：下半年将开展工业园区污染物排放专项执法",
            summary="生态环境部 announces 下半年将组织对全国化工园区开展污染物排放专项执法行动，重点检查VOCs、废水排放合规情况。",
            source="环球时报",
            url="https://www.huanqiu.com/",
            published_at=datetime(2025, 7, 1, 8, 0),
            tags=["执法", "园区", "VOCs"],
            category="policy",
            content="（新闻正文内容占位...）",
        ),
    ]
    for item in news_items:
        existing = db.query(NewsItem).filter(NewsItem.title == item.title).first()
        if not existing:
            db.add(item)
    db.commit()
    return {"message": f"已初始化 {len(news_items)} 条新闻"}


@router.get("/news/categories")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(NewsItem.category).distinct().all()
    return [c[0] for c in categories] if categories else ["industry", "policy", "standard", "news"]
