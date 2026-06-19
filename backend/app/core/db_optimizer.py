"""
数据库优化工具

包含以下功能：
1. 表统计信息更新（ANALYZE）
2. 死行清理（VACUUM）
3. 索引利用率监控
4. 查询性能诊断
"""

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DatabaseOptimizer:
    """数据库优化工具类"""

    @staticmethod
    async def analyze_tables(db: AsyncSession):
        """更新表统计信息（PostgreSQL）

        ANALYZE 收集表行数、列值分布等统计，使查询优化器选择更好的执行计划
        生产环境应定期运行（如每日凌晨）
        """
        try:
            await db.execute(text("ANALYZE tasks"))
            await db.execute(text("ANALYZE task_outputs"))
            await db.execute(text("ANALYZE users"))
            await db.commit()
            logger.info("数据库表统计信息已更新")
        except Exception as e:
            logger.error(f"更新表统计失败: {e}")
            await db.rollback()

    @staticmethod
    async def vacuum_tables(db: AsyncSession, full: bool = False):
        """清理死行并回收空间（PostgreSQL）

        Args:
            full: 若为 True，执行完整清理（更耗时但效果更好）
        """
        try:
            vacuum_cmd = "VACUUM FULL" if full else "VACUUM"
            for table in ["tasks", "task_outputs", "users"]:
                await db.execute(text(f"{vacuum_cmd} {table}"))
                logger.info(f"表 {table} 已清理")
            await db.commit()
        except Exception as e:
            logger.error(f"清理死行失败: {e}")
            await db.rollback()

    @staticmethod
    async def get_index_stats(db: AsyncSession) -> dict:
        """获取索引利用率统计（PostgreSQL）

        Returns:
            包含索引使用次数、大小等信息的字典
        """
        try:
            result = await db.execute(text("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as scan_count,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                FROM pg_stat_user_indexes
                ORDER BY idx_scan DESC
            """))
            rows = result.fetchall()
            return {
                "indexes": [
                    {
                        "schema": row[0],
                        "table": row[1],
                        "index": row[2],
                        "scans": row[3],
                        "tuples_read": row[4],
                        "tuples_fetched": row[5],
                        "size": row[6],
                    }
                    for row in rows
                ]
            }
        except Exception as e:
            logger.error(f"获取索引统计失败: {e}")
            return {"error": str(e)}

    @staticmethod
    async def get_slow_queries(db: AsyncSession) -> dict:
        """获取慢查询日志（需启用 pg_stat_statements 扩展）

        Returns:
            慢查询列表
        """
        try:
            result = await db.execute(text("""
                SELECT
                    query,
                    calls,
                    total_time,
                    mean_time,
                    max_time
                FROM pg_stat_statements
                WHERE mean_time > 100  -- 平均超过 100ms
                ORDER BY mean_time DESC
                LIMIT 10
            """))
            rows = result.fetchall()
            return {
                "slow_queries": [
                    {
                        "query": row[0][:100],  # 截断显示
                        "calls": row[1],
                        "total_time": f"{row[2]:.2f}ms",
                        "mean_time": f"{row[3]:.2f}ms",
                        "max_time": f"{row[4]:.2f}ms",
                    }
                    for row in rows
                ]
            }
        except Exception as e:
            logger.warning(f"无法获取慢查询日志（pg_stat_statements 可能未启用）: {e}")
            return {"warning": str(e)}

    @staticmethod
    async def get_table_stats(db: AsyncSession) -> dict:
        """获取表统计信息（PostgreSQL）"""
        try:
            result = await db.execute(text("""
                SELECT
                    schemaname,
                    tablename,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows,
                    n_mod_since_analyze as modifications,
                    last_vacuum,
                    last_analyze
                FROM pg_stat_user_tables
                ORDER BY n_live_tup DESC
            """))
            rows = result.fetchall()
            return {
                "tables": [
                    {
                        "schema": row[0],
                        "table": row[1],
                        "live_rows": row[2],
                        "dead_rows": row[3],
                        "modifications": row[4],
                        "last_vacuum": str(row[5]) if row[5] else "never",
                        "last_analyze": str(row[6]) if row[6] else "never",
                    }
                    for row in rows
                ]
            }
        except Exception as e:
            logger.error(f"获取表统计失败: {e}")
            return {"error": str(e)}


db_optimizer = DatabaseOptimizer()
