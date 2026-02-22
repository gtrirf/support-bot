import aiosqlite
from typing import Optional

_db: Optional[aiosqlite.Connection] = None

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    full_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS operators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    full_name TEXT,
    status TEXT CHECK(status IN ('free', 'busy')) DEFAULT 'free'
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    text TEXT NOT NULL,
    answer_text TEXT,
    answered_by INTEGER REFERENCES operators(id),
    answered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS live_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    operator_id INTEGER REFERENCES operators(id),
    status TEXT CHECK(status IN ('waiting', 'active', 'closed')) DEFAULT 'waiting',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP
);
"""


async def init_db(database_url: str) -> None:
    global _db
    _db = await aiosqlite.connect(database_url)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.executescript(CREATE_TABLES_SQL)
    await _db.commit()


async def close_db() -> None:
    global _db
    if _db:
        await _db.close()
        _db = None


def get_db() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db
