# database.py
import aiosqlite
from typing import Optional, List, Tuple, Any
from config import DATABASE

async def _column_exists(db, table: str, column: str) -> bool:
    cur = await db.execute(f"PRAGMA table_info({table})")
    cols = await cur.fetchall()
    return any(c[1] == column for c in cols)

async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                psn_id TEXT,
                platform TEXT,
                modes TEXT,
                goals TEXT,
                level TEXT,
                message_id INTEGER,
                state TEXT,
                trophies TEXT
            )
        """)
        # мягкие ALTER’ы
        if not await _column_exists(db, "users", "trophies"):
            await db.execute("ALTER TABLE users ADD COLUMN trophies TEXT")

        # Заявки
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trophy_applications (
                app_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                trophy_key TEXT NOT NULL,
                text TEXT,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending|approved|rejected|awaiting_reason
                reviewer_id INTEGER,
                reason TEXT,
                admin_chat_id INTEGER,
                admin_message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # мягкие ALTER’ы под новые поля
        if not await _column_exists(db, "trophy_applications", "admin_chat_id"):
            await db.execute("ALTER TABLE trophy_applications ADD COLUMN admin_chat_id INTEGER")
        if not await _column_exists(db, "trophy_applications", "admin_message_id"):
            await db.execute("ALTER TABLE trophy_applications ADD COLUMN admin_message_id INTEGER")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS trophy_application_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL  -- 'photo' | 'video' | 'document' | 'animation'
            )
        """)

        await db.execute("CREATE INDEX IF NOT EXISTS idx_trophy_applications_user ON trophy_applications(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_trophy_applications_status ON trophy_applications(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_trophy_files_app ON trophy_application_files(app_id)")

        await db.commit()

async def add_user(user_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, name, psn_id, platform, modes, goals, level, message_id, state, trophies)
            VALUES (?, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL)
        """, (user_id,))
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cur.fetchone()

async def update_user(user_id: int, field: str, value):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()

async def delete_user(user_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DATABASE) as db:
        cur = await db.execute("SELECT user_id FROM users")
        return await cur.fetchall()

# ---------- Трофеи: заявки ----------
async def create_trophy_application(user_id: int, trophy_key: str, text: Optional[str]) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        cur = await db.execute("""
            INSERT INTO trophy_applications (user_id, trophy_key, text)
            VALUES (?, ?, ?)
        """, (user_id, trophy_key, text))
        await db.commit()
        return cur.lastrowid

async def add_application_file(app_id: int, file_id: str, file_type: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            INSERT INTO trophy_application_files (app_id, file_id, file_type)
            VALUES (?, ?, ?)
        """, (app_id, file_id, file_type))
        await db.commit()

async def get_application(app_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        cur = await db.execute("SELECT * FROM trophy_applications WHERE app_id = ?", (app_id,))
        return await cur.fetchone()

async def get_application_files(app_id: int) -> List[tuple]:
    async with aiosqlite.connect(DATABASE) as db:
        cur = await db.execute("""
            SELECT file_id, file_type FROM trophy_application_files
             WHERE app_id = ?
             ORDER BY id ASC
        """, (app_id,))
        return await cur.fetchall()

async def set_application_status(app_id: int, status: str, reviewer_id: Optional[int] = None, reason: Optional[str] = None):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            UPDATE trophy_applications
               SET status = ?, reviewer_id = COALESCE(?, reviewer_id), reason = COALESCE(?, reason)
             WHERE app_id = ?
        """, (status, reviewer_id, reason, app_id))
        await db.commit()

async def set_application_admin_message(app_id: int, chat_id: int, message_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            UPDATE trophy_applications
               SET admin_chat_id = ?, admin_message_id = ?
             WHERE app_id = ?
        """, (chat_id, message_id, app_id))
        await db.commit()

async def get_application_admin_message(app_id: int) -> Optional[Tuple[int, int]]:
    async with aiosqlite.connect(DATABASE) as db:
        cur = await db.execute("""
            SELECT admin_chat_id, admin_message_id
              FROM trophy_applications
             WHERE app_id = ?
        """, (app_id,))
        row = await cur.fetchone()
        if row and row[0] and row[1]:
            return int(row[0]), int(row[1])
        return None

# ---------- Управление счётчиком заявок ----------
async def set_trophy_app_counter(start_from: int):
    """
    Устанавливает следующий ID для таблицы trophy_applications.
    Пример: set_trophy_app_counter(1) -> следующая заявка получит ID=1.
    """
    target = max(0, start_from - 1)  # seq всегда хранит "последний выданный", т.е. N-1
    async with aiosqlite.connect(DATABASE) as db:
        # Пытаемся обновить существующую запись
        await db.execute(
            "UPDATE sqlite_sequence SET seq = ? WHERE name = 'trophy_applications'",
            (target,),
        )
        # Если UPDATE не изменил строк, вставим новую запись
        cur = await db.execute("SELECT changes()")
        changed = (await cur.fetchone())[0]
        if not changed:
            await db.execute(
                "INSERT INTO sqlite_sequence (name, seq) VALUES ('trophy_applications', ?)",
                (target,),
            )
        await db.commit()