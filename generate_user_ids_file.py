#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Вспомогательный скрипт для создания файла user_ids.txt со списком участников группы.

Собирает user_id из различных источников:
1. Администраторы группы
2. Пользователи из БД (которые уже были в группе)
3. Можно добавить другие источники
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем путь к miniapp_api для импорта функций БД
sys.path.insert(0, str(Path(__file__).parent.parent / "miniapp_api"))

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
import sqlite3

from config import BOT_TOKEN, GROUP_ID

# Путь к базе данных
DB_PATH = os.getenv("DB_PATH", "/root/miniapp_api/app.db")
USER_IDS_FILE = Path(__file__).parent / "user_ids.txt"


async def get_chat_administrators(bot: Bot, chat_id: int):
    """Получает список администраторов группы."""
    try:
        administrators = await bot.get_chat_administrators(chat_id)
        return administrators
    except Exception as e:
        print(f"Ошибка получения администраторов: {e}")
        return []


def get_users_from_db(db_path: str):
    """Получает список всех user_id из таблицы users."""
    user_ids = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        rows = cursor.fetchall()
        user_ids = [row[0] for row in rows]
        conn.close()
    except Exception as e:
        print(f"Ошибка чтения БД: {e}")
    return user_ids


async def verify_user_in_group(bot: Bot, chat_id: int, user_id: int):
    """Проверяет, является ли пользователь участником группы."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status in ["member", "administrator", "creator", "restricted"]:
            return True
        return False
    except Exception:
        return False


async def main():
    """Основная функция."""
    print("=" * 60)
    print("Генерация файла user_ids.txt")
    print("=" * 60)
    
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    
    all_user_ids = set()
    
    try:
        # 1. Получаем администраторов
        print(f"\n1️⃣ Получаю администраторов группы {GROUP_ID}...")
        administrators = await get_chat_administrators(bot, GROUP_ID)
        admin_ids = []
        for admin in administrators:
            if admin.user and not admin.user.is_bot:
                admin_ids.append(admin.user.id)
                all_user_ids.add(admin.user.id)
        print(f"   Найдено администраторов: {len(admin_ids)}")
        
        # 2. Получаем пользователей из БД
        print(f"\n2️⃣ Получаю пользователей из БД...")
        db_user_ids = get_users_from_db(DB_PATH)
        print(f"   Найдено пользователей в БД: {len(db_user_ids)}")
        
        # Добавляем всех пользователей из БД (они точно были в группе когда-то)
        for user_id in db_user_ids:
            all_user_ids.add(user_id)
        
        print(f"\n3️⃣ Проверяю, кто из пользователей БД еще в группе...")
        verified_in_group = []
        for i, user_id in enumerate(db_user_ids, 1):
            if user_id not in admin_ids:  # Администраторов уже проверили
                is_member = await verify_user_in_group(bot, GROUP_ID, user_id)
                if is_member:
                    verified_in_group.append(user_id)
                    all_user_ids.add(user_id)
                
                # Показываем прогресс каждые 10 пользователей
                if i % 10 == 0:
                    print(f"   Проверено {i}/{len(db_user_ids)}...")
                
                # Небольшая задержка, чтобы не перегружать API
                await asyncio.sleep(0.1)
        
        print(f"   Пользователей из БД, которые еще в группе: {len(verified_in_group)}")
        
        # 3. Можно добавить другие источники user_id здесь
        # Например, из файла, из другого источника и т.д.
        
        # Сортируем для удобства
        sorted_user_ids = sorted(all_user_ids)
        
        print(f"\n📊 Итого уникальных user_id: {len(sorted_user_ids)}")
        
        # Сохраняем в файл
        print(f"\n💾 Сохраняю в файл {USER_IDS_FILE}...")
        with open(USER_IDS_FILE, 'w') as f:
            for user_id in sorted_user_ids:
                f.write(f"{user_id}\n")
        
        print(f"✅ Файл создан успешно!")
        print(f"   Сохранено {len(sorted_user_ids)} user_id")
        print(f"\n💡 Теперь можно запустить notify_users_without_profile.py")
        print(f"   для проверки этих пользователей и отправки сообщений")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())



