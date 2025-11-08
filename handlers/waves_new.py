import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import GROUP_ID, TROPHY_GROUP_CHAT_ID

logger = logging.getLogger(__name__)
router = Router()

BASE_DIR = Path(__file__).resolve().parent.parent
WEEKS_JSON_PATH = BASE_DIR / "json" / "weeks.json"
SPAWNS_JSON_PATH = BASE_DIR / "json" / "spawns.json"

CB_PART = "waves:part"
CB_WEEK = "waves:week"
CB_CONTINUE = "waves:continue"
CB_SPAWN = "waves:spawn"
CB_SPAWN_TYPE = "waves:spawn_type"
CB_EDIT = "waves:edit"
CB_EDIT_SELECT = "waves:edit_select"
CB_EDIT_CANCEL = "waves:edit_cancel"
CB_DONE = "waves:done"
CB_RESET = "waves:reset"
CB_BACK = "waves:back"
CB_BACK_WEEK = "waves:back_week"
CB_BACK_PART = "waves:back_part"
CB_CANCEL = "waves:cancel"

GROUP_IDS = tuple(
    chat_id for chat_id in (GROUP_ID, TROPHY_GROUP_CHAT_ID) if chat_id
)

# Сразу подготовленная заготовка для whitelisting конкретных пользователей.
# Пример:
# ALLOWED_USER_IDS = {
#     123456789,  # имя участника
#     999888777,  # ещё один участник
# }
ALLOWED_USER_IDS: set[int] = set()

MAX_WAVES = 15
SPAWNS_PER_WAVE = 3


@dataclass
class WeekInfo:
    code: str
    map_name: str
    mod1: str
    mod2: str


@dataclass
class WavesSession:
    chat_id: int
    user_id: int
    message_id: Optional[int] = None
    stage: str = "part"  # part -> week -> confirm -> entry
    part: Optional[str] = None
    week: Optional[str] = None
    map_name: Optional[str] = None
    mod1: Optional[str] = None
    mod2: Optional[str] = None
    map_slug: Optional[str] = None
    spawn_lookup: Dict[str, str] = field(default_factory=dict)
    pending_spawn_key: Optional[str] = None
    waves: List[List[str]] = field(default_factory=list)
    available_weeks: Dict[str, WeekInfo] = field(default_factory=dict)
    edit_mode: bool = False
    edit_target: Optional[tuple[int, int]] = None
    edit_original: Optional[str] = None

    def reset(self) -> None:
        self.stage = "part"
        self.part = None
        self.week = None
        self.map_name = None
        self.mod1 = None
        self.mod2 = None
        self.map_slug = None
        self.spawn_lookup.clear()
        self.pending_spawn_key = None
        self.available_weeks.clear()
        self.waves.clear()
        self.edit_mode = False
        self.edit_target = None
        self.edit_original = None


_sessions: Dict[int, WavesSession] = {}


def _normalize_week_code(value) -> str:
    if isinstance(value, str):
        return value
    return f"{value}"


@lru_cache(maxsize=1)
def _load_weeks() -> List[WeekInfo]:
    raw = json.loads(WEEKS_JSON_PATH.read_text(encoding="utf-8"))
    result: List[WeekInfo] = []
    for item in raw:
        result.append(
            WeekInfo(
                code=_normalize_week_code(item["week"]),
                map_name=item["map"],
                mod1=item["mod1"],
                mod2=item["mod2"],
            )
        )
    return result


@lru_cache(maxsize=1)
def _load_spawns() -> List[dict]:
    return json.loads(SPAWNS_JSON_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _spawns_by_slug() -> Dict[str, dict]:
    return {
        entry["map"]: entry
        for entry in _load_spawns()
        if "map" in entry
    }


def _get_weeks_by_part(part: str) -> List[WeekInfo]:
    target_prefix = f"{part}."
    return [
        item
        for item in _load_weeks()
        if item.code.startswith(target_prefix)
    ][:8]


def _find_spawn_config_by_slug(slug: Optional[str]) -> Optional[dict]:
    if not slug:
        return None
    return _spawns_by_slug().get(slug)


MAP_NAME_TO_SLUG_RAW = {
    "Берега отмщения": "shores",
    "Кровь на снегу": "bis",
    "Оборона деревни Аой": "aoi",
    "Тени войны": "shadows",
    "Сумерки и пепел": "twilight",
    "Кровь и сталь": "bas",
}
MAP_NAME_TO_SLUG = {k: v for k, v in MAP_NAME_TO_SLUG_RAW.items()}
MAP_NAME_TO_SLUG_LOWER = {k.lower(): v for k, v in MAP_NAME_TO_SLUG_RAW.items()}


def _resolve_map_slug(map_name: Optional[str]) -> Optional[str]:
    if not map_name:
        return None
    return MAP_NAME_TO_SLUG.get(map_name) or MAP_NAME_TO_SLUG_LOWER.get(map_name.lower())


SPAWN_LAYOUT = {
    "shores": [
        ["spawn1"],
        ["spawn1_type1", "spawn1_type2"],
        ["spawn2"],
        ["spawn3"],
        ["spawn4"],
    ],
    "aoi": [
        ["spawn1"],
        ["spawn2"],
        ["spawn3"],
        ["spawn4"],
        ["spawn5"],
    ],
    "shadows": [
        ["spawn1"],
        ["spawn1_type1", "spawn1_type2", "spawn1_type3"],
        ["spawn2"],
        ["spawn3"],
        ["spawn3_type1", "spawn3_type2", "spawn3_type3"],
    ],
    "bis": [
        ["spawn1"],
        ["spawn2"],
        ["spawn3"],
    ],
    "twilight": [
        ["spawn1"],
        ["spawn2"],
        ["spawn2_type1", "spawn2_type2"],
        ["spawn3"],
        ["spawn4"],
        ["spawn4_type1", "spawn4_type2"],
    ],
    "bas": [
        ["spawn1"],
        ["spawn2"],
        ["spawn2_type1", "spawn2_type2"],
        ["spawn3"],
        ["spawn3_type1", "spawn3_type2"],
        ["spawn4"],
    ],
}


def _get_type_keys_for_spawn(map_slug: Optional[str], base_key: str) -> List[str]:
    layout = SPAWN_LAYOUT.get(map_slug or "")
    if not layout:
        return []
    prefix = f"{base_key}_type"
    result: List[str] = []
    for row in layout:
        for key in row:
            if key.startswith(prefix):
                result.append(key)
    return result


def _commit_spawn_value(session: WavesSession, value: str) -> None:
    if session.edit_target is not None:
        wave_idx, spawn_idx = session.edit_target
        if wave_idx < len(session.waves) and spawn_idx < len(session.waves[wave_idx]):
            session.waves[wave_idx][spawn_idx] = value
        session.edit_target = None
        session.edit_original = None
        session.edit_mode = False
    else:
        if not session.waves or len(session.waves[-1]) == SPAWNS_PER_WAVE:
            if len(session.waves) >= MAX_WAVES:
                raise ValueError("Превышено количество волн.")
            session.waves.append([])
        session.waves[-1].append(value)

    session.pending_spawn_key = None


def _is_full(session: WavesSession) -> bool:
    if len(session.waves) != MAX_WAVES:
        return False
    for wave in session.waves:
        if len(wave) != SPAWNS_PER_WAVE:
            return False
        if any(value is None for value in wave):
            return False
    return True


async def _check_access(message: Message) -> bool:
    if message.chat.type != "private":
        await message.reply("Эта команда доступна только в личных сообщениях с ботом.")
        return False

    if message.from_user is None:
        await message.reply("Не удалось определить пользователя.")
        return False

    if message.from_user.id in ALLOWED_USER_IDS:
        return True

    bot = message.bot
    for chat_id in GROUP_IDS:
        try:
            member = await bot.get_chat_member(chat_id, message.from_user.id)
            if member.status in {"administrator", "creator"}:
                return True
        except Exception as exc:
            logger.debug("Не удалось проверить права в чате %s: %s", chat_id, exc)

    await message.reply("Команда доступна только администраторам групп, где находится бот.")
    return False


def _get_or_create_session(message: Message) -> WavesSession:
    user_id = message.from_user.id
    session = _sessions.get(user_id)
    if session:
        return session
    session = WavesSession(chat_id=message.chat.id, user_id=user_id)
    _sessions[user_id] = session
    return session


def _cleanup_session(session: WavesSession, keep_message: bool = False) -> None:
    session.reset()
    if not keep_message:
        session.message_id = None


def _build_part_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1-8 неделя", callback_data=f"{CB_PART}:1"),
        InlineKeyboardButton(text="9-16 неделя", callback_data=f"{CB_PART}:2"),
    )
    builder.row(
        InlineKeyboardButton(text="🚪 Выход", callback_data=CB_CANCEL),
    )
    return builder.as_markup()


def _build_week_keyboard(session: WavesSession) -> InlineKeyboardMarkup:
    weeks = _get_weeks_by_part(session.part or "1")
    session.available_weeks = {week.code: week for week in weeks}
    builder = InlineKeyboardBuilder()
    for week in weeks:
        label = f"{week.code} - {week.map_name}"
        builder.row(
            InlineKeyboardButton(
                text=label,
                callback_data=f"{CB_WEEK}:{week.code}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data=CB_BACK_PART),
        InlineKeyboardButton(text="🚪 Выход", callback_data=CB_CANCEL),
    )
    return builder.as_markup()


def _build_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="▶️ Да", callback_data=CB_CONTINUE),
        InlineKeyboardButton(text="↩️ Назад", callback_data=CB_BACK_WEEK),
        InlineKeyboardButton(text="🚪 Выход", callback_data=CB_CANCEL),
    )
    return builder.as_markup()


def _build_finish_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛠️ Исправить", callback_data=CB_EDIT),
        InlineKeyboardButton(text="✅ Готово", callback_data=CB_DONE),
        InlineKeyboardButton(text="♻️ Сброс", callback_data=CB_RESET),
    )
    return builder.as_markup()


def _build_spawn_keyboard(session: WavesSession) -> InlineKeyboardMarkup:
    spawn_config = _find_spawn_config_by_slug(session.map_slug)
    if not spawn_config:
        raise ValueError(
            f"Не найден конфиг спавнов для карты '{session.map_name or session.map_slug}'"
        )

    map_slug = spawn_config.get("map")
    layout = SPAWN_LAYOUT.get(map_slug or "")
    if not layout:
        raise ValueError(f"Неизвестный макет для карты '{map_slug}'")

    session.map_slug = map_slug
    session.spawn_lookup.clear()
    session.pending_spawn_key = None

    if _is_full(session) and session.edit_target is None and not session.edit_mode:
        return _build_finish_keyboard()

    builder = InlineKeyboardBuilder()
    counter = 0

    for row in layout:
        row_buttons: List[InlineKeyboardButton] = []
        for idx, key in enumerate(row):
            if "_type" in key:
                continue
            label = spawn_config.get(key)
            if not label:
                continue
            counter += 1
            btn_id = str(counter)
            session.spawn_lookup[btn_id] = label
            row_buttons.append(
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"{CB_SPAWN}:{btn_id}:{key}",
                )
            )
        if row_buttons:
            builder.row(*row_buttons)

    if session.edit_target is not None:
        builder.row(
            InlineKeyboardButton(text="↩️ Отменить", callback_data=CB_EDIT_CANCEL),
            InlineKeyboardButton(text="🚪 Выход", callback_data=CB_CANCEL),
        )
    else:
        extra_buttons: List[InlineKeyboardButton] = []
        if session.waves:
            extra_buttons.append(
                InlineKeyboardButton(text="🛠️ Исправить", callback_data=CB_EDIT)
            )
        extra_buttons.append(
            InlineKeyboardButton(text="🚪 Выход", callback_data=CB_CANCEL)
        )
        builder.row(*extra_buttons)

    return builder.as_markup()


def _build_type_keyboard(
    session: WavesSession,
    base_key: str,
    type_keys: List[str],
) -> InlineKeyboardMarkup:
    spawn_config = _find_spawn_config_by_slug(session.map_slug)
    session.pending_spawn_key = base_key
    builder = InlineKeyboardBuilder()
    for key in type_keys:
        label = spawn_config.get(key)
        if not label:
            continue
        builder.row(
            InlineKeyboardButton(
                text=label,
                callback_data=f"{CB_SPAWN_TYPE}:{base_key}:{key}",
            )
        )

    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data=CB_BACK),
    )
    cancel_buttons: List[InlineKeyboardButton] = []
    if session.edit_target is not None:
        cancel_buttons.append(
            InlineKeyboardButton(text="↩️ Отменить", callback_data=CB_EDIT_CANCEL)
        )
    cancel_buttons.append(
        InlineKeyboardButton(text="🚪 Выход", callback_data=CB_CANCEL)
    )
    builder.row(*cancel_buttons)
    return builder.as_markup()


def _build_edit_grid(session: WavesSession) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for w_idx, wave in enumerate(session.waves):
        if not wave:
            continue
        row_buttons: List[InlineKeyboardButton] = []
        for s_idx, _ in enumerate(wave):
            label = f"{w_idx + 1}.{s_idx + 1}"
            row_buttons.append(
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"{CB_EDIT_SELECT}:{w_idx}:{s_idx}",
                )
            )
        if row_buttons:
            builder.row(*row_buttons)

    builder.row(
        InlineKeyboardButton(text="↩️ Отменить", callback_data=CB_EDIT_CANCEL),
    )
    return builder.as_markup()


def _format_wave_progress(session: WavesSession) -> str:
    lines: List[str] = [
        f"Неделя: {session.week}",
        f"Карта: {session.map_name}",
        f"Модификатор 1: {session.mod1}",
        f"Модификатор 2: {session.mod2}",
        "",
    ]

    for w_idx, wave in enumerate(session.waves):
        parts: List[str] = []
        for s_idx, value in enumerate(wave):
            if session.edit_target == (w_idx, s_idx):
                parts.append("<u><b>Замена</b></u>")
            elif value:
                parts.append(value)
        if parts:
            lines.append(f"{w_idx + 1}. {', '.join(parts)}")
        else:
            lines.append(f"{w_idx + 1}.")

    if (
        session.edit_target is None
        and len(session.waves) < MAX_WAVES
        and (not session.waves or len(session.waves[-1]) == SPAWNS_PER_WAVE)
    ):
            lines.append(f"{len(session.waves) + 1}.")

    return "\n".join(lines)


@router.message(Command("waves"))
async def cmd_waves(message: Message) -> None:
    if not await _check_access(message):
        return

    session = _get_or_create_session(message)

    if session.message_id:
        try:
            await message.bot.delete_message(session.chat_id, session.message_id)
        except Exception as exc:
            logger.debug(
                "Не удалось удалить предыдущее сообщение %s: %s",
                session.message_id,
                exc,
            )

    _cleanup_session(session, keep_message=False)

    sent = await message.answer(
        "Выберите первую или вторую часть ротации:",
        reply_markup=_build_part_keyboard(),
    )
    session.message_id = sent.message_id
    session.stage = "part"


def _session_from_callback(callback: CallbackQuery) -> Optional[WavesSession]:
    user = callback.from_user
    if not user:
        return None
    session = _sessions.get(user.id)
    if session and session.message_id == callback.message.message_id:
        return session
    return None


@router.callback_query(F.data.startswith(f"{CB_PART}:"))
async def part_selected(callback: CallbackQuery) -> None:
    session = _session_from_callback(callback)
    if not session:
        await callback.answer("Сессия не найдена, вызовите /waves заново.", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    session.part = parts[2]
    session.stage = "week"

    await callback.message.edit_text(
        "Выберите номер недели:",
        reply_markup=_build_week_keyboard(session),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{CB_WEEK}:"))
async def week_selected(callback: CallbackQuery) -> None:
    session = _session_from_callback(callback)
    if not session:
        await callback.answer("Сессия не найдена, вызовите /waves заново.", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    week = session.available_weeks.get(parts[2])
    if not week:
        await callback.answer("Неделя недоступна.", show_alert=True)
        return

    session.week = week.code
    session.map_name = week.map_name
    session.mod1 = week.mod1
    session.mod2 = week.mod2
    session.stage = "confirm"
    session.map_slug = _resolve_map_slug(week.map_name)

    text = (
        f"Неделя: {week.code}\n"
        f"Карта: {week.map_name}\n"
        f"Модификатор 1: {week.mod1}\n"
        f"Модификатор 2: {week.mod2}\n\n"
        f"Продолжить?"
    )

    await callback.message.edit_text(
        text,
        reply_markup=_build_confirm_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == CB_BACK_WEEK)
async def back_to_week(callback: CallbackQuery) -> None:
    session = _session_from_callback(callback)
    if not session:
        await callback.answer()
        return

    if not session.part:
        await callback.answer("Сначала выберите часть ротации.", show_alert=True)
        return

    session.stage = "week"
    session.week = None
    session.map_name = None
    session.mod1 = None
    session.mod2 = None
    session.map_slug = None

    await callback.message.edit_text(
        "Выберите номер недели:",
        reply_markup=_build_week_keyboard(session),
    )
    await callback.answer()


@router.callback_query(F.data == CB_BACK_PART)
async def back_to_part(callback: CallbackQuery) -> None:
    session = _session_from_callback(callback)
    if not session:
        await callback.answer()
        return

    session.stage = "part"
    session.part = None
    session.week = None
    session.map_name = None
    session.mod1 = None
    session.mod2 = None
    session.map_slug = None
    session.available_weeks.clear()

    await callback.message.edit_text(
        "Выберите первую или вторую часть ротации:",
        reply_markup=_build_part_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == CB_CONTINUE)
async def confirm_continue(callback: CallbackQuery) -> None:
    session = _session_from_callback(callback)
    if not session:
        await callback.answer("Сессия не найдена, вызовите /waves заново.", show_alert=True)
        return

    if not session.week:
        await callback.answer("Сначала выберите неделю.", show_alert=True)
        return

    if not session.map_slug:
        await callback.answer("Не удалось определить карту для выбранной недели.", show_alert=True)
        return

    session.stage = "entry"
    session.waves.clear()
    session.edit_mode = False
    session.edit_target = None
    session.edit_original = None
    session.pending_spawn_key = None

    try:
        keyboard = _build_spawn_keyboard(session)
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await callback.message.edit_text(
        _format_wave_progress(session),
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{CB_SPAWN}:"))
async def spawn_pressed(callback: CallbackQuery) -> None:
    session = _session_from_callback(callback)
    if not session:
        await callback.answer("Сессия не найдена, вызовите /waves заново.", show_alert=True)
        return

    if session.stage != "entry":
        await callback.answer()
        return

    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    btn_id = parts[2]
    spawn_key = parts[3]

    spawn_name = session.spawn_lookup.get(btn_id)
    if not spawn_name:
        await callback.answer("Неизвестный спавн.", show_alert=True)
        return

    if _is_full(session) and session.edit_target is None:
        await callback.answer("Все волны уже записаны.", show_alert=True)
        return

    spawn_config = _find_spawn_config_by_slug(session.map_slug)
    type_keys = _get_type_keys_for_spawn(session.map_slug, spawn_key)

    if type_keys:
        await callback.message.edit_text(
            _format_wave_progress(session),
            reply_markup=_build_type_keyboard(session, spawn_key, type_keys),
        )
        await callback.answer()
        return

    _commit_spawn_value(session, spawn_name)

    markup = (
        _build_finish_keyboard()
        if _is_full(session) and session.edit_target is None
        else _build_spawn_keyboard(session)
    )

    await callback.message.edit_text(
        _format_wave_progress(session),
        reply_markup=markup,
    )
    await callback.answer(spawn_name)


@router.callback_query(F.data.startswith(f"{CB_SPAWN_TYPE}:"))
async def spawn_type_pressed(callback: CallbackQuery) -> None:
    session = _session_from_callback(callback)
    if not session:
        await callback.answer("Сессия не найдена, вызовите /waves заново.", show_alert=True)
        return

    if session.stage != "entry":
        await callback.answer()
        return

    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    base_key = parts[2]
    type_key = parts[3]

    spawn_config = _find_spawn_config_by_slug(session.map_slug)
    base_label = spawn_config.get(base_key)
    type_label = spawn_config.get(type_key)

    if not base_label or not type_label:
        await callback.answer("Неизвестный спавн.", show_alert=True)
        return

    alias_label = spawn_config.get(f"{type_key}_alias")
    if alias_label:
        final_label = alias_label
    else:
        final_label = f"{base_label} {type_label}"

    try:
        _commit_spawn_value(session, final_label)
    except ValueError:
        await callback.answer("Уже записано 15 волн.", show_alert=True)
        return

    markup = (
        _build_finish_keyboard()
        if _is_full(session) and session.edit_target is None
        else _build_spawn_keyboard(session)
    )

    await callback.message.edit_text(
        _format_wave_progress(session),
        reply_markup=markup,
    )
    await callback.answer(type_label)


@router.callback_query(F.data == CB_EDIT)
async def edit_requested(callback: CallbackQuery) -> None:
    session = _session_from_callback(callback)
    if not session:
        await callback.answer()
        return

    if session.stage != "entry":
        await callback.answer()
        return

    if not session.waves:
        await callback.answer("Пока нечего исправлять.", show_alert=True)
        return

    session.edit_mode = True
    session.edit_target = None
    session.edit_original = None
    session.pending_spawn_key = None

    await callback.message.edit_text(
        _format_wave_progress(session),
        reply_markup=_build_edit_grid(session),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{CB_EDIT_SELECT}:"))
async def edit_select(callback: CallbackQuery) -> None:
    session = _session_from_callback(callback)
    if not session:
        await callback.answer()
        return

    if session.stage != "entry":
        await callback.answer()
        return

    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    try:
        wave_idx = int(parts[2])
        spawn_idx = int(parts[3])
    except ValueError:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    if wave_idx >= len(session.waves) or spawn_idx >= len(session.waves[wave_idx]):
        await callback.answer("Позиция недоступна.", show_alert=True)
        return

    session.edit_mode = True
    session.edit_target = (wave_idx, spawn_idx)
    session.edit_original = session.waves[wave_idx][spawn_idx]
    session.pending_spawn_key = None

    await callback.message.edit_text(
        _format_wave_progress(session),
        reply_markup=_build_spawn_keyboard(session),
    )
    await callback.answer()


@router.callback_query(F.data == CB_EDIT_CANCEL)
async def edit_cancel(callback: CallbackQuery) -> None:
    session = _session_from_callback(callback)
    if not session:
        await callback.answer()
        return

    if session.stage != "entry":
        await callback.answer()
        return

    if session.edit_target is not None and session.edit_original is not None:
        wave_idx, spawn_idx = session.edit_target
        if wave_idx < len(session.waves) and spawn_idx < len(session.waves[wave_idx]):
            session.waves[wave_idx][spawn_idx] = session.edit_original

    session.edit_mode = False
    session.edit_target = None
    session.edit_original = None
    session.pending_spawn_key = None

    markup = (
        _build_finish_keyboard()
        if _is_full(session)
        else _build_spawn_keyboard(session)
    )

    await callback.message.edit_text(
        _format_wave_progress(session),
        reply_markup=markup,
    )
    await callback.answer()


@router.callback_query(F.data == CB_RESET)
async def reset_waves(callback: CallbackQuery) -> None:
    session = _session_from_callback(callback)
    if not session:
        await callback.answer()
        return

    if session.stage != "entry":
        await callback.answer()
        return

    session.waves.clear()
    session.edit_mode = False
    session.edit_target = None
    session.edit_original = None
    session.pending_spawn_key = None

    await callback.message.edit_text(
        _format_wave_progress(session),
        reply_markup=_build_spawn_keyboard(session),
    )
    await callback.answer("Список волн очищен.")


@router.callback_query(F.data == CB_DONE)
async def finish_placeholder(callback: CallbackQuery) -> None:
    await callback.answer("Функция будет добавлена позже.")


@router.callback_query(F.data == CB_BACK)
async def spawn_back(callback: CallbackQuery) -> None:
    session = _session_from_callback(callback)
    if not session:
        await callback.answer()
        return

    if session.stage != "entry":
        await callback.answer()
        return

    session.pending_spawn_key = None

    await callback.message.edit_text(
        _format_wave_progress(session),
        reply_markup=_build_spawn_keyboard(session),
    )
    await callback.answer()


@router.callback_query(F.data == CB_CANCEL)
async def cancel_session(callback: CallbackQuery) -> None:
    session = _session_from_callback(callback)
    if not session:
        await callback.answer()
        return

    chat_id = session.chat_id
    message_id = session.message_id
    user_id = session.user_id

    _cleanup_session(session)
    _sessions.pop(user_id, None)

    if message_id:
        try:
            await callback.bot.delete_message(chat_id, message_id)
        except Exception as exc:
            logger.debug("Не удалось удалить сообщение %s: %s", message_id, exc)

    await callback.answer()

