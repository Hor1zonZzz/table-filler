"""常量定义。"""

# ========== 并发控制 ==========

# 批量处理时的最大并发文档数
MAX_CONCURRENT_DOCUMENTS = 10

# ========== 重试配置 ==========

# 最大重试次数
MAX_RETRY_ATTEMPTS = 3

# 重试等待时间（秒）
RETRY_MIN_WAIT = 2
RETRY_MAX_WAIT = 30

# ========== PDF 渲染 ==========

# 默认 DPI
DEFAULT_PDF_DPI = 150

# 最大推荐 DPI（更高会消耗更多内存）
MAX_RECOMMENDED_DPI = 300

# ========== 置信度阈值 ==========

# 高置信度阈值（PASS）
HIGH_CONFIDENCE_THRESHOLD = 0.8

# 低置信度阈值（需要审核）
LOW_CONFIDENCE_THRESHOLD = 0.5

# ========== 文件类型 ==========

# 支持的 PDF 扩展名
PDF_EXTENSIONS = {".pdf"}

# 支持的图片扩展名
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

# 所有支持的文档扩展名
SUPPORTED_EXTENSIONS = PDF_EXTENSIONS | IMAGE_EXTENSIONS

# ========== 导出格式 ==========

# 支持的导出格式
EXPORT_FORMATS = {"excel", "json", "csv"}
