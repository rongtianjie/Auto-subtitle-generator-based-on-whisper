.PHONY: help install test lint format clean docker docker-up docker-down

help:
	@echo "SubWeaver 项目命令"
	@echo ""
	@echo "开发命令:"
	@echo "  make install      - 安装开发依赖"
	@echo "  make test         - 运行所有测试"
	@echo "  make test-unit    - 运行单元测试"
	@echo "  make test-int     - 运行集成测试"
	@echo "  make test-cov     - 运行测试并生成覆盖率报告"
	@echo "  make lint         - 代码检查"
	@echo "  make format       - 代码格式化"
	@echo "  make format-check - 检查代码格式"
	@echo "  make security     - 安全检查"
	@echo "  make type-check   - 类型检查"
	@echo ""
	@echo "Docker 命令:"
	@echo "  make docker       - 构建 Docker 镜像"
	@echo "  make docker-up    - 启动容器 (docker compose)"
	@echo "  make docker-down  - 停止容器"
	@echo "  make docker-logs  - 查看容器日志"
	@echo ""
	@echo "数据库命令:"
	@echo "  make db-migrate   - 运行数据库迁移"
	@echo "  make db-downgrade - 回滚数据库迁移"
	@echo "  make db-reset     - 重置数据库"
	@echo ""
	@echo "清理命令:"
	@echo "  make clean        - 清理临时文件"

# 安装
install:
	cd backend && uv sync --extra dev
	cd frontend && npm install
	pre-commit install

# 测试
test:
	cd backend && pytest -v

test-unit:
	cd backend && pytest -v -m unit

test-int:
	cd backend && pytest -v -m integration

test-e2e:
	cd frontend && npm run test:e2e

test-cov:
	cd backend && pytest -v --cov=app --cov-report=html --cov-report=term-missing
	@echo "覆盖率报告: backend/htmlcov/index.html"

# 代码质量
lint:
	cd backend && flake8 app tests
	cd backend && mypy app
	cd frontend && npm run lint

format:
	cd backend && black app tests
	cd backend && isort app tests
	cd frontend && npx prettier --write src

format-check:
	cd backend && black --check app tests
	cd backend && isort --check-only app tests
	cd frontend && npx prettier --check src

security:
	cd backend && bandit -r app
	cd frontend && npm audit

type-check:
	cd backend && mypy app

# Docker
docker:
	docker build -f docker/Dockerfile.backend -t subweaver-backend:latest .
	docker build -f docker/Dockerfile.frontend -t subweaver-frontend:latest .

docker-up:
	docker compose up -d
	@echo "容器已启动"
	@echo "前端: http://localhost:3000"
	@echo "API: http://localhost:8000"
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3001"

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-logs-backend:
	docker compose logs -f backend

docker-logs-worker:
	docker compose logs -f worker

# 数据库
db-migrate:
	cd backend && python -m alembic upgrade head

db-downgrade:
	cd backend && python -m alembic downgrade -1

db-reset:
	cd backend && python -m alembic downgrade base
	cd backend && python -m alembic upgrade head

db-revision:
	@read -p "Enter migration name: " name; \
	cd backend && python -m alembic revision --autogenerate -m "$$name"

# Kubernetes
k8s-apply:
	kubectl apply -f k8s/namespaces/
	kubectl apply -f k8s/storage/
	kubectl apply -f k8s/config/
	kubectl apply -f k8s/database/
	kubectl apply -f k8s/backend/
	kubectl apply -f k8s/frontend/
	kubectl apply -f k8s/worker/
	kubectl apply -f k8s/monitoring/
	kubectl apply -f k8s/ingress/

k8s-delete:
	kubectl delete namespace subweaver

k8s-status:
	kubectl get pods -n subweaver
	kubectl get services -n subweaver

k8s-logs-backend:
	kubectl logs -f deployment/backend -n subweaver

# 清理
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".pytest_cache" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
