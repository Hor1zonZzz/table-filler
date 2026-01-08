"""State 键定义。

集中管理所有 state 键，避免硬编码和拼写错误。
"""


class StateKeys:
    """集中管理的 State 键。

    命名规则：
    - session: 开头表示会话级别，跨多个对话保持
    - temp: 开头表示临时/调用级别，每次调用后清理
    """

    # ========== Session 级别 (跨对话保持) ==========

    # Recipe 相关
    RECIPE = "session:recipe"
    RECIPE_HISTORY = "session:recipe_history"

    # 统计信息
    PROCESSED_COUNT = "session:processed_count"

    # ========== Invocation 级别 (每次调用/每个文档) ==========

    # 文档相关
    DOCUMENT_IMAGES = "temp:document_images"
    DOCUMENT_PATH = "temp:document_path"
    DOCUMENT_TYPE = "temp:document_type"
    DOCUMENT_TOTAL_PAGES = "temp:document_total_pages"

    # 笔记系统
    NOTEBOOK = "temp:notebook"
    VIEWED_PAGES = "temp:viewed_pages"
    CURRENT_PAGE = "temp:current_page"

    # 提取和验证结果
    EXTRACTION_RESULT = "temp:extraction_result"
    VERIFICATION_RESULT = "temp:verification_result"

    # 批量处理
    BATCH_RESULTS = "temp:batch_results"
    BATCH_PROGRESS = "temp:batch_progress"

    # ========== 兼容旧版 (逐步废弃) ==========

    # 这些键用于兼容现有的 processing/ 模块
    PDF_IMAGES = "temp:pdf_images"
    FILLED_RECORD = "temp:filled_record"
    FORM_CONFIG = "form_config"
