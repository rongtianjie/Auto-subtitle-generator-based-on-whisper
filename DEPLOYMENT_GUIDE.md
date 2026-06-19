# 部署和基础设施优化指南

## Docker 快速启动

### 前置条件
- Docker >= 20.10
- Docker Compose >= 2.0
- 至少 4GB 内存
- 至少 10GB 磁盘空间

### 部署步骤

```bash
# 1. 克隆仓库
git clone <repository-url>
cd SubWeaver

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，修改敏感配置

# 3. 启动默认核心服务
docker compose up -d

# 4. 检查服务状态
docker compose ps
docker compose logs -f backend

# 5. 如需完整栈（worker + Prometheus + Grafana）
docker compose --profile full up -d

# 6. 访问应用
# 前端: http://localhost:3000
# API: http://localhost:8000
# Grafana: http://localhost:3001
# Prometheus: http://localhost:9090
```

默认 `docker compose up -d` 只会启动 `postgres`、`redis`、`backend`、`frontend` 四个核心服务；`worker`、`prometheus`、`grafana` 需要显式启用 profile。

### 容器架构

```
┌─────────────────────────────────────────┐
│         Nginx/Reverse Proxy             │
│         (或 Docker 网络)                 │
└───────────────┬─────────────────────────┘
                │
    ┌───────────┴────────────────────┬──────────────┐
    │                                │              │
┌───▼───┐                      ┌────▼────┐    ┌────▼────┐
│Frontend│                     │ Backend  │    │ Worker   │
│:3000   │                     │ :8000    │    │ (async)  │
└───┬───┘                      └────┬────┘    └────┬────┘
    │                               │             │
    │           ┌───────────────────┼─────────────┘
    │           │                   │
┌───▼───┐  ┌───▼────┐  ┌───────┐  ┌▼────────┐
│ Redis │  │Postgres│  │Prometheus│ Grafana│
│:6379  │  │:5432   │  │:9090     │:3001  │
└───────┘  └────────┘  └─────────┘ └───────┘
```

## Kubernetes 部署

### 前置条件
- Kubernetes >= 1.20
- kubectl 已配置
- Helm >= 3.0

### 部署步骤

```bash
# 1. 创建命名空间
kubectl create namespace subweaver

# 2. 创建 Secret
kubectl create secret generic subweaver-secret \
  --from-literal=db-password=your-password \
  --from-literal=secret-key=your-secret \
  -n subweaver

# 3. 应用配置和 PVC
kubectl apply -f k8s/namespaces/
kubectl apply -f k8s/storage/
kubectl apply -f k8s/config/

# 4. 部署数据库 (PostgreSQL + Redis)
kubectl apply -f k8s/database/

# 5. 部署应用
kubectl apply -f k8s/backend/
kubectl apply -f k8s/frontend/
kubectl apply -f k8s/worker/

# 6. 部署监控
kubectl apply -f k8s/monitoring/

# 7. 创建 Ingress
kubectl apply -f k8s/ingress/

# 8. 验证部署
kubectl get pods -n subweaver
kubectl get svc -n subweaver
kubectl logs -f deployment/backend -n subweaver
```

### Kubernetes 资源配置示例

```yaml
---
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: subweaver
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: subweaver-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: subweaver-secret
              key: db-url
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
# backend-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: subweaver
spec:
  selector:
    app: backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP

---
# horizontal-pod-autoscaler.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: subweaver
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## CI/CD 流水线

### GitHub Actions 示例

```yaml
name: Build and Deploy

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker images
        run: |
          docker build -f Dockerfile.backend -t subweaver-backend:${{ github.sha }} .
          docker build -f Dockerfile.frontend -t subweaver-frontend:${{ github.sha }} .
      
      - name: Push to registry
        env:
          REGISTRY: ghcr.io
        run: |
          echo ${{ secrets.GITHUB_TOKEN }} | docker login $REGISTRY -u $ --password-stdin
          docker tag subweaver-backend:${{ github.sha }} $REGISTRY/${{ github.repository }}/backend:latest
          docker push $REGISTRY/${{ github.repository }}/backend:latest
      
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/backend backend=ghcr.io/${{ github.repository }}/backend:${{ github.sha }} -n subweaver

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Run tests
        run: |
          cd backend
          uv sync --extra dev
          uv run pytest tests -v --cov=app
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

## 监控和告警

### 关键监控指标

```yaml
# rules.yml
groups:
  - name: application
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status_code=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "高错误率告警"
          description: "{{ $labels.endpoint }} 错误率 > 5%"

      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 1
        for: 5m
        annotations:
          summary: "高延迟告警"
          description: "p95 延迟 > 1s"

      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        annotations:
          summary: "数据库连接失败"
```

## 维护和升级

### 数据库备份

```bash
# 定期备份 PostgreSQL
docker compose exec postgres pg_dump -U postgres subweaver > backup.sql

# 恢复数据库
docker compose exec -T postgres psql -U postgres subweaver < backup.sql
```

### 日志管理

```bash
# 查看服务日志
docker compose logs -f backend
docker compose logs -f worker

# 清理日志
docker compose down -v
```

### 升级应用

```bash
# 1. 构建新镜像
docker compose build --no-cache

# 2. 更新容器
docker compose up -d

# 4. 检查健康状态
docker compose ps
```

## 安全建议

1. **环境变量**: 使用 `.env` 文件管理敏感配置，永远不要提交到版本控制
2. **镜像安全**: 定期更新基础镜像，扫描漏洞
3. **网络**: 使用专用网络隔离容器，限制端口暴露
4. **认证**: 启用 HTTPS，使用强密钥
5. **备份**: 定期备份数据库，测试恢复流程
6. **监控**: 设置告警，监控异常情况
7. **更新**: 定期更新依赖包和镜像

## 参考资源

- [Docker 文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Kubernetes 文档](https://kubernetes.io/docs/)
- [Helm 文档](https://helm.sh/docs/)
