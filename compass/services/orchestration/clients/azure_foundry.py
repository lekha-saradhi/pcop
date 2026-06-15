import os
from langchain_openai import ChatOpenAI
from openai import OpenAI


_DEFAULT_ENDPOINT = "https://integrate.api.nvidia.com/v1"
_DEFAULT_KEY = os.environ.get("NVIDIA_API_KEY", "placeholder")


def get_cognition_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ.get("NVIDIA_ENDPOINT", _DEFAULT_ENDPOINT),
        api_key=os.environ.get("NVIDIA_API_KEY", _DEFAULT_KEY),
    )


def get_compass_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ.get("NVIDIA_ENDPOINT", _DEFAULT_ENDPOINT),
        api_key=os.environ.get("NVIDIA_API_KEY", _DEFAULT_KEY),
    )


def get_langchain_cognition_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=os.environ.get("NVIDIA_ENDPOINT", _DEFAULT_ENDPOINT),
        api_key=os.environ.get("NVIDIA_API_KEY", _DEFAULT_KEY),
        model="deepseek-ai/deepseek-v4-pro",
        temperature=0.1,
        max_tokens=2000,
    )


def get_langchain_compass_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=os.environ.get("NVIDIA_ENDPOINT", _DEFAULT_ENDPOINT),
        api_key=os.environ.get("NVIDIA_API_KEY", _DEFAULT_KEY),
        model="deepseek-ai/deepseek-v4-pro",
        temperature=0.0,
        max_tokens=1000,
    )
