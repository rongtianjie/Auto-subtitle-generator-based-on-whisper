# 贡献指南

感谢您对 SubWeaver 项目的关注和贡献！本指南将帮助您快速了解如何参与项目开发。

## 目录

1. [开发环境设置](#开发环境设置)
2. [代码风格和质量](#代码风格和质量)
3. [提交规范](#提交规范)
4. [测试要求](#测试要求)
5. [拉取请求流程](#拉取请求流程)
6. [问题报告](#问题报告)
7. [项目架构](#项目架构)

## 开发环境设置

### 前置条件

- Python 3.11+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+
- Docker & Docker Compose (可选)

### 本地开发环境

#### 1. 克隆仓库

```bash
git clone <repository-url>
cd Auto-subtitle-generator-based-on-whisper
```

#### 2. 设置后端环境

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -e ".[dev]"

# 设置环境变量
cp .env.example .env
# 编辑 .env 文件，配置本地数据库等

# 初始化数据库
python -m alembic upgrade head
```

#### 3. 设置前端环境

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

#### 4. 启动服务

后端：
```bash
python -m uvicorn app.main:app --reload --port 8000
```

Worker（另一个终端）：
```bash
python -m app.worker.worker
```

前端已在 `npm run dev` 中运行在 http://localhost:5173

#### 5. 使用 Docker Compose（推荐）

```bash
docker-compose up -d
# 访问：
# - 前端: http://localhost:3000
# - API: http://localhost:8000
# - 监控: http://localhost:9090 (Prometheus) / http://localhost:3001 (Grafana)
```

## 代码风格和质量

本项目使用以下工具进行代码检查和格式化：

### 自动化工具

```bash
# 安装 pre-commit 钩子
pre-commit install

# 手动运行所有检查
pre-commit run --all-files

# 或分别运行
black backend/              # 代码格式化
isort backend/              # Import 排序
flake8 backend/             # Linting
mypy backend/               # 类型检查
bandit -r backend/          # 安全检查
```

### Python 代码风格

- 使用 Black 格式化（行长 100）
- 使用 isort 管理 imports
- 遵循 PEP 8 规范
- 类型提示是必需的

示例：

```python
from typing import Optional
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

async def get_task(
    task_id: int,
    session: AsyncSession,
) -> Optional[dict]:
    """获取任务详情。
    
    Args:
        task_id: 任务 ID
        session: 数据库会话
        
    Returns:
        任务数据，不存在时返回 None
    """
    query = select(Task).where(Task.id == task_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()
```

### TypeScript/JavaScript 代码风格

- 使用 Prettier 格式化
- 启用严格类型检查
- 组件文件使用 .tsx 扩展名

## 提交规范

本项目采用 Conventional Commits 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型 (type)

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码风格改变 (非功能性)
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建、依赖等变更
- `ci`: CI/CD 配置变更

### 范围 (scope)

使用英文小写，例如：
- `api`, `worker`, `database`, `frontend`, `config`

### 主题 (subject)

- 简明扼要，不超过 50 字符
- 使用祈使句
- 不以句点结尾

### 示例

```
feat(api): 添加任务分页接口

- 新增 GET /tasks 分页参数支持
- 支持 limit, offset, sort_by 参数
- 返回总数和分页信息

Closes #123
```

## 测试要求

### 运行测试

```bash
# 所有测试
pytest

# 特定测试
pytest tests/test_api.py

# 带覆盖率
pytest --cov=app

# 特定标记
pytest -m unit              # 单元测试
pytest -m integration       # 集成测试
pytest -m e2e              # 端到端测试
```

### 测试覆盖要求

- 新增代码的测试覆盖率 >= 80%
- 修复 bug 必须添加测试
- 关键业务逻辑必须有单元测试

### 测试示例

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_task():
    """测试创建任务。"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/tasks",
            json={
                "title": "Test Task",
                "source_type": "upload",
            }
        )
        assert response.status_code == 201
        assert response.json()["id"] is not None
```

### 前端测试

```bash
# 运行 E2E 测试
npm run test:e2e

# 特定测试文件
npx playwright test tests/e2e/task-creation.spec.ts

# 调试模式
npx playwright test --debug
```

## 拉取请求流程

### 1. 创建分支

使用 scope 作为分支名前缀：

```bash
git checkout -b feature/api-pagination
git checkout -b fix/task-timeout-issue
git checkout -b docs/setup-guide
```

### 2. 开发和提交

- 频繁提交，保持历史清晰
- 一个 commit 一个逻辑单元
- 运行 `pre-commit run --all-files` 确保代码质量

### 3. 推送和创建 PR

```bash
git push origin feature/api-pagination
```

然后在 GitHub 创建 Pull Request

### 4. PR 检查清单

PR 描述应包含：

- [ ] 问题描述（关联 issue #123）
- [ ] 解决方案概述
- [ ] 改动内容列表
- [ ] 测试验证方式
- [ ] 截图/视频（如适用）
- [ ] 是否有破坏性变更

### 5. 代码审查

- 自动 CI 检查必须通过
- 需要至少一个维护者的批准
- 反馈应在 1-2 个工作日内响应

### 6. 合并

一旦获批，PR 将被合并到 main 分支

## 问题报告

### Bug 报告

请使用 GitHub Issues 并包含：

1. **环境信息**
   - 操作系统
   - Python/Node.js 版本
   - 项目版本

2. **问题描述**
   - 现象
   - 预期行为
   - 实际行为

3. **复现步骤**
   - 逐步说明如何复现

4. **日志**
   - 完整的错误栈和日志

示例：

```markdown
## Bug 描述
上传大文件时应用崩溃

## 环境
- OS: macOS 12.1
- Python: 3.11.2
- Version: 1.0.0

## 复现步骤
1. 访问首页
2. 选择 > 100MB 的视频文件
3. 点击上传
4. 应用出现 500 错误

## 实际日志
[粘贴错误栈]

## 期望
应用应该处理大文件或显示友好错误提示
```

### 功能请求

使用 GitHub Discussions 或 Issues，标记为 `enhancement`

## 项目架构

### 后端架构

```
backend/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── core/                # 核心功能
│   │   ├── exceptions.py    # 异常定义
│   │   ├── validators.py    # 验证逻辑
│   │   ├── security.py      # 安全相关
│   │   ├── structured_logging.py
│   │   ├── metrics.py       # Prometheus 指标
│   │   └── alerting.py      # 告警规则
│   ├── api/                 # API 路由
│   │   └── v1/              # API v1
│   ├── models/              # SQLAlchemy 模型
│   ├── services/            # 业务逻辑
│   ├── schemas/             # Pydantic 模式
│   ├── worker/              # 后台任务
│   └── database.py          # 数据库配置
├── tests/                   # 测试
├── pyproject.toml          # 项目配置
└── alembic/                # 数据库迁移
```

### 关键设计模式

1. **异常处理**：统一使用 AppException 体系
2. **数据验证**：Pydantic schemas at API boundary
3. **异步**: AsyncSession for database, async def for endpoints
4. **日志**：structlog with JSON output
5. **监控**：Prometheus metrics
6. **测试**：Unit, integration, E2E 三层

### 前端架构

```
frontend/
├── src/
│   ├── main.tsx            # 入口点
│   ├── pages/              # 页面组件
│   ├── components/         # 可复用组件
│   ├── hooks/              # 自定义 Hook
│   ├── context/            # React Context
│   ├── lib/                # 工具函数
│   └── styles/             # 样式文件
└── tests/e2e/              # E2E 测试
```

## 常见开发任务

### 添加新的 API 端点

```python
# 1. 定义 Schema
class TaskCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None

# 2. 创建路由
@router.post("/tasks")
async def create_task(
    request: TaskCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    # 业务逻辑
    return {"id": 1}

# 3. 添加测试
async def test_create_task():
    # 测试逻辑
    pass
```

### 添加数据库迁移

```bash
# 修改模型后
alembic revision --autogenerate -m "Add new_column to tasks"

# 检查生成的迁移文件
# 修改后应用迁移
alembic upgrade head
```

### 添加新的监控指标

```python
# app/core/metrics.py
task_duration = Histogram(
    'task_duration_seconds',
    'Task processing duration',
    buckets=[1, 5, 10, 30, 60]
)

# 在代码中使用
with task_duration.time():
    # 处理任务
    pass
```

## 获取帮助

- **文档**：[README.md](README.md), [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **讨论**：GitHub Discussions
- **问题**：GitHub Issues
- **联系**：[维护者邮箱]

## 许可证

本项目采用 MIT License。提交 PR 即表示您同意该许可证。

---

感谢您的贡献！🎉
