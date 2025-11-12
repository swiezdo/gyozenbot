#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot handler для мини-приложения Tsushima
Интегрирует WebApp
"""

import asyncio
import aiohttp
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    MINI_APP_URL, API_BASE_URL, BOT_TOKEN, GROUP_ID
)
from api_client import api_get, api_post

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
    """Обработчик команды /start"""
    user = message.from_user
    
    welcome_text = f"""Привет, {user.first_name}! 👋

Я бот Tsushima.Ru, но друзья зовут меня Местный Гёдзен.

• Просматривать свою и чужие анкеты
• Создавать билды и делиться ими

Для начала работы откройте мини-приложение:"""
    
    # Создаем клавиатуру с кнопкой WebApp
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Открыть",
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
    logger.info(f"Запрашиваем билд {build_id} из API")
    try:
        response_wrapper = await api_get(f"/api/builds.get/{build_id}")
        async with response_wrapper as response:
            logger.info("Статус ответа: %s", response.status)
            if response.status == 404:
                logger.warning("Билд %s не найден", build_id)
                return None, "Билд не найден"
            if response.status == 403:
                data = await response.json()
                if data.get("is_private"):
                    logger.warning("Билд %s приватный", build_id)
                    return None, "Билд найден, но он приватный"
                return None, "Доступ к билду запрещен"
            if response.status == 200:
                data = await response.json()
                logger.info("Получены данные билда: %s", data)
                return data.get("build"), None

            logger.error("Неожиданный статус API: %s", response.status)
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

# ========== ОБРАБОТЧИКИ ЗАЯВОК НА ПОВЫШЕНИЕ УРОВНЯ МАСТЕРСТВА ==========

@router.callback_query(F.data.startswith("approve_mastery:"))
async def approve_mastery_callback(callback: CallbackQuery):
    """Обработка кнопки 'Одобрить' для заявки на повышение уровня"""
    try:
        # Парсинг callback_data: approve_mastery:{user_id}:{category_key}:{next_level}
        parts = callback.data.split(":")
        if len(parts) != 4:
            await callback.answer("❌ Ошибка формата данных", show_alert=True)
            return
        
        _, target_user_id_str, category_key, next_level_str = parts
        target_user_id = int(target_user_id_str)
        next_level = int(next_level_str)
        
        # Получаем username модератора
        moderator_username = callback.from_user.username or callback.from_user.first_name or "Модератор"
        
        # Делаем запрос к API для одобрения заявки
        data = aiohttp.FormData()
        data.add_field('user_id', str(target_user_id))
        data.add_field('category_key', category_key)
        data.add_field('next_level', str(next_level))
        data.add_field('moderator_username', moderator_username)
        
        try:
            response_wrapper = await api_post(
                "/api/mastery.approve",
                data=data,
                use_bot_token=True,
            )
            async with response_wrapper as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error("Ошибка API при одобрении: %s - %s", response.status, error_text)
                    await callback.answer("❌ Ошибка обработки заявки", show_alert=True)
                    return

                result = await response.json()

                if not result.get("success"):
                    await callback.answer("❌ Ошибка обработки заявки", show_alert=True)
                    return

                # Получаем данные из ответа
                category_name = result.get("category_name", category_key)
                level_name = result.get("level_name", f"Уровень {next_level}")
                psn_id = result.get("psn_id", "")
                username = result.get("username", "")

                # Отправляем сообщение в группу поздравлений
                if GROUP_ID:
                    try:
                        # Получаем username пользователя через Bot API
                        user_mention = psn_id  # fallback на psn_id
                        try:
                            chat_info = await callback.bot.get_chat(target_user_id)
                            if chat_info.username:
                                user_mention = f"@{chat_info.username}"
                            elif chat_info.first_name:
                                user_mention = chat_info.first_name
                            else:
                                user_mention = psn_id
                        except Exception as e:
                            logger.error("Ошибка получения username пользователя %s: %s", target_user_id, e)
                            user_mention = username if username else psn_id

                        await callback.bot.send_message(
                            chat_id=GROUP_ID,
                            text=(
                                "🎉 Участник {mention} ({psn}) повысил свой уровень в категории "
                                "<b>{category}</b> — Уровень {level_num}, {level_name}"
                            ).format(
                                mention=user_mention,
                                psn=psn_id,
                                category=category_name,
                                level_num=next_level,
                                level_name=level_name,
                            ),
                            parse_mode="HTML",
                        )
                    except Exception as e:
                        logger.error("Ошибка отправки сообщения в группу поздравлений: %s", e)

                # Редактируем исходное сообщение (добавляем информацию в конец и убираем кнопки)
                try:
                    original_text = callback.message.text or callback.message.caption or ""
                    updated_text = original_text + f"\n\n✅ Заявка одобрена @{moderator_username}"

                    if callback.message.photo or callback.message.video:
                        await callback.message.edit_caption(
                            caption=updated_text,
                            parse_mode="HTML",
                            reply_markup=None,
                        )
                    else:
                        await callback.message.edit_text(
                            text=updated_text,
                            parse_mode="HTML",
                            reply_markup=None,
                        )
                except Exception as e:
                    logger.error("Ошибка редактирования сообщения: %s", e)

                await callback.answer("✅ Заявка одобрена!", show_alert=False)
        
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при одобрении заявки: {e}")
            await callback.answer("❌ Ошибка подключения к серверу", show_alert=True)
        except Exception as e:
            logger.error(f"Неожиданная ошибка при одобрении заявки: {e}")
            await callback.answer("❌ Произошла ошибка", show_alert=True)
        
    except ValueError as e:
        logger.error(f"Ошибка парсинга callback данных: {e}")
        await callback.answer("❌ Ошибка обработки запроса", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка обработки одобрения заявки: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("reject_mastery:"))
async def reject_mastery_callback(callback: CallbackQuery):
    """Обработка кнопки 'Отклонить' для заявки на повышение уровня"""
    try:
        # Парсинг callback_data: reject_mastery:{user_id}:{category_key}:{next_level}
        parts = callback.data.split(":")
        if len(parts) != 4:
            await callback.answer("❌ Ошибка формата данных", show_alert=True)
            return
        
        _, target_user_id_str, category_key, next_level_str = parts
        target_user_id = int(target_user_id_str)
        next_level = int(next_level_str)
        
        # Получаем username модератора (того кто нажал кнопку)
        moderator_username = callback.from_user.username or callback.from_user.first_name or "Модератор"
        
        # Запрашиваем причину отклонения у модератора
        await callback.answer("Введите причину отклонения в ответ на следующее сообщение", show_alert=True)
        
        # Отправляем сообщение с инструкцией
        instruction_msg = await callback.message.reply(
            "❌ <b>Заявка будет отклонена</b>\n\n"
            "Пожалуйста, введите причину отклонения в ответ на это сообщение:",
            parse_mode="HTML"
        )
        
        # Сохраняем состояние ожидания причины
        if not hasattr(reject_mastery_callback, '_pending_rejects'):
            reject_mastery_callback._pending_rejects = {}
        
        original_text = callback.message.text or callback.message.caption or ""
        
        reject_mastery_callback._pending_rejects[instruction_msg.message_id] = {
            'user_id': target_user_id,
            'category_key': category_key,
            'next_level': next_level,
            'original_message_id': callback.message.message_id,
            'instruction_message_id': instruction_msg.message_id,
            'chat_id': callback.message.chat.id,
            'has_photo': (callback.message.photo is not None) or (callback.message.video is not None),
            'original_text': original_text,
            'moderator_username': moderator_username
        }
        
    except ValueError as e:
        logger.error(f"Ошибка парсинга callback данных: {e}")
        await callback.answer("❌ Ошибка обработки запроса", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка обработки отклонения заявки: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.message(F.reply_to_message)
async def handle_rejection_reason(message: Message):
    """Обработка ответа с причиной отклонения (для мастерства и трофеев)"""
    try:
        replied_message = message.reply_to_message
        
        # Проверяем, не является ли это ответом на сообщение об отклонении мастерства
        if hasattr(reject_mastery_callback, '_pending_rejects'):
            pending_key = replied_message.message_id
            if pending_key in reject_mastery_callback._pending_rejects:
                await handle_mastery_rejection(message, pending_key)
                return
        
        # Проверяем, не является ли это ответом на сообщение об отклонении трофея
        if hasattr(reject_trophy_callback, '_pending_rejects'):
            pending_key = replied_message.message_id
            if pending_key in reject_trophy_callback._pending_rejects:
                await handle_trophy_rejection(message, pending_key)
                return
        
    except Exception as e:
        logger.error(f"Ошибка обработки причины отклонения: {e}")
        await message.reply("❌ Произошла ошибка при обработке причины")


async def handle_mastery_rejection(message: Message, pending_key: int):
    """Обработка отклонения заявки на мастерство"""
    pending_data = reject_mastery_callback._pending_rejects.pop(pending_key)
    target_user_id = pending_data['user_id']
    category_key = pending_data['category_key']
    next_level = pending_data['next_level']
    original_message_id = pending_data['original_message_id']
    instruction_message_id = pending_data['instruction_message_id']
    chat_id = pending_data['chat_id']
    has_photo = pending_data.get('has_photo', False)
    original_text = pending_data.get('original_text', '')
    
    reason = message.text.strip() if message.text else "Причина не указана"
    
    # Получаем username модератора
    moderator_username = pending_data.get('moderator_username') or message.from_user.username or message.from_user.first_name or "Модератор"
    
    # Делаем запрос к API для отклонения заявки
    data = aiohttp.FormData()
    data.add_field('user_id', str(target_user_id))
    data.add_field('category_key', category_key)
    data.add_field('next_level', str(next_level))
    data.add_field('reason', reason)
    data.add_field('moderator_username', moderator_username)
    
    try:
        response_wrapper = await api_post(
            "/api/mastery.reject",
            data=data,
            use_bot_token=True,
        )
        async with response_wrapper as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(
                    "Ошибка API при отклонении мастерства: %s - %s",
                    response.status,
                    error_text,
                )
                await message.reply("❌ Ошибка обработки заявки")
                return

            result = await response.json()

            if not result.get("success"):
                await message.reply("❌ Ошибка обработки заявки")
                return

            # Редактируем сообщение-инструкцию
            try:
                updated_instruction_text = (
                    "❌ <b>Заявка отклонена</b>\n\n"
                    f"Кем: @{moderator_username}\n"
                    f"Причина: {reason}\n\n"
                    "✅ Уведомление отправлено пользователю"
                )

                await message.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=instruction_message_id,
                    text=updated_instruction_text,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error("Ошибка редактирования сообщения-инструкции: %s", e)

            # Убираем кнопки из исходного сообщения
            try:
                if has_photo:
                    await message.bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=original_message_id,
                        caption=original_text,
                        parse_mode="HTML",
                        reply_markup=None,
                    )
                else:
                    await message.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=original_message_id,
                        text=original_text,
                        parse_mode="HTML",
                        reply_markup=None,
                    )
            except Exception as e:
                logger.error("Ошибка редактирования исходного сообщения: %s", e)
    
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка сети при отклонении заявки на мастерство: {e}")
        await message.reply("❌ Ошибка подключения к серверу")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отклонении заявки на мастерство: {e}")
        await message.reply("❌ Произошла ошибка")


async def handle_trophy_rejection(message: Message, pending_key: int):
    """Обработка отклонения заявки на трофей"""
    pending_data = reject_trophy_callback._pending_rejects.pop(pending_key)
    target_user_id = pending_data['user_id']
    trophy_key = pending_data['trophy_key']
    original_message_id = pending_data['original_message_id']
    instruction_message_id = pending_data['instruction_message_id']
    chat_id = pending_data['chat_id']
    has_photo = pending_data.get('has_photo', False)
    original_text = pending_data.get('original_text', '')
    
    reason = message.text.strip() if message.text else "Причина не указана"
    
    # Получаем username модератора
    moderator_username = pending_data.get('moderator_username') or message.from_user.username or message.from_user.first_name or "Модератор"
    
    # Делаем запрос к API для отклонения заявки
    data = aiohttp.FormData()
    data.add_field('user_id', str(target_user_id))
    data.add_field('trophy_key', trophy_key)
    data.add_field('reason', reason)
    data.add_field('moderator_username', moderator_username)
    
    try:
        response_wrapper = await api_post(
            "/api/trophy.reject",
            data=data,
            use_bot_token=True,
        )
        async with response_wrapper as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error("Ошибка API при отклонении трофея: %s - %s", response.status, error_text)
                await message.reply("❌ Ошибка обработки заявки")
                return

            result = await response.json()

            if not result.get("success"):
                await message.reply("❌ Ошибка обработки заявки")
                return

            # Редактируем сообщение-инструкцию
            try:
                updated_instruction_text = (
                    "❌ <b>Заявка отклонена</b>\n\n"
                    f"Кем: @{moderator_username}\n"
                    f"Причина: {reason}\n\n"
                    "✅ Уведомление отправлено пользователю"
                )

                await message.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=instruction_message_id,
                    text=updated_instruction_text,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error("Ошибка редактирования сообщения-инструкции: %s", e)

            # Убираем кнопки из исходного сообщения
            try:
                if has_photo:
                    await message.bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=original_message_id,
                        caption=original_text,
                        parse_mode="HTML",
                        reply_markup=None,
                    )
                else:
                    await message.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=original_message_id,
                        text=original_text,
                        parse_mode="HTML",
                        reply_markup=None,
                    )
            except Exception as e:
                logger.error("Ошибка редактирования исходного сообщения: %s", e)
    
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка сети при отклонении заявки на трофей: {e}")
        await message.reply("❌ Ошибка подключения к серверу")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отклонении заявки на трофей: {e}")
        await message.reply("❌ Произошла ошибка")


# ========== ОБРАБОТЧИКИ ЗАЯВОК НА ПОЛУЧЕНИЕ ТРОФЕЯ ==========

@router.callback_query(F.data.startswith("approve_trophy:"))
async def approve_trophy_callback(callback: CallbackQuery):
    """Обработка кнопки 'Одобрить' для заявки на получение трофея"""
    try:
        # Парсинг callback_data: approve_trophy:{user_id}:{trophy_key}
        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("❌ Ошибка формата данных", show_alert=True)
            return
        
        _, target_user_id_str, trophy_key = parts
        target_user_id = int(target_user_id_str)
        
        # Получаем username модератора
        moderator_username = callback.from_user.username or callback.from_user.first_name or "Модератор"
        
        # Делаем запрос к API для одобрения заявки
        data = aiohttp.FormData()
        data.add_field('user_id', str(target_user_id))
        data.add_field('trophy_key', trophy_key)
        data.add_field('moderator_username', moderator_username)
        
        try:
            response_wrapper = await api_post(
                "/api/trophy.approve",
                data=data,
                use_bot_token=True,
            )
            async with response_wrapper as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        "Ошибка API при одобрении трофея: %s - %s",
                        response.status,
                        error_text,
                    )
                    await callback.answer("❌ Ошибка обработки заявки", show_alert=True)
                    return

                result = await response.json()

                if not result.get("success"):
                    await callback.answer("❌ Ошибка обработки заявки", show_alert=True)
                    return

                trophy_name = result.get("trophy_name", trophy_key)
                psn_id = result.get("psn_id", "")
                username = result.get("username", "")

                if GROUP_ID:
                    try:
                        user_mention = psn_id
                        try:
                            chat_info = await callback.bot.get_chat(target_user_id)
                            if chat_info.username:
                                user_mention = f"@{chat_info.username}"
                            elif chat_info.first_name:
                                user_mention = chat_info.first_name
                        except Exception as e:
                            logger.error("Ошибка получения username пользователя %s: %s", target_user_id, e)
                            if username:
                                user_mention = username

                        await callback.bot.send_message(
                            chat_id=GROUP_ID,
                            text=f"🎉 Участник {user_mention} ({psn_id}) получил трофей <b>{trophy_name}</b>!",
                            parse_mode="HTML",
                        )
                    except Exception as e:
                        logger.error("Ошибка отправки сообщения в группу поздравлений: %s", e)

                try:
                    original_text = callback.message.text or callback.message.caption or ""
                    updated_text = original_text + f"\n\n✅ Заявка одобрена @{moderator_username}"

                    if callback.message.photo or callback.message.video:
                        await callback.message.edit_caption(
                            caption=updated_text,
                            parse_mode="HTML",
                            reply_markup=None,
                        )
                    else:
                        await callback.message.edit_text(
                            text=updated_text,
                            parse_mode="HTML",
                            reply_markup=None,
                        )
                except Exception as e:
                    logger.error("Ошибка редактирования сообщения: %s", e)

                await callback.answer("✅ Заявка одобрена!", show_alert=False)

        except aiohttp.ClientError as e:
            logger.error("Ошибка сети при одобрении заявки на трофей: %s", e)
            await callback.answer("❌ Ошибка подключения к серверу", show_alert=True)
        except Exception as e:
            logger.error("Неожиданная ошибка при одобрении заявки на трофей: %s", e)
            await callback.answer("❌ Произошла ошибка", show_alert=True)
        
    except ValueError as e:
        logger.error(f"Ошибка парсинга callback данных: {e}")
        await callback.answer("❌ Ошибка обработки запроса", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка обработки одобрения заявки на трофей: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("reject_trophy:"))
async def reject_trophy_callback(callback: CallbackQuery):
    """Обработка кнопки 'Отклонить' для заявки на получение трофея"""
    try:
        # Парсинг callback_data: reject_trophy:{user_id}:{trophy_key}
        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("❌ Ошибка формата данных", show_alert=True)
            return
        
        _, target_user_id_str, trophy_key = parts
        target_user_id = int(target_user_id_str)
        
        # Получаем username модератора (того кто нажал кнопку)
        moderator_username = callback.from_user.username or callback.from_user.first_name or "Модератор"
        
        # Запрашиваем причину отклонения у модератора
        await callback.answer("Введите причину отклонения в ответ на следующее сообщение", show_alert=True)
        
        # Отправляем сообщение с инструкцией
        instruction_msg = await callback.message.reply(
            "❌ <b>Заявка будет отклонена</b>\n\n"
            "Пожалуйста, введите причину отклонения в ответ на это сообщение:",
            parse_mode="HTML"
        )
        
        # Сохраняем состояние ожидания причины
        if not hasattr(reject_trophy_callback, '_pending_rejects'):
            reject_trophy_callback._pending_rejects = {}
        
        original_text = callback.message.text or callback.message.caption or ""
        
        reject_trophy_callback._pending_rejects[instruction_msg.message_id] = {
            'user_id': target_user_id,
            'trophy_key': trophy_key,
            'original_message_id': callback.message.message_id,
            'instruction_message_id': instruction_msg.message_id,
            'chat_id': callback.message.chat.id,
            'has_photo': (callback.message.photo is not None) or (callback.message.video is not None),
            'original_text': original_text,
            'moderator_username': moderator_username
        }
        
    except ValueError as e:
        logger.error(f"Ошибка парсинга callback данных: {e}")
        await callback.answer("❌ Ошибка обработки запроса", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка обработки отклонения заявки на трофей: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)