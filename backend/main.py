"""
化工环保 Agent 后端服务
自进化智能体 — 记忆 + 向量检索 + LLM + 定时进化
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio
import os

from dotenv import load_dotenv
load_dotenv()

from app.logging_config import setup_logging
setup_logging()

from app.routers import knowledge, reports, devices, news, agent, compare, import_data, alerts, compliance, graph, tenant, regulation
from app.evolution import EvolutionEngine
from app.db.database import init_db
from app.vector_memory import VectorMemory
from app.llm_engine import LLMEngine
from app.scheduler import start_evolution_task, stop_all_tasks
from app.alert_checker import run_alert_checker
from app.middleware.tenant import TenantMiddleware

from app.logging_config import setup_logging
setup_logging()

# CORS 来源配置（从环境变量读取，支持逗号分隔多个域名）
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8501")
CORS_CONFIG = [url.strip() for url in _cors_origins.split(",") if url.strip()]
logger = logging.getLogger(__name__)


async def _evolution_cycle():
    """进化循环入口"""
    from app.tools import Tools
    from app.agent.loop import AgentLoop
    from app.memory import MemoryManager
    from app.db.database import SessionLocal
    from app.db.models import AgentState
    from datetime import datetime

    db = SessionLocal()
    try:
        memory = MemoryManager(db)
        tools = Tools(db)
        vector_mem = VectorMemory()
        loop_engine = AgentLoop(memory, tools)

        result = await loop_engine.run_evolution_cycle(tools, memory)

        sessions = memory.list_sessions()
        for session in sessions[:5]:
            sid = session["session_id"]
            turns = memory.get_turns(sid, limit=10)
            for turn in turns[-3:]:
                if turn["role"] == "user" and len(turn["content"]) > 20:
                    vector_mem.add_memory(sid, turn["content"], {"type": "user_query"})
                elif turn["role"] == "assistant" and len(turn["content"]) > 30:
                    vector_mem.add_memory(sid, turn["content"], {"type": "assistant_reply"})

        now = datetime.now()
        existing = db.query(AgentState).filter(AgentState.key == "last_evolution").first()
        if existing:
            existing.value = result.get("timestamp", "")
            existing.updated_at = now
        else:
            db.add(AgentState(key="last_evolution", value=result.get("timestamp", ""), updated_at=now))
        db.commit()
        logger.info("进化完成: 新增知识 %d 条", result.get("new_knowledge", 0))
    except Exception as e:
        logger.error("进化任务失败: %s", str(e))
    finally:
        db.close()


async def _modbus_poll_cycle():
    """Modbus 设备轮询循环"""
    from app.modbus_device import get_device_pool
    from app.db.database import SessionLocal
    from app.db.models import Device, DeviceReading
    from datetime import datetime

    db = SessionLocal()
    try:
        devices = db.query(Device).filter(
            Device.protocol.in_(["modbus", "modbus_hj212"])
        ).all()

        if not devices:
            return

        pool = get_device_pool()
        for device in devices:
            mn = device.mn or ""
            ip = device.ip_address or ""
            if not mn or not ip:
                continue

            pool.remove_device(mn)
            modbus_dev = pool.add_device(mn, ip, device.port or 8000, device.timeout or 5.0)

            try:
                result = modbus_dev.read_all_data()
                if result["success"]:
                    now = datetime.now()
                    for key, value in result["data"].items():
                        if isinstance(value, (int, float)):
                            reading = DeviceReading(
                                device_id=device.id,
                                factor=key,
                                value=float(value),
                                unit=device.unit,
                                timestamp=now,
                                status="normal",
                                raw_data=result.get("raw_response", ""),
                                data_type="hj212_parsed",
                            )
                            db.add(reading)
                    db.commit()
                    logger.info("Modbus轮询成功: MN=%s 数据项=%d", mn, len(result["data"]))
                else:
                    logger.warning("Modbus轮询失败: MN=%s", mn)
            except Exception as e:
                logger.error("Modbus轮询异常 MN=%s: %s", mn, str(e))

    except Exception as e:
        logger.error("Modbus轮询任务异常: %s", str(e))
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    vector_mem = VectorMemory()
    llm = LLMEngine()
    app.state.vector_mem = vector_mem
    app.state.llm = llm
    loop = asyncio.get_event_loop()
    start_evolution_task(_evolution_cycle, interval_hours=6, loop=loop)
    loop.create_task(run_alert_checker())
    start_evolution_task(_modbus_poll_cycle, interval_hours=0, interval_minutes=5, loop=loop)
    logger.info("Agent 启动完成：向量记忆 ✓ LLM引擎 ✓ 定时进化 ✓ 实时告警 ✓ Modbus轮询 ✓")
    yield
    stop_all_tasks()


app = FastAPI(
    title="化工环保Agent",
    description="化工行业环保领域智能助手 — 自进化迭代产品",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(TenantMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_CONFIG,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库"])
app.include_router(reports.router, prefix="/api/reports", tags=["报告写作"])
app.include_router(devices.router, prefix="/api/devices", tags=["设备数据"])
app.include_router(news.router, prefix="/api/news", tags=["新闻采集"])
app.include_router(agent.router, prefix="/api/agent", tags=["Agent智能"])
app.include_router(compare.router, prefix="/api/compare", tags=["标准对比"])
app.include_router(import_data.router, prefix="/api/import", tags=["数据导入"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["实时告警"])
app.include_router(compliance.router, prefix="/api/compliance", tags=["合规检查"])
app.include_router(tenant.router, prefix="/api", tags=["租户管理"])
app.include_router(graph.router, prefix="/api", tags=["知识图谱"])
app.include_router(regulation.router, prefix="/api/regulation", tags=["公约条款"])


@app.get("/api/health")
async def health_check():
    vector_mem = app.state.vector_mem
    vector_stats = vector_mem.get_stats() if vector_mem else {}
    return {
        "status": "ok",
        "service": "化工环保Agent v2.0",
        "vector_memories": vector_stats.get("semantic_memories", 0),
        "knowledge_items": vector_stats.get("knowledge_base", 0),
    }


@app.get("/api/agent/vector/stats")
async def vector_stats_endpoint():
    """向量记忆统计"""
    vector_mem = app.state.vector_mem
    return vector_mem.get_stats() if vector_mem else {}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

