# /gyozenbot/handlers/snippets.py
import logging
import re
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import API_BASE_URL, GROUP_ID, TROPHY_GROUP_CHAT_ID
from api_client import api_get, api_post, api_delete, _request

router = Router()
logger = logging.getLogger(__name__)


class SnippetStates(StatesGroup):
    """FSM стейты для работы со сниппетами"""
    main_menu = State()
    all_snippets = State()
    my_snippets = State()
    create_trigger = State()
    create_message = State()
    edit_trigger = State()
    edit_message = State()
    delete_confirm = State()


async def _check_user_is_admin_in_any_group(bot: Bot, user_id: int) -> bool:
    """
    Проверяет, является ли пользователь админом хотя бы в одной группе, где есть бот.
    Проверяет известные группы из config.
    """
    groups_to_check = [GROUP_ID, TROPHY_GROUP_CHAT_ID]
    
    for chat_id in groups_to_check:
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status in {"administrator", "creator"}:
                return True
        except Exception as e:
            logger.debug(f"Не удалось проверить статус пользователя {user_id} в группе {chat_id}: {e}")
            continue
    
    return False


async def get_all_snippets_api() -> list:
    """Получает все сниппеты через API"""
    try:
        response_wrapper = await api_get(
            "/api/snippets/all",
            params={"use_bot_token": "true"},
            use_bot_token=True
        )
        async with response_wrapper as response:
            if response.status == 200:
                data = await response.json()
                return data.get("snippets", [])
            else:
                logger.error(f"Ошибка получения всех сниппетов: {response.status}")
                return []
    except Exception as e:
        logger.error(f"Исключение при получении всех сниппетов: {e}", exc_info=True)
        return []


async def get_user_snippets_api(user_id: int) -> list:
    """Получает сниппеты пользователя через API"""
    try:
        response_wrapper = await api_get(
            f"/api/snippets/my",
            params={"user_id": user_id},
            use_bot_token=True
        )
        async with response_wrapper as response:
            if response.status == 200:
                data = await response.json()
                return data.get("snippets", [])
            else:
                logger.error(f"Ошибка получения сниппетов пользователя: {response.status}")
                return []
    except Exception as e:
        logger.error(f"Исключение при получении сниппетов пользователя: {e}", exc_info=True)
        return []


async def get_snippet_by_id_api(snippet_id: int) -> dict:
    """Получает сниппет по ID через API"""
    try:
        response_wrapper = await api_get(f"/api/snippets/{snippet_id}")
        async with response_wrapper as response:
            if response.status == 200:
                data = await response.json()
                return data.get("snippet", {})
            else:
                logger.error(f"Ошибка получения сниппета: {response.status}")
                return {}
    except Exception as e:
        logger.error(f"Исключение при получении сниппета: {e}", exc_info=True)
        return {}


async def create_snippet_api(user_id: int, trigger: str, message: str, media: str = None, media_type: str = None) -> bool:
    """Создает сниппет через API"""
    try:
        data = {
            "trigger": trigger,
            "message": message,
            "user_id": user_id,
        }
        if media:
            data["media"] = media
        if media_type:
            data["media_type"] = media_type
        
        response_wrapper = await api_post(
            "/api/snippets/create",
            data=data,
            use_bot_token=True
        )
        async with response_wrapper as response:
            if response.status == 200:
                return True
            else:
                logger.error(f"Ошибка создания сниппета: {response.status}")
                return False
    except Exception as e:
        logger.error(f"Исключение при создании сниппета: {e}", exc_info=True)
        return False


async def update_snippet_api(snippet_id: int, user_id: int, trigger: str = None, message: str = None, media: str = None, media_type: str = None) -> bool:
    """Обновляет сниппет через API"""
    try:
        data = {
            "user_id": user_id,
        }
        if trigger is not None:
            data["trigger"] = trigger
        if message is not None:
            data["message"] = message
        if media is not None:
            data["media"] = media
        if media_type is not None:
            data["media_type"] = media_type
        
        # Используем _request с методом PUT
        response_wrapper = await _request(
            "PUT",
            f"/api/snippets/{snippet_id}",
            data=data,
            use_bot_token=True
        )
        async with response_wrapper as response:
            if response.status == 200:
                return True
            else:
                logger.error(f"Ошибка обновления сниппета: {response.status}")
                return False
    except Exception as e:
        logger.error(f"Исключение при обновлении сниппета: {e}", exc_info=True)
        return False


async def delete_snippet_api(snippet_id: int, user_id: int) -> bool:
    """Удаляет сниппет через API"""
    try:
        response_wrapper = await api_delete(
            f"/api/snippets/{snippet_id}",
            params={"user_id": user_id},
            use_bot_token=True
        )
        async with response_wrapper as response:
            if response.status == 200:
                return True
            else:
                logger.error(f"Ошибка удаления сниппета: {response.status}")
                return False
    except Exception as e:
        logger.error(f"Исключение при удалении сниппета: {e}", exc_info=True)
        return False


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Строит клавиатуру главного меню"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="Все сниппеты", callback_data="snippets_all"))
    builder.row(InlineKeyboardButton(text="Мои сниппеты", callback_data="snippets_my"))
    builder.row(InlineKeyboardButton(text="Выход", callback_data="snippets_exit"))
    
    return builder.as_markup()


def build_snippets_keyboard(snippets: list, prefix: str = "snippet_") -> InlineKeyboardMarkup:
    """Строит клавиатуру со сниппетами (по 2 в ряд)"""
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки сниппетов (по 2 в ряд)
    for i in range(0, len(snippets), 2):
        row = []
        for j in range(2):
            if i + j < len(snippets):
                snippet = snippets[i + j]
                trigger = snippet.get('trigger', '')
                row.append(InlineKeyboardButton(
                    text=trigger,
                    callback_data=f"{prefix}{snippet.get('snippet_id')}"
                ))
        if row:
            builder.row(*row)
    
    # Кнопка "Назад"
    builder.row(InlineKeyboardButton(text="Назад", callback_data="snippets_back"))
    
    return builder.as_markup()


def build_my_snippets_keyboard(snippets: list) -> InlineKeyboardMarkup:
    """Строит клавиатуру для "Мои сниппеты" с кнопкой создания"""
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки сниппетов (по 2 в ряд)
    for i in range(0, len(snippets), 2):
        row = []
        for j in range(2):
            if i + j < len(snippets):
                snippet = snippets[i + j]
                trigger = snippet.get('trigger', '')
                row.append(InlineKeyboardButton(
                    text=trigger,
                    callback_data=f"snippet_my_{snippet.get('snippet_id')}"
                ))
        if row:
            builder.row(*row)
    
    # Кнопка "Создать сниппет"
    builder.row(InlineKeyboardButton(text="Создать сниппет", callback_data="snippet_create"))
    
    # Кнопка "Назад"
    builder.row(InlineKeyboardButton(text="Назад", callback_data="snippets_back"))
    
    return builder.as_markup()


def build_snippet_management_keyboard(snippet_id: int) -> InlineKeyboardMarkup:
    """Строит клавиатуру управления сниппетом"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="Просмотр", callback_data=f"snippet_view_{snippet_id}"))
    builder.row(InlineKeyboardButton(text="Редактировать", callback_data=f"snippet_edit_{snippet_id}"))
    builder.row(InlineKeyboardButton(text="Удалить", callback_data=f"snippet_delete_{snippet_id}"))
    builder.row(InlineKeyboardButton(text="Назад", callback_data="snippets_my"))
    
    return builder.as_markup()


def build_delete_confirm_keyboard(snippet_id: int) -> InlineKeyboardMarkup:
    """Строит клавиатуру подтверждения удаления"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="Да, удалить", callback_data=f"snippet_delete_confirm_{snippet_id}"))
    builder.row(InlineKeyboardButton(text="Отмена", callback_data=f"snippet_manage_{snippet_id}"))
    
    return builder.as_markup()


def build_cancel_keyboard() -> InlineKeyboardMarkup:
    """Строит клавиатуру с кнопкой отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="snippet_cancel"))
    return builder.as_markup()


@router.message(Command("snippets"))
async def snippets_command(message: Message, state: FSMContext, bot: Bot):
    """Обработчик команды /snippets (только в личке, только для админов)"""
    if message.chat.type != "private":
        return
    
    if message.from_user is None:
        return
    
    user_id = message.from_user.id
    
    # Проверка админства
    is_admin = await _check_user_is_admin_in_any_group(bot, user_id)
    if not is_admin:
        await message.answer("❌ Команда доступна только администраторам групп")
        return
    
    # Строим клавиатуру
    keyboard = build_main_menu_keyboard()
    
    # Отправляем сообщение
    text = "Панель управления сниппетами"
    sent_message = await message.answer(text, reply_markup=keyboard)
    
    # Сохраняем ID сообщения в состоянии
    await state.set_state(SnippetStates.main_menu)
    await state.update_data(message_id=sent_message.message_id)


@router.callback_query(F.data == "snippets_all")
async def snippets_all_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Все сниппеты'"""
    snippets = await get_all_snippets_api()
    
    if not snippets:
        text = "Все сниппеты Tsushima.Ru\n\nСниппетов пока нет"
        keyboard = build_snippets_keyboard([])
    else:
        text = "Все сниппеты Tsushima.Ru"
        keyboard = build_snippets_keyboard(snippets)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.set_state(SnippetStates.all_snippets)
    await callback.answer()


@router.callback_query(F.data == "snippets_my")
async def snippets_my_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Мои сниппеты'"""
    user_id = callback.from_user.id
    snippets = await get_user_snippets_api(user_id)
    
    if not snippets:
        text = "Мои сниппеты:\n\nУ вас нет созданных сниппетов"
    else:
        text = "Мои сниппеты:"
    
    keyboard = build_my_snippets_keyboard(snippets)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.set_state(SnippetStates.my_snippets)
    await callback.answer()


@router.callback_query(F.data.startswith("snippet_") & ~F.data.startswith("snippet_my_") & ~F.data.startswith("snippet_create") & ~F.data.startswith("snippet_cancel") & ~F.data.startswith("snippet_view_") & ~F.data.startswith("snippet_edit_") & ~F.data.startswith("snippet_delete_") & ~F.data.startswith("snippet_manage_"))
async def snippet_trigger_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработчик нажатия на триггер сниппета (из 'Все сниппеты')"""
    snippet_id = int(callback.data.replace("snippet_", ""))
    snippet = await get_snippet_by_id_api(snippet_id)
    
    if not snippet:
        await callback.answer("Сниппет не найден", show_alert=True)
        return
    
    trigger = snippet.get('trigger', '')
    message_text = snippet.get('message', '')
    media = snippet.get('media')
    media_type = snippet.get('media_type')
    
    # Формируем текст
    text = f"*{trigger}*\n\n*{message_text}*"
    
    # Отправляем сообщение
    if media and media_type:
        if media_type == 'photo':
            await bot.send_photo(
                chat_id=callback.from_user.id,
                photo=media,
                caption=text,
                parse_mode="Markdown"
            )
        elif media_type == 'video':
            await bot.send_video(
                chat_id=callback.from_user.id,
                video=media,
                caption=text,
                parse_mode="Markdown"
            )
    else:
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=text,
            parse_mode="Markdown"
        )
    
    # Возвращаемся в главное меню
    keyboard = build_main_menu_keyboard()
    await callback.message.edit_text("Панель управления сниппетами", reply_markup=keyboard)
    await state.set_state(SnippetStates.main_menu)
    await callback.answer()


@router.callback_query(F.data.startswith("snippet_my_"))
async def snippet_my_trigger_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик нажатия на триггер сниппета (из 'Мои сниппеты') - показывает меню управления"""
    snippet_id = int(callback.data.replace("snippet_my_", ""))
    snippet = await get_snippet_by_id_api(snippet_id)
    
    if not snippet:
        await callback.answer("Сниппет не найден", show_alert=True)
        return
    
    trigger = snippet.get('trigger', '')
    text = f"Управление сниппетом: *{trigger}*"
    keyboard = build_snippet_management_keyboard(snippet_id)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await state.update_data(managed_snippet_id=snippet_id)
    await callback.answer()


@router.callback_query(F.data.startswith("snippet_view_"))
async def snippet_view_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработчик кнопки 'Просмотр'"""
    snippet_id = int(callback.data.replace("snippet_view_", ""))
    snippet = await get_snippet_by_id_api(snippet_id)
    
    if not snippet:
        await callback.answer("Сниппет не найден", show_alert=True)
        return
    
    trigger = snippet.get('trigger', '')
    message_text = snippet.get('message', '')
    media = snippet.get('media')
    media_type = snippet.get('media_type')
    
    # Формируем текст
    text = f"*{trigger}*\n\n*{message_text}*"
    
    # Отправляем сообщение
    if media and media_type:
        if media_type == 'photo':
            await bot.send_photo(
                chat_id=callback.from_user.id,
                photo=media,
                caption=text,
                parse_mode="Markdown"
            )
        elif media_type == 'video':
            await bot.send_video(
                chat_id=callback.from_user.id,
                video=media,
                caption=text,
                parse_mode="Markdown"
            )
    else:
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=text,
            parse_mode="Markdown"
        )
    
    await callback.answer("Сниппет отправлен в личку")


@router.callback_query(F.data.startswith("snippet_edit_"))
async def snippet_edit_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Редактировать'"""
    snippet_id = int(callback.data.replace("snippet_edit_", ""))
    snippet = await get_snippet_by_id_api(snippet_id)
    
    if not snippet:
        await callback.answer("Сниппет не найден", show_alert=True)
        return
    
    await state.update_data(editing_snippet_id=snippet_id, editing_trigger=snippet.get('trigger'))
    
    text = f"Введите новый триггер для сниппета (текущий: {snippet.get('trigger')})"
    keyboard = build_cancel_keyboard()
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.set_state(SnippetStates.edit_trigger)
    await callback.answer()


@router.callback_query(F.data.startswith("snippet_delete_"))
async def snippet_delete_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Удалить'"""
    if callback.data.startswith("snippet_delete_confirm_"):
        # Подтверждение удаления
        snippet_id = int(callback.data.replace("snippet_delete_confirm_", ""))
        user_id = callback.from_user.id
        success = await delete_snippet_api(snippet_id, user_id)
        
        if success:
            # Возвращаемся в "Мои сниппеты"
            user_id = callback.from_user.id
            snippets = await get_user_snippets_api(user_id)
            
            if not snippets:
                text = "Мои сниппеты:\n\nУ вас нет созданных сниппетов"
            else:
                text = "Мои сниппеты:"
            
            keyboard = build_my_snippets_keyboard(snippets)
            await callback.message.edit_text(text, reply_markup=keyboard)
            await state.set_state(SnippetStates.my_snippets)
            await callback.answer("✅ Сниппет удален")
        else:
            await callback.answer("❌ Ошибка при удалении сниппета", show_alert=True)
    else:
        # Запрос подтверждения
        snippet_id = int(callback.data.replace("snippet_delete_", ""))
        snippet = await get_snippet_by_id_api(snippet_id)
        
        if not snippet:
            await callback.answer("Сниппет не найден", show_alert=True)
            return
        
        trigger = snippet.get('trigger', '')
        text = f"Вы уверены, что хотите удалить сниппет *{trigger}*?"
        keyboard = build_delete_confirm_keyboard(snippet_id)
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        await state.set_state(SnippetStates.delete_confirm)
        await callback.answer()


@router.callback_query(F.data.startswith("snippet_manage_"))
async def snippet_manage_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата к меню управления сниппетом"""
    snippet_id = int(callback.data.replace("snippet_manage_", ""))
    snippet = await get_snippet_by_id_api(snippet_id)
    
    if not snippet:
        await callback.answer("Сниппет не найден", show_alert=True)
        return
    
    trigger = snippet.get('trigger', '')
    text = f"Управление сниппетом: *{trigger}*"
    keyboard = build_snippet_management_keyboard(snippet_id)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await state.update_data(managed_snippet_id=snippet_id)
    await callback.answer()


@router.callback_query(F.data == "snippet_create")
async def snippet_create_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Создать сниппет'"""
    text = "Введите название сниппета, например - ммс (будет вызываться через ?ммс)"
    keyboard = build_cancel_keyboard()
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.set_state(SnippetStates.create_trigger)
    await callback.answer()


@router.callback_query(F.data == "snippet_cancel")
async def snippet_cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Отмена'"""
    user_id = callback.from_user.id
    snippets = await get_user_snippets_api(user_id)
    
    if not snippets:
        text = "Мои сниппеты:\n\nУ вас нет созданных сниппетов"
    else:
        text = "Мои сниппеты:"
    
    keyboard = build_my_snippets_keyboard(snippets)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.set_state(SnippetStates.my_snippets)
    await callback.answer()


@router.callback_query(F.data == "snippets_back")
async def snippets_back_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад'"""
    keyboard = build_main_menu_keyboard()
    await callback.message.edit_text("Панель управления сниппетами", reply_markup=keyboard)
    await state.set_state(SnippetStates.main_menu)
    await callback.answer()


@router.callback_query(F.data == "snippets_exit")
async def snippets_exit_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Выход'"""
    await callback.message.delete()
    await state.clear()
    await callback.answer()


@router.message(SnippetStates.create_trigger)
async def process_trigger_input(message: Message, state: FSMContext):
    """Обработчик ввода триггера"""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение с названием сниппета")
        return
    
    trigger = message.text.strip()
    
    # Валидация: одно слово, только буквы (кириллица/латиница), без цифр и символов
    if not re.match(r'^[a-zA-Zа-яА-ЯёЁ]+$', trigger):
        await message.answer("❌ Триггер должен быть одним словом, состоящим только из букв (без цифр и символов)")
        return
    
    # Проверка уникальности через API (пока просто сохраняем, проверка будет при создании)
    await state.update_data(trigger=trigger.lower())
    
    # Редактируем сообщение
    text = "Введите текст/описание для сниппета, если необходимо прикрепите одно изображение или видео"
    keyboard = build_cancel_keyboard()
    
    # Получаем message_id из состояния
    data = await state.get_data()
    message_id = data.get('message_id')
    
    if message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка редактирования сообщения: {e}")
            # Если не удалось отредактировать, отправляем новое
            sent_message = await message.answer(text, reply_markup=keyboard)
            await state.update_data(message_id=sent_message.message_id)
    else:
        sent_message = await message.answer(text, reply_markup=keyboard)
        await state.update_data(message_id=sent_message.message_id)
    
    await state.set_state(SnippetStates.create_message)


@router.message(SnippetStates.create_message)
async def process_message_input(message: Message, state: FSMContext):
    """Обработчик ввода сообщения и медиа"""
    data = await state.get_data()
    trigger = data.get('trigger')
    
    if not trigger:
        await message.answer("❌ Ошибка: триггер не найден. Начните заново.")
        await state.clear()
        return
    
    # Проверяем наличие медиа
    media = None
    media_type = None
    
    if message.photo:
        if len(message.photo) > 0:
            media = message.photo[-1].file_id  # Берем фото наибольшего размера
            media_type = 'photo'
    elif message.video:
        media = message.video.file_id
        media_type = 'video'
    
    # Валидация: если есть медиа, должно быть только одно
    if message.photo and message.video:
        await message.answer("❌ Пожалуйста, прикрепите только одно изображение ИЛИ одно видео, не оба")
        return
    
    # Проверяем наличие текста
    message_text = message.caption if (message.photo or message.video) else message.text
    
    if not message_text or not message_text.strip():
        await message.answer("❌ Пожалуйста, введите текст для сниппета")
        return
    
    message_text = message_text.strip()
    
    # Создаем сниппет через API
    user_id = message.from_user.id
    success = await create_snippet_api(user_id, trigger, message_text, media, media_type)
    
    if not success:
        await message.answer("❌ Ошибка при создании сниппета. Попробуйте еще раз.")
        return
    
    # Возвращаемся в "Мои сниппеты"
    snippets = await get_user_snippets_api(user_id)
    
    if not snippets:
        text = "Мои сниппеты:\n\nУ вас нет созданных сниппетов"
    else:
        text = "Мои сниппеты:"
    
    keyboard = build_my_snippets_keyboard(snippets)
    
    # Редактируем сообщение
    message_id = data.get('message_id')
    if message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка редактирования сообщения: {e}")
            # Если не удалось отредактировать, отправляем новое
            sent_message = await message.answer(text, reply_markup=keyboard)
            await state.update_data(message_id=sent_message.message_id)
    else:
        sent_message = await message.answer(text, reply_markup=keyboard)
        await state.update_data(message_id=sent_message.message_id)
    
    await state.set_state(SnippetStates.my_snippets)
    await message.answer("✅ Сниппет успешно создан!")


@router.message(SnippetStates.edit_trigger)
async def process_edit_trigger_input(message: Message, state: FSMContext):
    """Обработчик ввода нового триггера при редактировании"""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение с названием сниппета")
        return
    
    trigger = message.text.strip()
    
    # Валидация: одно слово, только буквы (кириллица/латиница), без цифр и символов
    if not re.match(r'^[a-zA-Zа-яА-ЯёЁ]+$', trigger):
        await message.answer("❌ Триггер должен быть одним словом, состоящим только из букв (без цифр и символов)")
        return
    
    data = await state.get_data()
    snippet_id = data.get('editing_snippet_id')
    
    if not snippet_id:
        await message.answer("❌ Ошибка: ID сниппета не найден. Начните заново.")
        await state.clear()
        return
    
    await state.update_data(editing_trigger=trigger.lower())
    
    # Редактируем сообщение
    text = "Введите новый текст/описание для сниппета, если необходимо прикрепите одно изображение или видео"
    keyboard = build_cancel_keyboard()
    
    # Получаем message_id из состояния
    message_id = data.get('message_id')
    
    if message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка редактирования сообщения: {e}")
            # Если не удалось отредактировать, отправляем новое
            sent_message = await message.answer(text, reply_markup=keyboard)
            await state.update_data(message_id=sent_message.message_id)
    else:
        sent_message = await message.answer(text, reply_markup=keyboard)
        await state.update_data(message_id=sent_message.message_id)
    
    await state.set_state(SnippetStates.edit_message)


@router.message(SnippetStates.edit_message)
async def process_edit_message_input(message: Message, state: FSMContext):
    """Обработчик ввода нового сообщения и медиа при редактировании"""
    data = await state.get_data()
    snippet_id = data.get('editing_snippet_id')
    trigger = data.get('editing_trigger')
    
    if not snippet_id or not trigger:
        await message.answer("❌ Ошибка: данные сниппета не найдены. Начните заново.")
        await state.clear()
        return
    
    # Проверяем наличие медиа
    media = None
    media_type = None
    
    if message.photo:
        if len(message.photo) > 0:
            media = message.photo[-1].file_id
            media_type = 'photo'
    elif message.video:
        media = message.video.file_id
        media_type = 'video'
    
    # Валидация: если есть медиа, должно быть только одно
    if message.photo and message.video:
        await message.answer("❌ Пожалуйста, прикрепите только одно изображение ИЛИ одно видео, не оба")
        return
    
    # Проверяем наличие текста
    message_text = message.caption if (message.photo or message.video) else message.text
    
    if not message_text or not message_text.strip():
        await message.answer("❌ Пожалуйста, введите текст для сниппета")
        return
    
    message_text = message_text.strip()
    
    # Обновляем сниппет через API
    user_id = message.from_user.id
    success = await update_snippet_api(snippet_id, user_id, trigger, message_text, media, media_type)
    
    if not success:
        await message.answer("❌ Ошибка при обновлении сниппета. Попробуйте еще раз.")
        return
    
    # Возвращаемся в "Мои сниппеты"
    user_id = message.from_user.id
    snippets = await get_user_snippets_api(user_id)
    
    if not snippets:
        text = "Мои сниппеты:\n\nУ вас нет созданных сниппетов"
    else:
        text = "Мои сниппеты:"
    
    keyboard = build_my_snippets_keyboard(snippets)
    
    # Редактируем сообщение
    message_id = data.get('message_id')
    if message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка редактирования сообщения: {e}")
            # Если не удалось отредактировать, отправляем новое
            sent_message = await message.answer(text, reply_markup=keyboard)
            await state.update_data(message_id=sent_message.message_id)
    else:
        sent_message = await message.answer(text, reply_markup=keyboard)
        await state.update_data(message_id=sent_message.message_id)
    
    await state.set_state(SnippetStates.my_snippets)
    await message.answer("✅ Сниппет успешно обновлен!")

