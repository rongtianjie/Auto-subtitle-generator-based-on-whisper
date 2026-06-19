<p align="center">
  <img src="frontend/public/hero-banner.png" alt="SubWeaver — Banner" width="100%">
</p>

<h1 align="center">SubWeaver</h1>

<p align="center">
  <strong>A web-based audio/video transcription and subtitle generation service powered by OpenAI Whisper, featuring multi-language translation, online video downloading, user authentication, task queue management, and persistent log viewer.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react" alt="React">
  <img src="https://img.shields.io/badge/PostgreSQL-16+-4169E1?logo=postgresql" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Docker-compose-2496ED?logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

## Overview

SubWeaver is a modern, full-stack web application that leverages OpenAI Whisper to automatically transcribe speech from audio and video files into text and subtitles. It supports file uploads and online video URLs (YouTube, etc.), generates multiple output formats (TXT, SRT, VTT, bilingual SRT/VTT), and translates subtitles into various languages via an OpenAI-compatible LLM API.

Built with FastAPI + React + PostgreSQL, it features a clean dashboard, real-time progress streaming via SSE, user authentication, admin panel, persistent logging, and Docker Compose deployment for easy setup.

---

## Features

### 🎯 Core Capabilities
- **Multi-source input** — Upload local audio/video files or provide an online video URL (YouTube, etc.)
- **AI-powered transcription** — Multiple Whisper model sizes (`tiny`, `base`, `small`, `medium`, `large`) to balance speed and accuracy
- **Whisper model management** — View download status, download, and delete Whisper models directly from the web UI
- **Flexible output formats** — Plain text (TXT), standard subtitles (SRT, VTT), bilingual subtitles (SRT / VTT with original + translation)
- **Multi-language translation** — Translate subtitles into 11+ languages via OpenAI-compatible LLM (Chinese, Japanese, Korean, French, German, Spanish, Russian, Portuguese, Arabic, Thai, Vietnamese, and more)
- **Real-time progress** — Server-Sent Events (SSE) for live task progress updates

### 🛠 Platform Features
- **User authentication** — Register, login, JWT with access/refresh tokens, "Remember Me" and password saving support
- **Initial admin setup** — Guided first-run setup page at `/admin/setup` to create the initial administrator
- **Role-based access** — User and Admin roles with separate interfaces
- **Admin dashboard** — Task management, user management (toggle-active, delete, reset password), system configuration, file management (list, filter, sort, preview, download, soft/hard delete), health checks, statistics, LLM connection testing, and model list fetching
- **System log viewer** — Admin can view and stream real-time logs directly from the web UI
- **Guest mode** — Create transcription tasks without registration (limited quota)
- **Task cancellation** — Users can cancel their own queued or processing tasks; admins can cancel any task
- **Sequential task queue** — Fair queue with estimated wait times, real-time position updates
- **Health check system** — Automatic startup verification of database, ffmpeg, Whisper model, and LLM connection
- **Configurable file retention** — Auto-cleanup of expired files
- **Docker Compose deployment** — One-command setup with all dependencies

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy (async), Alembic |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS 4, Radix UI |
| **Database** | PostgreSQL 16 |
| **AI/ML** | OpenAI Whisper, OpenAI-compatible LLM API |
| **Media** | ffmpeg, yt-dlp |
| **Infra** | Docker, Docker Compose |
| **Testing** | pytest, pytest-cov, httpx, pytest-asyncio |

---

## Quick Start

### Docker Compose (Only Supported Method)

```bash
# Clone the repository
git clone https://github.com/rongtianjie/SubWeaver.git
cd SubWeaver

# Copy environment configuration for Docker Compose
cp .env.example .env

# Start the default core services
docker compose up -d

# Open http://localhost:3000 in your browser
```

The frontend is available at `http://localhost:3000`. The backend API is available at `http://localhost:8000`, and the API documentation is at `http://localhost:8000/docs`.

To also start the background worker and monitoring stack, use:

```bash
docker compose --profile full up -d
```

> **Note:** This project **only supports Docker Compose deployment**. Manual/native setup is no longer supported.

### Services

| Service | Port | Description |
|---------|------|-------------|
| **Frontend (Nginx)** | `3000` | Web UI |
| **Backend (FastAPI)** | `8000` | REST API + SSE streams |
| **Worker** | — | Background task processor (Whisper transcription, translation, `full` profile only) |
| **Database (PostgreSQL)** | `5432` | Primary data store |
| **Prometheus** | `9090` | Metrics dashboard (`full` / `monitoring` profile only) |
| **Grafana** | `3001` | Monitoring UI (`full` / `monitoring` profile only) |

### Environment Variables

Copy `.env.example` to `.env` and adjust the following key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `change-me-in-production` | JWT signing key (change in production!) |
| `LLM_BASE_URL` | `http://host.docker.internal:8000/v1` | OpenAI-compatible LLM API endpoint for translation |
| `LLM_API_KEY` | `your-api-key` | LLM API key |
| `LLM_MODEL` | `gpt-3.5-turbo` | LLM model name |
| `DB_PASSWORD` | `change-me-in-production` | PostgreSQL password |
| `MAX_FILE_SIZE_MB` | via backend config | Maximum upload file size |
| `RETENTION_DAYS` | via backend config | File retention period |
| `WORKER_POLL_INTERVAL` | `5` | Worker polling interval in seconds |
| `CORS_ORIGINS` | `http://localhost:3000,http://example.com` | Allowed CORS origins for the frontend |

---

## API Overview

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/v1/auth/register` | Register a new user | No |
| `POST` | `/api/v1/auth/login` | Login | No |
| `POST` | `/api/v1/auth/refresh` | Refresh access token | Refresh token |
| `GET` | `/api/v1/auth/me` | Get current user info | JWT |
| `GET` | `/api/v1/auth/admin-exists` | Check if an admin exists in the system | No |
| `POST` | `/api/v1/auth/register-admin` | Register the initial admin (only when none exists) | No |
| `GET` | `/api/v1/tasks/defaults` | Get default task creation config (model, etc.) | No |
| `POST` | `/api/v1/tasks` | Create a transcription task (upload or URL) | Optional (guest) |
| `GET` | `/api/v1/tasks` | List user tasks | JWT |
| `GET` | `/api/v1/tasks/{id}` | Get task details | No |
| `PUT` | `/api/v1/tasks/{id}/cancel` | Cancel own queued/processing task | Optional (guest) |
| `DELETE` | `/api/v1/tasks/{id}` | Delete a task | JWT |
| `GET` | `/api/v1/tasks/{id}/stream` | SSE real-time progress | No |
| `GET` | `/api/v1/tasks/{id}/outputs` | List task outputs | No |
| `GET` | `/api/v1/tasks/{id}/outputs/{oid}/download` | Download output file | No |
| `GET` | `/api/v1/tasks/queue` | Get queue status | No |
| `GET` | `/api/v1/files` | List uploaded files | JWT |
| `DELETE` | `/api/v1/files/{filename}` | Delete an uploaded file | JWT |
| `GET` | `/api/v1/health` | Basic health check | No |
| `GET` | `/api/v1/health/ready` | Readiness check with all services | No |
| `GET` | `/api/v1/admin/stats` | Platform statistics | Admin |
| `GET` | `/api/v1/admin/health` | Detailed health check of all subsystems | Admin |
| `GET` | `/api/v1/admin/tasks` | List all tasks | Admin |
| `DELETE` | `/api/v1/admin/tasks/{id}` | Delete any task | Admin |
| `PUT` | `/api/v1/admin/tasks/{id}/cancel` | Cancel a queued/processing task | Admin |
| `PUT` | `/api/v1/admin/tasks/{id}/retry` | Retry a failed task | Admin |
| `GET` | `/api/v1/admin/users` | List all users (search, paginate) | Admin |
| `PUT` | `/api/v1/admin/users/{id}/role` | Update user role | Admin |
| `PUT` | `/api/v1/admin/users/{id}/toggle-active` | Enable/disable user | Admin |
| `DELETE` | `/api/v1/admin/users/{id}` | Delete user (tasks preserved) | Admin |
| `POST` | `/api/v1/admin/users/{id}/reset-password` | Reset user to random 6-char password | Admin |
| `GET` | `/api/v1/admin/users/{id}/tasks` | List specific user's tasks | Admin |
| `GET` | `/api/v1/admin/files` | List all files (upload, output, orphan) with filter/sort | Admin |
| `DELETE` | `/api/v1/admin/files` | Delete files (soft/hard mode) | Admin |
| `GET` | `/api/v1/admin/files/{file_id}/download` | Download any file | Admin |
| `GET` | `/api/v1/admin/files/{file_id}/preview` | Preview file content (text) or stream (media) | Admin |
| `GET` | `/api/v1/admin/config` | Get system config | Admin |
| `PUT` | `/api/v1/admin/config/{key}` | Update system config | Admin |
| `POST` | `/api/v1/admin/llm/test` | Test LLM connection and latency | Admin |
| `POST` | `/api/v1/admin/llm/fetch-models` | Fetch available models from LLM backend | Admin |
| `GET` | `/api/v1/admin/logs` | List available log files | Admin |
| `GET` | `/api/v1/admin/logs/{filename}` | Read log file content | Admin |
| `GET` | `/api/v1/admin/logs/{filename}/stream` | SSE real-time log stream | Admin |

| `GET` | `/api/v1/models` | List all Whisper models with download status | No |
| `POST` | `/api/v1/models/{name}/download` | Download a Whisper model | Admin |
| `DELETE` | `/api/v1/models` | Delete all downloaded Whisper models | Admin |

Full API documentation is available at `/docs` when the backend is running.

---

## System Logging

The service uses **loguru** for structured logging with three output targets:

| Target | Path | Description |
|--------|------|-------------|
| **stdout** | Docker logs | Colorized console output via `docker logs` |
| **app.log** | `/app/storage/logs/app.log` | All log levels, rotated daily (30 days retention, gzip compressed) |
| **error.log** | `/app/storage/logs/error.log` | Only ERROR level, same rotation policy |

### Web Log Viewer

Administrators can view logs directly from the web UI via the **System Logs** tab in the admin panel:

- **Historical logs** — Select a log file from the left sidebar to view its contents
- **Real-time streaming** — Click "实时日志" to tail the log file via SSE and watch new entries appear live
- **Auto-scroll** — Automatically scrolls when near the bottom; disable to browse freely

### Log API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/v1/admin/logs` | List available log files | Admin |
| `GET` | `/api/v1/admin/logs/{filename}` | Read log file content (optional `?tail=N` parameter) | Admin |
| `GET` | `/api/v1/admin/logs/{filename}/stream` | SSE real-time log stream | Admin |

---

## Testing

The project includes 82 test cases across 8 test modules with comprehensive coverage:

```bash
cd backend

# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=app --cov-report=term

# Generate HTML coverage report
uv run pytest --cov=app --cov-report=html
```

**Test coverage**:
- **Security** — Password hashing, JWT generation/validation/expiry
- **Schema validation** — Auth, task, and admin Pydantic schemas
- **Startup checker** — Check engine registration, execution, report output
- **File storage** — Upload, download, cleanup, multi-task isolation
- **Task queue** — Enqueue, dequeue, position calculation, average duration
- **Utility functions** — Video-to-audio conversion, SRT read/write, translation
- **API endpoints** — Register, login, token refresh, user info, root path

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST API endpoints
│   │   ├── core/            # Security, storage, task queue, logging
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic services
│   │   ├── worker/          # Background task worker
│   │   └── startup_checker/ # System health checks
│   ├── tests/               # Test suite
│   ├── alembic/             # Database migrations
│   └── docker-entrypoint.sh # Docker container entrypoint
├── frontend/
│   ├── src/
│   │   ├── components/      # UI components
│   │   ├── pages/           # Page views
│   │   ├── hooks/           # Custom React hooks
│   │   ├── lib/             # Utilities and API client
│   │   └── types/           # TypeScript types
│   └── public/              # Static assets
├── storage/                 # File storage (uploads, outputs, logs)
├── docker-compose.yml       # Production deployment
├── docker-compose.dev.yml   # Development database
├── run_worker.py            # Worker process entrypoint (used by Worker container)
├── .env.example             # Docker Compose environment template
└── backend/.env.example     # Backend-only environment template
```

---

## License

[MIT](LICENSE)
