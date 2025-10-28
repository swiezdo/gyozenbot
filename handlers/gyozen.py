import re
import time
import random
from aiogram import Router
from aiogram.types import Message

from waiting_phrases import WAITING_PHRASES
from ai_client import get_response
from image_generator import generate_image
from config import GROUP_ID, GYOZEN_TOPIC_ID, OWNER_ID

router = Router()

PATTERN = re.compile(r"г[ёе]д[зс][еэ]н", re.IGNORECASE)
RECENT_SECONDS = 60

def _is_recent(ts: float) -> bool:
    return time.time() - ts <= RECENT_SECONDS

def _is_allowed_context(m: Message) -> bool:
    # ЛС — только владельцу (на всякий случай)
    if m.chat.type == "private":
        return m.from_user and m.from_user.id == OWNER_ID
    # Группа/супергруппа — только заданная группа и тема
    if m.chat.type in ("group", "supergroup"):
        if m.chat.id != GROUP_ID:
            return False
        return bool(m.is_topic_message and m.message_thread_id == GYOZEN_TOPIC_ID)
    return False

@router.message()
async def gyozen_entrypoint(message: Message):
    text = (message.text or "").strip()
    print(f"DEBUG: Получено сообщение для гёдзена: '{text}' от {message.from_user.id}")
    
    if not text:
        print("DEBUG: Пустое сообщение, пропускаем")
        return
    if not _is_recent(message.date.timestamp()):
        print("DEBUG: Сообщение не свежее, пропускаем")
        return
    if not _is_allowed_context(message):
        print(f"DEBUG: Контекст не разрешен - чат: {message.chat.id}, тип: {message.chat.type}, тема: {message.message_thread_id}")
        print(f"DEBUG: Ожидается GROUP_ID: {GROUP_ID}, GYOZEN_TOPIC_ID: {GYOZEN_TOPIC_ID}")
        return
    if not PATTERN.search(text):
        print("DEBUG: Паттерн 'гёдзен' не найден, пропускаем")
        return
    
    print("DEBUG: Обрабатываем сообщение гёдзена")

    # Ветка "нарисуй ..."
    m = re.search(r"г[ёе]д[зс][еэ]н.*нарисуй(.*)$", text, re.IGNORECASE | re.DOTALL)
    if m:
        prompt_tail = (m.group(1) or "").strip()
        if not prompt_tail:
            await message.reply("Опиши, что ты хочешь увидеть.")
            return
        wait_msg = await message.reply("Генерирую изображение... 🎨")
        url = await generate_image(prompt_tail)
        if url:
            await wait_msg.delete()
            await message.reply_photo(url, caption="Готово. 🎭")
        else:
            await wait_msg.edit_text("Не вышло создать изображение. Попробуй иначе сформулировать.")
        return

    # Обычный ИИ-ответ
    waiting = await message.reply(random.choice(WAITING_PHRASES))
    reply = await get_response(text)
    try:
        await waiting.edit_text(reply)
    except Exception:
        await message.reply(reply)
