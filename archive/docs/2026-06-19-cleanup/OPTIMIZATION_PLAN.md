# SubWeaver 完整优化方案

**版本**: 1.0  
**日期**: 2026-06-18  
**状态**: 待执行  

---

## 📋 执行概览

本文档涵盖 SubWeaver 项目的全面优化，分为三个阶段共 17 项优化任务。

| 阶段 | 任务数 | 重点 | 预计工期 |
|------|--------|------|---------|
| **第一阶段** | 5 | 关键修复、安全增强 | 4-6 小时 |
| **第二阶段** | 6 | 代码质量、稳定性 | 6-8 小时 |
| **第三阶段** | 6 | 可维护性、监控 | 4-6 小时 |

---

## 🔴 第一阶段：关键修复（高优先级）

### 任务 1.1：统一异常处理框架

**问题现象**：
- API 端点返回格式不一致（有些 `{"message": "..."}`, 有些 `{"detail": "..."}`)
- HTTP 状态码选择不一致（文件大小超限返回 400，任务限制返回 429）
- 没有全局异常捕获，错误堆栈泄露给前端

**影响范围**：
- `backend/app/api/v1/*.py` - 所有路由文件
- `backend/app/services/*.py` - 服务层
- `frontend/src/lib/api.ts` - 错误处理拦截器

**实现方案**：

```plaintext
1. 创建 app/core/exceptions.py
   ├─ 定义标准异常类（AppException, ValidationError, AuthError 等）
   ├─ 定义异常到 HTTP 状态码的映射
   └─ 定义统一的错误响应模型

2. 创建 app/core/middleware.py
   ├─ 全局异常处理中间件
   ├─ 日志记录异常（ERROR 级别）
   └─ 返回统一格式的错误响应

3. 修改 app/main.py
   ├─ 注册异常处理中间件
   └─ 添加异常处理器

4. 更新 app/api/v1/*.py
   ├─ 替换 HTTPException 为自定义异常
   └─ 移除重复的错误处理逻辑

5. 更新 frontend/src/lib/api.ts
   ├─ 统一解析错误响应
   └─ 支持所有 4xx/5xx 状态码
```

**新增文件**：
- `backend/app/core/exceptions.py` (150 行)
- `backend/app/core/middleware.py` (100 行)

**修改文件**：
- `backend/app/main.py` (5 行)
- `backend/app/api/v1/*.py` (每个 -10 行)
- `frontend/src/lib/api.ts` (20 行)

**验证方式**：
```bash
# 测试各种错误状态
curl -X POST http://localhost:8765/api/v1/auth/register \
  -d '{"username":""}' -H "Content-Type: application/json"

# 检查响应格式一致性
# 所有错误都应该是: { "error_code": "...", "message": "...", "timestamp": "..." }
```

---

### 任务 1.2：文件上传安全加固

**问题现象**：
- `backend/app/api/v1/tasks.py:89-113` 只检查文件大小，不验证格式
- 缺少恶意文件检测
- 没有上传速率限制
- 文件名没有清理（可能有 path traversal 风险）

**影响范围**：
- `backend/app/api/v1/tasks.py:create_task()` 
- `backend/app/core/storage.py:save_upload_stream()`

**实现方案**：

```plaintext
1. 创建 app/core/validators.py
   ├─ ALLOWED_MIME_TYPES = {audio/*, video/*}
   ├─ 函数 validate_upload_filename(filename)
   │  └─ 使用 pathlib.Path.name 清理路径
   ├─ 函数 validate_mime_type(file_obj)
   │  └─ 使用 python-magic 库检测
   └─ 函数 scan_malware(file_path) [可选集成点]

2. 修改 app/api/v1/tasks.py:create_task()
   ├─ 验证 file.filename (不含路径)
   ├─ 读取文件头 magic bytes 验证格式
   ├─ 添加上传限流（按 IP 每分钟最多 5 个文件）
   └─ 使用 Pydantic schema 替代 JSON 解析

3. 修改 app/core/storage.py:save_upload_stream()
   ├─ 使用清理后的文件名
   └─ 添加文件完整性检查（大小匹配）

4. 更新 pyproject.toml
   ├─ 添加依赖: python-magic-bin (跨平台)
   └─ 添加依赖: slowapi (速率限制)
```

**新增文件**：
- `backend/app/core/validators.py` (120 行)
- `backend/app/core/rate_limiter.py` (80 行)

**修改文件**：
- `backend/app/api/v1/tasks.py` (50 行变更)
- `backend/app/core/storage.py` (30 行变更)
- `backend/pyproject.toml` (2 行)

**验证方式**：
```bash
# 测试非音视频文件拒绝
curl -X POST http://localhost:8765/api/v1/tasks \
  -F "source_type=upload" -F "file=@malicious.exe"
# 预期: 400 Bad Request, error_code: "INVALID_FILE_TYPE"

# 测试速率限制
for i in {1..6}; do
  curl -X POST ... --data @large_file.mp4 &
done
# 预期: 第 6 个请求收到 429 Too Many Requests
```

---

### 任务 1.3：SSE 连接泄漏修复

**问题现象**：
- `backend/app/api/v1/tasks.py:297-325` SSE 流在任务完成后可能不关闭
- 没有超时机制，长期连接未释放
- 没有心跳检测，僵尸连接无法识别

**影响范围**：
- `backend/app/api/v1/tasks.py:stream_task_progress()`
- `frontend/src/hooks/useSSE.ts`

**实现方案**：

```plaintext
1. 修改 backend/app/api/v1/tasks.py:stream_task_progress()
   ├─ 添加超时控制（30 秒无数据则关闭）
   ├─ 添加心跳包（keepalive event，每 10 秒一次）
   ├─ 改进错误处理（捕获 StopIteration）
   └─ 添加连接计数监控

2. 创建 app/core/sse_manager.py
   ├─ 全局 SSE 连接追踪
   ├─ 定期清理过期连接
   └─ 提供监控端点 /health/sse-connections

3. 修改 frontend/src/hooks/useSSE.ts
   ├─ 实现自动重连（最多 3 次重试，指数退避）
   ├─ 添加心跳检测（无数据 15 秒则重连）
   ├─ 正确处理 error 事件
   └─ 清理资源（useEffect cleanup）

4. 修改 app/main.py
   ├─ 注册 SSE 清理任务（定期运行）
   └─ 优雅关闭时等待连接关闭
```

**新增文件**：
- `backend/app/core/sse_manager.py` (100 行)

**修改文件**：
- `backend/app/api/v1/tasks.py` (40 行变更)
- `frontend/src/hooks/useSSE.ts` (60 行变更)
- `backend/app/main.py` (10 行)

**验证方式**：
```bash
# 监控 SSE 连接
curl http://localhost:8765/api/v1/health/sse-connections
# 预期: { "active_connections": 0, "total_created": 5, "avg_lifetime_seconds": 25 }

# 测试自动重连
# 1. 启动 SSE 连接到任务 /api/v1/tasks/{id}/stream
# 2. 中断后端连接（docker compose restart backend）
# 3. 观察前端是否自动重连
```

---

### 任务 1.4：前端状态管理重构

**问题现象**：
- `frontend/src/pages/Home.tsx` 超过 600 行，有 15+ 个 `useState`
- 混合了上传逻辑、URL 输入、模型选择、任务列表
- 难以单元测试，修改一个功能容易引入 bug
- 全局状态（认证、主题）混在页面中

**影响范围**：
- `frontend/src/pages/Home.tsx` (600+ 行)
- `frontend/src/components/shared/TaskListCard.tsx`
- `frontend/src/pages/TaskDetail.tsx`
- `frontend/src/hooks/useAuth.tsx`

**实现方案**：

```plaintext
1. 创建全局状态管理 (使用 Context API)
   ├─ src/context/AppContext.tsx
   │  └─ 管理: 认证、主题、任务列表、通知
   ├─ src/context/useAppContext.ts
   └─ 提供 useAppState, useAppActions hook

2. 拆分 Home.tsx 为独立组件
   ├─ src/pages/Home.tsx (改为容器，150 行)
   ├─ src/components/home/TaskSourceSelector.tsx (150 行)
   │  └─ 处理 upload/url 切换和输入
   ├─ src/components/home/ModelSelector.tsx (120 行)
   │  └─ Whisper 模型选择和下载状态
   ├─ src/components/home/OutputFormatSelector.tsx (100 行)
   │  └─ 输出格式和语言选择
   ├─ src/components/home/SubmitSection.tsx (80 line)
   │  └─ 验证和提交逻辑
   └─ src/components/home/TaskList.tsx (150 行)
      └─ 最近任务列表（复用 TaskListCard）

3. 优化逻辑
   ├─ 提取表单验证为 hooks/useTaskForm.ts
   ├─ 提取 SSE 监听为 hooks/useTaskStream.ts
   └─ 提取模型管理为 hooks/useModelManager.ts

4. 添加错误边界
   ├─ src/components/ErrorBoundary.tsx
   └─ 应用到主要页面
```

**新增文件**：
- `frontend/src/context/AppContext.tsx` (150 行)
- `frontend/src/context/useAppContext.ts` (30 行)
- `frontend/src/components/home/TaskSourceSelector.tsx` (150 行)
- `frontend/src/components/home/ModelSelector.tsx` (120 行)
- `frontend/src/components/home/OutputFormatSelector.tsx` (100 行)
- `frontend/src/components/home/SubmitSection.tsx` (80 行)
- `frontend/src/components/home/TaskList.tsx` (150 行)
- `frontend/src/components/ErrorBoundary.tsx` (80 行)
- `frontend/src/hooks/useTaskForm.ts` (100 行)
- `frontend/src/hooks/useTaskStream.ts` (80 行)
- `frontend/src/hooks/useModelManager.ts` (90 line)

**修改文件**：
- `frontend/src/pages/Home.tsx` (从 600 行减至 150 行)
- `frontend/src/App.tsx` (添加 ErrorBoundary 和 AppContextProvider)

**验证方式**：
```bash
npm run build  # 无编译错误

# 在浏览器中手动测试
# 1. 切换上传/URL 模式，状态应该保留
# 2. 刷新页面，上次选择的格式应该保留（localStorage）
# 3. 打开多个标签，状态应该实时同步
# 4. 出错时应显示友好的错误提示，不是白屏
```

---

### 任务 1.5：前端 API 层增强

**问题现象**：
- `frontend/src/lib/api.ts` 没有请求超时配置，默认无限等待
- 缺少自动重试机制，网络抖动导致请求失败
- 错误处理只检查 401，其他 4xx/5xx 状态码被忽略
- 没有请求排队和去重

**影响范围**：
- `frontend/src/lib/api.ts`
- 所有调用 API 的组件和 hooks

**实现方案**：

```plaintext
1. 增强 frontend/src/lib/api.ts
   ├─ 配置超时 (30 秒)
   ├─ 实现重试机制
   │  ├─ 自动重试 GET 请求（最多 3 次）
   │  ├─ 指数退避 (100ms, 200ms, 400ms)
   │  └─ 不重试 4xx 错误（除了 429）
   ├─ 改进错误拦截器
   │  ├─ 提取 error.response.data.message
   │  ├─ 处理网络错误 (ECONNREFUSED 等)
   │  └─ 返回结构化错误对象
   └─ 添加请求队列（防止同时发送过多请求）

2. 创建 frontend/src/lib/request-queue.ts
   ├─ 管理请求队列（最多并发 5 个）
   └─ 自动去重（相同 method + url 的请求）

3. 创建 frontend/src/lib/errors.ts (增强现有)
   ├─ 标准化异常类 ApiError, NetworkError 等
   └─ 用户友好的错误消息映射

4. 修改所有 API 调用
   ├─ 统一使用新的错误处理
   └─ 添加 loading 和 error 状态管理
```

**新增文件**：
- `frontend/src/lib/request-queue.ts` (100 行)

**修改文件**：
- `frontend/src/lib/api.ts` (60 行变更)
- `frontend/src/lib/errors.ts` (40 行变更)
- 所有 API 调用点 (更新 catch 块)

**验证方式**：
```bash
# 使用浏览器开发者工具网络面板

# 测试 1: 请求超时
# 修改 /etc/hosts 映射到不可达 IP，观察 30 秒后超时

# 测试 2: 自动重试
# 使用 Charles 或 Fiddler 在第 1、2 次请求时断开，第 3 次允许
# 观察请求应该成功（重试 3 次）

# 测试 3: 错误处理
# 修改请求头触发 500 错误，检查是否显示友好提示
```

---

## 🟠 第二阶段：代码质量（中优先级）

### 任务 2.1：改进任务服务架构

**问题现象**：
- `backend/app/services/task_service.py` 只有 105 行，方法太少
- 业务逻辑散布在 API 路由中
- 缺少单元测试
- JSON 手动解析，没有 schema 验证

**影响范围**：
- `backend/app/api/v1/tasks.py` (API 路由)
- `backend/app/services/task_service.py` (服务层)
- `backend/app/schemas/task.py` (数据模型)

**实现方案**：

```plaintext
1. 增强 backend/app/schemas/task.py
   ├─ 创建 TaskCreateRequest schema
   │  ├─ source_type: Literal["upload", "url"]
   │  ├─ file: Optional[UploadFile]
   │  ├─ source_url: Optional[HttpUrl]
   │  ├─ output_formats: List[str] with validation
   │  └─ translate_target_langs: Optional[List[str]]
   ├─ 创建验证器 (Pydantic validator)
   │  ├─ 验证 output_formats 值有效
   │  ├─ 验证语言代码存在
   │  └─ 验证 source_type 和 file/url 匹配
   └─ 添加 AppError response schema

2. 扩展 backend/app/services/task_service.py
   ├─ TaskCreationService 类
   │  ├─ async validate_request(schema)
   │  ├─ async process_file_upload(file)
   │  └─ async create_with_validation(...)
   ├─ TaskQueryService 类
   │  ├─ async get_by_id(id)
   │  ├─ async list_for_user(user_id, filters)
   │  ├─ async list_for_admin(filters)
   │  └─ async get_queue_position(id)
   ├─ TaskMutationService 类
   │  ├─ async cancel(task_id)
   │  ├─ async delete(task_id)
   │  └─ async retry(task_id)
   └─ TaskAnalyticsService 类
      ├─ async count_guest_tasks_today(ip)
      ├─ async get_task_stats()
      └─ async get_user_stats(user_id)

3. 修改 backend/app/api/v1/tasks.py
   ├─ 使用新的 schema 类
   ├─ 注入服务依赖
   ├─ 简化端点逻辑（业务逻辑移到服务层）
   └─ 统一错误处理

4. 添加单元测试
   ├─ backend/tests/test_task_service.py (200 行)
   ├─ backend/tests/test_task_api.py (150 行)
   └─ 覆盖: 创建、验证、查询、删除、权限
```

**新增文件**：
- `backend/tests/test_task_service.py` (200 行)

**修改文件**：
- `backend/app/services/task_service.py` (105 -> 400 行)
- `backend/app/schemas/task.py` (增加 schema 定义)
- `backend/app/api/v1/tasks.py` (60% 代码移到服务层)

**验证方式**：
```bash
cd backend
uv run pytest tests/test_task_service.py -v
# 预期: 所有测试通过

# 功能测试
curl -X POST http://localhost:8765/api/v1/tasks \
  -F "source_type=invalid"  # 无效值
# 预期: 400 validation error

curl -X POST http://localhost:8765/api/v1/tasks \
  -F "source_type=upload" \
  -F "file=@test.mp4"
# 预期: 201 Created，task 创建成功
```

---

### 任务 2.2：Worker 稳定性加固

**问题现象**：
- `backend/app/worker/worker.py:38-61` 整个循环用一个宽泛的 `except Exception` 捕获
- 没有 graceful shutdown，`stop()` 方法调用后不等待
- 错误恢复太简单（只是 `await asyncio.sleep(5)` 继续）
- 进度追踪使用全局 dict + 线程锁，高并发下可能丢失更新

**影响范围**：
- `backend/app/worker/worker.py` (399 行)
- `backend/app/worker/whisper_runner.py` (进度追踪)
- `backend/run_worker.py` (Worker 进程启动)

**实现方案**：

```plaintext
1. 创建 backend/app/core/error_handling.py
   ├─ 装饰器 @handle_task_error
   │  ├─ 捕获 asyncio.CancelledError（graceful shutdown）
   │  ├─ 捕获 OutOfMemoryError（特殊处理）
   │  ├─ 捕获业务异常（设置任务为 failed）
   │  └─ 记录详细日志和堆栈跟踪
   ├─ 装饰器 @with_retry
   │  ├─ 指数退避 (1s, 2s, 4s, 8s)
   │  ├─ 最多重试 3 次
   │  └─ 支持 jitter 防止雷鸣羊群
   └─ 装饰器 @with_timeout
      └─ 设置最大执行时间，超时则 cancel

2. 改进 backend/app/worker/worker.py
   ├─ 使用 @handle_task_error 装饰 _process_task
   ├─ 改进 run() 循环
   │  ├─ 分开处理不同类型的异常
   │  ├─ ConnectionError 时指数退避
   │  ├─ OutOfMemoryError 时清理缓存后重试
   │  └─ 其他错误 log 并继续
   ├─ 实现正确的 graceful shutdown
   │  ├─ stop() 设置标志后等待当前任务
   │  ├─ 等待超时 30 秒后强制退出
   │  └─ cleanup_task 应被等待而不是忽略
   └─ 添加监控指标
      ├─ 处理的任务数
      ├─ 成功/失败比率
      └─ 平均处理时间

3. 改进进度追踪 backend/app/worker/whisper_runner.py
   ├─ 使用数据库而不是全局 dict 存储进度
   │  └─ 表 task_progress (task_id, progress, last_update)
   ├─ 定期清理过期进度（超过 1 小时的）
   └─ 支持分布式追踪（多个 Worker 实例）

4. 修改 backend/run_worker.py
   ├─ 添加信号处理 (SIGTERM, SIGINT)
   ├─ 优雅关闭（调用 worker.stop()）
   └─ 等待所有清理完成

5. 添加监控
   ├─ backend/app/api/v1/health.py 添加端点 /health/worker
   └─ 返回 worker 状态、处理速率、错误率
```

**新增文件**：
- `backend/app/core/error_handling.py` (150 行)
- `backend/app/models/task_progress.py` (SQLAlchemy 模型)

**修改文件**：
- `backend/app/worker/worker.py` (100 行变更)
- `backend/app/worker/whisper_runner.py` (50 行变更)
- `backend/run_worker.py` (30 行变更)
- `backend/app/api/v1/health.py` (40 行新增)

**验证方式**：
```bash
# 测试 graceful shutdown
docker compose up -d
sleep 5
docker compose exec worker kill -SIGTERM 1
# 观察 Worker 日志，应该看到"正在完成当前任务..."
# 然后任务完成，Worker 退出，不应该强制杀死

# 测试错误恢复
# 临时断开数据库，观察 Worker 是否指数退避重连
docker compose pause db
sleep 20
docker compose unpause db
# 预期: 看到"连接数据库失败，重试中..."然后恢复

# 测试监控端点
curl http://localhost:8765/api/v1/health/worker
# 预期: { "status": "running", "tasks_processed": 42, "success_rate": 0.95, ... }
```

---

### 任务 2.3：数据库查询优化

**问题现象**：
- SQLAlchemy 模型没有定义索引，查询可能全表扫描
- 列表接口可能 N+1 查询（获取任务列表时逐个查询用户）
- 没有查询优化指导，SELECT * 过度获取字段
- 连接池配置不合理

**影响范围**：
- `backend/app/models/*.py` (所有模型)
- `backend/app/database.py` (连接池配置)
- `backend/app/services/*.py` (查询)

**实现方案**：

```plaintext
1. 优化模型定义 backend/app/models/*.py
   ├─ Task 模型
   │  ├─ 添加索引: (status, created_at), (user_id, created_at)
   │  ├─ 添加索引: (queue_position), (client_ip, created_at)
   │  └─ 列字段定义 __to_dict__ 支持选择性返回
   ├─ User 模型
   │  ├─ 添加唯一索引: (username), (email)
   │  └─ 添加索引: (is_active, created_at)
   └─ TaskOutput 模型
      └─ 添加索引: (task_id, format_type)

2. 改进连接池 backend/app/database.py
   ├─ 设置 pool_size=10, max_overflow=20
   ├─ 设置 pool_recycle=3600 (1 小时回收)
   ├─ 启用 pool_pre_ping=True (连接健康检查)
   └─ 配置连接超时 connect_args={'timeout': 30}

3. 优化查询 backend/app/services/*.py
   ├─ TaskService.get_user_tasks()
   │  ├─ 使用 selectinload(Task.user) 预加载
   │  ├─ 使用 selectinload(Task.outputs) 预加载
   │  └─ 只选择需要的字段
   ├─ TaskService.get_task_outputs()
   │  └─ 直接查询，已经是最优
   └─ 其他列表接口同样优化

4. 添加查询监控
   ├─ 使用 SQLAlchemy event 记录缓慢查询
   ├─ 日志 SQL 执行时间 > 500ms
   └─ 提供 /admin/metrics/slow-queries 端点

5. 添加迁移 backend/alembic/versions/
   └─ migration: add_indexes_and_constraints.py
      ├─ 创建所有索引
      └─ 添加外键约束
```

**新增文件**：
- `backend/alembic/versions/{timestamp}_add_indexes.py` (100 行)

**修改文件**：
- `backend/app/models/*.py` (添加索引定义，+50 行)
- `backend/app/database.py` (连接池优化，+15 行)
- `backend/app/services/*.py` (查询优化，+80 行)

**验证方式**：
```bash
cd backend

# 运行迁移
uv run alembic upgrade head

# 检查索引是否创建
docker compose exec db psql -U subweaver -d subweaver \
  -c "\d subweaver_task"
# 应该看到新增的索引

# 性能测试：查询 1000 条任务
time curl http://localhost:8765/api/v1/admin/tasks?page=1&page_size=100
# 预期: 响应时间 < 100ms

# 运行测试
uv run pytest tests/test_task_service.py -v
# 预期: 所有查询速度变快，测试通过
```

---

### 任务 2.4：前端 API 集成测试

**问题现象**：
- 前端缺少集成测试，只有单元测试框架
- 没有 E2E 测试，手动测试容易遗漏
- 无法验证前后端交互

**影响范围**：
- `frontend/` 整体测试覆盖

**实现方案**：

```plaintext
1. 添加 Playwright E2E 测试框架
   ├─ npm install -D @playwright/test
   ├─ playwright.config.ts 配置
   └─ tests/ 目录

2. 编写核心场景测试 frontend/tests/e2e/
   ├─ 01-auth.spec.ts (200 行)
   │  ├─ 注册、登录、登出
   │  ├─ 会话过期处理
   │  └─ 记住我功能
   ├─ 02-task-creation.spec.ts (300 行)
   │  ├─ 上传文件
   │  ├─ 输入 URL
   │  ├─ 选择模型和格式
   │  ├─ 验证错误（文件太大、无效 URL）
   │  └─ 成功创建任务
   ├─ 03-task-monitoring.spec.ts (200 line)
   │  ├─ SSE 实时进度更新
   │  ├─ 任务列表自动刷新
   │  └─ 断网重连
   ├─ 04-admin-features.spec.ts (200 line)
   │  ├─ 用户管理
   │  ├─ 文件管理
   │  └─ 系统配置
   └─ 05-error-handling.spec.ts (150 line)
      ├─ 后端错误显示
      ├─ 网络错误处理
      └─ 超时重试

3. 添加单元测试
   ├─ frontend/tests/unit/lib/api.test.ts (150 line)
   │  ├─ 请求重试逻辑
   │  ├─ 错误处理
   │  └─ 请求队列
   └─ frontend/tests/unit/hooks/useTaskForm.test.ts (100 line)

4. 添加 CI/CD 测试任务
   └─ .github/workflows/test.yml
      ├─ 前端: npm run test:e2e
      ├─ 后端: pytest
      └─ 在 Pull Request 时自动运行
```

**新增文件**：
- `frontend/playwright.config.ts`
- `frontend/tests/e2e/01-auth.spec.ts` (200 行)
- `frontend/tests/e2e/02-task-creation.spec.ts` (300 行)
- `frontend/tests/e2e/03-task-monitoring.spec.ts` (200 行)
- `frontend/tests/e2e/04-admin-features.spec.ts` (200 行)
- `frontend/tests/e2e/05-error-handling.spec.ts` (150 行)
- `frontend/tests/unit/lib/api.test.ts` (150 行)
- `.github/workflows/test.yml` (50 行)

**修改文件**：
- `frontend/package.json` (添加 playwright 依赖)

**验证方式**：
```bash
# 本地运行测试
cd frontend
npm run test:e2e

# 运行特定测试
npm run test:e2e -- tests/e2e/02-task-creation.spec.ts

# 生成 HTML 报告
npx playwright show-report
```

---

### 任务 2.5：后端集成测试扩展

**问题现象**：
- 现有 95 行测试代码，覆盖率可能不够
- 缺少集成测试（真实数据库）
- 没有 fixture 重用，测试代码重复

**影响范围**：
- `backend/tests/` 目录

**实现方案**：

```plaintext
1. 改进测试框架 backend/tests/conftest.py
   ├─ 创建完整的 fixtures
   │  ├─ async_client (AsyncClient)
   │  ├─ db_session (AsyncSession)
   │  ├─ test_user (创建测试用户)
   │  ├─ test_admin (创建管理员)
   │  ├─ test_task (创建测试任务)
   │  └─ mock_llm (模拟 LLM 服务)
   ├─ 数据库自动清理（每个测试后）
   └─ 临时文件目录

2. 编写集成测试 backend/tests/integration/
   ├─ test_task_workflow.py (250 line)
   │  ├─ 完整任务生命周期
   │  ├─ 文件上传 -> 转录 -> 翻译 -> 下载
   │  └─ 权限检查、错误处理
   ├─ test_auth_workflow.py (150 line)
   │  ├─ 注册 -> 登录 -> token 刷新 -> 登出
   │  └─ 会话管理
   ├─ test_admin_workflow.py (200 line)
   │  ├─ 用户管理完整流程
   │  ├─ 文件管理完整流程
   │  └─ 配置管理完整流程
   ├─ test_error_handling.py (150 line)
   │  ├─ 各种错误场景
   │  └─ 边界条件
   └─ test_concurrent_tasks.py (150 line)
      ├─ 并发任务处理
      └─ 队列管理

3. 提高覆盖率目标
   ├─ 添加覆盖率报告
   ├─ 设置最低覆盖率 80%
   └─ 在 CI/CD 中检查

4. 性能测试 backend/tests/performance/
   ├─ test_file_upload_performance.py
   │  └─ 1GB 文件上传性能
   └─ test_concurrent_requests.py
      └─ 100 并发请求性能
```

**新增文件**：
- `backend/tests/integration/test_task_workflow.py` (250 行)
- `backend/tests/integration/test_auth_workflow.py` (150 行)
- `backend/tests/integration/test_admin_workflow.py` (200 行)
- `backend/tests/integration/test_error_handling.py` (150 line)
- `backend/tests/integration/test_concurrent_tasks.py` (150 line)
- `backend/tests/performance/test_upload.py` (100 line)
- `backend/pytest.ini` (配置覆盖率)

**修改文件**：
- `backend/tests/conftest.py` (大幅扩展)
- `pyproject.toml` (测试配置)

**验证方式**：
```bash
cd backend

# 运行所有测试
uv run pytest -v

# 生成覆盖率报告
uv run pytest --cov=app --cov-report=html
open htmlcov/index.html

# 运行特定测试
uv run pytest tests/integration/test_task_workflow.py -v
```

---

### 任务 2.6：API 文档完善

**问题现象**：
- FastAPI 自动生成 Swagger 文档，但缺少详细说明
- 没有 request/response 示例
- 错误响应文档不完整
- 安全认证文档不清楚

**影响范围**：
- 所有 API 端点（文档，不是代码）
- `backend/app/main.py`

**实现方案**：

```plaintext
1. 增强所有路由的文档注释
   ├─ 每个端点添加详细描述
   ├─ 添加 tags 分组
   ├─ 添加 examples
   └─ 标记 deprecated 端点

2. 统一响应格式文档
   ├─ 成功响应 200, 201 的格式
   ├─ 错误响应 400, 401, 403, 404, 429, 500 的格式
   └─ 在 OpenAPI schema 中定义

3. 生成 API 文档
   ├─ 导出 openapi.json
   ├─ 生成 markdown 文档
   └─ 发布到 wiki

4. 安全文档
   ├─ 说明 JWT 认证方式
   ├─ 说明 refresh token 流程
   └─ 说明各端点权限需求

实施例子（修改 backend/app/api/v1/tasks.py）:

```python
@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建转录任务",
    description="""
    创建新的音视频转录任务。支持本地文件上传或在线视频 URL。
    
    - 上传文件：source_type=upload，同时上传 file
    - 在线视频：source_type=url，提供 source_url（支持 YouTube 等）
    - 游客每天最多 3 个任务（可在后台配置）
    - 已登录用户无限制
    
    返回任务信息，status 为 "pending"，将进入队列等待处理。
    """,
    responses={
        201: {
            "description": "任务创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "id": "uuid-string",
                        "status": "pending",
                        "queue_position": 3,
                        ...
                    }
                }
            }
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "INVALID_FILE_TYPE",
                        "message": "文件类型不支持，仅支持音视频文件",
                    }
                }
            }
        },
    }
)
async def create_task(...):
    """实现代码..."""
```

**修改文件**：
- `backend/app/api/v1/*.py` (添加详细文档注释)
- `backend/app/main.py` (配置 OpenAPI 信息)

**验证方式**：
```bash
# 访问 Swagger UI
curl http://localhost:8765/docs

# 检查所有端点都有详细说明
# 检查 request/response 示例正确
# 验证错误响应文档完整
```

---

## 🟡 第三阶段：可维护性和监控（低优先级）

### 任务 3.1：结构化日志系统增强

**问题现象**：
- 现有日志使用 loguru，但没有结构化输出
- 缺少审计日志（谁做了什么）
- 性能慢的操作没有记录（用于诊断）

**实现方案**：

```plaintext
1. 创建 backend/app/core/structured_logging.py
   ├─ JSON 格式日志输出
   ├─ 添加上下文信息 (request_id, user_id, ip)
   └─ 日志分级：app.log, error.log, audit.log

2. 添加上下文中间件 backend/app/core/middleware.py
   ├─ 为每个请求生成 request_id (UUID)
   ├─ 记录请求开始和结束
   └─ 记录处理时间

3. 添加审计日志
   ├─ 谁修改了配置
   ├─ 谁删除了文件
   ├─ 谁取消了任务
   └─ 审计表 audit_log (table in DB)

4. 性能日志
   ├─ 记录 > 500ms 的数据库查询
   ├─ 记录 > 1s 的 API 端点
   └─ 记录 > 30s 的后台任务
```

**新增文件**：
- `backend/app/models/audit_log.py`
- `backend/alembic/versions/{timestamp}_create_audit_log.py`

**修改文件**：
- `backend/app/core/logging.py`
- 各个修改数据的端点

---

### 任务 3.2：监控和告警

**问题现象**：
- 缺少系统监控，无法及时发现问题
- 没有性能指标收集
- 错误率无法追踪

**实现方案**：

```plaintext
1. 添加 Prometheus 指标
   ├─ 请求数/错误数/响应时间
   ├─ 数据库连接池状态
   ├─ Worker 处理速率
   └─ 文件存储使用量

2. 创建指标端点
   ├─ /metrics (Prometheus 格式)
   ├─ /health/metrics (JSON 格式)
   └─ 包含上面的所有指标

3. 可视化仪表板
   ├─ 部署 Grafana
   ├─ 导入 Prometheus 数据
   └─ 创建关键指标仪表板

4. 告警规则
   ├─ 错误率 > 5% 告警
   ├─ 响应时间 > 5s 告警
   ├─ 队列等待时间 > 1h 告警
   └─ 存储使用量 > 90% 告警
```

**新增文件**：
- `backend/app/core/metrics.py`
- `docker-compose.monitoring.yml`

**修改文件**：
- `backend/app/main.py`
- `docker-compose.yml`

---

### 任务 3.3：日志查看优化

**问题现象**：
- 当前日志查看器比较基础
- 没有日志搜索和过滤
- 没有日志聚合（多个 worker 的日志混在一起）

**实现方案**：

```plaintext
1. 改进日志 API
   ├─ /logs?level=ERROR&task_id=xxx&since=2h
   ├─ 支持按 level、task_id、time range 过滤
   └─ 支持全文搜索（if elasticsearch integrated）

2. 改进前端日志查看器
   ├─ 搜索框
   ├─ 日志等级过滤
   ├─ 按任务关联日志
   └─ 导出日志（CSV、JSON）

3. 可选: 集成 ELK
   ├─ Elasticsearch 存储日志
   ├─ Kibana 查看和分析
   └─ 用于生产环境
```

---

### 任务 3.4：性能基准和优化

**问题现象**：
- 没有性能基准，不知道系统能处理多少负载
- 没有压力测试

**实现方案**：

```plaintext
1. 压力测试脚本 backend/tests/load/
   ├─ 并发上传文件
   ├─ 并发创建任务
   └─ 并发下载文件

2. 生成基准报告
   ├─ 最大吞吐量 (tasks/sec)
   ├─ p95/p99 响应时间
   └─ 内存/CPU 峰值

3. 优化建议
   ├─ 根据结果调整工作池大小
   ├─ 调整缓存大小
   └─ 考虑分片存储
```

---

### 任务 3.5：部署和基础设施

**问题现象**：
- Docker Compose 配置不够完善
- 没有资源限制
- 日志轮转配置在容器内，重启后丢失
- 没有备份策略

**实现方案**：

```plaintext
1. 完善 docker-compose.yml
   ├─ 添加资源限制 (memory, cpus)
   ├─ 添加卷挂载路径
   ├─ 添加环境变量说明
   └─ 添加 depends_on 依赖

2. 日志管理
   ├─ 使用 docker logdriver 
   ├─ 配置日志轮转
   └─ 发送到外部日志服务

3. 备份策略
   ├─ 定期备份数据库
   ├─ 定期备份输出文件
   └─ 定期备份配置

4. 部署文档
   ├─ 生成部署 checklist
   ├─ 写清故障排查步骤
   └─ 写清性能调优建议

5. Kubernetes 支持 (可选)
   ├─ 编写 Helm Chart
   ├─ 支持 HPA 自动扩展
   └─ 支持 rolling update
```

---

### 任务 3.6：开发者工具和流程

**问题现象**：
- 没有本地开发 hot reload
- 没有代码质量检查自动化
- Git hook 不完整

**实现方案**：

```plaintext
1. 本地开发优化
   ├─ 前端: npm run dev (已有)
   ├─ 后端: docker-compose -f docker-compose.dev.yml up
   └─ 自动重新加载

2. 代码质量工具
   ├─ 后端: black, flake8, mypy (自动修复)
   ├─ 前端: prettier, eslint (自动修复)
   └─ 集成 git pre-commit hook

3. Git workflow
   ├─ 提交前检查: lint, type-check, tests
   ├─ PR 模板
   └─ Conventional commits

4. 文档
   ├─ CONTRIBUTING.md
   ├─ DEVELOPMENT.md
   └─ ARCHITECTURE.md (系统设计文档)
```

**新增文件**：
- `CONTRIBUTING.md`
- `DEVELOPMENT.md`
- `ARCHITECTURE.md`
- `.pre-commit-config.yaml`
- `backend/Makefile`

---

## 📊 实施时间表

```
阶段 1 (关键修复) - 约 16 小时
├─ 1.1: 异常处理 (3h)
├─ 1.2: 文件验证 (2.5h)
├─ 1.3: SSE 修复 (2.5h)
├─ 1.4: 前端状态管理 (5h)
└─ 1.5: API 层增强 (3h)

阶段 2 (代码质量) - 约 20 小时
├─ 2.1: 任务服务架构 (4h)
├─ 2.2: Worker 稳定性 (4h)
├─ 2.3: 数据库优化 (3h)
├─ 2.4: 前端 E2E 测试 (5h)
├─ 2.5: 后端集成测试 (3h)
└─ 2.6: API 文档 (1h)

阶段 3 (可维护性) - 约 14 小时
├─ 3.1: 结构化日志 (2.5h)
├─ 3.2: 监控告警 (3.5h)
├─ 3.3: 日志查看优化 (2h)
├─ 3.4: 性能基准 (2h)
├─ 3.5: 部署优化 (2.5h)
└─ 3.6: 开发者工具 (1.5h)

总计: 约 50 小时 (约 1-2 周，取决于并行度和调试时间)
```

---

## ✅ 验证和质量检查

完成每个任务后的检查清单：

- [ ] 代码通过 linter 和 type-check
- [ ] 单元/集成测试全部通过，覆盖率不下降
- [ ] 本地 docker compose 能正常启动和运行
- [ ] 没有新增的性能回归
- [ ] 没有新增的安全漏洞
- [ ] API 文档更新
- [ ] 变更日志更新

---

## 🎯 预期收益

实施完整优化方案后，项目将获得：

| 维度 | 当前 | 优化后 |
|------|------|--------|
| **代码质量** | 中等 | 高（Sonarlint A 级） |
| **测试覆盖率** | ~60% | ~85% |
| **错误处理** | 不统一 | 统一且全面 |
| **性能** | 基础 | 优化（db 查询+50%） |
| **可维护性** | 中等 | 高（clear separation of concerns） |
| **监控** | 无 | Prometheus + Grafana |
| **开发效率** | 手动测试 | 自动化 CI/CD |
| **文档** | 基础 | 完整（API、部署、架构） |

---

## 📝 下一步

1. ✅ **确认方案** - 检查优先级和范围是否符合期望
2. ⏭️ **阶段 1 实施** - 开始执行关键修复
3. 📊 **进度追踪** - 每个任务完成后更新状态
4. 🔄 **迭代反馈** - 根据执行情况调整后续计划

