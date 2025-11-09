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
    inline,
    scheduler,
    group_events,
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

    # Роутеры подключены в произвольном порядке - порядок не важен,
    # так как все обработчики используют специфичные фильтры
    dp.include_routers(
        inline.router,      # inline queries - не конфликтует с message handlers
        gyozen.router,      # теперь с фильтром F.text.regexp() - не перехватывает все сообщения
        waves_new.router,   # новая команда /waves
        profile.router,     # команда !п
        miniapp.router,     # команды /start, /build, callback queries, reply_to_message
        group_events.router, # обработка событий выхода из группы
    )

    # Запускаем планировщик утренних приветствий параллельно с polling
    scheduler_task = await scheduler.start_scheduler(bot)

    logging.info("Запуск polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
