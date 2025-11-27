# /gyozenbot/handlers/utils.py
"""
Утилиты для хэндлеров бота.
"""

from aiogram.types import Message
from config import (
    LEGENDS_TOPIC_FIRST_MESSAGE,
    MEMES_TOPIC_FIRST_MESSAGE,
    GYOZEN_TOPIC_FIRST_MESSAGE,
    YOTTO_TOPIC_FIRST_MESSAGE,
    VIDEOS_TOPIC_FIRST_MESSAGE,
    GUIDES_TOPIC_FIRST_MESSAGE,
)


# Список всех констант FIRST_MESSAGE для проверки
TOPIC_FIRST_MESSAGE_IDS = [
    LEGENDS_TOPIC_FIRST_MESSAGE,
    MEMES_TOPIC_FIRST_MESSAGE,
    GYOZEN_TOPIC_FIRST_MESSAGE,
    YOTTO_TOPIC_FIRST_MESSAGE,
    VIDEOS_TOPIC_FIRST_MESSAGE,
    GUIDES_TOPIC_FIRST_MESSAGE,
]


def get_target_user_id(message: Message) -> int:
    """
    Определяет user_id целевого пользователя для команд бота.
    
    Логика:
    1. Если это reply на сообщение с ID любого из *_TOPIC_FIRST_MESSAGE → 
       возвращает user_id автора команды (это обычное сообщение в теме, а не реальный ответ)
    2. Если это reply на другое сообщение → возвращает user_id автора того сообщения
    3. Если просто команда без reply → возвращает user_id автора команды
    
    Args:
        message: Сообщение с командой
        
    Returns:
        user_id целевого пользователя
    """
    if message.reply_to_message:
        # Если ответ на сообщение с ID одного из FIRST_MESSAGE - это обычное сообщение в теме
        if message.reply_to_message.message_id in TOPIC_FIRST_MESSAGE_IDS:
            return message.from_user.id
        else:
            # Ответ на реальное сообщение - возвращаем user_id автора того сообщения
            if message.reply_to_message.from_user is None:
                # Если в reply_to_message нет from_user, возвращаем автора команды
                return message.from_user.id
            return message.reply_to_message.from_user.id
    else:
        # Просто команда без ответа - возвращаем user_id автора команды
        return message.from_user.id

