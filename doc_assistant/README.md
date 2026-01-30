# Doc Assistant

## 启动

### 服务化
```bash
uv run phoenix serve
uv run adk api_server --host 0.0.0.0 --port 8000 \                                   
  --memory_service_uri "sqlite:///./data/memory.db" \
  --session_service_uri "sqlite:///./data/sessions.db" \
  .
```

### 基础启动 (无自动保存到 Memory)

```bash
cd project
uv run adk api_server --host 0.0.0.0 --port 8000 .
# your project path can be
# /project
#   /doc_assistant
adk web --port 8000 \
  --memory_service_uri "sqlite:///./data/memory.db" \
  --session_service_uri "sqlite:///./data/sessions.db"
```

### 启用自动 Memory 保存 (推荐)

使用 MemoryPlugin 自动在会话不活跃时保存到 Memory:

```bash
cd project
uv run adk web --port 8000 \
  --memory_service_uri "sqlite:///./data/memory.db" \
  --session_service_uri "sqlite:///./data/sessions.db" \
  --extra_plugins "doc_assistant.plugins.MemoryPlugin"
```

访问 http://127.0.0.1:8000

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MEMORY_PLUGIN_TIMEOUT` | 不活跃超时时间（秒），超时后自动保存 Session 到 Memory | 20 |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | - |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | - |

## 架构说明

### Memory 保存机制

MemoryPlugin 使用基于 Invocation 完成的定时器:

1. 用户发送消息，触发一次 Invocation
2. Invocation 完成后（所有 LLM 调用、工具执行完成），`after_run_callback` 被触发
3. Plugin 重置该 Session 的不活跃定时器
4. 如果 N 秒内没有新的 Invocation，自动保存 Session 到 Memory
5. 保存采用增量方式，只保存新增的 events

这比旧的 LLM 回调方式更可靠，因为:
- 每个用户消息只触发一次定时器重置（而不是每次 LLM 调用都重置）
- 定时器在所有处理完成后才开始计时
- 不会遗漏最后的事件
