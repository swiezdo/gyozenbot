# /gyozenbot/handlers/profile.py
import logging
from aiogram import Router, F
from aiogram.types import Message

from config import GROUP_ID, LEGENDS_TOPIC_FIRST_MESSAGE, TROPHY_GROUP_CHAT_ID
from api_client import api_get, api_post

# Разрешенные группы для команды !п
ALLOWED_GROUP_IDS = [
    GROUP_ID,  # Основная группа из конфига
    TROPHY_GROUP_CHAT_ID,  # Группа для трофеев
]

router = Router()

# Настройка логирования
logger = logging.getLogger(__name__)

def _is_allowed_context(message: Message) -> bool:
    """
    Проверяет, разрешён ли контекст для команды профиля.
    Разрешает команду в разрешенных группах.
    """
    # ЛС - не разрешено
    if message.chat.type == "private":
        logger.debug(f"ЛС не разрешено для команды профиля")
        return False
    
    # Группа/супергруппа — проверяем список разрешенных групп
    if message.chat.type in ("group", "supergroup"):
        if message.chat.id not in ALLOWED_GROUP_IDS:
            logger.debug(f"Чат {message.chat.id} не входит в список разрешённых групп {ALLOWED_GROUP_IDS}")
            return False
        
        # Разрешаем команду !п во всех темах разрешенных групп
        if message.is_topic_message:
            logger.info(f"Сообщение в теме {message.message_thread_id}, команда !п разрешена во всех темах")
            return True
        else:
            logger.info(f"Сообщение не в теме, команда !п разрешена")
            return True
    
    logger.debug(f"Неизвестный тип чата: {message.chat.type}")
    return False

def _get_target_user_id(message: Message) -> int:
    """
    Определяет user_id пользователя, чей профиль нужно показать.
    
    Логика:
    1. Если это reply на сообщение с ID темы (2673) → показать профиль автора команды
    2. Если это reply на другое сообщение → показать профиль автора того сообщения  
    3. Если просто команда !п → показать профиль автора команды
    """
    if message.reply_to_message:
        # Если ответ на сообщение с ID темы - это обычное сообщение в теме
        if message.reply_to_message.message_id == LEGENDS_TOPIC_FIRST_MESSAGE:
            return message.from_user.id
        else:
            # Ответ на реальное сообщение - показываем профиль автора того сообщения
            return message.reply_to_message.from_user.id
    else:
        # Просто команда без ответа - показываем профиль автора команды
        return message.from_user.id

@router.message(F.text == "!п")
async def profile_command(message: Message):
    """
    Обработчик команды !п для просмотра профиля пользователя.
    Отправляет скриншот профиля через API endpoint.
    """
    logger.info(f"Обнаружена команда !п от пользователя {message.from_user.id}")
    
    # Проверяем контекст
    if not _is_allowed_context(message):
        logger.warning(f"Команда !п от пользователя {message.from_user.id} в неразрешённом контексте (чат: {message.chat.id}, тема: {message.message_thread_id})")
        return
    
    logger.info(f"Контекст разрешён для команды !п от пользователя {message.from_user.id}")
    
    try:
        # Определяем целевого пользователя
        target_user_id = _get_target_user_id(message)
        logger.info(f"Целевой пользователь для команды !п: {target_user_id}")
        
        # Проверяем наличие пользователя через API
        response_wrapper = await api_get(f"/api/user_info/{target_user_id}")
        async with response_wrapper as response:
            if response.status == 404:
                logger.info("Профиль пользователя %s не найден", target_user_id)
                await message.reply("❌ Профиль не найден")
                return

            if response.status != 200:
                logger.error(
                    "Неожиданный ответ API /api/user_info/%s: %s",
                    target_user_id,
                    response.status,
                )
                await message.reply("❌ Ошибка при проверке профиля")
                return

        params = {
            "chat_id": str(message.chat.id),
        }
        if message.is_topic_message:
            params["message_thread_id"] = message.message_thread_id

        response_wrapper = await api_post(f"/api/send_profile/{target_user_id}", params=params)
        async with response_wrapper as response:
            if response.status == 200:
                logger.info("Скриншот профиля отправлен ботом для %s", target_user_id)
                return

            try:
                payload = await response.json()
                detail = payload.get("detail", "Unknown error")
            except Exception:
                detail = await response.text()

            logger.error(
                "Ошибка API при отправке скриншота профиля: %s - %s",
                response.status,
                detail,
            )
            await message.reply(f"❌ Ошибка при создании скриншота профиля: {detail}")
        
    except Exception as e:
        # Обработка других ошибок
        logger.error(f"Ошибка при обработке команды !п: {str(e)}", exc_info=True)
        error_msg = f"❌ Ошибка при получении профиля: {str(e)}"
        await message.reply(error_msg)
