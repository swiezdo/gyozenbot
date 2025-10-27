# /gyozenbot/handlers/profile.py
import sys
import os
import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

# Добавляем путь к miniapp_api для импорта db модуля
sys.path.append('/root/miniapp_api')
from db import get_user

from config import GROUP_ID, TOPIC_ID, LEGENDS_TOPIC_FIRST_MESSAGE

router = Router()

# Путь к базе данных miniapp_api
DB_PATH = "/root/miniapp_api/app.db"

# Настройка логирования
logger = logging.getLogger(__name__)

def _is_allowed_context(message: Message) -> bool:
    """
    Проверяет, разрешён ли контекст для команды профиля.
    """
    # ЛС - не разрешено
    if message.chat.type == "private":
        logger.debug(f"ЛС не разрешено для команды профиля")
        return False
    
    # Группа/супергруппа — только заданная группа
    if message.chat.type in ("group", "supergroup"):
        if message.chat.id != GROUP_ID:
            logger.debug(f"Чат {message.chat.id} не совпадает с разрешённым {GROUP_ID}")
            return False
        
        # Проверяем тему - разрешаем команду !п во всех темах основной группы
        if message.is_topic_message:
            logger.info(f"Сообщение в теме {message.message_thread_id}, команда !п разрешена во всех темах")
            return True
        else:
            logger.info(f"Сообщение не в теме, разрешено")
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
        text += f"💻 <b>Платформы:</b> {', '.join(platforms)}\n"
    
    # Режимы игры
    modes = profile_data.get('modes', [])
    if modes:
        text += f"🎯 <b>Режимы:</b> {', '.join(modes)}\n"
    
    # Цели
    goals = profile_data.get('goals', [])
    if goals:
        text += f"🎯 <b>Цели:</b> {', '.join(goals)}\n"
    
    # Сложности
    difficulties = profile_data.get('difficulties', [])
    if difficulties:
        text += f"⚡ <b>Сложности:</b> {', '.join(difficulties)}\n"
    
    # Трофеи
    trophies = profile_data.get('trophies', [])
    if trophies:
        text += f"🏆 <b>Трофеи:</b> {', '.join(trophies)}\n"
    
    return text

@router.message()
async def profile_command(message: Message):
    """
    Обработчик команды !п для просмотра профиля пользователя.
    """
    logger.info(f"Получено сообщение: '{message.text}' от пользователя {message.from_user.id} в чате {message.chat.id}")
    
    # Проверяем, что это команда !п
    if not message.text or message.text.strip() != "!п":
        logger.debug(f"Сообщение '{message.text}' не является командой !п, пропускаем")
        return
    
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
        
        # Получаем профиль из БД
        logger.info(f"Запрашиваем профиль пользователя {target_user_id} из БД {DB_PATH}")
        profile_data = get_user(DB_PATH, target_user_id)
        logger.info(f"Получены данные профиля: {profile_data}")
        
        # Форматируем и отправляем ответ
        formatted_profile = _format_profile(profile_data)
        logger.info(f"Отправляем ответ пользователю {message.from_user.id}")
        await message.reply(formatted_profile, parse_mode="HTML")
        logger.info(f"Ответ успешно отправлен")
        
    except Exception as e:
        # Обработка ошибок
        logger.error(f"Ошибка при обработке команды !п: {str(e)}", exc_info=True)
        error_msg = f"❌ Ошибка при получении профиля: {str(e)}"
        await message.reply(error_msg)
