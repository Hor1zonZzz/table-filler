from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

# from .tools import pdf_to_markdown


def get_current_time(city: str) -> dict:
    """返回指定城市中的当前时间。"""
    return {"status": "success", "city": city, "time": "10:30 AM"}


# 创建 LiteLLM 模型实例（用于 OpenAI 兼容 API）
model = LiteLlm(
    model="openai/deepseek-chat",  # LiteLLM 格式: provider/model
)

# 创建 Agent
root_agent = LlmAgent(
    model=model,
    name="deepseek_agent",
    description="一个基于 DeepSeek 的智能助手",
    instruction="""你是一个智能助手，能够帮助用户完成各种任务。
请用清晰、简洁的方式回答问题。
如果不确定答案，请诚实地告诉用户。
""",
    tools=[get_current_time],
)
