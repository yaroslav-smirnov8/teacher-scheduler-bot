"""Groq provider (Llama 4 / chatgpt-oss)"""
import time
import logging
import httpx
from ai_homework.providers.base import AIProvider

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "llama-4-scout-17b-16e-instruct",
        timeout: int = 60,
    ):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "Groq"

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
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature,
                        "max_tokens": 2500,
                    },
                )
                duration = time.monotonic() - start

                if resp.status_code != 200:
                    logger.error(
                        "provider=%s model=%s status=%d duration=%.2fs",
                        self.name, self._model, resp.status_code, duration,
                    )
                    return None, f"Groq returned status {resp.status_code}"

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
            return None, "Groq request timed out"
        except Exception as e:
            duration = time.monotonic() - start
            logger.warning("provider=%s model=%s duration=%.2fs error=%s", self.name, self._model, duration, str(e))
            return None, f"Groq error: {e}"
