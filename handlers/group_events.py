# /gyozenbot/handlers/group_events.py
import logging
import os
from aiogram import Router, F
from aiogram.types import ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import GROUP_ID, MINI_APP_URL
from api_client import api_delete

# Настройка логирования
logger = logging.getLogger(__name__)

router = Router()


@router.chat_member(F.chat.id == GROUP_ID)
async def handle_member_status_change(event: ChatMemberUpdated):
    """
    Обработчик изменения статуса участника группы.
    Обрабатывает выход из группы и присоединение к группе.
    """
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status
    user_id = event.from_user.id
    
    # Обработка выхода из группы
    if old_status in ["member", "administrator", "restricted"]:
        if new_status in ["left", "kicked", "banned"]:
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
    
    # Обработка присоединения к группе
    elif old_status in ["left", "kicked", "banned"]:
        if new_status in ["member", "administrator", "restricted"]:
            logger.info(
                f"Пользователь {user_id} присоединился к группе. "
                f"Старый статус: {old_status}, новый статус: {new_status}"
            )
            
            try:
                # Формируем приветственное сообщение
                welcome_text = (
                    "🎉 <b>Добро пожаловать в группу Tsushima.Ru!</b>\n\n"
                    "Теперь вы можете пользоваться приложением. "
                    "Откройте мини-приложение, заполните профиль и начните использовать все возможности!"
                )
                
                # Создаем клавиатуру с кнопкой для открытия мини-приложения
                builder = InlineKeyboardBuilder()
                builder.add(InlineKeyboardButton(
                    text="Открыть приложение",
                    web_app=WebAppInfo(url=MINI_APP_URL)
                ))
                
                # Отправляем сообщение пользователю в личку
                banner_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "banner.png")
                if os.path.exists(banner_path):
                    photo = FSInputFile(banner_path)
                    await event.bot.send_photo(
                        chat_id=user_id,
                        photo=photo,
                        caption=welcome_text,
                        reply_markup=builder.as_markup(),
                        parse_mode="HTML"
                    )
                else:
                    await event.bot.send_message(
                        chat_id=user_id,
                        text=welcome_text,
                        reply_markup=builder.as_markup(),
                        parse_mode="HTML"
                    )
                
                logger.info(f"Приветственное сообщение отправлено пользователю {user_id}")
                
            except Exception as e:
                logger.error(
                    f"Исключение при отправке приветственного сообщения пользователю {user_id}: {str(e)}",
                    exc_info=True
                )

