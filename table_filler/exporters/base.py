"""导出器基类。

定义导出器的抽象接口，所有具体导出器需实现此接口。
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..models.recipe import Recipe


class ExporterBase(ABC):
    """导出器抽象基类。

    所有导出器必须继承此类并实现其抽象方法。
    导出器负责将批处理结果输出到特定格式的文件。

    Example:
        >>> class JsonExporter(ExporterBase):
        ...     @property
        ...     def format_name(self) -> str:
        ...         return "json"
        ...
        ...     @property
        ...     def file_extension(self) -> str:
        ...         return ".json"
        ...
        ...     def export(self, results, output_path, recipe, **options):
        ...         # 实现导出逻辑
        ...         pass
    """

    @property
    @abstractmethod
    def format_name(self) -> str:
        """返回格式名称。

        Returns:
            格式的人类可读名称，如 "excel", "json", "csv"
        """
        ...

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """返回文件扩展名。

        Returns:
            文件扩展名（含点），如 ".xlsx", ".json", ".csv"
        """
        ...

    @abstractmethod
    def export(
        self,
        results: dict[str, Any],
        output_path: Path,
        recipe: Recipe,
        **options: Any,
    ) -> dict[str, Any]:
        """导出结果到文件。

        Args:
            results: 批处理结果，包含:
                - successful: 成功的记录列表
                - needs_review: 需要审核的记录列表
                - failed: 失败的记录列表
                - total_count: 总处理数
            output_path: 输出文件路径
            recipe: Recipe 配方，用于获取字段定义
            **options: 导出选项（各导出器自定义）

        Returns:
            dict 包含:
            - status: "success" 或 "error"
            - file_path: 输出文件路径
            - message: 描述信息
            - statistics: 导出统计
            - error: 错误信息（如果有）
        """
        ...

    def generate_filename(self, prefix: str = "export") -> str:
        """生成带时间戳的文件名。

        Args:
            prefix: 文件名前缀

        Returns:
            格式化的文件名，如 "export_20240115_143052.xlsx"
        """
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}{self.file_extension}"
