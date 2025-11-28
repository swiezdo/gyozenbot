# /gyozenbot/handlers/notifications_settings.py
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import API_BASE_URL
from api_client import api_get, api_post

router = Router()
logger = logging.getLogger(__name__)

# Описания режимов уведомлений
NOTIFICATION_DESCRIPTIONS = {
    'check': 'Вы будете уведомлены если кто-то будет искать игроков для прохождения еженедельных обновлений в игре (Главы, сюжет, выживание и т.д)',
    'speedrun': 'Вы будете уведомлены если кто-то будет искать игроков для прохождения выживания в режиме "Кошмар" на время.',
    'raid': 'Вы будете уведомлены если кто-то будет искать игроков для прохождения любой или всех глав повести об Иё',
    'ghost': 'Вы будете уведомлены если кто-то будет искать игроков для прохождения чего угодно в игре, это универсальное уведомление для тех, кому без разницы в какой режим играть и на какой сложности.',
    'hellmode': 'Вы будете уведомлены если кто-то будет искать игроков для прохождения выживания в режиме HellMode (Платина с 7-ю модификаторами).',
    'story': 'Вы будете уведомлены если кто-то будет искать игроков для прохождения сюжетных миссий на любой сложности.',
    'rivals': 'Вы будете уведомлены если кто-то будет искать игроков для прохождения режима Соперники на любой сложности.',
    'trials': 'Вы будете уведомлены если кто-то будет искать игроков для прохождения Испытаний Иё.',
}

# Названия режимов для кнопок
NOTIFICATION_NAMES = {
    'check': 'Галочки',
    'speedrun': 'Спидран',
    'raid': 'Набег/Рейд',
    'ghost': 'Призрак',
    'hellmode': 'HellMode',
    'story': 'Сюжет',
    'rivals': 'Соперники',
    'trials': 'Испытания Иё',
}

# Порядок отображения режимов
NOTIFICATION_ORDER = ['check', 'speedrun', 'raid', 'ghost', 'hellmode', 'story', 'rivals', 'trials']


class NotificationSettings(StatesGroup):
    """FSM стейты для настройки уведомлений"""
    main_menu = State()
    check = State()
    speedrun = State()
    raid = State()
    ghost = State()
    hellmode = State()
    story = State()
    rivals = State()
    trials = State()


async def get_user_notifications(user_id: int) -> dict:
    """Получает настройки уведомлений пользователя через API"""
    try:
        response_wrapper = await api_get(
            f"/api/notifications/user/{user_id}",
            use_bot_token=True
        )
        async with response_wrapper as response:
            if response.status == 200:
                data = await response.json()
                return data.get("notifications", {})
            else:
                logger.error(f"Ошибка получения настроек уведомлений: {response.status}")
                return {}
    except Exception as e:
        logger.error(f"Исключение при получении настроек уведомлений: {e}", exc_info=True)
        return {}


async def toggle_notification(user_id: int, notification_type: str) -> int:
    """Переключает настройку уведомления через API. Возвращает новое значение (0 или 1)"""
    try:
        response_wrapper = await api_post(
            f"/api/notifications/user/{user_id}/toggle/{notification_type}",
            use_bot_token=True
        )
        async with response_wrapper as response:
            if response.status == 200:
                data = await response.json()
                return data.get("value", 0)
            else:
                logger.error(f"Ошибка переключения уведомления: {response.status}")
                return -1
    except Exception as e:
        logger.error(f"Исключение при переключении уведомления: {e}", exc_info=True)
        return -1


def build_main_menu_keyboard(notifications: dict) -> InlineKeyboardMarkup:
    """Строит клавиатуру главного меню"""
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки режимов (по 2 в ряд)
    for i in range(0, len(NOTIFICATION_ORDER), 2):
        row = []
        for j in range(2):
            if i + j < len(NOTIFICATION_ORDER):
                notification_type = NOTIFICATION_ORDER[i + j]
                name = NOTIFICATION_NAMES[notification_type]
                value = notifications.get(notification_type, 0)
                status = "🔔" if value == 1 else "🔕"
                row.append(InlineKeyboardButton(
                    text=f"{status} {name}",
                    callback_data=f"notif_mode_{notification_type}"
                ))
        builder.row(*row)
    
    # Кнопка "Готово" на отдельной линии
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="notif_done"))
    
    return builder.as_markup()


def build_mode_keyboard(notification_type: str, value: int) -> InlineKeyboardMarkup:
    """Строит клавиатуру для режима уведомления"""
    builder = InlineKeyboardBuilder()
    
    # Кнопка включения/выключения
    status_text = "🔕 Выкл." if value == 1 else "🔔 Вкл."
    builder.row(InlineKeyboardButton(
        text=status_text,
        callback_data=f"notif_toggle_{notification_type}"
    ))
    
    # Кнопка "Назад"
    builder.row(InlineKeyboardButton(text="Назад", callback_data="notif_back"))
    
    return builder.as_markup()


@router.message(Command("notifications"))
async def notifications_command(message: Message, state: FSMContext):
    """Обработчик команды /notifications (только в личке)"""
    if message.chat.type != "private":
        return
    
    user_id = message.from_user.id
    
    # Получаем настройки уведомлений
    notifications = await get_user_notifications(user_id)
    
    # Строим клавиатуру
    keyboard = build_main_menu_keyboard(notifications)
    
    # Отправляем сообщение
    text = "Здесь вы можете настроить какие уведомления хотите получать"
    sent_message = await message.answer(text, reply_markup=keyboard)
    
    # Сохраняем ID сообщения в состоянии
    await state.set_state(NotificationSettings.main_menu)
    await state.update_data(message_id=sent_message.message_id)


@router.callback_query(F.data == "notifications_settings")
async def notifications_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик callback кнопки 'Уведомления' из уведомления"""
    user_id = callback.from_user.id
    
    # Получаем настройки уведомлений
    notifications = await get_user_notifications(user_id)
    
    # Строим клавиатуру
    keyboard = build_main_menu_keyboard(notifications)
    
    # Отправляем сообщение
    text = "Здесь вы можете настроить какие уведомления хотите получать"
    sent_message = await callback.message.answer(text, reply_markup=keyboard)
    
    # Сохраняем ID сообщения в состоянии
    await state.set_state(NotificationSettings.main_menu)
    await state.update_data(message_id=sent_message.message_id)
    
    await callback.answer()


@router.callback_query(F.data.startswith("notif_mode_"))
async def mode_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора режима уведомления"""
    notification_type = callback.data.replace("notif_mode_", "")
    
    if notification_type not in NOTIFICATION_DESCRIPTIONS:
        await callback.answer("Неизвестный режим", show_alert=True)
        return
    
    user_id = callback.from_user.id
    
    # Получаем текущие настройки
    notifications = await get_user_notifications(user_id)
    value = notifications.get(notification_type, 0)
    
    # Получаем описание и название
    description = NOTIFICATION_DESCRIPTIONS[notification_type]
    name = NOTIFICATION_NAMES[notification_type]
    
    # Строим клавиатуру
    keyboard = build_mode_keyboard(notification_type, value)
    
    # Редактируем сообщение
    text = f"{description}"
    await callback.message.edit_text(text, reply_markup=keyboard)
    
    # Устанавливаем соответствующий стейт
    state_mapping = {
        'check': NotificationSettings.check,
        'speedrun': NotificationSettings.speedrun,
        'raid': NotificationSettings.raid,
        'ghost': NotificationSettings.ghost,
        'hellmode': NotificationSettings.hellmode,
        'story': NotificationSettings.story,
        'rivals': NotificationSettings.rivals,
        'trials': NotificationSettings.trials,
    }
    await state.set_state(state_mapping[notification_type])
    await state.update_data(notification_type=notification_type)
    
    await callback.answer()


@router.callback_query(F.data.startswith("notif_toggle_"))
async def toggle_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик переключения уведомления - переключает и возвращается в главное меню"""
    notification_type = callback.data.replace("notif_toggle_", "")
    
    if notification_type not in NOTIFICATION_DESCRIPTIONS:
        await callback.answer("Неизвестный режим", show_alert=True)
        return
    
    user_id = callback.from_user.id
    
    # Переключаем уведомление
    new_value = await toggle_notification(user_id, notification_type)
    
    if new_value == -1:
        await callback.answer("Ошибка при переключении уведомления", show_alert=True)
        return
    
    # Получаем обновленные настройки уведомлений
    notifications = await get_user_notifications(user_id)
    
    # Строим клавиатуру главного меню
    keyboard = build_main_menu_keyboard(notifications)
    
    # Возвращаемся к главному меню
    text = "Здесь вы можете настроить какие уведомления хотите получать"
    await callback.message.edit_text(text, reply_markup=keyboard)
    
    # Возвращаемся к главному меню
    await state.set_state(NotificationSettings.main_menu)
    
    await callback.answer()


@router.callback_query(F.data == "notif_back")
async def back_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' - возврат к главному меню"""
    user_id = callback.from_user.id
    
    # Получаем настройки уведомлений
    notifications = await get_user_notifications(user_id)
    
    # Строим клавиатуру главного меню
    keyboard = build_main_menu_keyboard(notifications)
    
    # Редактируем сообщение
    text = "Здесь вы можете настроить какие уведомления хотите получать"
    await callback.message.edit_text(text, reply_markup=keyboard)
    
    # Возвращаемся к главному меню
    await state.set_state(NotificationSettings.main_menu)
    
    await callback.answer()


@router.callback_query(F.data == "notif_done")
async def done_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Готово' - удаление сообщения"""
    # Удаляем сообщение
    await callback.message.delete()
    
    # Очищаем состояние
    await state.clear()
    
    await callback.answer()

