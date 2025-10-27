# /gyozenbot/main.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN
from handlers import gyozen, waves, miniapp

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

    dp.include_routers(
        miniapp.router,
        waves.router,
        gyozen.router
    )

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
