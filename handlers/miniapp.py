#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot handler для мини-приложения Tsushima
Интегрирует WebApp и обработку модерации трофеев
"""

import asyncio
import aiohttp
import json
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ChatMemberStatus

from config import (
    MINI_APP_URL, API_BASE_URL, TROPHY_GROUP_CHAT_ID, TROPHY_GROUP_TOPIC_ID
)

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
    """Обработчик команды /start"""
    user = message.from_user
    
    welcome_text = f"""Привет, {user.first_name}! 👋

Я бот Tsushima.Ru, но друзья зовут меня Местный Гёдзен.

🏆 Здесь ты можешь:
• Подавать заявки на получение трофеев
• Отслеживать свой прогресс
• Получать уведомления о статусе заявок
• Просматривать свою и чужие анкеты
• Создавать билды и делиться ими

Для начала работы откройте мини-приложение:"""
    
    # Создаем клавиатуру с кнопкой WebApp
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🏆 Открыть",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}")
    ))
    
    await message.answer(welcome_text, reply_markup=builder.as_markup())

@router.message(Command("build", "билд"))
async def build_command(message: Message):
    """Обработчик команды /build <ID> или /билд <ID>"""
    args = message.text.split()
    
    # Проверка наличия аргумента
    if len(args) < 2:
        await message.reply(
            "❌ <b>Неверный формат команды</b>\n\n"
            "Использование: /build <ID>\n"
            "Пример: /build 12",
            parse_mode="HTML"
        )
        return
    
    # Проверка, что ID - число
    try:
        build_id = int(args[1])
    except ValueError:
        await message.reply("❌ ID билда должен быть числом")
        return
    
    # Получаем данные билда
    build_data, error_message = await fetch_build_data(build_id)
    
    if error_message:
        await message.reply(f"❌ {error_message}")
        return
    
    # Отправляем медиагруппу
    await send_build_media_group(message, build_data)

async def fetch_build_data(build_id: int) -> tuple:
    """Получает данные билда по ID из API
    
    Returns:
        tuple: (build_data: dict|None, error_message: str|None)
    """
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_BASE_URL}/api/builds.get/{build_id}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 404:
                    return None, "Билд не найден"
                elif response.status == 403:
                    data = await response.json()
                    if data.get('is_private'):
                        return None, "Билд найден, но он приватный"
                    return None, "Доступ к билду запрещен"
                elif response.status == 200:
                    data = await response.json()
                    return data.get('build'), None
                else:
                    logger.error(f"Неожиданный статус API: {response.status}")
                    return None, f"Ошибка сервера (код {response.status})"
    except asyncio.TimeoutError:
        logger.error(f"Таймаут при запросе билда {build_id}")
        return None, "Превышено время ожидания ответа от сервера"
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка сети при запросе билда {build_id}: {e}")
        return None, "Ошибка подключения к серверу"
    except Exception as e:
        logger.error(f"Неожиданная ошибка при запросе билда {build_id}: {e}")
        return None, "Произошла непредвиденная ошибка"

async def send_build_media_group(message: Message, build_data: dict):
    """Отправляет билд как медиагруппу с 2 фото и информацией"""
    
    # Формируем текст с информацией о билде
    tags_text = ', '.join(build_data.get('tags', [])) if build_data.get('tags') else '—'
    description_text = build_data.get('description', 'Описание отсутствует')
    
    caption = f"""🛠️ <b>{build_data['name']}</b>

👤 <b>Автор:</b> {build_data.get('author', 'Неизвестно')}
⚔️ <b>Класс:</b> {build_data.get('class', 'Не указан')}
🏷️ <b>Теги:</b> {tags_text}

📝 <b>Описание:</b>
{description_text}"""
    
    media_group = []
    
    # Первая картинка с описанием
    if build_data.get('photo_1'):
        photo1_url = f"{API_BASE_URL}{build_data['photo_1']}"
        media_group.append(InputMediaPhoto(
            media=photo1_url,
            caption=caption,
            parse_mode="HTML"
        ))
    
    # Вторая картинка (без текста)
    if build_data.get('photo_2'):
        photo2_url = f"{API_BASE_URL}{build_data['photo_2']}"
        media_group.append(InputMediaPhoto(media=photo2_url))
    
    # Отправка медиагруппы или ошибки
    if media_group:
        try:
            await message.answer_media_group(media=media_group)
        except Exception as e:
            logger.error(f"Ошибка отправки медиагруппы: {e}")
            await message.reply(
                f"❌ Не удалось загрузить изображения билда\n\n"
                f"Попробуйте позже или откройте билд в приложении"
            )
    else:
        # Если нет фото, отправляем только текст
        await message.reply(
            f"{caption}\n\n"
            f"⚠️ <i>У этого билда нет изображений</i>",
            parse_mode="HTML"
        )

async def get_trophy_and_user_info(user_id: int, trophy_name: str) -> tuple:
    """Получает название трофея и PSN ID пользователя"""
    display_name = trophy_name
    psn_id = str(user_id)
    
    try:
        # Получаем данные трофея
        async with aiohttp.ClientSession() as session:
            trophy_url = f"{API_BASE_URL}/api/trophy_info/{trophy_name}"
            async with session.get(trophy_url) as trophy_response:
                if trophy_response.status == 200:
                    trophy_data = await trophy_response.json()
                    display_name = f"{trophy_data.get('name', trophy_name)} {trophy_data.get('emoji', '')}".strip()
            
            # Получаем PSN ID пользователя
            user_url = f"{API_BASE_URL}/api/user_info/{user_id}"
            async with session.get(user_url) as user_response:
                if user_response.status == 200:
                    user_data = await user_response.json()
                    psn_id = user_data.get('psn_id', str(user_id))
    except Exception as e:
        logger.error(f"Ошибка получения данных: {e}")
    
    return display_name, psn_id

@router.callback_query(F.data.startswith("trophy_approve:"))
async def handle_trophy_approve(callback: CallbackQuery):
    """Обработчик callback кнопки одобрения трофея"""
    await callback.answer()
    
    callback_data = callback.data
    parts = callback_data.split(":")
    
    if len(parts) == 3:
        user_id = int(parts[1])
        trophy_name = parts[2]
        
        # Получаем данные трофея и пользователя
        trophy_display_name, psn_id = await get_trophy_and_user_info(user_id, trophy_name)
        
        success = await approve_trophy(user_id, trophy_name)
        
        if success:
            await callback.message.edit_text(
                f"✅ Заявка одобрена\n\nТрофей: {trophy_display_name}\nПользователь: {psn_id}"
            )
        else:
            await callback.message.edit_text(
                f"❌ Ошибка при одобрении трофея"
            )

@router.callback_query(F.data.startswith("trophy_reject:"))
async def handle_trophy_reject(callback: CallbackQuery):
    """Обработчик callback кнопки отклонения трофея"""
    await callback.answer()
    
    callback_data = callback.data
    parts = callback_data.split(":")
    
    if len(parts) == 3:
        user_id = int(parts[1])
        trophy_name = parts[2]
        
        # Получаем данные трофея и пользователя
        trophy_display_name, psn_id = await get_trophy_and_user_info(user_id, trophy_name)
        
        success = await reject_trophy(user_id, trophy_name)
        
        if success:
            await callback.message.edit_text(
                f"❌ Заявка отклонена\n\nТрофей: {trophy_display_name}\nПользователь: {psn_id}"
            )
        else:
            await callback.message.edit_text(
                f"❌ Ошибка при отклонении трофея"
            )

async def approve_trophy(user_id: int, trophy_name: str) -> bool:
    """Одобряет трофей через API"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_BASE_URL}/api/trophies.approve"
            data = {
                "user_id": user_id,
                "trophy_name": trophy_name
            }
            
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Трофей {trophy_name} одобрен для пользователя {user_id}: {result}")
                    return True
                else:
                    logger.error(f"Ошибка одобрения трофея: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Ошибка при одобрении трофея: {e}")
        return False

async def reject_trophy(user_id: int, trophy_name: str) -> bool:
    """Отклоняет трофей через API"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_BASE_URL}/api/trophies.reject"
            data = {
                "user_id": user_id,
                "trophy_name": trophy_name
            }
            
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Трофей {trophy_name} отклонен для пользователя {user_id}: {result}")
                    return True
                else:
                    logger.error(f"Ошибка отклонения трофея: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Ошибка при отклонении трофея: {e}")
        return False
