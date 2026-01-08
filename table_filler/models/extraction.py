"""提取结果数据模型。"""

from typing import Any

from pydantic import BaseModel, Field


class FieldValue(BaseModel):
    """单个字段的提取值。"""

    value: Any = Field(..., description="提取的值")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="置信度 (0.0-1.0)",
    )
    source_page: int | None = Field(
        default=None,
        description="值来源的页码 (1-indexed)",
    )
    source_text: str = Field(
        default="",
        description="文档中的原始文本",
    )


class ExtractionResult(BaseModel):
    """单个文档的提取结果。"""

    document_path: str = Field(..., description="文档路径")
    fields: dict[str, FieldValue] = Field(
        default_factory=dict,
        description="提取的字段值，键为字段名",
    )
    pages_viewed: list[int] = Field(
        default_factory=list,
        description="已查看的页码列表",
    )
    notes: str = Field(
        default="",
        description="提取过程中的备注",
    )
    extraction_complete: bool = Field(
        default=False,
        description="提取是否完成",
    )

    def get_field_value(self, field_name: str) -> Any | None:
        """获取字段值。

        Args:
            field_name: 字段名称

        Returns:
            字段值，如果不存在则返回 None
        """
        field = self.fields.get(field_name)
        return field.value if field else None

    def get_low_confidence_fields(
        self,
        threshold: float = 0.8,
    ) -> list[tuple[str, FieldValue]]:
        """获取低置信度的字段。

        Args:
            threshold: 置信度阈值

        Returns:
            低置信度字段列表，每项为 (字段名, 字段值) 元组
        """
        return [
            (name, value)
            for name, value in self.fields.items()
            if value.confidence < threshold
        ]
