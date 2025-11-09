import logging
import requests

from aiogram import Router, F
from aiogram.types import Message

from config import GROUP_ID, TROPHY_GROUP_CHAT_ID, API_BASE_URL

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

    api_url = API_BASE_URL or "http://localhost:8000"
    if not api_url.startswith("http"):
        api_url = "http://localhost:8000"

    endpoint_url = f"{api_url}/api/send_waves"
    params = {
        "chat_id": str(message.chat.id),
        "base_url": api_url,
    }

    if message.is_topic_message:
        params["message_thread_id"] = message.message_thread_id

    try:
        logger.info("Вызываем эндпоинт %s с параметрами %s", endpoint_url, params)
        response = requests.post(endpoint_url, params=params, timeout=60)

        if response.status_code == 200:
            logger.info("Скриншот волн успешно отправлен.")
            return

        try:
            error_detail = response.json().get("detail", "Unknown error")
        except ValueError:
            error_detail = response.text

        logger.error(
            "Ошибка API при отправке скриншота волн: %s - %s",
            response.status_code,
            error_detail,
        )
        await message.reply(f"❌ Ошибка при создании скриншота волн: {error_detail}")

    except requests.exceptions.RequestException as exc:
        logger.error("Ошибка запроса к API: %s", exc, exc_info=True)
        await message.reply(f"❌ Ошибка при обращении к API: {exc}")
    except Exception as exc:
        logger.error("Ошибка при обработке команды !волны: %s", exc, exc_info=True)
        await message.reply(f"❌ Ошибка при отправке волн: {exc}")

