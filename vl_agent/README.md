# VL Agent

PDF 表格数据提取 Agent，基于 Google ADK 构建。

## 启动服务

### 使用 ADK 内置 API Server

```bash
# 内存存储（默认，重启后数据丢失）
uv run adk api_server --port 8000 .

# SQLite 持久化
uv run adk api_server --port 8000 --session_service_uri "sqlite:///./sessions.db" .

# PostgreSQL 持久化
uv run adk api_server --port 8000 --session_service_uri "postgresql://user:pass@host/db" .
```

> 注意：命令需要在项目根目录（`LTC-strategy3`）下执行，`.` 表示当前目录作为 agents 目录。

### 使用独立入口

```bash
uv run python -m vl_agent.main
```

## API 使用

### 列出可用 Agents

```bash
curl http://127.0.0.1:8000/list-apps
```

### 创建 Session

```bash
curl -X POST "http://127.0.0.1:8000/apps/vl_agent/users/{user_id}/sessions/{session_id}" \
  -H "Content-Type: application/json" \
  -d "{}"
```

### 发送消息

```bash
curl -X POST "http://127.0.0.1:8000/run" \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "vl_agent",
    "userId": "{user_id}",
    "sessionId": "{session_id}",
    "newMessage": {
      "role": "user",
      "parts": [{"text": "你的消息"}]
    }
  }'
```

### 流式响应

```bash
curl -X POST "http://127.0.0.1:8000/run_sse" \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "vl_agent",
    "userId": "{user_id}",
    "sessionId": "{session_id}",
    "newMessage": {
      "role": "user",
      "parts": [{"text": "你的消息"}]
    },
    "streaming": true
  }'
```

### 查看 Session

```bash
curl "http://127.0.0.1:8000/apps/vl_agent/users/{user_id}/sessions/{session_id}"
```

### 列出用户所有 Sessions

```bash
curl "http://127.0.0.1:8000/apps/vl_agent/users/{user_id}/sessions"
```

### 删除 Session

```bash
curl -X DELETE "http://127.0.0.1:8000/apps/vl_agent/users/{user_id}/sessions/{session_id}"
```

## 环境变量

在 `vl_agent/.env` 中配置：

```env
DEEPSEEK_API_KEY=your_api_key
```

> 存储配置通过命令行参数 `--session_service_uri` 指定，无需在 .env 中配置。
