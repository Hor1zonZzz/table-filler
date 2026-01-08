"""Recipe（配方）数据模型定义。

Recipe 是整个表格填写系统的核心配置，定义了：
- 要提取的字段及其类型
- 验证规则
- 提取提示
- 异常处理策略
"""

from enum import Enum
from typing import Any
from uuid import uuid4
from datetime import datetime

from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """字段数据类型。"""

    TEXT = "text"
    NUMBER = "number"
    INTEGER = "integer"
    FLOAT = "float"
    DATE = "date"
    DATETIME = "datetime"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    PHONE = "phone"
    EMAIL = "email"
    ID_NUMBER = "id_number"
    ADDRESS = "address"
    BOOLEAN = "boolean"
    ENUM = "enum"  # 枚举，需配合 enum_choices 使用
    LIST = "list"  # 列表，可包含多个值


class MissingStrategy(str, Enum):
    """字段缺失处理策略。"""

    ERROR = "error"  # 标记为提取失败
    DEFAULT = "default"  # 使用默认值
    NULL = "null"  # 接受空值
    ASK = "ask"  # 标记为需人工审核


class ConflictStrategy(str, Enum):
    """字段值冲突处理策略（当找到多个值时）。"""

    FIRST = "first"  # 使用第一个出现的值
    LAST = "last"  # 使用最后一个出现的值
    LONGEST = "longest"  # 使用最长的值
    ASK = "ask"  # 标记为需人工审核
    MERGE = "merge"  # 合并所有值（用于 LIST 类型）


class ValidationRule(BaseModel):
    """验证规则。"""

    rule_type: str = Field(
        ...,
        description="规则类型: required, regex, min_length, max_length, "
        "min_value, max_value, choices, format, custom",
    )
    value: Any = Field(default=None, description="规则参数值")
    error_message: str = Field(default="", description="验证失败时的错误消息")


class ExtractionHint(BaseModel):
    """提取提示，帮助 VL 模型定位和提取字段。"""

    location_hints: list[str] = Field(
        default_factory=list,
        description="位置提示: header, footer, table, first_page, last_page, sidebar",
    )
    visual_cues: list[str] = Field(
        default_factory=list,
        description="视觉特征: bold, underlined, in_box, highlighted, handwritten",
    )
    context_keywords: list[str] = Field(
        default_factory=list,
        description="上下文关键词，出现在字段值附近的文字",
    )
    extraction_prompt: str = Field(
        default="",
        description="自定义提取提示，帮助 VL 模型理解如何提取此字段",
    )


class FieldDefinition(BaseModel):
    """字段定义。"""

    # 基本信息
    name: str = Field(..., description="字段唯一标识符 (snake_case)")
    display_name: str = Field(default="", description="人类可读的显示名称")
    description: str = Field(default="", description="字段描述，说明该字段的含义")

    # 类型信息
    field_type: FieldType = Field(default=FieldType.TEXT, description="字段数据类型")
    format_pattern: str | None = Field(
        default=None,
        description="格式模式，用于 date/phone 等类型",
    )
    enum_choices: list[str] | None = Field(
        default=None,
        description="枚举选项，仅当 field_type=ENUM 时使用",
    )

    # 提取辅助
    aliases: list[str] = Field(
        default_factory=list,
        description="别名列表，文档中可能使用的其他名称",
    )
    extraction_hint: ExtractionHint = Field(
        default_factory=ExtractionHint,
        description="提取提示",
    )

    # 验证
    required: bool = Field(default=False, description="是否为必填字段")
    validation_rules: list[ValidationRule] = Field(
        default_factory=list,
        description="验证规则列表",
    )

    # 异常处理
    missing_strategy: MissingStrategy = Field(
        default=MissingStrategy.NULL,
        description="字段缺失时的处理策略",
    )
    conflict_strategy: ConflictStrategy = Field(
        default=ConflictStrategy.FIRST,
        description="发现多个值时的处理策略",
    )
    default_value: Any = Field(default=None, description="默认值")


class Recipe(BaseModel):
    """完整的提取配方。"""

    # 元数据
    recipe_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
        description="配方唯一标识符",
    )
    name: str = Field(default="", description="配方名称")
    description: str = Field(default="", description="配方描述")
    version: str = Field(default="1.0.0", description="版本号")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="创建时间",
    )
    updated_at: str = Field(default="", description="最后更新时间")

    # 文档类型
    document_type: str = Field(
        default="general",
        description="文档类型: contract, invoice, form, report, general",
    )
    expected_pages: str = Field(
        default="any",
        description="预期页数: single, 1-5, 5-10, any",
    )

    # 字段定义
    fields: list[FieldDefinition] = Field(
        default_factory=list,
        description="字段定义列表",
    )

    # 全局设置
    extraction_order: list[str] = Field(
        default_factory=list,
        description="字段提取顺序（按字段名）",
    )
    global_context: str = Field(
        default="",
        description="全局上下文，帮助 VL 模型理解文档类型",
    )

    def get_field(self, name: str) -> FieldDefinition | None:
        """根据名称获取字段定义。

        Args:
            name: 字段名称

        Returns:
            字段定义，如果不存在则返回 None
        """
        for field in self.fields:
            if field.name == name:
                return field
        return None

    def get_required_fields(self) -> list[FieldDefinition]:
        """获取所有必填字段。

        Returns:
            必填字段列表
        """
        return [f for f in self.fields if f.required]

    def get_field_names(self) -> list[str]:
        """获取所有字段名称。

        Returns:
            字段名称列表
        """
        return [f.name for f in self.fields]

    def add_field(self, field: FieldDefinition) -> None:
        """添加字段。

        Args:
            field: 要添加的字段定义
        """
        # 检查是否已存在
        if self.get_field(field.name):
            raise ValueError(f"Field '{field.name}' already exists")
        self.fields.append(field)
        self.updated_at = datetime.now().isoformat()

    def remove_field(self, name: str) -> bool:
        """删除字段。

        Args:
            name: 要删除的字段名称

        Returns:
            是否成功删除
        """
        for i, field in enumerate(self.fields):
            if field.name == name:
                self.fields.pop(i)
                self.updated_at = datetime.now().isoformat()
                return True
        return False

    def update_field(self, name: str, updates: dict[str, Any]) -> bool:
        """更新字段。

        Args:
            name: 要更新的字段名称
            updates: 更新内容

        Returns:
            是否成功更新
        """
        field = self.get_field(name)
        if not field:
            return False

        for key, value in updates.items():
            if hasattr(field, key):
                setattr(field, key, value)

        self.updated_at = datetime.now().isoformat()
        return True
