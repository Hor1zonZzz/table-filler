"""笔记工具。

供 Agent 在跨页面处理时记录和回忆信息。
"""

from datetime import datetime
from typing import Any

from google.adk.tools import ToolContext

from shared.state_keys import StateKeys


def add_note(
    tool_context: ToolContext,
    content: str,
    tag: str,
) -> dict[str, Any]:
    """记录发现的信息。

    在查看页面时发现重要信息后立即调用此工具记录。
    笔记在跨页面查看时持续存在，允许你从多个页面积累数据，
    最后编译成完整的提取结果。

    对于多页文档，这是必不可少的工具，因为相关信息（如第1页的当事人名称、
    第3页的金额）需要合并处理。

    Args:
        content: 要记录的信息。请具体明确，包含字段名和值，
            例如 "contract_id: ABC-2024-001" 或 "party_a: 华为技术有限公司"
        tag: 笔记分类标签。使用以下之一:
            - "field": 确定的字段值
            - "uncertain": 不确定的值（低置信度）
            - "observation": 一般观察记录
            - "location": 记录信息所在位置

    Returns:
        dict 包含:
        - status: "success"
        - note_id: 笔记编号
        - page: 记录时所在页码
        - message: 确认信息

    Example:
        >>> add_note("contract_id: ABC-2024-001", "field")
        {"status": "success", "note_id": 1, ...}

        >>> add_note("party_a: 华为技术有限公司", "field")
        >>> add_note("金额不清楚: 可能是 50000 或 500000", "uncertain")
        >>> add_note("签名在第 5 页右下角", "location")
    """
    # 获取或初始化笔记本
    notebook = tool_context.state.get(StateKeys.NOTEBOOK, [])

    # 创建笔记条目
    note_id = len(notebook) + 1
    current_page = tool_context.state.get(StateKeys.CURRENT_PAGE)

    note = {
        "id": note_id,
        "content": content,
        "tag": tag,
        "timestamp": datetime.now().isoformat(),
        "page": current_page,
    }

    notebook.append(note)
    tool_context.state[StateKeys.NOTEBOOK] = notebook

    return {
        "status": "success",
        "note_id": note_id,
        "page": current_page,
        "message": f"笔记 #{note_id} 已添加 (标签: '{tag}')",
    }


def read_notes(
    tool_context: ToolContext,
    tag: str | None = None,
) -> dict[str, Any]:
    """读取之前记录的笔记。

    在生成最终提取结果前调用此工具，回顾之前记录的所有信息。
    可以按标签过滤，只查看特定类型的笔记。

    Args:
        tag: 可选的标签过滤器。如果不指定，返回所有笔记。
            常用标签:
            - "field": 已提取的字段值
            - "uncertain": 不确定的值
            - "observation": 一般观察
            - "location": 信息位置

    Returns:
        dict 包含:
        - status: "success"
        - total_notes: 笔记本中的总笔记数
        - filtered_count: 符合过滤条件的笔记数
        - filter_tag: 使用的过滤标签
        - notes: 笔记列表，每条包含:
            - id: 笔记编号
            - content: 记录的信息
            - tag: 笔记标签
            - timestamp: 记录时间
            - page: 记录时所在页码

    Example:
        >>> read_notes()              # 获取所有笔记
        >>> read_notes("field")       # 只获取字段笔记
        >>> read_notes("uncertain")   # 获取不确定的值

        典型工作流程:
        1. read_notes("field") → 获取所有已提取的值
        2. read_notes("uncertain") → 检查需要注意的内容
        3. 编译最终提取结果 JSON
    """
    notebook = tool_context.state.get(StateKeys.NOTEBOOK, [])

    if tag:
        filtered = [n for n in notebook if n.get("tag") == tag]
    else:
        filtered = notebook

    return {
        "status": "success",
        "total_notes": len(notebook),
        "filtered_count": len(filtered),
        "filter_tag": tag,
        "notes": filtered,
    }


def clear_notes(
    tool_context: ToolContext,
    tag: str | None = None,
) -> dict[str, Any]:
    """清除笔记。

    谨慎使用此工具。通常应该保留所有笔记直到提取完成。
    只在需要重新开始提取或删除错误记录时使用。

    Args:
        tag: 如果指定，只清除该标签的笔记。
            如果不指定，清除所有笔记。

    Returns:
        dict 包含:
        - status: "success"
        - cleared_count: 清除的笔记数
        - remaining_count: 剩余笔记数
        - message: 确认信息

    Example:
        >>> clear_notes("observation")  # 只清除观察笔记
        {"status": "success", "cleared_count": 3, "remaining_count": 5, ...}

        >>> clear_notes()               # 清除所有笔记（谨慎使用）
        {"status": "success", "cleared_count": 8, "remaining_count": 0, ...}
    """
    notebook = tool_context.state.get(StateKeys.NOTEBOOK, [])

    if tag:
        original_count = len(notebook)
        notebook = [n for n in notebook if n.get("tag") != tag]
        cleared_count = original_count - len(notebook)
        tool_context.state[StateKeys.NOTEBOOK] = notebook
        return {
            "status": "success",
            "cleared_count": cleared_count,
            "remaining_count": len(notebook),
            "message": f"已清除 {cleared_count} 条标签为 '{tag}' 的笔记",
        }
    else:
        cleared_count = len(notebook)
        tool_context.state[StateKeys.NOTEBOOK] = []
        return {
            "status": "success",
            "cleared_count": cleared_count,
            "remaining_count": 0,
            "message": f"已清除所有 {cleared_count} 条笔记",
        }
