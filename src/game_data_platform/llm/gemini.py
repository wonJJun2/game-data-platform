import logging
import os
import re
import time

from google import genai
from google.genai import types
from google.genai.errors import ClientError


logger = logging.getLogger(__name__)


class GeminiClient:
    provider = "gemini"

    def __init__(self) -> None:
        api_key = os.environ["GEMINI_API_KEY"]

        self.model = os.environ["LLM_MODEL"]

        self.min_request_interval = float(
            os.getenv(
                "LLM_MIN_REQUEST_INTERVAL_SECONDS",
                "5",
            )
        )

        self._last_request_at = 0.0

        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=120_000,

                # 503/504 같은 서버 오류는 SDK가 짧게 재시도.
                # 429는 아래 generate()에서 별도로 처리한다.
                retry_options=types.HttpRetryOptions(
                    attempts=3,
                    initial_delay=1.0,
                    max_delay=10.0,
                    http_status_codes=[
                        408,
                        500,
                        502,
                        503,
                        504,
                    ],
                ),
            ),
        )

    def _throttle(self) -> None:
        elapsed = (
            time.monotonic()
            - self._last_request_at
        )

        remaining = (
            self.min_request_interval
            - elapsed
        )

        if remaining > 0:
            time.sleep(remaining)

        self._last_request_at = (
            time.monotonic()
        )

    @staticmethod
    def _get_retry_seconds(
        error: Exception,
    ) -> float:
        message = str(error)

        match = re.search(
            r"Please retry in ([0-9.]+)s",
            message,
        )

        if match:
            return float(
                match.group(1)
            )

        # RetryInfo를 파싱할 수 없는 경우
        # 무료 RPM window를 고려한 fallback
        return 60.0

    def generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
    ) -> str:
        config = types.GenerateContentConfig(
            system_instruction=(
                system_instruction
            ),
        )

        # 429 발생 시 최대 2번 추가 시도
        max_quota_retries = 2

        for attempt in range(
            max_quota_retries + 1
        ):
            self._throttle()

            try:
                response = (
                    self.client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=config,
                    )
                )

                if not response.text:
                    raise ValueError(
                        "LLM returned empty response"
                    )

                return response.text.strip()

            except ClientError as exc:
                status_code = getattr(
                    exc,
                    "status_code",
                    None,
                )

                if status_code != 429:
                    raise

                if attempt >= max_quota_retries:
                    raise

                retry_seconds = (
                    self._get_retry_seconds(
                        exc
                    )
                )

                # 서버가 알려준 quota reset보다
                # 약간 뒤에 다시 요청
                sleep_seconds = (
                    retry_seconds + 1
                )

                logger.warning(
                    "Gemini quota exceeded. "
                    "Retrying in %.1f seconds.",
                    sleep_seconds,
                )

                time.sleep(
                    sleep_seconds
                )

        raise RuntimeError(
            "Unexpected Gemini retry state"
        )