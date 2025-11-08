# handlers/waves.py
import json
import re
import logging
from pathlib import Path
from typing import List
from html import escape

from aiogram import Router, F
from aiogram.types import Message

logger = logging.getLogger(__name__)
router = Router()

# ======= ПУТЬ К ФАЙЛУ (корень проекта) =======
WAVES_JSON_PATH = (Path(__file__).resolve().parent.parent / "json" / "waves.json")

# ======= ОФОРМЛЕНИЕ =======
SEP_TOP = "━━━━━━━━━━━━━━━━━━━━"
SEP_BOT = "━━━━━━━━━━━━━━━━━━━━"
MAP_EMOJI  = "🗺️"
MODS_EMOJI = "🧪"

# ======= УТИЛИТЫ =======

async def _sender_is_admin(message: Message) -> bool:
    try:
        cm = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        return cm.status in {"creator", "administrator"}
    except Exception:
        return False

def _strip_number_prefix(s: str) -> str:
    return re.sub(r"^\s*\d+[\.\)\-:]*\s*", "", s).strip()

def _smart_cap(s: str) -> str:
    s = s.strip()
    return (s[:1].upper() + s[1:].lower()) if s else s

def _parse_save_payload(text: str):
    """
    Формат:
    !записатьволны
    Название карты
    Название модификаторов
    1. хижина, лес, лес
    ...
    (ровно 15 строк)
    """
    lines = [ln.rstrip() for ln in text.splitlines()]

    if len(lines) < 4:
        raise ValueError("Недостаточно строк. Нужны: команда, карта, модификаторы, 15 строк волн.")

    title = lines[1].strip()
    mods  = lines[2].strip()
    waves_raw = [ln.strip() for ln in lines[3:] if ln.strip()]
    waves = [_strip_number_prefix(w) for w in waves_raw]

    if not title:
        raise ValueError("Пустое название карты.")
    if not mods:
        raise ValueError("Пустая строка модификаторов.")
    if len(waves) != 15:
        raise ValueError(f"Должно быть ровно 15 волн, сейчас: {len(waves)}.")

    for idx, w in enumerate(waves, start=1):
        parts = [p.strip() for p in w.split(",")]
        if len(parts) != 3:
            raise ValueError(f"В волне {idx} должно быть ровно 3 спавна через запятую. Нашёл: '{w}'")

    return title, mods, waves

def _atomic_write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def _format_html(title: str, mods: str, waves: List[str]) -> str:
    """
    HTML-вывод:
    - Карта/моды как в ТЗ.
    - Волны: курсив для номера, подчёркнутые спавны; для 3/6/9/12/15 — ещё и жирные.
    - Спавны авто-капитализируются: 'лес' -> 'Лес'
    - Пустая строка после 3, 6, 9 и 12 волн.
    """
    out: List[str] = []
    out.append(SEP_TOP)
    out.append(f"{MAP_EMOJI} Карта: <b>{escape(title)}</b>")
    out.append(f"{MODS_EMOJI} Модификаторы:")
    out.append(f"<b>{escape(mods)}</b>")
    out.append(SEP_TOP)

    for i, w in enumerate(waves, start=1):
        parts = [p.strip() for p in w.split(",")]
        parts = [_smart_cap(p) for p in parts]

        # каждая 3-я волна — жирным
        if i % 3 == 0:
            parts_fmt = [f"<u><b>{escape(p)}</b></u>" for p in parts]
        else:
            parts_fmt = [f"<u>{escape(p)}</u>" for p in parts]

        line = f"<i>{i}.</i> " + ", ".join(parts_fmt)
        out.append(line)

        # пустая строка после 3, 6, 9, 12 (но не после 15)
        if i % 3 == 0 and i != 15:
            out.append("")

    out.append(SEP_BOT)
    return "\n".join(out)

# ======= ХЕНДЛЕРЫ =======
# Используем регэксп-фильтры (без helper-лямбд), чтобы исключить NameError
@router.message(F.text.regexp(r"^\s*!записатьволны\b"))
async def cmd_save_waves(message: Message):
    if not await _sender_is_admin(message):
        await message.reply("Эта команда доступна только администраторам.")
        return
    try:
        title, mods, waves = _parse_save_payload(message.text or "")
        data = {"title": title, "mods": mods, "waves": waves}
        _atomic_write_json(WAVES_JSON_PATH, data)
        await message.reply(f"✅ Волны сохранены в {WAVES_JSON_PATH.name}")
    except Exception as e:
        await message.reply(
            "❌ Ошибка: " + str(e) +
            "\n\nОжидаемый формат:\n"
            "!записатьволны\n"
            "Название карты\n"
            "Название модификаторов\n"
            "1. хижина, лес, лес\n"
            "2. лес, лес, пляж\n"
            "...\n(всего 15 строк)"
        )

@router.message(F.text.regexp(r"^\s*!волны\b"))
async def cmd_show_waves(message: Message):
    if not WAVES_JSON_PATH.exists():
        await message.reply("⚠️ waves.json пока не создан. Сначала используйте !записатьволны.")
        return
    try:
        data = json.loads(WAVES_JSON_PATH.read_text(encoding="utf-8"))
        title = str(data.get("title", "")).strip()
        mods  = str(data.get("mods", "")).strip()
        waves = data.get("waves", [])
        if not isinstance(waves, list) or len(waves) != 15:
            raise ValueError("Некорректный формат 'waves' в файле.")
        text = _format_html(title, mods, waves)
        await message.reply(text, parse_mode="HTML")
    except Exception as e:
        await message.reply(f"❌ Не удалось прочитать waves.json: {e}")
