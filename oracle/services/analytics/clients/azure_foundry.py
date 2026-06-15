import os
import logging
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

_DEFAULT_ENDPOINT = "https://integrate.api.nvidia.com/v1"


def get_narrate_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=os.environ.get("NVIDIA_ENDPOINT", _DEFAULT_ENDPOINT),
        model=os.environ.get("NARRATE_MODEL", "deepseek-ai/deepseek-v4-pro"),
        api_key=os.environ.get("NVIDIA_API_KEY", "placeholder"),
        temperature=0.2,
        max_tokens=3000,
    )
