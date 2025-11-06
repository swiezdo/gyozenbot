# /gyozenbot/handlers/group_events.py
import sys
import logging
from aiogram import Router, F
from aiogram.types import ChatMemberUpdated

# Добавляем путь к miniapp_api для импорта db модуля
sys.path.append('/root/miniapp_api')
from db import delete_user_all_data

from config import GROUP_ID

# Путь к базе данных miniapp_api
DB_PATH = "/root/miniapp_api/app.db"

# Настройка логирования
logger = logging.getLogger(__name__)

router = Router()


@router.chat_member(F.chat.id == GROUP_ID)
async def handle_member_left(event: ChatMemberUpdated):
    """
    Обработчик события выхода пользователя из группы.
    Удаляет все данные пользователя из базы данных при выходе.
    """
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status
    
    # Проверяем, что пользователь был участником и теперь вышел
    if old_status in ["member", "administrator", "restricted"]:
        if new_status in ["left", "kicked", "banned"]:
            user_id = event.from_user.id
            
            logger.info(
                f"Пользователь {user_id} покинул группу. "
                f"Старый статус: {old_status}, новый статус: {new_status}"
            )
            
            try:
                # Удаляем все данные пользователя
                success = delete_user_all_data(DB_PATH, user_id)
                
                if success:
                    logger.info(
                        f"Успешно удалены все данные пользователя {user_id} "
                        f"из базы данных и файлов на сервере"
                    )
                else:
                    logger.error(
                        f"Ошибка при удалении данных пользователя {user_id}. "
                        f"Возможно, пользователь не найден в базе данных."
                    )
            except Exception as e:
                logger.error(
                    f"Исключение при удалении данных пользователя {user_id}: {str(e)}",
                    exc_info=True
                )

