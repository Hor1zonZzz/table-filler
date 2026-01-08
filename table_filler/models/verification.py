"""验证结果数据模型。"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    """验证状态。"""

    PASS = "PASS"  # 验证通过
    FAIL = "FAIL"  # 验证失败（发现严重问题）
    NEEDS_REVIEW = "NEEDS_REVIEW"  # 需要人工审核


class IssueType(str, Enum):
    """问题类型。"""

    HALLUCINATION = "hallucination"  # 幻觉（值不在文档中）
    TYPO = "typo"  # 拼写错误
    WRONG_FIELD = "wrong_field"  # 字段匹配错误
    MISSED = "missed"  # 遗漏（应有值但未提取）
    FORMAT_ERROR = "format_error"  # 格式错误
    LOW_CONFIDENCE = "low_confidence"  # 低置信度


class VerificationIssue(BaseModel):
    """单个验证问题。"""

    field_name: str = Field(..., description="问题字段名称")
    issue_type: IssueType = Field(..., description="问题类型")
    message: str = Field(..., description="问题描述")
    original_value: Any = Field(default=None, description="原始提取值")
    corrected_value: Any = Field(default=None, description="更正后的值")
    source_page: int | None = Field(default=None, description="相关页码")


class VerificationResult(BaseModel):
    """验证结果。"""

    status: VerificationStatus = Field(..., description="验证状态")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="整体置信度",
    )
    pages_checked: list[int] = Field(
        default_factory=list,
        description="已检查的页码列表",
    )
    issues: list[VerificationIssue] = Field(
        default_factory=list,
        description="发现的问题列表",
    )
    corrected_record: dict[str, Any] = Field(
        default_factory=dict,
        description="更正后的记录",
    )
    notes: str = Field(
        default="",
        description="验证备注",
    )

    def has_critical_issues(self) -> bool:
        """检查是否有严重问题。

        Returns:
            是否存在幻觉或严重错误
        """
        critical_types = {IssueType.HALLUCINATION, IssueType.WRONG_FIELD}
        return any(issue.issue_type in critical_types for issue in self.issues)

    def get_issues_by_type(self, issue_type: IssueType) -> list[VerificationIssue]:
        """按类型获取问题。

        Args:
            issue_type: 问题类型

        Returns:
            该类型的问题列表
        """
        return [issue for issue in self.issues if issue.issue_type == issue_type]
