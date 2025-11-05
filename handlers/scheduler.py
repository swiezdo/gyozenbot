# /gyozenbot/handlers/scheduler.py
import asyncio
import logging
from datetime import datetime, date
from zoneinfo import ZoneInfo

from aiogram import Bot
from ai_client import get_response
from config import GROUP_ID

logger = logging.getLogger(__name__)

# Таймзона для Москвы
MOSCOW_TZ = ZoneInfo("Europe/Moscow")
# Время отправки (9:00)
SEND_HOUR = 9
SEND_MINUTE = 0

# Дата последней отправки (для защиты от повторной отправки)
_last_sent_date: date | None = None

async def send_morning_greeting(bot: Bot):
    """Отправляет утреннее приветствие от Гёдзена в группу"""
    try:
        prompt = "Напиши краткое утреннее приветствие в своем стиле. Пожелай всем хорошего дня, используя метафоры и эпические образы, как в древних легендах."
        
        logger.info("Генерирую утреннее приветствие от Гёдзена...")
        greeting = await get_response(prompt)
        
        if greeting:
            await bot.send_message(
                chat_id=GROUP_ID,
                text=greeting
            )
            logger.info(f"Утреннее приветствие отправлено в группу {GROUP_ID}")
        else:
            logger.warning("Не удалось сгенерировать утреннее приветствие")
            
    except Exception as e:
        logger.error(f"Ошибка при отправке утреннего приветствия: {e}", exc_info=True)

async def scheduler_loop(bot: Bot):
    """Основной цикл планировщика - проверяет время каждую минуту"""
    global _last_sent_date
    
    logger.info("Планировщик утренних приветствий запущен")
    
    while True:
        try:
            # Получаем текущее время в МСК
            now_moscow = datetime.now(MOSCOW_TZ)
            current_date = now_moscow.date()
            current_hour = now_moscow.hour
            current_minute = now_moscow.minute
            
            # Проверяем, наступило ли время отправки (10:00) и не отправляли ли уже сегодня
            if (current_hour == SEND_HOUR and 
                current_minute == SEND_MINUTE and 
                _last_sent_date != current_date):
                
                logger.info(f"Время отправки наступило ({now_moscow.strftime('%H:%M')} МСК)")
                await send_morning_greeting(bot)
                _last_sent_date = current_date
                
        except Exception as e:
            logger.error(f"Ошибка в цикле планировщика: {e}", exc_info=True)
        
        # Ждем 1 минуту перед следующей проверкой
        await asyncio.sleep(60)

async def start_scheduler(bot: Bot):
    """Запускает планировщик как фоновую задачу"""
    asyncio.create_task(scheduler_loop(bot))

