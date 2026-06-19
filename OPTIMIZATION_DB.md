"""
数据库查询优化总结

本次优化涵盖以下改进：

1. 连接池优化
   - 生产环境使用 QueuePool（基础 20 连接，最多 50）
   - 开发环境使用 NullPool（避免调试时连接占用）
   - 启用 pool_recycle=3600（防止数据库强制断开）
   - autoflush=False 显式控制刷新时机

2. 新增索引（6 个复合索引）
   - idx_tasks_status_position: 队列查询优化
   - idx_tasks_user_created: 用户任务列表查询
   - idx_tasks_created_at: 时间排序和过期清理
   - idx_tasks_client_ip_created: 游客日限制检查
   - idx_tasks_completed_at: 分析报表查询
   - idx_tasks_status_created: 按状态过滤列表
   
   TaskOutput 表新增：
   - idx_task_outputs_task_id: FK 查询优化
   - idx_task_outputs_format_type: 格式过滤
   - idx_task_outputs_language_pair: 语言对过滤

3. 查询优化
   - selectinload(Task.outputs): 预加载避免 N+1 查询
   - 利用复合索引加速 offset/limit 分页
   - get_by_status() 新方法：快速获取特定状态任务（Worker 用）

4. 数据库维护工具（db_optimizer.py）
   - analyze_tables(): 更新表统计（PostgreSQL）
   - vacuum_tables(): 清理死行和回收空间
   - get_index_stats(): 索引利用率监控
   - get_slow_queries(): 慢查询诊断
   - get_table_stats(): 表统计信息

5. 新增健康检查端点
   - GET /health/db-stats: 查看数据库统计
   - POST /health/db-analyze: 更新统计信息（管理员）
   - POST /health/db-vacuum: 清理死行（管理员）

预期性能改进：
✓ 队列查询减少 60-80%（从表扫描 → 索引范围扫描）
✓ 用户任务列表查询减少 70-90%（复合索引覆盖）
✓ 游客日限制检查减少 50-70%（索引范围扫描）
✓ 分页查询加速 3-5 倍（更高效的索引扫描）
✓ 避免 N+1 查询（selectinload 预加载）

迁移步骤（如果使用 Alembic）：
1. 创建迁移：alembic revision --autogenerate -m "add database indices"
2. 查看迁移：alembic upgrade head
3. 运行优化：POST /health/db-analyze （生产环境需管理员权限）

直接SQL迁移（不使用 ORM）：
CREATE INDEX idx_tasks_client_ip_created ON tasks(client_ip, created_at);
CREATE INDEX idx_tasks_completed_at ON tasks(completed_at);
CREATE INDEX idx_tasks_status_created ON tasks(status, created_at);
CREATE INDEX idx_task_outputs_task_id ON task_outputs(task_id);
CREATE INDEX idx_task_outputs_format_type ON task_outputs(format_type);
CREATE INDEX idx_task_outputs_language_pair ON task_outputs(language_pair);
ANALYZE;
"""
