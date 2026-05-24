"""Provider factory - builds provider chain from config"""
import logging
from bot.config import (
    NVIDIA_NIM_API_KEY, NVIDIA_NIM_BASE_URL, NVIDIA_NIM_MODEL,
    NVIDIA_NIM_MAX_TOKENS, NVIDIA_NIM_TIMEOUT_SEC,
    MISTRAL_API_KEY, MISTRAL_MODEL,
    GROQ_API_KEY, GROQ_MODEL,
)
from ai_homework.providers.base import AIProvider
from ai_homework.providers.nvidia_nim import NvidiaNimProvider
from ai_homework.providers.mistral import MistralProvider
from ai_homework.providers.groq import GroqProvider

logger = logging.getLogger(__name__)


def get_provider_chain() -> list[AIProvider]:
    providers: list[AIProvider] = []

    if NVIDIA_NIM_API_KEY:
        providers.append(NvidiaNimProvider(
            api_key=NVIDIA_NIM_API_KEY,
            base_url=NVIDIA_NIM_BASE_URL,
            model=NVIDIA_NIM_MODEL,
            max_tokens=NVIDIA_NIM_MAX_TOKENS,
            timeout=NVIDIA_NIM_TIMEOUT_SEC,
        ))
    else:
        logger.warning("NVIDIA_NIM_API_KEY not set — skipping NVIDIA NIM provider")

    if MISTRAL_API_KEY:
        providers.append(MistralProvider(
            api_key=MISTRAL_API_KEY,
            model=MISTRAL_MODEL,
        ))
    else:
        logger.warning("MISTRAL_API_KEY not set — skipping Mistral provider")

    if GROQ_API_KEY:
        providers.append(GroqProvider(
            api_key=GROQ_API_KEY,
            model=GROQ_MODEL,
        ))
    else:
        logger.warning("GROQ_API_KEY not set — skipping Groq provider")

    return providers
