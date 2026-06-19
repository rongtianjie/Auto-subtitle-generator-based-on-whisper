"""
测试配置和共享 fixtures

包含：
- 数据库会话管理
- 示例数据工厂
- 认证 fixtures
- API 客户端工厂
"""
import os
import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base
from app.models.user import User
from app.models.task import Task
from app.core.security import get_password_hash
from app.core.exceptions import UnauthorizedException


# 测试资源目录
TESTS_DIR = Path(__file__).parent
FIXTURES_DIR = TESTS_DIR / "fixtures"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环（session 级别）"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db_engine():
    """创建测试数据库引擎"""
    database_url = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_db_engine):
    """获取测试数据库会话"""
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """创建示例用户"""
    user = User(
        id=uuid4(),
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def sample_user_id(sample_user: User) -> str:
    """获取示例用户 ID"""
    return str(sample_user.id)


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """创建管理员用户"""
    user = User(
        id=uuid4(),
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("admin123"),
        is_active=True,
        is_admin=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def sample_task(db_session: AsyncSession, sample_user: User) -> Task:
    """创建示例任务"""
    task = Task(
        id=uuid4(),
        user_id=sample_user.id,
        title="Test Task",
        source_type="upload",
        file_path="/tmp/test.mp3",
        source_filename="test.mp3",
        whisper_model="base",
        output_formats=["txt", "srt"],
        status="pending",
    )
    db_session.add(task)
    await db_session.flush()
    return task


@pytest.fixture
async def guest_task(db_session: AsyncSession) -> Task:
    """创建游客任务"""
    task = Task(
        id=uuid4(),
        title="Guest Task",
        source_type="upload",
        file_path="/tmp/guest.mp3",
        source_filename="guest.mp3",
        whisper_model="base",
        output_formats=["srt"],
        status="pending",
        client_ip="192.168.1.1",
    )
    db_session.add(task)
    await db_session.flush()
    return task


@pytest.fixture
def auth_headers(sample_user: User):
    """获取认证头（需要实现 JWT 生成）"""
    # 这个需要根据实际的认证实现调整
    return {
        "Authorization": f"Bearer fake_token_for_{sample_user.id}"
    }


@pytest.fixture
def admin_auth_headers(admin_user: User):
    """获取管理员认证头"""
    return {
        "Authorization": f"Bearer fake_admin_token_for_{admin_user.id}"
    }


@pytest.fixture
def api_client():
    """获取异步 HTTP 客户端工厂"""
    # 这个会在集成测试中使用
    import httpx

    class AsyncClient:
        def __init__(self, base_url="http://localhost:8000"):
            self.base_url = base_url
            self.client = httpx.AsyncClient(base_url=base_url)

        async def close(self):
            await self.client.aclose()

    return AsyncClient


@pytest.fixture
def sample_audio_file():
    """获取示例音频文件路径"""
    # 返回测试样本文件的路径
    sample_path = FIXTURES_DIR / "sample.mp3"

    # 如果样本不存在，创建一个虚拟文件
    if not sample_path.exists():
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        sample_path.write_text("fake audio data")

    return str(sample_path)

