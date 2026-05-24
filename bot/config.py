"""Configuration for aiogram bot"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set")

DATABASE_URL: str = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/teacherhelper')

# AI Homework Providers
NVIDIA_NIM_API_KEY: str = os.getenv('NVIDIA_NIM_API_KEY', '')
NVIDIA_NIM_BASE_URL: str = os.getenv('NVIDIA_NIM_BASE_URL', 'https://integrate.api.nvidia.com/v1')
NVIDIA_NIM_MODEL: str = os.getenv('NVIDIA_NIM_MODEL', 'minimaxai/minimax-m2.7')
NVIDIA_NIM_MAX_TOKENS: int = int(os.getenv('NVIDIA_NIM_MAX_TOKENS', '2500'))
NVIDIA_NIM_TIMEOUT_SEC: int = int(os.getenv('NVIDIA_NIM_TIMEOUT_SEC', '60'))

MISTRAL_API_KEY: str = os.getenv('MISTRAL_API_KEY', '')
MISTRAL_MODEL: str = os.getenv('MISTRAL_MODEL', 'mistral-small-latest')

GROQ_API_KEY: str = os.getenv('GROQ_API_KEY', '')
GROQ_MODEL: str = os.getenv('GROQ_MODEL', 'llama-4-scout-17b-16e-instruct')