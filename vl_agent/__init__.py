"""VL Agent package for image Q&A tasks."""

import os
from pathlib import Path

from dotenv import load_dotenv

# 加载环境变量 (优先加载 vl_agent/.env，然后是项目根目录 .env)
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()  # 加载项目根目录的 .env

from . import tracing  # 初始化 Phoenix tracing
from . import agent

__all__ = ["agent"]
