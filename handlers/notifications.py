# /gyozenbot/handlers/notifications.py
import logging
import re
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from config import GROUP_ID, LEGENDS_TOPIC_FIRST_MESSAGE
from api_client import api_get

router = Router()

# Настройка логирования
logger = logging.getLogger(__name__)

# Маппинг команд на типы уведомлений
COMMAND_MAPPING = {
    '!галочки': 'check',
    '!спидран': 'speedrun',
    '!набег': 'raid',
    '!призрак': 'ghost',
    '!хм': 'hellmode',
    '!сюжет': 'story',
    '!соперники': 'rivals',
    '!испытания': 'trials',
}


def _is_legends_topic(message: Message) -> bool:
    """
    Проверяет, что сообщение находится в теме LEGENDS.
    В Telegram форумах message_thread_id может быть равен ID первого сообщения темы.
    """
    if message.chat.id != GROUP_ID:
        logger.debug(f"Chat ID не совпадает: {message.chat.id} != {GROUP_ID}")
        return False
    
    if not message.is_topic_message:
        logger.debug("Сообщение не в теме")
        return False
    
    logger.debug(
        f"Проверка темы: message_thread_id={message.message_thread_id}, "
        f"LEGENDS_TOPIC_FIRST_MESSAGE={LEGENDS_TOPIC_FIRST_MESSAGE}"
    )
    
    if message.message_thread_id != LEGENDS_TOPIC_FIRST_MESSAGE:
        return False
    
    return True


def _extract_commands(text: str) -> list[str]:
    """
    Извлекает команды из текста сообщения.
    Возвращает список типов уведомлений.
    """
    if not text:
        return []
    
    found_commands = []
    text_lower = text.lower()
    
    for command, notification_type in COMMAND_MAPPING.items():
        # Ищем команду в тексте (команды начинаются с !, поэтому используем простой поиск)
        command_lower = command.lower()
        if command_lower in text_lower:
            found_commands.append(notification_type)
    
    return found_commands


def _format_message_url(chat_id: int, message_id: int) -> str:
    """
    Форматирует URL сообщения в формате t.me/c/{chat_id}/{message_id}.
    Убирает префикс -100 и минус из chat_id.
    """
    # Убираем минус и префикс -100
    chat_id_str = str(chat_id)
    if chat_id_str.startswith('-100'):
        chat_id_str = chat_id_str[4:]  # Убираем '-100'
    elif chat_id_str.startswith('-'):
        chat_id_str = chat_id_str[1:]  # Убираем только минус
    return f"https://t.me/c/{chat_id_str}/{message_id}"


async def _send_notification_to_user(
    bot,
    user_id: int,
    original_message: Message,
    notification_type: str
) -> bool:
    """
    Отправляет уведомление пользователю в личку.
    Пересылает сообщение и отправляет отдельное сообщение с кнопками.
    Возвращает True при успешной отправке, False при ошибке.
    """
    try:
        # Пересылаем сообщение
        await bot.forward_message(
            chat_id=user_id,
            from_chat_id=original_message.chat.id,
            message_id=original_message.message_id
        )
        
        # Создаем кнопки
        message_url = _format_message_url(
            original_message.chat.id,
            original_message.message_id
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Перейти", url=message_url),
                InlineKeyboardButton(text="Уведомления", callback_data="notifications_settings")
            ]
        ])
        
        # Отправляем сообщение с кнопками
        await bot.send_message(
            chat_id=user_id,
            text="🔔 Новое уведомление о поиске игроков",
            reply_markup=keyboard
        )
        
        return True
        
    except Exception as e:
        logger.warning(
            f"Не удалось отправить уведомление пользователю {user_id}: {e}"
        )
        return False


@router.message(
    F.chat.id == GROUP_ID,
    F.text
)
async def handle_notification_commands(message: Message):
    """
    Обработчик команд уведомлений в теме LEGENDS.
    Реагирует на команды в тексте и отправляет уведомления подписчикам.
    """
    # Проверяем, что это группа/супергруппа
    if message.chat.type not in ("group", "supergroup"):
        logger.debug(f"Сообщение не в группе/супергруппе: {message.chat.type}")
        return
    
    # Проверяем, что сообщение в теме LEGENDS
    if not _is_legends_topic(message):
        logger.debug(
            f"Сообщение не в теме LEGENDS: chat_id={message.chat.id}, "
            f"is_topic={message.is_topic_message}, thread_id={message.message_thread_id}"
        )
        return
    
    logger.debug(f"Проверяем текст сообщения: {message.text}")
    
    # Извлекаем команды из текста
    commands = _extract_commands(message.text or '')
    
    if not commands:
        logger.debug(f"Команды не найдены в тексте: {message.text}")
        return
    
    logger.info(
        f"Обнаружены команды уведомлений: {commands} в сообщении {message.message_id} "
        f"от пользователя {message.from_user.id}"
    )
    
    # Обрабатываем каждую найденную команду
    for notification_type in commands:
        try:
            # Получаем список подписчиков через API
            response_wrapper = await api_get(
                f"/api/notifications/{notification_type}",
                use_bot_token=True
            )
            
            async with response_wrapper as response:
                if response.status != 200:
                    logger.error(
                        f"Ошибка API при получении подписчиков для {notification_type}: "
                        f"status {response.status}"
                    )
                    continue
                
                data = await response.json()
                subscribers = data.get("subscribers", [])
                
                if not subscribers:
                    logger.info(f"Нет подписчиков для типа уведомления {notification_type}")
                    continue
                
                logger.info(
                    f"Найдено {len(subscribers)} подписчиков для типа {notification_type}"
                )
                
                # Отправляем уведомления каждому подписчику
                success_count = 0
                for user_id in subscribers:
                    if await _send_notification_to_user(
                        message.bot,
                        user_id,
                        message,
                        notification_type
                    ):
                        success_count += 1
                
                logger.info(
                    f"Отправлено {success_count} из {len(subscribers)} уведомлений "
                    f"для типа {notification_type}"
                )
        
        except Exception as e:
            logger.error(
                f"Ошибка при обработке команды {notification_type}: {e}",
                exc_info=True
            )

