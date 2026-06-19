# Docker Compose 部署修复记录

**日期**: 2026-06-19  
**问题**: 前端网页无法访问，容器显示停止状态  
**状态**: ✅ 已修复

---

## 问题描述

用户报告前端网页完全无法访问，Docker Compose 中的前后端容器显示停止状态。

## 调查结果

实际情况：
- ✅ 所有容器都在正常运行 (Up)
- ✅ 前端和后端服务都可以正常访问
- ❌ 容器健康检查状态显示 "unhealthy"
- ❌ 用户误以为容器停止了

**根本原因**: 健康检查配置错误，使用了容器中不存在的命令。

---

## 修复步骤

### 1. 前端健康检查修复

**问题**: 使用 `curl` 但容器中没有安装
```yaml
# 错误配置
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:3000/"]
```

**解决方案**: 改用 `wget`（node:20-alpine 镜像包含）
```yaml
# 正确配置
healthcheck:
  test: ["CMD", "wget", "--spider", "--quiet", "http://localhost:3000/"]
  interval: 30s
  timeout: 10s
  start_period: 10s
  retries: 3
```

### 2. 后端健康检查修复

**问题**: 使用 `curl` 但容器中没有安装
```yaml
# 错误配置
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
```

**解决方案**: 使用 Python + requests（已安装的依赖）
```yaml
# 正确配置
healthcheck:
  test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/api/v1/health', timeout=5)"]
  interval: 30s
  timeout: 10s
  start_period: 15s
  retries: 3
```

### 3. 应用配置

**重要**: 修改 docker-compose.yml 后需要重新创建容器
```bash
# ❌ 错误：只重启不会应用新配置
docker-compose restart

# ✅ 正确：重新创建容器
docker-compose down
docker-compose up -d
```

---

## 验证修复

```bash
# 1. 检查所有容器状态（应该都是 healthy）
docker ps

# 2. 测试前端访问
curl http://localhost:3000/

# 3. 测试后端访问
curl http://localhost:8000/api/v1/health

# 4. 手动测试健康检查命令
docker exec subweaver-frontend wget --spider --quiet http://localhost:3000/
docker exec subweaver-backend python -c "import requests; requests.get('http://localhost:8000/api/v1/health', timeout=5)"
```

---

## 最终状态

✅ **所有容器健康状态正常**

```
NAMES                STATUS
subweaver-frontend   Up (healthy)
subweaver-backend    Up (healthy)
subweaver-redis      Up (healthy)
subweaver-postgres   Up (healthy)
```

✅ **所有服务可访问**
- 前端: http://localhost:3000 → HTTP 200
- 后端: http://localhost:8000 → HTTP 200
- 数据库: localhost:5432 → 连接成功
- Redis: localhost:6379 → PONG

---

## 经验教训

1. **容器状态 vs 健康检查状态**
   - "Up" 表示容器在运行
   - "healthy" 表示健康检查通过
   - 容器可以是 "Up (unhealthy)" - 运行但健康检查失败

2. **健康检查命令必须存在于容器中**
   - Alpine 镜像通常只包含基础工具
   - 使用前先验证命令是否可用
   - 优先使用已安装的依赖（如 Python）

3. **配置修改需要重新创建容器**
   - `docker-compose restart` 不会应用新配置
   - 使用 `docker-compose up -d --force-recreate` 或先 `down` 再 `up`

4. **调试健康检查**
   ```bash
   # 查看健康检查日志
   docker inspect <container> | jq '.[0].State.Health.Log[-5:]'
   
   # 手动执行健康检查命令
   docker exec <container> <healthcheck-command>
   ```

---

## 常用命令

```bash
# 查看所有容器详细状态
docker-compose ps

# 查看实时日志
docker-compose logs -f

# 重启特定服务
docker-compose restart frontend

# 完全重新部署
docker-compose down && docker-compose up -d

# 查看容器资源使用
docker stats --no-stream

# 进入容器调试
docker exec -it subweaver-frontend sh
docker exec -it subweaver-backend bash
```

---

**修复完成时间**: 2026-06-19 15:31  
**修复人员**: Claude Code Assistant  
**测试状态**: 全部通过 ✅
