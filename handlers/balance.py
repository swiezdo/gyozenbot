# /gyozenbot/handlers/balance.py
import logging
from aiogram import Router, F
from aiogram.types import Message

from config import GROUP_ID, TROPHY_GROUP_CHAT_ID
from api_client import api_get
from handlers.utils import get_target_user_id

# Разрешенные группы для команды !баланс
ALLOWED_GROUP_IDS = [
    GROUP_ID,  # Основная группа из конфига
    TROPHY_GROUP_CHAT_ID,  # Группа для трофеев
]

router = Router()

# Настройка логирования
logger = logging.getLogger(__name__)


def _is_allowed_context(message: Message) -> bool:
    """
    Проверяет, разрешён ли контекст для команды баланса.
    Разрешает команду в разрешенных группах.
    """
    # ЛС - не разрешено
    if message.chat.type == "private":
        logger.debug(f"ЛС не разрешено для команды баланса")
        return False
    
    # Группа/супергруппа — проверяем список разрешенных групп
    if message.chat.type in ("group", "supergroup"):
        if message.chat.id not in ALLOWED_GROUP_IDS:
            logger.debug(f"Чат {message.chat.id} не входит в список разрешённых групп {ALLOWED_GROUP_IDS}")
            return False
        
        # Разрешаем команду !баланс во всех темах разрешенных групп
        if message.is_topic_message:
            logger.info(f"Сообщение в теме {message.message_thread_id}, команда !баланс разрешена во всех темах")
            return True
        else:
            logger.info(f"Сообщение не в теме, команда !баланс разрешена")
            return True
    
    logger.debug(f"Неизвестный тип чата: {message.chat.type}")
    return False


@router.message(F.text == "!баланс")
async def balance_command(message: Message):
    """
    Обработчик команды !баланс для просмотра баланса пользователя.
    Показывает баланс целевого пользователя в формате "Баланс @участника - N Магатама 🪙"
    """
    logger.info(f"Обнаружена команда !баланс от пользователя {message.from_user.id}")
    
    # Проверяем контекст
    if not _is_allowed_context(message):
        logger.warning(f"Команда !баланс от пользователя {message.from_user.id} в неразрешённом контексте (чат: {message.chat.id}, тема: {message.message_thread_id})")
        return
    
    logger.info(f"Контекст разрешён для команды !баланс от пользователя {message.from_user.id}")
    
    try:
        # Определяем целевого пользователя
        target_user_id = get_target_user_id(message)
        logger.info(f"Целевой пользователь для команды !баланс: {target_user_id}")
        
        # Получаем информацию о пользователе через API
        response_wrapper = await api_get(f"/api/user_info/{target_user_id}")
        async with response_wrapper as response:
            if response.status == 404:
                logger.info("Пользователь %s не найден", target_user_id)
                await message.reply("❌ Пользователь не найден")
                return

            if response.status != 200:
                logger.error(
                    "Неожиданный ответ API /api/user_info/%s: %s",
                    target_user_id,
                    response.status,
                )
                await message.reply("❌ Ошибка при получении баланса")
                return

            # Получаем данные пользователя
            user_data = await response.json()
            balance = user_data.get("balance", 0)
            
            # Получаем username пользователя для упоминания
            user_mention = str(target_user_id)  # fallback на user_id
            try:
                bot = message.bot
                chat_info = await bot.get_chat(target_user_id)
                if chat_info.username:
                    user_mention = f"@{chat_info.username}"
                elif chat_info.first_name:
                    user_mention = chat_info.first_name
                else:
                    user_mention = str(target_user_id)
            except Exception as e:
                logger.error("Ошибка получения username пользователя %s: %s", target_user_id, e)
                user_mention = str(target_user_id)
            
            # Формируем ответ
            balance_text = f"Баланс {user_mention} — {balance} Магатама 🪙"
            await message.reply(balance_text)
            logger.info("Баланс пользователя %s отправлен: %d Магатама", target_user_id, balance)
        
    except Exception as e:
        # Обработка других ошибок
        logger.error(f"Ошибка при обработке команды !баланс: {str(e)}", exc_info=True)
        error_msg = f"❌ Ошибка при получении баланса: {str(e)}"
        await message.reply(error_msg)

