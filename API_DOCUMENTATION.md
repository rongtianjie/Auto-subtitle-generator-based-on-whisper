"""
API 文档

# Whisper 自动字幕生成平台 API

## 基本信息

- **Base URL**: `http://localhost:8000/api/v1`
- **协议**: HTTP/HTTPS
- **内容类型**: JSON, Multipart Form Data
- **认证**: Bearer Token (JWT)
- **文档**: [Swagger UI](http://localhost:8000/docs) / [ReDoc](http://localhost:8000/redoc)

## 概述

本 API 提供完整的音视频转录和翻译功能，支持：
- ✓ 本地文件上传
- ✓ YouTube/其他视频源 URL
- ✓ 多种输出格式 (TXT, SRT, VTT)
- ✓ 多语言翻译
- ✓ 实时进度流 (SSE)
- ✓ 批量任务管理

## 认证

所有需要认证的端点需要在请求头中包含 Bearer Token:

```
Authorization: Bearer <your_jwt_token>
```

### 获取 Token

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123"
}
```

**响应:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "username": "user@example.com",
    "email": "user@example.com"
  }
}
```

## 错误响应

所有错误响应遵循统一格式:

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "参数验证失败",
  "timestamp": "2026-06-19T12:34:56Z",
  "details": {
    "field": "error message"
  }
}
```

### 错误代码

| Code | HTTP | 说明 | 处理建议 |
|------|------|------|--------|
| `VALIDATION_ERROR` | 400 | 参数验证失败 | 检查请求参数 |
| `AUTHENTICATION_FAILED` | 401 | 认证失败 | 重新登录获取 Token |
| `TOKEN_EXPIRED` | 401 | Token 已过期 | 刷新 Token 或重新登录 |
| `FORBIDDEN` | 403 | 无权限访问 | 检查用户权限 |
| `NOT_FOUND` | 404 | 资源不存在 | 检查资源 ID |
| `FILE_TOO_LARGE` | 413 | 文件过大 | 文件需 < 2GB |
| `UNSUPPORTED_FORMAT` | 415 | 不支持的格式 | 检查文件格式 |
| `RATE_LIMITED` | 429 | 请求过于频繁 | 等待后重试 |
| `INTERNAL_ERROR` | 500 | 服务器错误 | 联系支持 |
| `SERVICE_UNAVAILABLE` | 503 | 服务暂时不可用 | 稍后重试 |

## 端点文档

### 任务管理

#### 创建任务

**请求:**
```http
POST /tasks
Content-Type: multipart/form-data

source_type=upload
title=My Video
whisper_model=base
output_formats=srt&output_formats=vtt
translate_target_langs=zh&translate_target_langs=ja
file=@video.mp4
```

**或使用 JSON (URL 模式):**
```http
POST /tasks
Content-Type: application/json

{
  "source_type": "url",
  "source_url": "https://youtube.com/watch?v=...",
  "title": "YouTube Video",
  "whisper_model": "base",
  "output_formats": ["srt", "vtt"],
  "translate_target_langs": ["zh", "ja"]
}
```

**参数:**

| 参数 | 类型 | 必需 | 说明 | 示例 |
|------|------|------|------|------|
| source_type | string | ✓ | 数据源: `upload` 或 `url` | upload |
| title | string | - | 任务标题 (max 255) | My Video |
| file | file | ✓ (upload) | 音视频文件 | video.mp4 |
| source_url | string | ✓ (url) | 视频 URL | https://youtube.com/... |
| whisper_model | string | ✓ | 模型: tiny/base/small/medium/large | base |
| output_formats | array | - | 输出格式: txt/srt/vtt | ["srt", "vtt"] |
| translate_target_langs | array | - | 翻译语言代码 | ["zh", "ja", "ko"] |

**响应 (201 Created):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "My Video",
  "source_type": "upload",
  "source_filename": "video.mp4",
  "whisper_model": "base",
  "output_formats": ["srt", "vtt"],
  "translate_target_langs": ["zh", "ja"],
  "status": "pending",
  "progress": 0,
  "queue_position": 5,
  "estimated_seconds": 120,
  "created_at": "2026-06-19T12:34:56Z"
}
```

**错误响应:**
- 400: 验证失败 (缺少参数、无效格式)
- 401: 未认证
- 413: 文件过大
- 429: 请求过于频繁

---

#### 获取任务列表

**请求:**
```http
GET /tasks?page=1&page_size=20&status=processing
Authorization: Bearer <token>
```

**参数:**

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | integer | 1 | 页码 |
| page_size | integer | 20 | 每页数量 (max 100) |
| status | string | - | 过滤状态: pending/processing/completed/failed/cancelled |

**响应 (200 OK):**
```json
{
  "tasks": [
    {
      "id": "uuid",
      "title": "Video 1",
      "source_type": "upload",
      "status": "processing",
      "progress": 0.45,
      "progress_message": "正在进行语音识别...",
      "queue_position": null,
      "estimated_seconds": 60,
      "created_at": "2026-06-19T12:00:00Z",
      "started_at": "2026-06-19T12:05:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

---

#### 获取单个任务

**请求:**
```http
GET /tasks/{task_id}
Authorization: Bearer <token>
```

**响应 (200 OK):**
```json
{
  "id": "uuid",
  "title": "My Video",
  "source_type": "upload",
  "source_filename": "video.mp4",
  "whisper_model": "base",
  "status": "completed",
  "progress": 1.0,
  "output_formats": ["srt", "vtt"],
  "translate_target_langs": ["zh"],
  "created_at": "2026-06-19T12:00:00Z",
  "started_at": "2026-06-19T12:05:00Z",
  "completed_at": "2026-06-19T12:10:00Z"
}
```

**错误响应:**
- 404: 任务不存在
- 401: 未认证
- 403: 无权限访问

---

#### 更新任务进度 (仅 Worker/Admin)

**请求:**
```http
PATCH /tasks/{task_id}
Content-Type: application/json
Authorization: Bearer <token>

{
  "progress": 0.75,
  "progress_message": "正在翻译字幕..."
}
```

**响应 (200 OK):**
```json
{
  "id": "uuid",
  "progress": 0.75,
  "progress_message": "正在翻译字幕..."
}
```

---

#### 取消任务

**请求:**
```http
POST /tasks/{task_id}/cancel
Authorization: Bearer <token>
```

**响应 (200 OK):**
```json
{
  "id": "uuid",
  "status": "processing",
  "cancel_requested": true,
  "progress_message": "正在等待当前阶段结束..."
}
```

**错误响应:**
- 404: 任务不存在
- 400: 任务已完成/已失败，无法取消

---

#### 删除任务

**请求:**
```http
DELETE /tasks/{task_id}
Authorization: Bearer <token>
```

**响应 (204 No Content)** - 无响应体

**错误响应:**
- 404: 任务不存在
- 401: 未认证

---

### 任务输出

#### 获取任务输出列表

**请求:**
```http
GET /tasks/{task_id}/outputs
Authorization: Bearer <token>
```

**响应 (200 OK):**
```json
[
  {
    "id": "uuid",
    "task_id": "uuid",
    "format_type": "srt",
    "file_path": "/files/task_uuid/subtitles.srt",
    "file_size": 12345,
    "created_at": "2026-06-19T12:10:00Z"
  },
  {
    "id": "uuid",
    "task_id": "uuid",
    "format_type": "bilingual_srt",
    "language_pair": "en-zh",
    "file_path": "/files/task_uuid/subtitles-zh.srt",
    "file_size": 23456,
    "created_at": "2026-06-19T12:15:00Z"
  }
]
```

---

#### 下载输出文件

**请求:**
```http
GET /tasks/{task_id}/outputs/{output_id}/download
Authorization: Bearer <token>
```

**响应 (200 OK)** - 文件二进制内容

**Header:**
```
Content-Type: text/plain; charset=utf-8
Content-Disposition: attachment; filename="subtitles.srt"
```

---

### 实时进度流 (SSE)

#### 订阅任务进度

**请求:**
```http
GET /tasks/{task_id}/stream
Accept: text/event-stream
Authorization: Bearer <token>
```

**响应 (200 OK):**
```
Content-Type: text/event-stream
Transfer-Encoding: chunked

data: {"status":"processing","progress":0.0,"message":"正在准备处理...","timestamp":"2026-06-19T12:05:00Z"}

data: {"status":"processing","progress":0.1,"message":"正在提取音频...","timestamp":"2026-06-19T12:05:10Z"}

data: {"status":"processing","progress":0.25,"message":"正在进行语音识别...","timestamp":"2026-06-19T12:05:20Z"}

...

data: {"status":"completed","progress":1.0,"message":"任务完成","outputs":[{"format":"srt","url":"/download/..."}],"timestamp":"2026-06-19T12:10:00Z"}
```

**事件类型:**
- `progress` - 进度更新
- `completed` - 任务完成
- `failed` - 任务失败
- `cancelled` - 任务已取消
- `keepalive` - 保活信号（每 30 秒）

---

### 队列管理

#### 获取队列状态

**请求:**
```http
GET /tasks/queue/status
```

**响应 (200 OK):**
```json
{
  "pending_count": 5,
  "processing_count": 2,
  "avg_duration": 180,
  "queue": [
    {
      "position": 1,
      "task_id": "uuid",
      "title": "Video 1",
      "estimated_seconds": 120
    },
    {
      "position": 2,
      "task_id": "uuid",
      "title": "Video 2",
      "estimated_seconds": 150
    }
  ]
}
```

---

### 健康检查

#### 基本健康检查

**请求:**
```http
GET /health
```

**响应 (200 OK):**
```json
{
  "status": "ok",
  "service": "Whisper Platform"
}
```

---

#### 就绪检查

**请求:**
```http
GET /health/ready
```

**响应 (200/503):**
```json
{
  "status": "ok",
  "checks": [
    {
      "name": "database",
      "status": true,
      "message": "Connected"
    },
    {
      "name": "ffmpeg",
      "status": true,
      "message": "Available"
    },
    {
      "name": "whisper_model",
      "status": true,
      "message": "Models loaded"
    }
  ]
}
```

---

#### SSE 连接统计

**请求:**
```http
GET /health/sse-connections
```

**响应 (200 OK):**
```json
{
  "active_connections": 3,
  "total_created": 42,
  "avg_lifetime_seconds": 120
}
```

---

## 使用示例

### Python (requests)

```python
import requests
import time

# 获取 Token
response = requests.post(
    'http://localhost:8000/api/v1/auth/login',
    json={
        'username': 'user@example.com',
        'password': 'password123'
    }
)
token = response.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# 上传文件并创建任务
with open('video.mp4', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/tasks',
        files={'file': f},
        data={
            'source_type': 'upload',
            'title': 'My Video',
            'whisper_model': 'base',
            'output_formats': 'srt',
            'translate_target_langs': 'zh'
        },
        headers=headers
    )

task_id = response.json()['id']
print(f'Task created: {task_id}')

# 订阅实时进度
response = requests.get(
    f'http://localhost:8000/api/v1/tasks/{task_id}/stream',
    headers=headers,
    stream=True
)

for line in response.iter_lines():
    if line:
        import json
        event = json.loads(line.decode('utf-8').replace('data: ', ''))
        print(f"Progress: {event['progress']*100:.0f}% - {event['message']}")
        
        if event['status'] == 'completed':
            break

# 获取输出
response = requests.get(
    f'http://localhost:8000/api/v1/tasks/{task_id}/outputs',
    headers=headers
)
outputs = response.json()
print(f'Outputs: {len(outputs)} files')

# 下载输出
for output in outputs:
    url = f"http://localhost:8000/api/v1/tasks/{task_id}/outputs/{output['id']}/download"
    response = requests.get(url, headers=headers)
    with open(output['file_path'].split('/')[-1], 'wb') as f:
        f.write(response.content)
```

### JavaScript (fetch)

```javascript
const token = localStorage.getItem('token');
const headers = { 'Authorization': `Bearer ${token}` };

// 创建任务
const formData = new FormData();
formData.append('source_type', 'upload');
formData.append('title', 'My Video');
formData.append('whisper_model', 'base');
formData.append('output_formats', 'srt');
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/api/v1/tasks', {
  method: 'POST',
  headers,
  body: formData
});

const task = await response.json();
console.log('Task created:', task.id);

// 订阅实时进度
const eventSource = new EventSource(
  `http://localhost:8000/api/v1/tasks/${task.id}/stream`,
  { headers }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${(data.progress * 100).toFixed(0)}% - ${data.message}`);
  
  if (data.status === 'completed') {
    eventSource.close();
  }
};
```

---

## 速率限制

- **游客**: 5 请求/分钟
- **认证用户**: 100 请求/分钟
- **管理员**: 无限制

超过限制时返回 `429 Too Many Requests`。

---

## 支持的语言

### Whisper 支持语言

Auto (自动检测), English, Chinese, Spanish, French, German, Italian, Japanese, Korean, Portuguese, Russian, Turkish, 等 99+ 种语言

### 翻译支持语言

zh (中文), en (English), ja (日本語), ko (한국어), fr (Français), de (Deutsch), es (Español), ru (Русский), pt (Português), ar (العربية), th (ไทย), vi (Tiếng Việt), it (Italiano), nl (Nederlands), pl (Polski), tr (Türkçe), id (Bahasa Indonesia)

---

## FAQ

**Q: 文件大小限制是多少？**
A: 最大 2GB，建议 < 1GB

**Q: 上传后多久能得到结果？**
A: 取决于文件长度和模型。平均 1 小时视频需要 5-30 分钟（base 模型）

**Q: 能否取消正在处理的任务？**
A: 可以，调用 `/tasks/{task_id}/cancel` 端点

**Q: Token 过期后怎么办？**
A: 调用 `/auth/refresh` 刷新，或重新登录

**Q: 支持批量上传吗？**
A: 目前不支持，需要逐个上传

---

## 联系支持

- **邮件**: support@example.com
- **文档**: https://docs.example.com
- **问题跟踪**: https://github.com/user/project/issues
"""
