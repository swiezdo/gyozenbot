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


# --- Бот ----------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")            # из .env
if not BOT_TOKEN:
    _fail("❌ BOT_TOKEN не найден в .env!")

# --- AI --------------
AI_PROVIDER = os.getenv("AI_PROVIDER", "")  # "openai" | "deepseek"
FINE_TUNED_MODEL = None           # например, "ft:gpt-4o-..."

TEMPERATURE = 0.8
MAX_TOKENS = 1000

# --- Telegram / Группы и темы (храним тут, не в .env - это не секреты) ---------------
OWNER_ID = 1053983438             # ID владельца
GROUP_ID = -1002365374672         # ID основной группы
GYOZEN_TOPIC_ID = 847             # ID темы для гёдзена (ИИ)
TROPHY_GROUP_CHAT_ID = -1002348168326  # ID группы для трофеев
CONGRATULATION_GROUP_ID = -1002348168326

# --- Картинки (через OpenAI DALL·E) --------------------------
IMAGE_MODEL = "dall-e-3"
IMAGE_SIZE  = "1024x1024"

# --- Ключи API (из .env — только секреты) --------------------
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# --- Мини-приложение ----------------------------------------
MINI_APP_URL = "https://tsushimaru.com/"
API_BASE_URL = "https://api.tsushimaru.com"

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
