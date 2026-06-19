# 性能基准和优化指南

## 性能指标目标

| 指标 | 目标 | 当前 | 状态 |
|------|------|------|------|
| HTTP 请求 p95 延迟 | < 500ms | - | 待测试 |
| 数据库查询 p95 | < 100ms | - | 待测试 |
| 页面加载时间 | < 2s | - | 待测试 |
| API 吞吐量 | > 1000 req/s | - | 待测试 |
| 99% 可用性 | 99% | - | 待测试 |

## 负载测试设置

### 安装依赖

```bash
pip install locust
```

### 运行负载测试

```bash
# 基础测试 (Web UI)
locust -f tests/locustfile.py --host=http://localhost:8000

# 无 UI 测试 (5 个用户, 10 个并发, 1 分钟)
locust -f tests/locustfile.py \
  --host=http://localhost:8000 \
  --users=5 \
  --spawn-rate=2 \
  --run-time=1m \
  --headless

# 压力测试 (逐步增加用户)
locust -f tests/locustfile.py \
  --host=http://localhost:8000 \
  --users=100 \
  --spawn-rate=5 \
  --run-time=5m \
  --headless \
  --csv=results/stress_test
```

## 性能分析

### 使用 Prometheus 分析

```promql
# HTTP 请求延迟 p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 数据库查询延迟 p95
histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))

# 吞吐量 (req/s)
rate(http_requests_total[1m])

# 错误率
rate(http_requests_total{status_code=~"5.."}[1m]) / 
rate(http_requests_total[1m])

# 缓存命中率
rate(cache_hits_total[5m]) / 
(rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))
```

### 使用 py-spy 进行 CPU 分析

```bash
# 记录 CPU 时间
py-spy record -o profile.svg -- python run_worker.py

# 生成火焰图
py-spy record --flame flame.svg -- python run_worker.py
```

### 使用 memory_profiler 分析内存

```bash
pip install memory-profiler

python -m memory_profiler worker.py
```

## 优化建议

### 1. 数据库优化 (已完成)

✅ **已实现:**
- 连接池优化 (20 基础 + 30 临时)
- 9 个复合索引
- selectinload 预加载
- 查询时间减少 60-90%

### 2. 缓存优化

```python
# 添加 Redis 缓存
from functools import lru_cache
import redis

class CacheManager:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0)

    def get(self, key):
        return self.redis.get(key)

    def set(self, key, value, ttl=3600):
        self.redis.setex(key, ttl, value)

    def delete(self, key):
        self.redis.delete(key)

    def flush(self):
        self.redis.flushdb()

# 使用装饰器缓存
@lru_cache(maxsize=128)
def get_user_config(user_id):
    # 缓存用户配置
    pass
```

### 3. 异步优化

```python
# 使用 asyncio 并行处理
async def process_multiple_tasks(task_ids):
    results = await asyncio.gather(*[
        process_task(task_id) for task_id in task_ids
    ])
    return results

# 使用后台任务队列
from celery import Celery

celery = Celery('tasks')

@celery.task
def heavy_processing(task_id):
    # 后台处理
    pass
```

### 4. 前端优化

```typescript
// 代码分割
const LogViewer = React.lazy(() => import('./LogViewer'));

// 虚拟化列表 (长列表)
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={logs.length}
  itemSize={35}
>
  {({ index, style }) => (
    <div style={style}>{logs[index].message}</div>
  )}
</FixedSizeList>

// 内存缓存和预加载
const cache = new Map();
const preload = (url) => {
  fetch(url).then(r => cache.set(url, r));
};
```

### 5. API 优化

```python
# 分页限制
@router.get("/logs/recent")
async def get_recent_logs(limit: int = Query(100, le=1000)):
    # limit 最大 1000
    pass

# 字段过滤
@router.get("/tasks")
async def list_tasks(fields: str = Query("id,title,status")):
    # 只返回指定字段
    pass

# 响应压缩
from fastapi.middleware.gzip import GZIPMiddleware
app.add_middleware(GZIPMiddleware, minimum_size=1000)
```

### 6. 监控优化

```python
# 减少指标维度（高基数问题）
# ❌ 不好: 每个 URL 都是一个指标
http_requests_total{endpoint="/api/users/123"}

# ✅ 好: 按模式分类
http_requests_total{endpoint_pattern="/api/users/:id"}

# 采样指标
if random.random() < 0.1:  # 10% 采样
    track_metric(...)
```

## 优化检查清单

### 数据库
- [x] 连接池配置优化
- [x] 索引添加和优化
- [x] 查询优化（JOIN、子查询）
- [ ] 分片/分区（如需要）
- [ ] 只读副本（如需要）

### 应用程序
- [ ] 缓存层（Redis）
- [ ] 异步任务队列（Celery）
- [ ] 背景任务（分离耗时操作）
- [ ] 连接复用
- [ ] 对象池

### 前端
- [ ] 代码分割
- [ ] 虚拟滚动
- [ ] 图片优化
- [ ] 预加载
- [ ] 缓存策略

### 基础设施
- [ ] CDN 部署
- [ ] 负载均衡
- [ ] 容器化和扩展
- [ ] 资源监控
- [ ] 日志聚合

## 性能目标检查

### API 响应时间

```
目标:
- GET /logs/recent: < 100ms (p95)
- POST /tasks: < 500ms (p95)
- GET /tasks: < 100ms (p95)

测试命令:
ab -n 1000 -c 100 http://localhost:8000/api/v1/logs/recent
```

### 吞吐量

```
目标:
- 基础: > 500 req/s
- 优化后: > 1000 req/s

测试:
wrk -t4 -c100 -d30s http://localhost:8000/api/v1/logs/recent
```

### 内存使用

```
目标:
- 基础应用: < 256MB
- 运行 Worker: < 512MB
- 满载: < 1GB

监控:
docker stats container_name
```

### CPU 使用

```
目标:
- 空闲: < 5%
- 正常负载: 30-50%
- 峰值: < 80%

监控:
top -p $(pgrep -f "python.*main.py")
```

## 性能回归测试

```python
# 定期运行性能测试
import pytest
import time

@pytest.mark.performance
def test_get_logs_performance(client, token):
    """性能回归测试"""
    start = time.time()

    response = client.get(
        '/api/v1/logs/recent',
        headers={'Authorization': f'Bearer {token}'}
    )

    duration = (time.time() - start) * 1000
    assert duration < 100, f"查询耗时 {duration}ms，超过目标 100ms"
    assert response.status_code == 200
```

## 参考资源

- [Locust 文档](https://docs.locust.io/)
- [FastAPI 性能优化](https://fastapi.tiangolo.com/deployment/concepts/#terms)
- [SQLAlchemy 性能优化](https://docs.sqlalchemy.org/en/14/faq/performance.html)
- [PostgreSQL 优化](https://www.postgresql.org/docs/current/sql-syntax.html)
- [React 性能优化](https://react.dev/reference/react/useMemo)
