# /gyozenbot/handlers/moderation.py
import logging
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, ChatPermissions

# Настройка логирования
logger = logging.getLogger(__name__)

router = Router()


def _format_hours(hours: int) -> str:
    """
    Возвращает правильное склонение слова "час" в зависимости от числа.
    """
    if hours % 10 == 1 and hours % 100 != 11:
        return f"{hours} час"
    elif hours % 10 in (2, 3, 4) and hours % 100 not in (12, 13, 14):
        return f"{hours} часа"
    else:
        return f"{hours} часов"


async def _check_admin_rights(message: Message) -> bool:
    """
    Проверяет, является ли отправитель сообщения администратором группы.
    """
    if message.chat.type not in ("group", "supergroup"):
        return False
    
    if message.from_user is None:
        return False
    
    bot = message.bot
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in {"administrator", "creator"}
    except Exception as exc:
        logger.debug("Не удалось проверить права администратора: %s", exc)
        return False


async def _get_target_user(message: Message):
    """
    Извлекает целевого пользователя из reply_to_message.
    Возвращает user_id или None.
    """
    if not message.reply_to_message:
        return None
    
    if message.reply_to_message.from_user is None:
        return None
    
    return message.reply_to_message.from_user.id


@router.message(F.text == "!кик", F.reply_to_message)
async def kick_command(message: Message):
    """
    Обработчик команды !кик - кикает пользователя из группы.
    Работает только как ответ на сообщение.
    """
    logger.info(f"Обнаружена команда !кик от пользователя {message.from_user.id}")
    
    # Проверка контекста
    if message.chat.type not in ("group", "supergroup"):
        logger.debug("Команда !кик вызвана не в группе")
        return
    
    # Проверка прав администратора
    if not await _check_admin_rights(message):
        logger.warning(f"Пользователь {message.from_user.id} не является администратором")
        await message.reply("❌ Команда доступна только администраторам")
        return
    
    # Получение целевого пользователя
    target_user_id = await _get_target_user(message)
    if target_user_id is None:
        logger.warning("Не удалось определить целевого пользователя для !кик")
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    # Нельзя кикнуть самого себя
    if target_user_id == message.from_user.id:
        await message.reply("❌ Нельзя кикнуть самого себя")
        return
    
    try:
        bot = message.bot
        # Кикаем пользователя (баним и сразу разбаниваем)
        await bot.ban_chat_member(
            chat_id=message.chat.id,
            user_id=target_user_id,
            until_date=datetime.now() + timedelta(seconds=1)
        )
        await bot.unban_chat_member(
            chat_id=message.chat.id,
            user_id=target_user_id
        )
        
        logger.info(f"Пользователь {target_user_id} кикнут из группы {message.chat.id}")
        await message.reply("✅ Пользователь кикнут")
        
    except Exception as e:
        logger.error(f"Ошибка при кике пользователя {target_user_id}: {str(e)}", exc_info=True)
        await message.reply("❌ Ошибка при выполнении команды")


@router.message(F.text == "!бан", F.reply_to_message)
async def ban_command(message: Message):
    """
    Обработчик команды !бан - банит пользователя в группе.
    Работает только как ответ на сообщение.
    """
    logger.info(f"Обнаружена команда !бан от пользователя {message.from_user.id}")
    
    # Проверка контекста
    if message.chat.type not in ("group", "supergroup"):
        logger.debug("Команда !бан вызвана не в группе")
        return
    
    # Проверка прав администратора
    if not await _check_admin_rights(message):
        logger.warning(f"Пользователь {message.from_user.id} не является администратором")
        await message.reply("❌ Команда доступна только администраторам")
        return
    
    # Получение целевого пользователя
    target_user_id = await _get_target_user(message)
    if target_user_id is None:
        logger.warning("Не удалось определить целевого пользователя для !бан")
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    # Нельзя забанить самого себя
    if target_user_id == message.from_user.id:
        await message.reply("❌ Нельзя забанить самого себя")
        return
    
    try:
        bot = message.bot
        # Баним пользователя навсегда
        await bot.ban_chat_member(
            chat_id=message.chat.id,
            user_id=target_user_id
        )
        
        logger.info(f"Пользователь {target_user_id} забанен в группе {message.chat.id}")
        await message.reply("✅ Пользователь забанен")
        
    except Exception as e:
        logger.error(f"Ошибка при бане пользователя {target_user_id}: {str(e)}", exc_info=True)
        await message.reply("❌ Ошибка при выполнении команды")


@router.message(F.text.regexp(r"^!мут(\s+\d+)?$"), F.reply_to_message)
async def mute_command(message: Message):
    """
    Обработчик команды !мут - ограничивает права пользователя.
    Работает только как ответ на сообщение.
    Формат: !мут [часы] (по умолчанию 24 часа)
    """
    logger.info(f"Обнаружена команда !мут от пользователя {message.from_user.id}")
    
    # Проверка контекста
    if message.chat.type not in ("group", "supergroup"):
        logger.debug("Команда !мут вызвана не в группе")
        return
    
    # Проверка прав администратора
    if not await _check_admin_rights(message):
        logger.warning(f"Пользователь {message.from_user.id} не является администратором")
        await message.reply("❌ Команда доступна только администраторам")
        return
    
    # Получение целевого пользователя
    target_user_id = await _get_target_user(message)
    if target_user_id is None:
        logger.warning("Не удалось определить целевого пользователя для !мут")
        await message.reply("❌ Не удалось определить пользователя")
        return
    
    # Нельзя замутить самого себя
    if target_user_id == message.from_user.id:
        await message.reply("❌ Нельзя замутить самого себя")
        return
    
    # Парсинг времени из команды
    text = message.text or ""
    parts = text.split()
    hours = 24  # По умолчанию 24 часа
    
    if len(parts) > 1:
        try:
            hours = int(parts[1])
            if hours <= 0:
                await message.reply("❌ Время должно быть положительным числом")
                return
            if hours > 8760:  # Максимум 1 год (365 дней * 24 часа)
                await message.reply("❌ Максимальное время мута - 1 год")
                return
        except ValueError:
            await message.reply("❌ Неверный формат времени")
            return
    
    try:
        bot = message.bot
        # Вычисляем время окончания мута
        until_date = datetime.now() + timedelta(hours=hours)
        
        # Ограничиваем права пользователя (запрещаем отправку сообщений)
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        
        logger.info(
            f"Пользователь {target_user_id} замучен в группе {message.chat.id} на {hours} часов"
        )
        
        hours_text = _format_hours(hours)
        await message.reply(f"✅ Пользователь получил мут на {hours_text}")
        
    except Exception as e:
        logger.error(f"Ошибка при муте пользователя {target_user_id}: {str(e)}", exc_info=True)
        await message.reply("❌ Ошибка при выполнении команды")

