# Doc Assistant

## 启动

```bash
cd project
adk web --port 8000 \
  --memory_service_uri "sqlite:///./data/memory.db" \
  --session_service_uri "sqlite:///./data/sessions.db"
```

访问 http://127.0.0.1:8000
