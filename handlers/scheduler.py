# /gyozenbot/handlers/scheduler.py
import asyncio
import logging
from datetime import datetime, date
from zoneinfo import ZoneInfo

from aiogram import Bot
from ai_client import get_response
from config import GROUP_ID

logger = logging.getLogger(__name__)

# Таймзона для Берлина (немецкое время)
BERLIN_TZ = ZoneInfo("Europe/Berlin")
# Время отправки (9:00)
SEND_HOUR = 9
SEND_MINUTE = 0

# Дата последней отправки (для защиты от повторной отправки)
_last_sent_date: date | None = None

async def send_morning_greeting(bot: Bot):
    """Отправляет утреннее приветствие от Гёдзена в группу"""
    try:
        prompt = "Напиши краткое утреннее приветствие в своем стиле. Пожелай всем хорошего дня, используя метафоры и эпические образы, как в древних легендах."
        
        greeting = await get_response(prompt)
        
        if greeting:
            await bot.send_message(
                chat_id=GROUP_ID,
                text=greeting
            )
            
    except Exception as e:
        pass

async def scheduler_loop(bot: Bot):
    """Основной цикл планировщика - проверяет время каждую минуту"""
    global _last_sent_date
    
    while True:
        try:
            # Получаем текущее время в немецком времени
            now_berlin = datetime.now(BERLIN_TZ)
            current_date = now_berlin.date()
            current_hour = now_berlin.hour
            current_minute = now_berlin.minute
            
            # Проверяем, наступило ли время отправки и не отправляли ли уже сегодня
            if (current_hour == SEND_HOUR and 
                current_minute == SEND_MINUTE and 
                _last_sent_date != current_date):
                
                await send_morning_greeting(bot)
                _last_sent_date = current_date
                
        except Exception as e:
            pass
        
        # Ждем 1 минуту перед следующей проверкой
        await asyncio.sleep(60)

async def start_scheduler(bot: Bot):
    """Запускает планировщик как фоновую задачу"""
    task = asyncio.create_task(scheduler_loop(bot))
    return task

