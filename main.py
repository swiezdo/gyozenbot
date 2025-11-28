# /gyozenbot/main.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN
from handlers import (
    gyozen,
    waves_new,
    miniapp,
    profile,
    balance,
    help,
    inline,
    scheduler,
    group_events,
    waves_preview,
    moderation,
    notifications,
)

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(message)s"
    )

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()

    # Роутеры подключены в определенном порядке - порядок важен!
    # Более специфичные хэндлеры (например, moderation) должны быть перед общими (например, miniapp с F.reply_to_message)
    dp.include_routers(
        inline.router,      # inline queries - не конфликтует с message handlers
        help.router,        # команда /help
        moderation.router,  # команды модерации !кик, !бан, !мут (должен быть перед miniapp.router)
        gyozen.router,      # теперь с фильтром F.text.regexp() - не перехватывает все сообщения
        waves_new.router,   # новая команда /waves
        profile.router,     # команда !п
        balance.router,     # команда !баланс
        waves_preview.router,  # команда !волны
        notifications.router,  # обработка команд уведомлений в теме LEGENDS
        miniapp.router,     # команды /start, /build, callback queries, reply_to_message
        group_events.router, # обработка событий выхода из группы
    )

    # Запускаем планировщик утренних приветствий параллельно с polling
    scheduler_task = await scheduler.start_scheduler(bot)

    logging.info("Запуск polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
