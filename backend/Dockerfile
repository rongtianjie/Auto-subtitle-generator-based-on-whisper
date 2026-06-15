FROM python:3.12-slim AS base

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright + Chromium（用于自动获取 B 站 cookies）
RUN pip install --no-cache-dir playwright && \
    playwright install --with-deps chromium 2>&1 | tail -5

# 复制代码
COPY . .

# 创建存储目录
RUN mkdir -p /app/storage/uploads /app/storage/outputs /app/storage/logs /app/models

# entrypoint 脚本
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
