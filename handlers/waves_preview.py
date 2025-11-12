import logging
from aiogram import Router, F
from aiogram.types import Message

from config import GROUP_ID, TROPHY_GROUP_CHAT_ID
from api_client import api_post

ALLOWED_GROUP_IDS = [
    GROUP_ID,
    TROPHY_GROUP_CHAT_ID,
]

router = Router()
logger = logging.getLogger(__name__)


def _is_allowed_context(message: Message) -> bool:
    if message.chat.type == "private":
        logger.debug("Команда !волны недоступна в личных сообщениях")
        return False

    if message.chat.type in ("group", "supergroup"):
        if message.chat.id not in ALLOWED_GROUP_IDS:
            logger.debug(
                "Чат %s не входит в разрешённый список %s",
                message.chat.id,
                ALLOWED_GROUP_IDS,
            )
            return False
        return True

    logger.debug("Неизвестный тип чата: %s", message.chat.type)
    return False


@router.message(F.text == "!волны")
async def waves_command(message: Message):
    """
    Отправляет в чат скриншот текущей ротации волн.
    """
    logger.info("Обнаружена команда !волны от пользователя %s", message.from_user.id)

    if not _is_allowed_context(message):
        logger.info(
            "Команда !волны отклонена: чат %s не разрешён",
            message.chat.id,
        )
        return

    params = {
        "chat_id": str(message.chat.id),
    }

    if message.is_topic_message:
        params["message_thread_id"] = message.message_thread_id

    try:
        response_wrapper = await api_post("/api/send_waves", params=params)
        async with response_wrapper as response:
            if response.status == 200:
                logger.info("Скриншот волн успешно отправлен.")
                return

            try:
                payload = await response.json()
                error_detail = payload.get("detail", "Unknown error")
            except Exception:
                error_detail = await response.text()

            logger.error(
                "Ошибка API при отправке скриншота волн: %s - %s",
                response.status,
                error_detail,
            )
            await message.reply(f"❌ Ошибка при создании скриншота волн: {error_detail}")

    except Exception as exc:
        logger.error("Ошибка при обработке команды !волны: %s", exc, exc_info=True)
        await message.reply(f"❌ Ошибка при отправке волн: {exc}")

