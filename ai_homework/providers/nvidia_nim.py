"""NVIDIA NIM provider (MiniMax M2.7)"""
import time
import logging
import httpx
from ai_homework.providers.base import AIProvider

logger = logging.getLogger(__name__)


class NvidiaNimProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        model: str = "minimaxai/minimax-m2.7",
        max_tokens: int = 2500,
        timeout: int = 60,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._max_tokens = max_tokens
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "NVIDIA NIM"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
    ) -> tuple[str | None, str | None]:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature,
                        "max_tokens": self._max_tokens,
                    },
                )
                duration = time.monotonic() - start

                if resp.status_code != 200:
                    logger.error(
                        "provider=%s model=%s status=%d duration=%.2fs",
                        self.name, self._model, resp.status_code, duration,
                    )
                    return None, f"NVIDIA NIM returned status {resp.status_code}"

                data = resp.json()
                text = data["choices"][0]["message"]["content"].strip()

                logger.info(
                    "provider=%s model=%s duration=%.2fs success=true",
                    self.name, self._model, duration,
                )
                return text, None

        except httpx.TimeoutException:
            duration = time.monotonic() - start
            logger.warning("provider=%s model=%s duration=%.2fs error=timeout", self.name, self._model, duration)
            return None, "NVIDIA NIM request timed out"
        except Exception as e:
            duration = time.monotonic() - start
            logger.warning("provider=%s model=%s duration=%.2fs error=%s", self.name, self._model, duration, str(e))
            return None, f"NVIDIA NIM error: {e}"
