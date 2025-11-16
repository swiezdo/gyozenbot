#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик inline queries для поиска билдов
"""

import aiohttp
import logging
from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent
)

from config import API_BASE_URL, MINI_APP_URL

logger = logging.getLogger(__name__)
router = Router()


def _get_raw_base() -> str:
    """Получает базовый URL для статических ресурсов мини-приложения."""
    return MINI_APP_URL.rstrip('/')


def _get_class_icons() -> dict:
    """Получает словарь с URL иконок классов (lazy evaluation)"""
    _raw_base = _get_raw_base()
    return {
        'Самурай': f'{_raw_base}/assets/icons/classes/samurai.png',
        'Охотник': f'{_raw_base}/assets/icons/classes/hunter.png',
        'Убийца': f'{_raw_base}/assets/icons/classes/assassin.png',
        'Ронин': f'{_raw_base}/assets/icons/classes/ronin.png'
    }

async def search_builds(query: str, limit: int = 10) -> list:
    """Поиск билдов через API"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_BASE_URL}/api/builds.search"
            params = {"query": query, "limit": limit}
            
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('builds', [])
                else:
                    logger.error(f"API вернул статус {response.status}")
                    return []
    except Exception as e:
        logger.error(f"Ошибка поиска билдов: {e}")
        return []

def truncate_text(text: str, max_length: int = 50) -> str:
    """Обрезает текст до указанной длины"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

@router.inline_query()
async def inline_query_handler(inline_query: InlineQuery):
    """Обработчик inline запросов для поиска билдов"""
    query = inline_query.query.strip()
    
    # Если запрос пустой, показываем подсказку
    if not query:
        await inline_query.answer(
            results=[],
            switch_pm_text="🔍 Введите название, теги или ID билда",
            switch_pm_parameter="help",
            cache_time=1
        )
        return
    
    # Ищем билды
    builds = await search_builds(query, limit=10)
    
    if not builds:
        await inline_query.answer(
            results=[],
            switch_pm_text="❌ Билды не найдены",
            switch_pm_parameter="help",
            cache_time=1
        )
        return
    
    # Формируем результаты для Telegram
    results = []
    
    # Получаем иконки классов (lazy evaluation)
    class_icons = _get_class_icons()
    
    for build in builds:
        # Получаем иконку класса
        build_class = build.get('class', 'Самурай')
        class_icon_url = class_icons.get(build_class, class_icons['Самурай'])
        
        # Формируем title: "ID: Название"
        title = f"{build['build_id']}: {build['name']}"
        
        # Формируем description
        description_lines = []
        
        # Первая строка: Автор
        author = build.get('author', 'Неизвестно')
        if author:
            description_lines.append(f"Автор: {author}")
        
        # Вторая строка: Теги через запятую
        tags = build.get('tags', [])
        if tags:
            tags_text = ', '.join(tags)
            description_lines.append(tags_text)
        else:
            # Если тегов нет, можем показать ID
            description_lines.append(f"ID: {build['build_id']}")
        
        # Объединяем строки через перенос строки
        # Telegram может отобразить до 2 строк в description
        description = "\n".join(description_lines[:2])  # Берем максимум 2 строки
        
        # Используем команду /билд в input_message_content
        # Сообщение отправится в тот чат, откуда был сделан inline query
        # Затем существующий обработчик команды /билд обработает его и отправит медиагруппу
        # Миниатюра: используем PNG-иконку класса (SVG не поддерживается Telegram)
        thumbnail_url = class_icon_url
        
        result = InlineQueryResultArticle(
            id=str(build['build_id']),
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,  # Используем фото билда вместо SVG
            input_message_content=InputTextMessageContent(
                message_text=f"/билд {build['build_id']}"
            )
        )
        
        results.append(result)
    
    # Отправляем результаты
    await inline_query.answer(
        results=results,
        cache_time=300,  # Кешируем на 5 минут
        is_personal=False  # Результаты одинаковые для всех
    )

# Примечание: chosen_inline_result не используется, так как сообщение с командой /билд
# автоматически отправляется в чат через input_message_content, и его обрабатывает
# существующий обработчик команды /билд из handlers/miniapp.py
# Это гарантирует, что медиагруппа будет отправлена в правильный чат

