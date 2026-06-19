# 开发指南

本文档涵盖日常开发工作流程和工具使用。

## 快速开始

### 最快方式（推荐）

```bash
# 1. 安装依赖
make install

# 2. 启动 Docker Compose
make docker-up

# 3. 在浏览器打开
# 前端: http://localhost:3000
# API: http://localhost:8000
# 监控: http://localhost:3001
```

### 本地开发方式

需要手动启动各个服务：

```bash
# 终端 1: 后端 API
cd backend
uv run python -m uvicorn app.main:app --reload --port 8000

# 终端 2: 前端
cd frontend
npm run dev

# 终端 3: Worker
cd backend
uv run python run_worker.py
```

## 开发工作流

### 1. 创建分支

```bash
# 新功能
git checkout -b feature/task-priority

# 修复 bug
git checkout -b fix/timeout-issue

# 文档
git checkout -b docs/api-guide
```

### 2. 开发代码

遵循以下步骤：

```bash
# 编辑代码...

# 格式化代码
make format

# 运行测试
make test

# 代码检查
make lint

# 类型检查
make type-check
```

### 3. 提交更改

```bash
git add .
git commit -m "feat(api): 添加任务优先级支持"

# 确保通过 pre-commit 钩子
pre-commit run --all-files
```

### 4. 创建 Pull Request

在 GitHub 上创建 PR，填写完整信息后等待审查。

## 常见开发任务

### 添加新的 API 端点

1. **定义请求/响应模式**：

```python
# backend/app/schemas/task.py
from pydantic import BaseModel
from typing import Optional

class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    priority: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated Task",
                "priority": 1
            }
        }

class TaskResponse(BaseModel):
    id: int
    title: str
    priority: int
    status: str
```

2. **实现服务方法**：

```python
# backend/app/services/task_service.py
class TaskMutationService:
    async def update_task(
        self,
        task_id: int,
        request: TaskUpdateRequest,
        session: AsyncSession
    ) -> Task:
        task = await self.query_service.get_task(task_id, session)
        if not task:
            raise TaskNotFoundError(task_id)
        
        for field, value in request.dict(exclude_unset=True).items():
            setattr(task, field, value)
        
        session.add(task)
        await session.flush()
        return task
```

3. **创建 API 路由**：

```python
# backend/app/api/v1/tasks.py
@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    request: TaskUpdateRequest,
    session: AsyncSession = Depends(get_session),
    service: TaskMutationService = Depends()
) -> TaskResponse:
    """更新任务。
    
    参数:
        task_id: 任务 ID
        request: 更新数据
    
    返回:
        更新后的任务
    """
    task = await service.update_task(task_id, request, session)
    await session.commit()
    return TaskResponse.from_orm(task)
```

4. **添加测试**：

```python
# backend/tests/test_task_api.py
@pytest.mark.asyncio
async def test_update_task(api_client, sample_task):
    response = await api_client.put(
        f"/api/v1/tasks/{sample_task.id}",
        json={"title": "Updated Title"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"
```

5. **更新文档**：

在 `docs/API_DOCUMENTATION.md` 中添加端点文档。

### 添加数据库迁移

```bash
# 修改 backend/app/models/task.py 后
cd backend

# 自动生成迁移
python -m alembic revision --autogenerate -m "add priority column"

# 检查生成的迁移文件
cat alembic/versions/xxx_add_priority_column.py

# 手动编辑后应用
python -m alembic upgrade head
```

### 添加新的监控指标

```python
# backend/app/core/metrics.py
task_priority_distribution = Histogram(
    'task_priority_distribution',
    'Distribution of task priorities',
    labelnames=['priority'],
    buckets=[1, 5, 10]
)

# 在代码中使用
task_priority_distribution.labels(priority=request.priority).observe(1)
```

### 前端组件开发

```typescript
// frontend/src/components/PrioritySelector.tsx
import React from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface PrioritySelectorProps {
  value: number
  onChange: (value: number) => void
  disabled?: boolean
}

export function PrioritySelector({
  value,
  onChange,
  disabled = false
}: PrioritySelectorProps) {
  return (
    <Select value={value.toString()} onValueChange={(v) => onChange(parseInt(v))}>
      <SelectTrigger disabled={disabled}>
        <SelectValue placeholder="Select priority" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="1">High</SelectItem>
        <SelectItem value="5">Medium</SelectItem>
        <SelectItem value="10">Low</SelectItem>
      </SelectContent>
    </Select>
  )
}
```

## 调试技巧

### Python 调试

```python
# 设置断点
import pdb; pdb.set_trace()

# 或使用 ipdb (更好的界面)
import ipdb; ipdb.set_trace()

# 在 VS Code 中调试
# 在 launch.json 中配置，然后按 F5
```

### 数据库调试

```bash
# 进入数据库
docker compose exec postgres psql -U postgres -d subweaver

# 查看表结构
\dt

# 查询数据
SELECT * FROM tasks LIMIT 10;

# 查看索引
\d tasks
```

### API 调试

```bash
# 使用 curl
curl -X GET http://localhost:8000/api/v1/tasks

# 使用 httpie (更友好)
uv tool install httpie
http GET localhost:8000/api/v1/tasks

# 使用 FastAPI 的交互式文档
# http://localhost:8000/docs
```

### 日志检查

```bash
# 查看实时日志
docker compose logs -f backend

# 查看特定服务的日志
docker compose logs -f worker

# 搜索日志
docker compose logs backend | grep "ERROR"

# 查看管理端日志文件列表（需要管理员认证）
curl http://localhost:8000/api/v1/admin/logs
```

## 性能分析

### CPU 分析

```python
# 使用 cProfile
import cProfile
import pstats

cProfile.run('your_function()', 'output.prof')

p = pstats.Stats('output.prof')
p.sort_stats('cumulative').print_stats(10)
```

### 内存分析

```python
# 使用 memory-profiler
from memory_profiler import profile

@profile
def your_function():
    # 代码...
    pass
```

运行：
```bash
python -m memory_profiler script.py
```

### 数据库查询分析

```bash
# 启用 PostgreSQL 日志
# 在 docker-compose.yml 中添加
# command: ["postgres", "-c", "log_statement=all"]

# 查看慢查询
curl http://localhost:8000/api/v1/health/db-stats
```

## 测试策略

### 单元测试

测试单个函数或方法的逻辑：

```python
def test_calculate_priority_score():
    assert calculate_priority_score(1) == 100
    assert calculate_priority_score(5) == 50
    assert calculate_priority_score(10) == 10
```

### 集成测试

测试多个组件的交互：

```python
@pytest.mark.asyncio
async def test_task_creation_workflow(api_client, db_session):
    # 创建任务
    response = await api_client.post("/api/v1/tasks", json={...})
    task_id = response.json()["id"]
    
    # 更新任务
    response = await api_client.put(f"/api/v1/tasks/{task_id}", json={...})
    
    # 验证数据库
    task = await db_session.get(Task, task_id)
    assert task.priority == 1
```

### E2E 测试

测试完整的用户工作流：

```typescript
test('user can create and update task', async ({ page }) => {
  // 导航到首页
  await page.goto('http://localhost:3000')
  
  // 填充表单
  await page.fill('[name="title"]', 'New Task')
  
  // 提交
  await page.click('button[type="submit"]')
  
  // 验证结果
  await expect(page).toHaveURL(/\/task\/\d+/)
})
```

## 发布流程

### 版本号

使用 Semantic Versioning (MAJOR.MINOR.PATCH)：

- MAJOR: 破坏性变更
- MINOR: 新功能（向后兼容）
- PATCH: Bug 修复

### 发布步骤

1. 更新版本号：
   - backend/pyproject.toml
   - frontend/package.json
   - backend/app/__init__.py

2. 更新 CHANGELOG.md

3. 创建 git tag：
   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```

4. 构建和发布：
   ```bash
   make docker
   # 推送到容器仓库
   ```

## 常见问题

### Q: 修改了 Dockerfile 后需要重新构建吗？
A: 需要。运行 `docker compose build --no-cache`

### Q: 如何重置数据库？
A: 运行 `make db-reset` 或 `docker compose down -v`

### Q: 前端 hot reload 不工作？
A: 检查 frontend/vite.config.ts 中的 HMR 配置

### Q: Worker 任务卡住了怎么办？
A: 查看日志 `docker compose logs worker`，如需要可重启 `docker compose restart worker`

### Q: 如何连接远程数据库进行测试？
A: 修改 .env 中的 DATABASE_URL，指向远程数据库

## 推荐工具

### VS Code 扩展
- Python: ms-python.python
- Prettier: esbenp.prettier-vscode
- GitLens: eamodio.gitlens
- REST Client: humao.rest-client

### 命令行工具
- httpie: HTTP 客户端
- pgcli: PostgreSQL CLI
- redis-cli: Redis CLI（已随 Redis 提供）
- jq: JSON 处理

### IDE 快捷键

**VS Code:**
- F5: 开始调试
- Ctrl+Shift+D: 打开调试面板
- Ctrl+`: 打开终端
- Ctrl+Shift+P: 命令面板

---

Happy coding! 🚀
