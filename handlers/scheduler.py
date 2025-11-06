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
        
        logger.info("🤖 Генерирую утреннее приветствие от Гёдзена...")
        greeting = await get_response(prompt)
        
        if greeting:
            logger.info(f"✅ Приветствие сгенерировано, длина: {len(greeting)} символов")
            result = await bot.send_message(
                chat_id=GROUP_ID,
                text=greeting
            )
            logger.info(f"✅ Утреннее приветствие успешно отправлено в группу {GROUP_ID}, message_id: {result.message_id}")
        else:
            logger.warning("⚠️ Не удалось сгенерировать утреннее приветствие (пустой ответ от AI)")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке утреннего приветствия: {e}", exc_info=True)

async def scheduler_loop(bot: Bot):
    """Основной цикл планировщика - проверяет время каждую минуту"""
    global _last_sent_date
    
    logger.info("Планировщик утренних приветствий запущен")
    logger.info(f"Ожидаемое время отправки: {SEND_HOUR:02d}:{SEND_MINUTE:02d} (Europe/Berlin)")
    
    while True:
        try:
            # Получаем текущее время в немецком времени
            now_berlin = datetime.now(BERLIN_TZ)
            current_date = now_berlin.date()
            current_hour = now_berlin.hour
            current_minute = now_berlin.minute
            
            # Логируем текущее время каждую минуту для отладки
            logger.debug(f"Проверка времени: {now_berlin.strftime('%H:%M')} (Europe/Berlin), ожидаем {SEND_HOUR:02d}:{SEND_MINUTE:02d}, последняя отправка: {_last_sent_date}")
            
            # Проверяем, наступило ли время отправки и не отправляли ли уже сегодня
            if (current_hour == SEND_HOUR and 
                current_minute == SEND_MINUTE and 
                _last_sent_date != current_date):
                
                logger.info(f"⏰ Время отправки наступило! ({now_berlin.strftime('%H:%M')} Europe/Berlin)")
                logger.info(f"Последняя отправка была: {_last_sent_date}, текущая дата: {current_date}")
                await send_morning_greeting(bot)
                _last_sent_date = current_date
                logger.info(f"✅ Приветствие отправлено, _last_sent_date обновлена на {_last_sent_date}")
            elif current_hour == SEND_HOUR and current_minute == SEND_MINUTE:
                # Время совпадает, но уже отправляли сегодня
                logger.warning(f"⏰ Время отправки наступило ({now_berlin.strftime('%H:%M')} Europe/Berlin), но уже отправляли сегодня ({_last_sent_date})")
            else:
                # Время не совпадает - логируем только если близко к времени отправки (для отладки)
                if abs(current_hour - SEND_HOUR) <= 1 or (current_hour == SEND_HOUR and abs(current_minute - SEND_MINUTE) <= 5):
                    logger.debug(f"Время еще не наступило: {now_berlin.strftime('%H:%M')} (Europe/Berlin), ожидаем {SEND_HOUR:02d}:{SEND_MINUTE:02d}")
                
        except Exception as e:
            logger.error(f"Ошибка в цикле планировщика: {e}", exc_info=True)
        
        # Ждем 1 минуту перед следующей проверкой
        await asyncio.sleep(60)

async def start_scheduler(bot: Bot):
    """Запускает планировщик как фоновую задачу"""
    logger.info("🚀 Запуск планировщика утренних приветствий...")
    task = asyncio.create_task(scheduler_loop(bot))
    logger.info(f"✅ Планировщик запущен как фоновая задача: {task}")
    return task

