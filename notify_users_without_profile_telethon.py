#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для получения всех участников группы через Telethon Client API
и уведомления тех, у кого нет профиля в БД.
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем путь к miniapp_api для импорта функций БД
sys.path.insert(0, str(Path(__file__).parent.parent / "miniapp_api"))

from telethon import TelegramClient
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, GROUP_ID, MINI_APP_URL, TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE
from db import get_user

# Путь к базе данных
DB_PATH = os.getenv("DB_PATH", "/root/miniapp_api/app.db")

# Файл сессии Telethon
SESSION_FILE = Path(__file__).parent / "telethon_session.session"


async def get_all_group_members(client: TelegramClient, group_id: int):
    """
    Получает список всех участников группы через Telethon.
    
    Args:
        client: Экземпляр TelegramClient
        group_id: ID группы
    
    Returns:
        Список user_id участников группы
    """
    user_ids = []
    
    try:
        # Получаем всех участников группы
        print("   Загружаю участников...")
        participants = await client.get_participants(group_id)
        
        for participant in participants:
            # Пропускаем ботов
            if not participant.bot and participant.id:
                user_ids.append(participant.id)
        
        print(f"   Найдено участников (не ботов): {len(user_ids)}")
        return user_ids
        
    except Exception as e:
        print(f"   Ошибка получения участников группы: {e}")
        import traceback
        traceback.print_exc()
        return []


async def check_user_in_db(user_id: int) -> bool:
    """Проверяет наличие пользователя в базе данных."""
    try:
        user = get_user(DB_PATH, user_id)
        return user is not None
    except Exception:
        return False


async def send_profile_invitation(bot: Bot, user_id: int):
    """Отправляет приглашение создать профиль пользователю."""
    try:
        message_text = (
            "👻 <b>Привет, призрак!</b>\n\n"
            "Я заметил, что ты являешься участником группы <b>Tsushima.Ru</b>, "
            "но у тебя ещё нет профиля в мини-приложении.\n\n"
            "Пожалуйста, удели время и создай профиль! Это даст тебе возможность:\n\n"
            "✨ Отслеживать свой прогресс мастерства\n"
            "🏆 Получать и отображать трофеи\n"
            "📊 Просматривать статистику и достижения\n"
            "👥 Видеть других участников и их профили\n"
            "📝 Создавать и делиться билдами\n"
            "💬 Комментировать и оценивать билды других игроков\n\n"
            "Создание профиля займёт всего пару минут!"
        )
        
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(
            text="Открыть приложение",
            web_app=WebAppInfo(url=MINI_APP_URL)
        ))
        
        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        
        print(f"✅ Сообщение отправлено пользователю {user_id}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения пользователю {user_id}: {e}")
        return False


async def main():
    """Основная функция скрипта."""
    print("=" * 60)
    print("Скрипт уведомления участников без профиля (через Telethon)")
    print("=" * 60)
    
    # Проверяем наличие API_ID и API_HASH
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("\n❌ Ошибка: TELEGRAM_API_ID и TELEGRAM_API_HASH должны быть установлены в .env")
        print("   Получите их здесь: https://my.telegram.org/apps")
        return
    
    # Создаем клиент Telethon
    client = TelegramClient(str(SESSION_FILE), int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
    
    # Создаем бота для отправки сообщений
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    
    try:
        # Подключаемся к Telegram через Telethon
        print("\n🔌 Подключаюсь к Telegram через Telethon...")
        if TELEGRAM_PHONE:
            await client.start(phone=TELEGRAM_PHONE)
        else:
            await client.start()
        print("✅ Подключено!")
        
        # Получаем всех участников группы
        print(f"\n📋 Получаю список всех участников группы {GROUP_ID}...")
        all_user_ids = await get_all_group_members(client, GROUP_ID)
        
        if not all_user_ids:
            print("❌ Не удалось получить список участников")
            return
        
        print(f"\n🔍 Проверяю {len(all_user_ids)} пользователей на наличие профиля в БД...")
        
        users_without_profile = []
        users_checked = 0
        
        for user_id in all_user_ids:
            users_checked += 1
            
            # Проверяем наличие в БД
            has_profile = await check_user_in_db(user_id)
            
            if not has_profile:
                users_without_profile.append(user_id)
                print(f"⚠️  Пользователь {user_id} не имеет профиля в БД")
            else:
                if users_checked % 20 == 0:  # Показываем прогресс каждые 20 пользователей
                    print(f"✓  Проверено {users_checked}/{len(all_user_ids)}...")
        
        print(f"\n📊 Результаты проверки:")
        print(f"   Всего участников: {len(all_user_ids)}")
        print(f"   Проверено: {users_checked}")
        print(f"   Без профиля: {len(users_without_profile)}")
        
        if not users_without_profile:
            print("\n✅ Все участники группы имеют профиль!")
            return
        
        # Спрашиваем подтверждение перед отправкой
        print(f"\n⚠️  Будет отправлено {len(users_without_profile)} сообщений.")
        response = input("Продолжить? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y', 'да', 'д']:
            print("❌ Отменено пользователем")
            return
        
        # Отправляем сообщения
        print(f"\n📤 Отправляю сообщения...")
        sent_count = 0
        failed_count = 0
        
        for i, user_id in enumerate(users_without_profile, 1):
            success = await send_profile_invitation(bot, user_id)
            if success:
                sent_count += 1
            else:
                failed_count += 1
            
            # Показываем прогресс
            if i % 10 == 0:
                print(f"   Отправлено {i}/{len(users_without_profile)}...")
            
            # Задержка между отправками
            await asyncio.sleep(1)
        
        print(f"\n✅ Готово!")
        print(f"   Успешно отправлено: {sent_count}")
        print(f"   Ошибок: {failed_count}")
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

