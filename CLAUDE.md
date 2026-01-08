# CLAUDE.md

## 项目概述

基于 **Google ADK (Agent Development Kit)** 构建的通用表格填写助手。VL（视觉语言）模型像人类一样直接查看 PDF 页面并提取字段，无需 OCR。

**核心特性：**
- **Recipe 驱动**：通过配方定义提取字段和规则
- **Planner + Executor 架构**：System 2 慢思考配置 + System 1 快执行提取
- **防幻觉验证**：Verifier Agent 验证提取结果
- **VL 直接查看**：无需 OCR，直接分析文档图片
- **并行处理**：支持批量文档并发处理
- **可插拔导出**：支持多种输出格式（Excel 等）

## 命令

```bash
# 运行 Agent（使用 ADK CLI）
uv run adk run orchestrator

# 安装依赖
uv sync

# 代码检查和格式化
ruff check .
ruff format .

# 类型检查
basedpyright
```

## 架构

### 概览

```
                              User
                                │
                                ▼
┌───────────────────────────────────────────────────────────┐
│            conversation_agent (LlmAgent)                   │
│                                                           │
│  tools: [batch_process_documents, export_results]         │
│  sub_agents: [planner_agent]                              │
└───────────────────────────────────────────────────────────┘
        │                              │
        │ transfer                     │ 调用工具
        ▼                              ▼
┌─────────────────┐      ┌──────────────────────────────────┐
│ planner_agent   │      │    batch_process_documents()     │
│ (System 2)      │      │              │                   │
│                 │      │    ┌─────────┴──────────┐        │
│ 创建/配置 Recipe │      │    │   每个文档并行      │        │
│                 │      │    ▼                    │        │
│ tools: [        │      │  extraction_pipeline    │        │
│  create_recipe, │      │  (SequentialAgent)      │        │
│  update_recipe, │      │    │                    │        │
│  add_field,     │      │    ├── executor_agent   │        │
│  remove_field,  │      │    │   (VL 提取)        │        │
│  validate,      │      │    │                    │        │
│  finish         │      │    └── verifier_agent   │        │
│ ]               │      │        (VL 验证)        │        │
└─────────────────┘      └──────────────────────────────────┘
```

### 目录结构

```
LTC-strategy3/
├── main.py                              # 入口
├── CLAUDE.md                            # 项目文档
│
├── shared/                              # 共享模块
│   ├── constants.py                     # 常量定义
│   └── state_keys.py                    # State 键定义
│
├── table_filler/                        # 核心模块
│   ├── models/                          # Pydantic 数据模型
│   │   ├── recipe.py                    # Recipe 配方定义
│   │   ├── extraction.py                # 提取结果
│   │   └── verification.py              # 验证结果
│   │
│   ├── planner/                         # Planner Agent (System 2)
│   │   ├── agent.py                     # planner_agent
│   │   └── tools/
│   │       ├── recipe_builder.py        # create_recipe, update_recipe, add_field, remove_field
│   │       ├── recipe_validator.py      # validate_recipe
│   │       └── transfer.py              # finish_planning
│   │
│   ├── executor/                        # Executor Agent (System 1)
│   │   ├── agent.py                     # executor_agent (VL)
│   │   ├── pipeline.py                  # extraction_pipeline (SequentialAgent)
│   │   └── tools/
│   │       ├── document_loader.py       # load_document
│   │       ├── page_viewer.py           # get_page_count, view_page
│   │       ├── batch_viewer.py          # view_all_pages (批量加载所有页面)
│   │       └── notebook.py              # add_note, read_notes, clear_notes
│   │
│   ├── verifier/                        # Verifier Agent (防幻觉)
│   │   └── agent.py                     # verifier_agent (VL)
│   │
│   ├── exporters/                       # 可插拔导出器
│   │   ├── base.py                      # ExporterBase 抽象类
│   │   └── excel_exporter.py            # Excel 导出
│   │
│   └── callbacks.py                     # VL 模型图片注入回调
│
├── orchestrator/                        # 顶级对话 Agent
│   ├── agent.py                         # conversation_agent + root_agent
│   └── tools/
│       ├── batch_processor.py           # batch_process_documents
│       └── export_tool.py               # export_results
│
└── vl_agent/                            # VL 图片分析模块（独立）
    ├── agent.py
    ├── callbacks.py
    └── tools/
        ├── pdf_renderer.py              # PDF 渲染
        ├── pdf_loader_batch.py          # PDF 批量加载
        └── picture_loader.py            # 图片加载
```

## Recipe（配方）系统

Recipe 是提取配置的核心，定义要提取的字段及其规则：

```python
from table_filler.models.recipe import Recipe, FieldDefinition, FieldType

recipe = Recipe(
    name="合同提取",
    description="提取销售合同关键信息",
    document_type="contract",
    fields=[
        FieldDefinition(
            name="contract_id",
            display_name="合同编号",
            description="合同唯一标识符",
            field_type=FieldType.TEXT,
            required=True,
        ),
        FieldDefinition(
            name="amount",
            display_name="合同金额",
            field_type=FieldType.CURRENCY,
            aliases=["总价", "金额"],
        ),
    ],
)
```

### 字段类型

| 类型 | 用途 | 示例 |
|------|------|------|
| `text` | 普通文本 | 名称、地址 |
| `number` | 数字 | 数量、编号 |
| `date` | 日期 | 签署日期 |
| `currency` | 金额 | 合同金额 |
| `percentage` | 百分比 | 利率 |
| `phone` | 电话 | 联系电话 |
| `email` | 邮箱 | 联系邮箱 |
| `boolean` | 是/否 | 是否盖章 |
| `enum` | 枚举选项 | 合同类型 |
| `list` | 多值列表 | 附件列表 |

## Agent 模式

### conversation_agent（顶级）

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

model = LiteLlm(model="openai/deepseek-chat")

conversation_agent = LlmAgent(
    model=model,
    name="conversation_agent",
    tools=[batch_process_documents, export_results],
    sub_agents=[planner_agent],  # 通过 transfer 切换
)

root_agent = conversation_agent
```

### planner_agent（配置）

```python
planner_agent = LlmAgent(
    model=model,
    name="planner_agent",
    tools=[
        create_recipe,
        update_recipe,
        add_field,
        remove_field,
        validate_recipe,
        finish_planning,
    ],
    output_key="session:recipe",
)
```

### extraction_pipeline（提取+验证）

```python
from google.adk.agents import SequentialAgent

extraction_pipeline = SequentialAgent(
    name="extraction_pipeline",
    sub_agents=[executor_agent, verifier_agent],
)
```

## 数据流程

```
1. 用户描述需求
   "我需要从合同 PDF 中提取：合同编号、甲方、乙方、金额"
                    │
                    ▼
2. Planner 创建配方（transfer 到 planner_agent）
   - 分析需求
   - 创建 Recipe → session:recipe
   - 完成后 transfer 回 conversation_agent
                    │
                    ▼
3. 用户提供文档
   "处理这些文件: D:/contracts/*.pdf"
                    │
                    ▼
4. 批量处理（调用 batch_process_documents）
   - 并行加载文档（最多 10 并发）
   - 每个文档运行 extraction_pipeline:
     - executor_agent: view_all_pages 一次加载所有页面，提取字段
     - verifier_agent: 验证结果，防止幻觉
   - 汇总结果 → temp:batch_results
                    │
                    ▼
5. 报告结果
   "处理了 50 个文档：45 成功，3 待审核，2 失败"
                    │
                    ▼
6. 导出（调用 export_results）
   → export_20240115_143052.xlsx
```

## State 管理

| 键 | 作用域 | 用途 |
|----|--------|------|
| `session:recipe` | Session | 当前配方 |
| `temp:document_images` | Invocation | 文档图片 |
| `temp:document_path` | Invocation | 文档路径 |
| `temp:notebook` | Invocation | 提取笔记 |
| `temp:viewed_pages` | Invocation | 已查看页面 |
| `temp:extraction_result` | Invocation | 提取结果 |
| `temp:verification_result` | Invocation | 验证结果 |
| `temp:batch_results` | Invocation | 批处理结果 |

## 环境变量

在 `.env` 文件中配置：

```bash
# DeepSeek (Planner/Conversation)
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.deepseek.com/v1

# DashScope (VL Models - Executor/Verifier)
DASHSCOPE_API_KEY=your_api_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

## 关键工具

### Planner 工具

| 工具 | 职责 |
|------|------|
| `create_recipe` | 创建新配方 |
| `update_recipe` | 更新字段属性 |
| `add_field` | 添加新字段 |
| `remove_field` | 删除字段 |
| `validate_recipe` | 验证配方完整性 |
| `finish_planning` | 完成配置，返回主对话 |

### Executor 工具

| 工具 | 职责 |
|------|------|
| `load_document` | 加载 PDF/图片 |
| `get_page_count` | 获取页数 |
| `view_all_pages` | 一次性加载所有页面（最多50页） |
| `add_note` | 记录信息 |
| `read_notes` | 读取笔记 |
| `clear_notes` | 清除笔记 |

### 笔记标签

| 标签 | 用途 |
|------|------|
| `field` | 确定的字段值 |
| `uncertain` | 不确定的值 |
| `observation` | 一般观察 |
| `location` | 信息位置 |

## 并发与重试

```python
# 并发控制
MAX_CONCURRENT_DOCUMENTS = 10
semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOCUMENTS)

# 重试机制
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
async def process_document(...):
    ...
```

## Google ADK 参考

- 文档: https://google.github.io/adk-docs/llms.txt
- `SequentialAgent` 用于强制顺序执行
- `LlmAgent` 的 `sub_agents` + `transfer_to_agent` 实现 Agent 切换
- `output_key` 自动保存 Agent 输出到 state
- 工具函数的 docstring 自动生成 schema
