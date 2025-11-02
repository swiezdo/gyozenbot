# /gyozenbot/handlers/profile.py
import sys
import os
import logging
import requests
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

# Добавляем путь к miniapp_api для импорта db модуля
sys.path.append('/root/miniapp_api')
from db import get_user

from config import GROUP_ID, LEGENDS_TOPIC_FIRST_MESSAGE, API_BASE_URL

# Разрешенные группы для команды !п
ALLOWED_GROUP_IDS = [
    GROUP_ID,  # Основная группа из конфига
    -1002348168326,  # Группа для трофеев (из miniapp_api/app.py)
]

router = Router()

# Путь к базе данных miniapp_api
DB_PATH = "/root/miniapp_api/app.db"

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

def _format_profile(profile_data: dict) -> str:
    """
    Форматирует данные профиля в красивое сообщение.
    """
    if not profile_data:
        return "❌ Профиль не найден"
    
    # Проверяем, заполнен ли профиль
    if not profile_data.get('real_name') and not profile_data.get('psn_id'):
        return "❌ Пользователь не зарегистрирован или профиль не заполнен"
    
    # Формируем сообщение
    text = "👤 <b>Профиль пользователя</b>\n\n"
    
    # Реальное имя
    if profile_data.get('real_name'):
        text += f"📝 <b>Имя:</b> {profile_data['real_name']}\n"
    
    # PSN ID
    if profile_data.get('psn_id'):
        text += f"🎮 <b>PSN ID:</b> {profile_data['psn_id']}\n"
    
    # Платформы
    platforms = profile_data.get('platforms', [])
    if platforms:
        text += f"💻 <b>Платформы:</b>\n"
        for platform in platforms:
            text += f"- {platform}\n"
    
    # Режимы игры
    modes = profile_data.get('modes', [])
    if modes:
        text += f"🎲 <b>Режимы:</b>\n"
        for mode in modes:
            text += f"- {mode}\n"
    
    # Цели
    goals = profile_data.get('goals', [])
    if goals:
        text += f"🎯 <b>Цели:</b>\n"
        for goal in goals:
            text += f"- {goal}\n"
    
    # Сложности
    difficulties = profile_data.get('difficulties', [])
    if difficulties:
        text += f"⚡ <b>Сложности:</b>\n"
        for difficulty in difficulties:
            text += f"- {difficulty}\n"
    
    # Трофеи удалены из системы
    
    return text

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
        
        # Получаем профиль из БД для проверки существования
        logger.info(f"Запрашиваем профиль пользователя {target_user_id} из БД {DB_PATH}")
        profile_data = get_user(DB_PATH, target_user_id)
        
        if not profile_data:
            error_msg = "❌ Профиль не найден"
            await message.reply(error_msg)
            return
        
        # Подготавливаем параметры для API запроса
        chat_id = str(message.chat.id)
        message_thread_id = message.message_thread_id if message.is_topic_message else None
        
        # Определяем URL API
        api_url = os.getenv("API_BASE_URL", API_BASE_URL or "http://localhost:8000")
        if not api_url.startswith("http"):
            api_url = "http://localhost:8000"
        
        endpoint_url = f"{api_url}/api/send_profile/{target_user_id}"
        
        # Параметры запроса
        params = {
            "chat_id": chat_id
        }
        if message_thread_id:
            params["message_thread_id"] = message_thread_id
        
        logger.info(f"Вызываем API endpoint: {endpoint_url} с параметрами: {params}")
        
        # Вызываем API endpoint
        response = requests.post(endpoint_url, params=params, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Скриншот профиля успешно отправлен: {result.get('message', 'OK')}")
            # Не отправляем дополнительное сообщение, фото уже отправлено
        else:
            error_detail = response.json().get('detail', 'Unknown error') if response.status_code < 500 else response.text
            logger.error(f"Ошибка API при отправке скриншота: {response.status_code} - {error_detail}")
            error_msg = f"❌ Ошибка при создании скриншота профиля: {error_detail}"
            await message.reply(error_msg)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса к API: {str(e)}", exc_info=True)
        error_msg = f"❌ Ошибка при обращении к API: {str(e)}"
        await message.reply(error_msg)
    except Exception as e:
        # Обработка других ошибок
        logger.error(f"Ошибка при обработке команды !п: {str(e)}", exc_info=True)
        error_msg = f"❌ Ошибка при получении профиля: {str(e)}"
        await message.reply(error_msg)
