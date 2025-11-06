# /gyozenbot/main.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN
from handlers import gyozen, waves, miniapp, profile, inline, scheduler

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
        waves.router,       # команды !волны и !записатьволны
        profile.router,     # команда !п
        miniapp.router,     # команды /start, /build, callback queries, reply_to_message
    )

    # Запускаем планировщик утренних приветствий параллельно с polling
    logging.info("Инициализация планировщика...")
    scheduler_task = await scheduler.start_scheduler(bot)
    logging.info(f"Планировщик инициализирован, задача: {scheduler_task}")

    logging.info("Запуск polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
