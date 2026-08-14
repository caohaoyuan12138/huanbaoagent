"""
定时任务调度器 — 使用 asyncio 后台任务替代 APScheduler
无需外部依赖，在 FastAPI lifespan 中管理
"""
import asyncio
import logging
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_scheduled_tasks: dict = {}


async def _run_periodic(interval_seconds: int, coro_factory: Callable, *args, **kwargs):
    """周期性执行后台任务"""
    while True:
        try:
            logger.info("=== 开始定时任务 [%s] ===", datetime.now().isoformat())
            await coro_factory(*args, **kwargs)
            logger.info("定时任务完成")
        except Exception as e:
            logger.error("定时任务失败: %s", str(e))
        await asyncio.sleep(interval_seconds)


def start_evolution_task(coro_factory: Callable, interval_hours: int = 6, interval_minutes: int = 0, loop: Optional[asyncio.AbstractEventLoop] = None):
    """启动定时任务"""
    total_seconds = interval_hours * 3600 + interval_minutes * 60
    if total_seconds == 0:
        total_seconds = 300
    evt_loop = loop or asyncio.get_event_loop()
    task_name = f"task_{hash(coro_factory.__name__)}"
    if task_name in _scheduled_tasks:
        _scheduled_tasks[task_name].cancel()

    _scheduled_tasks[task_name] = evt_loop.create_task(
        _run_periodic(total_seconds, coro_factory)
    )
    logger.info("定时任务已启动，间隔 %d 秒", total_seconds)
    return _scheduled_tasks[task_name]


def stop_all_tasks():
    """停止所有定时任务"""
    for name, task in _scheduled_tasks.items():
        task.cancel()
        logger.info("已停止任务: %s", name)
    _scheduled_tasks.clear()
