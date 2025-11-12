# /gyozenbot/handlers/group_events.py
import logging
from aiogram import Router, F
from aiogram.types import ChatMemberUpdated

from config import GROUP_ID
from api_client import api_delete

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
                response_wrapper = await api_delete(
                    f"/api/users/{user_id}",
                    use_bot_token=True,
                )
                async with response_wrapper as response:
                    if response.status == 200:
                        logger.info(
                            "Успешно удалены все данные пользователя %s "
                            "из базы данных и файлов на сервере",
                            user_id,
                        )
                    elif response.status == 404:
                        logger.warning(
                            "Данные пользователя %s не найдены во время очистки",
                            user_id,
                        )
                    else:
                        detail = await response.text()
                        logger.error(
                            "Ошибка при удалении данных пользователя %s: %s %s",
                            user_id,
                            response.status,
                            detail,
                        )
            except Exception as e:
                logger.error(
                    f"Исключение при удалении данных пользователя {user_id}: {str(e)}",
                    exc_info=True
                )

