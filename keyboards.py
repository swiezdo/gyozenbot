from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import GROUP_LINK, TROPHIES_PER_PAGE

# Старт регистрации
def start_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать регистрацию", callback_data="start_registration")]
        ]
    )

# Платформы
def platform_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💻 ПК", callback_data="platform_pc")],
            [InlineKeyboardButton(text="🎮 PlayStation", callback_data="platform_playstation")],
        ]
    )

# Режимы (ВАЖНО: callback’и совпадают с твоими mapping’ами + есть mode_done)
def modes_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📖 Сюжет", callback_data="mode_story")],
            [InlineKeyboardButton(text="🏹 Выживание", callback_data="mode_survival")],
            [InlineKeyboardButton(text="🗻 Испытания Иё", callback_data="mode_trials")],
            [InlineKeyboardButton(text="📜 Главы", callback_data="mode_chapters")],
            [InlineKeyboardButton(text="✅ Готово", callback_data="mode_done")],
        ]
    )

# Цели (ВАЖНО: goal_done)
def goals_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏆 Получение трофеев", callback_data="goal_trophies")],
            [InlineKeyboardButton(text="🔎 Узнать что-то новое", callback_data="goal_learn")],
            [InlineKeyboardButton(text="👥 Поиск тиммейтов", callback_data="goal_teammates")],
            [InlineKeyboardButton(text="✅ Готово", callback_data="goal_done")],
        ]
    )

# Уровни сложности (ВАЖНО: level_done)
def level_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🥉 Бронза", callback_data="level_bronze"),
                InlineKeyboardButton(text="🥈 Серебро", callback_data="level_silver"),
            ],
            [
                InlineKeyboardButton(text="🥇 Золото", callback_data="level_gold"),
                InlineKeyboardButton(text="🏅 Платина", callback_data="level_platinum"),
            ],
            [
                InlineKeyboardButton(text="👻 Кошмар", callback_data="level_nightmare"),
                InlineKeyboardButton(text="🔥 HellMode", callback_data="level_hell"),
            ],
            [InlineKeyboardButton(text="✅ Завершить регистрацию", callback_data="level_done")],
        ]
    )

# После регистрации — с кнопкой Трофеи
def after_register_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏯 Группа Tsushima.Ru", url=GROUP_LINK)],
            [InlineKeyboardButton(text="📜 Профиль", callback_data="view_profile")],
            [InlineKeyboardButton(text="🏆 Трофеи", callback_data="trophies_open")],
            [InlineKeyboardButton(text="🏁 Начать заново", callback_data="start_over")],
        ]
    )

def back_to_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_main")]
        ]
    )

# ----- Трофеи -----
def trophies_list_keyboard(page: int, items: list[tuple[str, str]], has_prev: bool, has_next: bool):
    rows = []
    for key, title in items:
        rows.append([InlineKeyboardButton(text=title, callback_data=f"trophy_open:{key}:{page}")])

    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"trophy_page:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️ Вперёд", callback_data=f"trophy_page:{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def trophy_detail_keyboard(trophy_key: str, page: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Подать заявку", callback_data=f"trophy_apply:{trophy_key}:{page}")],
            [InlineKeyboardButton(text="⬅️ К списку", callback_data=f"trophy_back:{page}")]
        ]
    )

def trophy_cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="trophy_cancel")]
        ]
    )

def trophy_review_keyboard(app_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"trophy_mod_approve:{app_id}")],
            [InlineKeyboardButton(text="⛔ Отклонить", callback_data=f"trophy_mod_reject:{app_id}")]
        ]
    )
