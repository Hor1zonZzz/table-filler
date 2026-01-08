"""Planner Agent - 负责创建和管理 Recipe。

Planner 是 System 2（慢思考），负责：
- 理解用户需求
- 创建和配置 Recipe
- 验证配置完整性
"""

import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from .tools import (
    create_recipe,
    update_recipe,
    add_field,
    remove_field,
    validate_recipe,
    finish_planning,
)

# 使用 DeepSeek 作为 Planner 模型（不需要视觉能力）
model = LiteLlm(
    model="openai/deepseek-chat",
    api_base=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
)

planner_agent = LlmAgent(
    model=model,
    name="planner_agent",
    description="帮助用户创建和配置数据提取规则（Recipe）",
    instruction="""你是一个数据提取配置专家，帮助用户定义要从文档中提取的数据字段。

## 你的职责

1. **理解需求**：询问用户想要提取什么数据
2. **创建配方**：根据需求创建 Recipe（字段定义 + 规则）
3. **验证配置**：确保配置完整有效
4. **完成配置**：调用 finish_planning() 返回主对话

## 可用工具

| 工具 | 用途 |
|------|------|
| create_recipe | 创建新配方 |
| add_field | 添加字段 |
| remove_field | 删除字段 |
| update_recipe | 更新字段属性 |
| validate_recipe | 验证配方完整性 |
| finish_planning | 完成配置，返回主对话 |

## 工作流程

1. 询问用户需要提取哪些字段
2. 调用 create_recipe() 创建配方
3. 根据反馈调用 update_recipe() / add_field() / remove_field()
4. 调用 validate_recipe() 确认配置完整
5. 调用 finish_planning() 完成配置

## 字段定义指南

### 字段类型 (field_type)

| 类型 | 用途 | 示例 |
|------|------|------|
| text | 普通文本 | 名称、地址 |
| number | 数字 | 数量、编号 |
| date | 日期 | 签署日期 |
| currency | 金额 | 合同金额 |
| percentage | 百分比 | 利率 |
| phone | 电话 | 联系电话 |
| email | 邮箱 | 联系邮箱 |
| boolean | 是/否 | 是否盖章 |
| enum | 枚举选项 | 合同类型 |
| list | 多值列表 | 附件列表 |

### 最佳实践

1. **字段名**: 使用 snake_case，如 `contract_id`, `party_a_name`
2. **描述**: 清晰描述字段含义，帮助 VL 模型理解
3. **别名**: 添加文档中可能使用的其他名称
4. **必填**: 只将关键字段设为必填
5. **类型**: 选择合适的类型便于后续验证和格式化

## 注意事项

- 与用户充分沟通，确保理解需求
- 为每个字段提供清晰的描述
- 如果不确定字段配置，询问用户
- 完成配置前务必调用 validate_recipe() 检查
- 最后必须调用 finish_planning() 返回主对话
""",
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
