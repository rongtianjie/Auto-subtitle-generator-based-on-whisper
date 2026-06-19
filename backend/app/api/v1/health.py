from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.startup_checker.checker import checker
from app.startup_checker.checks.db_check import check_database
from app.startup_checker.checks.ffmpeg_check import check_ffmpeg
from app.startup_checker.checks.whisper_check import check_whisper_model
from app.startup_checker.checks.llm_check import check_llm_connection
from app.core.task_queue import task_queue
from app.core.sse_manager import sse_manager
from app.core.db_optimizer import db_optimizer

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("")
async def health():
    return {"status": "ok", "service": "Whisper Platform"}


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    checks = await asyncio_gather_checks()
    queue_info = await task_queue.get_queue_info(db)
    all_ok = all(c.status or c.severity != "error" for c in checks)

    return {
        "status": "ok" if all_ok else "degraded",
        "checks": [c.model_dump() for c in checks],
        "queue": queue_info,
    }


async def asyncio_gather_checks():
    import asyncio
    results = await asyncio.gather(
        check_database(),
        check_ffmpeg(),
        check_whisper_model(),
        check_llm_connection(),
        return_exceptions=True,
    )
    return [r for r in results if not isinstance(r, Exception)]


@router.get("/sse-connections")
async def sse_connections_status():
    """获取 SSE 连接监控信息"""
    return sse_manager.get_stats()


@router.get("/db-stats")
async def database_stats(db: AsyncSession = Depends(get_db)):
    """获取数据库统计信息（表大小、索引利用率等）"""
    table_stats = await db_optimizer.get_table_stats(db)
    index_stats = await db_optimizer.get_index_stats(db)
    slow_queries = await db_optimizer.get_slow_queries(db)

    return {
        "tables": table_stats,
        "indexes": index_stats,
        "slow_queries": slow_queries,
    }


@router.post("/db-analyze")
async def database_analyze(db: AsyncSession = Depends(get_db)):
    """更新数据库表统计信息（管理员操作）"""
    await db_optimizer.analyze_tables(db)
    return {"status": "success", "message": "数据库统计信息已更新"}


@router.post("/db-vacuum")
async def database_vacuum(db: AsyncSession = Depends(get_db)):
    """清理数据库死行（管理员操作）"""
    await db_optimizer.vacuum_tables(db, full=False)
    return {"status": "success", "message": "数据库死行已清理"}
