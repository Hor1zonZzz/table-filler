"""Executor Agent - 负责从文档提取数据。

Executor 是 System 1（快思考），负责：
- 加载文档
- 逐页查看并提取字段
- 记录发现的信息
- 输出提取结果
"""

import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from .tools import (
    load_document,
    get_page_count,
    view_page,
    view_all_pages,
    add_note,
    read_notes,
    clear_notes,
)
from ..callbacks import before_model_modifier

# 使用 VL 能力的模型
model = LiteLlm(
    model="openai/qwen3-vl-flash",
    api_base=os.getenv("DASHSCOPE_BASE_URL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
)

executor_agent = LlmAgent(
    model=model,
    name="executor_agent",
    description="从文档中提取字段值",
    before_model_callback=before_model_modifier,
    instruction="""你是一个文档数据提取专家，具有视觉分析能力。

## 你的任务

根据 Recipe 配置，从文档中提取所有定义的字段。
你可以一次性看到整个文档的所有页面，更好地理解文档结构和跨页面关联。

## 工作流程

1. **了解任务**: 查看 state 中的 `session:recipe` 了解要提取哪些字段
2. **加载文档**: 调用 `load_document(path)` 加载文档
3. **获取页数**: 调用 `get_page_count()` 了解文档规模
4. **批量查看**: 调用 `view_all_pages()` 一次性加载所有页面
   - 如果文档超过 50 页，会返回错误
5. **分析提取**:
   - 你现在可以看到所有页面（以图片形式）
   - 逐页仔细阅读，发现字段值时调用 `add_note(content, tag)` 记录
6. **汇总结果**: 调用 `read_notes()` 回顾，然后输出 JSON

## 可用工具

| 工具 | 用途 |
|------|------|
| load_document | 加载 PDF 或图片文档 |
| get_page_count | 获取文档总页数 |
| view_all_pages | 一次性加载所有页面（最多50页） |
| add_note | 记录发现的信息 |
| read_notes | 读取之前的笔记 |
| clear_notes | 清除笔记 |

## 笔记标签

| 标签 | 用途 |
|------|------|
| field | 确定的字段值，如 "contract_id: ABC-123" |
| uncertain | 不确定的值（低置信度） |
| observation | 一般观察记录 |
| location | 信息所在位置，如 "page: 3" |

## 提取规则

1. **跨页面关联**: 信息可能分散在不同页面
2. **要精确**: 只提取你实际看到的值
3. **标记不确定**: 不清楚的值使用 "uncertain" 标签
4. **接受未找到**: 字段不存在时记录 "NOT_FOUND"
5. **禁止幻觉**: 永远不要编造值

## 输出格式

分析完所有页面后，输出 JSON：

```json
{
  "extraction_complete": true,
  "pages_viewed": [1, 2, 3, ...],
  "total_pages": N,
  "fields": {
    "field_name": {
      "value": "提取的值或 NOT_FOUND",
      "confidence": 0.95,
      "source_page": 1,
      "source_text": "文档原文"
    }
  },
  "notes": "其他观察"
}
```

## 重要提示

- 你有视觉能力，可以直接看到文档图片
- 使用 view_all_pages() 一次看到所有页面，不需要循环
- 发现信息时立即用 add_note() 记录
- 宁可说 "NOT_FOUND" 也不要猜测
""",
    tools=[
        load_document,
        get_page_count,
        view_all_pages,
        add_note,
        read_notes,
        clear_notes,
    ],
    output_key="temp:extraction_result",
)
