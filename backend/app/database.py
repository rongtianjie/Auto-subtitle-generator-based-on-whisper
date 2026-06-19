from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool

from app.config import settings

# 数据库连接池优化配置
if settings.DEBUG:
    # 开发环境：禁用连接池，避免调试时连接被占用
    pool_class = NullPool
    pool_kwargs = {}
else:
    # 生产环境：使用队列池，优化高并发性能
    pool_class = QueuePool
    pool_kwargs = {
        "pool_size": 20,           # 基础连接数
        "max_overflow": 30,        # 最多额外创建 30 个临时连接
        "pool_timeout": 30,        # 等待连接超时时间
        "pool_recycle": 3600,      # 1 小时回收一次连接（防止数据库端强制断开）
        "pre_ping": True,          # 获取连接前先 ping 检测
    }

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=pool_class,
    **pool_kwargs,
)
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # 避免意外的自动刷新，显式控制
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
