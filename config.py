# /gyozenbot/config.py
from dotenv import load_dotenv
import os
import sys

# Загружаем переменные из .env (только секреты/токены)
load_dotenv()

# --- Helpers -------------------------------------------------
def _as_int_env(name: str, default: int | None) -> int | None:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default

def _fail(msg: str):
    print(msg, file=sys.stderr)
    raise SystemExit(1)

# Доп. хелперы для легаси-переменных (безопасные дефолты)
def _as_float_env(name: str, default: float) -> float:
    v = os.getenv(name)
    try:
        return float(v) if v is not None else default
    except ValueError:
        return default

def _as_int_env_default(name: str, default: int) -> int:
    v = os.getenv(name)
    try:
        return int(v) if v is not None else default
    except ValueError:
        return default

# --- Бот ----------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")            # из .env
if not BOT_TOKEN:
    _fail("❌ BOT_TOKEN не найден в .env!")

GROUP_LINK = "https://t.me/+ZFiVYVrz-PEzYjBi"

# --- AI --------------
AI_PROVIDER = "deepseek"          # "openai" | "deepseek"
FINE_TUNED_MODEL = None           # например, "ft:gpt-4o-..."

TEMPERATURE = 0.8
MAX_TOKENS = 1000

# --- Legacy/compat для старого кода (ai_client.py и др.) -----
# Эти переменные часто импортируют напрямую из config.
MODEL_NAME         = os.getenv("MODEL_NAME", FINE_TUNED_MODEL or "gpt-4o-mini")
TOP_P              = _as_float_env("TOP_P", 1.0)
FREQUENCY_PENALTY  = _as_float_env("FREQUENCY_PENALTY", 0.0)
PRESENCE_PENALTY   = _as_float_env("PRESENCE_PENALTY", 0.0)
SYSTEM_PROMPT      = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant for Tsushima.Ru bot.")

# --- Telegram / Группа (храним тут, не в .env) ---------------
# Подставь свои реальные ID ниже:
OWNER_ID = 1053983438             # ID владельца
GROUP_ID = -1002365374672         # ID группы
GYOZEN_TOPIC_ID = 847              # ID темы для гёдзена (ИИ)

# (Если вдруг захочешь брать из env, можно раскомментить):
# OWNER_ID = _as_int_env("OWNER_ID", 1053983438)
# GROUP_ID = _as_int_env("GROUP_ID", -1002365374672)
# TOPIC_ID = _as_int_env("TOPIC_ID", 847)

# --- Картинки (через OpenAI DALL·E) --------------------------
IMAGE_MODEL = "dall-e-3"
IMAGE_SIZE  = "1024x1024"

# --- Ключи API (из .env — только секреты) --------------------
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# --- Мини-приложение ----------------------------------------
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://swiezdo.github.io/tsushimaru_app/")
API_BASE_URL = os.getenv("API_BASE_URL", "https://tsushimaru.com")

# Группа для поздравлений участников
CONGRATULATIONS_CHAT_ID = os.getenv("CONGRATULATIONS_CHAT_ID", "-1002365374672")

# --- Константы для тем -------------------------------------
# ID первого сообщения темы "legends" - если ответ на это сообщение, 
# то это обычное сообщение в теме, а не реальный ответ
LEGENDS_TOPIC_FIRST_MESSAGE = 2673

# --- Валидация конфигурации ----------------------------------
# Для текста:
if AI_PROVIDER not in ("openai", "deepseek"):
    _fail("❌ AI_PROVIDER должен быть 'openai' или 'deepseek'.")

if AI_PROVIDER == "openai" and not (OPENAI_API_KEY or FINE_TUNED_MODEL):
    # Даже с Fine-tune ключ обычно нужен, но оставим мягкую проверку:
    print("⚠️ Внимание: AI_PROVIDER=openai, а OPENAI_API_KEY пуст. Убедись, что доступ к модели есть.", file=sys.stderr)

if AI_PROVIDER == "deepseek" and not DEEPSEEK_API_KEY:
    _fail("❌ AI_PROVIDER=deepseek, но DEEPSEEK_API_KEY пуст — добавь его в .env.")

# Для картинок (DALL·E):
if not OPENAI_API_KEY:
    print("⚠️ Для генерации изображений (DALL·E) нужен OPENAI_API_KEY в .env. Иначе image_generator не заработает.", file=sys.stderr)
