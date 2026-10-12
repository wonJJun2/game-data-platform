import os

from game_data_platform.llm.base import LLMClient
from game_data_platform.llm.gemini import GeminiClient


def create_llm_client() -> LLMClient:
    provider = os.getenv(
        "LLM_PROVIDER",
        "gemini",
    ).lower()

    if provider == "gemini":
        return GeminiClient()

    raise ValueError(
        f"Unsupported LLM provider: {provider}"
    )