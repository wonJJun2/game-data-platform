from typing import Protocol


class LLMClient(Protocol):
    provider: str
    model: str

    def generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
    ) -> str:
        ...