#!/bin/bash
set -e

echo "========================================="
echo "  SubWeaver - Docker Entrypoint"
echo "========================================="

# 等待 PostgreSQL 就绪
echo "[1/2] 等待数据库就绪..."
for i in {1..30}; do
  if pg_isready -h postgres -U postgres > /dev/null 2>&1; then
    echo "✓ 数据库已就绪"
    break
  fi
  echo "等待中... ($i/30)"
  sleep 1
done

# 数据库迁移是可选的（skip for now）
echo "[2/2] 跳过数据库迁移（在应用启动时自动执行）"

# 启动应用
echo "⏳ 启动 Uvicorn 应用..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

