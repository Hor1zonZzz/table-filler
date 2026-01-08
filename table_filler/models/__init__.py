"""数据模型定义。"""

from .recipe import (
    FieldType,
    MissingStrategy,
    ConflictStrategy,
    ValidationRule,
    ExtractionHint,
    FieldDefinition,
    Recipe,
)
from .extraction import FieldValue, ExtractionResult
from .verification import VerificationStatus, VerificationIssue, VerificationResult

__all__ = [
    # Recipe 相关
    "FieldType",
    "MissingStrategy",
    "ConflictStrategy",
    "ValidationRule",
    "ExtractionHint",
    "FieldDefinition",
    "Recipe",
    # 提取结果
    "FieldValue",
    "ExtractionResult",
    # 验证结果
    "VerificationStatus",
    "VerificationIssue",
    "VerificationResult",
]
