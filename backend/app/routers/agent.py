"""
化工环保 Agent - 自进化智能体核心
支持工具链调用、记忆系统、向量检索、LLM推理、自进化循环
"""
from fastapi import APIRouter, Depends, Body, HTTPException, Query, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta
import json
import os

from app.db.database import get_db
from app.db.models import (
    Standard, PollutionFactor, PollutionLimit, Device, DeviceReading,
    NewsItem, ReportInstance, ReportTemplate, EnterpriseStandard
)
from app.memory import MemoryManager
from app.vector_memory import VectorMemory
from app.tools import Tools
from app.agent.loop import AgentLoop
from app.llm_engine import LLMEngine
from app.auth import require_auth, create_token

router = APIRouter()

# 配置常量
MAX_SESSIONS = 20
DEFAULT_LLM_TIMEOUT = 60


@router.post("/chat")
async def chat(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """
    主对话入口 — 支持工具调用、记忆检索、多步推理、LLM增强
    """
    # JWT 认证（可选）
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        user_info = require_auth({"Authorization": f"Bearer {token}"})
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    message = payload.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message 不能为空")

    session_id = payload.get("session_id", f"default_{datetime.utcnow().isoformat()[:13]}")
    mode = payload.get("mode", "react")

    # 请求级实例（每次请求独立，无共享状态）
    memory = MemoryManager(db)
    vector_mem = VectorMemory()
    tools = Tools(db)
    agent = AgentLoop(memory, tools)
    llm = LLMEngine()

    # 1. 检索相关记忆（SQL + 向量）
    sql_memories = memory.retrieve(session_id, message, top_k=5)
    vector_memories = vector_mem.search_memories(message, session_id, top_k=3)

    # 2. 检索知识库
    knowledge_context = await tools.search_knowledge(message)

    # 3. 保存用户输入到向量库
    vector_mem.add_memory(session_id, message, {"type": "user_query"})

    # 4. 执行 Agent 推理循环
    result = await agent.run(
        query=message,
        session_id=session_id,
        tools=tools,
        memories=sql_memories,
        knowledge=knowledge_context,
        mode=mode,
    )

    # 5. 用 LLM 增强回复（如有 API Key）
    reply = result.get("reply", "")
    if llm.enabled and reply:
        enhanced = await llm.generate_reply(
            query=message,
            context="\n".join(m["text"][:200] for m in sql_memories),
            memories=sql_memories[:3],
            knowledge=knowledge_context,
        )
        if enhanced and enhanced != reply and "未配置" not in enhanced:
            reply = enhanced

    # 6. 保存对话到向量库和 SQL 记忆
    if reply:
        vector_mem.add_memory(session_id, reply, {"type": "assistant_reply"})

    # 7. 记录使用
    memory.record_usage(session_id, message, "chat")

    # 8. 记录工具性能
    for tool_name in result.get("tools_used", []):
        from app.db.models import ToolPerformance
        perf = ToolPerformance(
            tool_name=tool_name,
            success=True,
            session_id=session_id,
            query_preview=message[:200],
            created_at=datetime.now(),
        )
        db.add(perf)
    db.commit()

    return {
        "reply": reply,
        "steps": result.get("steps", []),
        "mode": mode,
        "session_id": session_id,
        "context": {
            "sql_memories_found": len(sql_memories),
            "vector_memories_found": len(vector_memories),
            "knowledge_entries": len(knowledge_context.get("standards", {}).get("limits", [])),
        },
    }


@router.post("/stream")
async def chat_stream(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """
    SSE 流式对话入口 — 与 /chat 逻辑相同，但按 token 流式返回。
    """
    message = payload.get("message", "").strip()
    session_id = payload.get("session_id", f"default_{datetime.utcnow().isoformat()[:13]}")
    mode = payload.get("mode", "react")

    # 请求级实例
    memory = MemoryManager(db)
    vector_mem = VectorMemory()
    tools = Tools(db)
    agent = AgentLoop(memory, tools)
    llm = LLMEngine()

    sql_memories = memory.retrieve(session_id, message, top_k=5)
    vector_memories = vector_mem.search_memories(message, session_id, top_k=3)
    knowledge_context = await tools.search_knowledge(message)
    vector_mem.add_memory(session_id, message, {"type": "user_query"})

    async def event_generator() -> AsyncGenerator[str, None]:
        yield f"data: {json.dumps({'type': 'thinking', 'content': '正在分析...'})}\n\n"

        result = await agent.run(
            query=message,
            session_id=session_id,
            tools=tools,
            memories=sql_memories,
            knowledge=knowledge_context,
            mode=mode,
        )

        for step in result.get("steps", []):
            if step.get("type") == "action":
                tool_name = step.get("tool", "")
                args = step.get("args", {})
                yield f"data: {json.dumps({'type': 'tool_call', 'content': f'{tool_name}: {json.dumps(args, ensure_ascii=False)}'})}\n\n"
            elif step.get("type") == "thought":
                yield f"data: {json.dumps({'type': 'thinking', 'content': step.get('content', '')})}\n\n"

        reply = result.get("reply", "")
        if llm.enabled and reply:
            enhanced = await llm.generate_reply(
                query=message,
                context="\n".join(m["text"][:200] for m in sql_memories),
                memories=sql_memories[:3],
                knowledge=knowledge_context,
            )
            if enhanced and enhanced != reply and "未配置" not in enhanced:
                reply = enhanced

        if reply:
            vector_mem.add_memory(session_id, reply, {"type": "assistant_reply"})

        memory.record_usage(session_id, message, "chat")

        chunk_size = 8
        for i in range(0, len(reply), chunk_size):
            chunk = reply[i:i + chunk_size]
            yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'content': reply})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/status")
def agent_status(db: Session = Depends(get_db)):
    memory = MemoryManager(db)
    tools = Tools(db)
    vector_mem = VectorMemory()
    llm = LLMEngine()
    stats = memory.get_usage_stats()
    sessions = memory.list_sessions()
    vector_stats = vector_mem.get_stats() if vector_mem else {}
    from app.db.models import AgentState
    last_evo = db.query(AgentState).filter(AgentState.key == "last_evolution").first()

    return {
        "total_interactions": stats.get("total", 0),
        "sessions": len(sessions),
        "tool_calls": stats.get("tool_calls", 0),
        "knowledge_entries": stats.get("knowledge_entries", 0),
        "evolution_rounds": stats.get("evolution_rounds", 0),
        "vector_semantic_memories": vector_stats.get("semantic_memories", 0),
        "vector_knowledge_items": vector_stats.get("knowledge_base", 0),
        "llm_enabled": llm.enabled,
        "llm_model": llm.model,
        "last_evolution": last_evo.value if last_evo else None,
        "usage_stats": stats,
    }


@router.get("/guidance")
def get_guidance(db: Session = Depends(get_db)):
    memory = MemoryManager(db)
    tools = Tools(db)
    llm = LLMEngine()
    stats = memory.get_usage_stats()
    sessions = memory.list_sessions()

    capabilities = [
        {"name": "标准查询", "status": "active", "description": "搜索国标/地标/行标排放限值"},
        {"name": "数据分析", "status": "active", "description": "设备监测数据趋势分析与异常检测"},
        {"name": "报告生成", "status": "active", "description": "自动生成巡查、超标、合规等各类报告"},
        {"name": "资讯采集", "status": "active", "description": "全网环保新闻与政策动态"},
        {"name": "网络爬取", "status": "active", "description": "自动爬取最新环保标准入库"},
        {"name": "向量记忆", "status": "active", "description": f"已存储 {stats.get('knowledge_entries', 0)} 条语义记忆"},
        {"name": "LLM推理", "status": "active" if llm.enabled else "inactive", "description": "Agnes AI 智能推理"},
        {"name": "定时进化", "status": "active", "description": f"每6小时自动学习更新"},
    ]

    suggestions = []
    if stats.get("total", 0) == 0:
        suggestions.append("尝试: 查询 GB31570-2023 的 VOCs 排放限值")
        suggestions.append("尝试: 分析最近7天的排放数据趋势")
        suggestions.append("尝试: 采集最新环保标准到知识库")
    if stats.get("knowledge_entries", 0) < 10:
        suggestions.append("建议: 先运行一次网络爬取，扩充知识库")
        suggestions.append("建议: 导入企业监测数据，开始分析")

    return {
        "capabilities": capabilities,
        "suggestions": suggestions,
        "total_interactions": stats.get("total", 0),
        "knowledge_entries": stats.get("knowledge_entries", 0),
        "llm_enabled": llm.enabled,
    }


@router.get("/memory/sessions")
def list_sessions(db: Session = Depends(get_db)):
    memory = MemoryManager(db)
    sessions = memory.list_sessions()
    for s in sessions:
        s["conversation"] = memory.get_session_summary(s["session_id"])["conversation"][-3:]
    return sessions


@router.get("/memory/sessions/{session_id}")
def get_session_detail(session_id: str, db: Session = Depends(get_db)):
    memory = MemoryManager(db)
    vector_mem = VectorMemory()
    summary = memory.get_session_summary(session_id)
    vector_items = vector_mem.search_memories("", session_id, top_k=10)
    return {
        **summary,
        "session_id": session_id,
        "vector_memories": vector_items,
    }


@router.delete("/memory/sessions/{session_id}")
def clear_session(session_id: str, db: Session = Depends(get_db)):
    memory = MemoryManager(db)
    memory.clear_session(session_id)
    return {"message": f"已清除会话 {session_id} 的记忆"}


@router.post("/memory/clear-all")
def clear_all_memory(db: Session = Depends(get_db)):
    memory = MemoryManager(db)
    memory.clear_all()
    VectorMemory().clear_all()
    return {"message": "已清除所有记忆"}


@router.post("/evolve")
async def trigger_evolution(
    db: Session = Depends(get_db),
):
    tools = Tools(db)
    memory = MemoryManager(db)
    vector_mem = VectorMemory()
    loop_engine = AgentLoop(memory, tools)

    result = await loop_engine.run_evolution_cycle(tools, memory)

    # 同步到向量库
    sessions = memory.list_sessions()
    for session in sessions[:5]:
        sid = session["session_id"]
        turns = memory.get_turns(sid, limit=10)
        for turn in turns[-3:]:
            if turn["role"] == "user" and len(turn["content"]) > 20:
                vector_mem.add_memory(sid, turn["content"], {"type": "user_query"})
            elif turn["role"] == "assistant" and len(turn["content"]) > 30:
                vector_mem.add_memory(sid, turn["content"], {"type": "assistant_reply"})

    return result


@router.post("/crawl/standards")
async def crawl_standards_endpoint(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    tools = Tools(db)
    result = await tools.crawl_andingest_standards(
        source=payload.get("source", "auto"),
        limit=payload.get("limit", 20),
    )
    return result


@router.get("/crawl/history")
def crawl_history(db: Session = Depends(get_db)):
    from app.db.models import CrawlLog
    logs = db.query(CrawlLog).order_by(CrawlLog.crawled_at.desc()).limit(20).all()
    return [{"id": l.id, "url": l.url, "source": l.source, "new_standards": l.new_standards,
             "errors": l.errors, "status": l.status, "crawled_at": str(l.crawled_at)} for l in logs]


@router.post("/data/upload")
async def upload_data(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    tools = Tools(db)
    result = await tools.process_uploaded_data(payload)
    return result


@router.get("/knowledge/stats")
def knowledge_stats_endpoint(db: Session = Depends(get_db)):
    from sqlalchemy import func
    from app.db.models import NewsItem, Device, EnterpriseStandard
    standards = db.query(func.count(Standard.id)).scalar() or 0
    factors = db.query(func.count(PollutionFactor.id)).scalar() or 0
    limits = db.query(func.count(PollutionLimit.id)).scalar() or 0
    news = db.query(func.count(NewsItem.id)).scalar() or 0
    devices = db.query(func.count(Device.id)).scalar() or 0
    enterprise = db.query(func.count(EnterpriseStandard.id)).scalar() or 0
    vector_stats = VectorMemory().get_stats()
    return {
        "standards": standards, "factors": factors, "limits": limits,
        "news": news, "devices": devices, "enterprise_standards": enterprise,
        "vector_memories": vector_stats.get("semantic_memories", 0),
        "vector_knowledge": vector_stats.get("knowledge_base", 0),
    }


@router.post("/feedback")
def submit_feedback(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """用户反馈 — 1=有用, -1=无用"""
    from app.evolution import EvolutionEngine
    session_id = payload.get("session_id", "default")
    feedback = payload.get("feedback")  # 1 or -1
    query = payload.get("query", "")

    engine = EvolutionEngine(db)
    engine.record_feedback(session_id, feedback, query)
    return {"message": "反馈已记录", "feedback": feedback}


@router.get("/evolution/stats")
def evolution_stats(db: Session = Depends(get_db)):
    """进化统计"""
    from app.evolution import EvolutionEngine
    engine = EvolutionEngine(db)
    return engine.get_evolution_stats()


@router.get("/evolution/history")
def evolution_history(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """进化历史"""
    from app.evolution import EvolutionEngine
    engine = EvolutionEngine(db)
    return engine.get_evolution_history(limit=limit)
