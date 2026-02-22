from app.db.database import get_db


# ── Users ──────────────────────────────────────────────────────────────────

async def upsert_user(telegram_id: int, username: str | None, full_name: str) -> dict:
    db = get_db()
    await db.execute(
        "INSERT OR IGNORE INTO users (telegram_id, username, full_name) VALUES (?, ?, ?)",
        (telegram_id, username, full_name),
    )
    await db.execute(
        "UPDATE users SET username=?, full_name=? WHERE telegram_id=?",
        (username, full_name, telegram_id),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
    row = await cursor.fetchone()
    return dict(row)


async def get_user_by_telegram_id(telegram_id: int) -> dict | None:
    db = get_db()
    cursor = await db.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_user_by_id(user_id: int) -> dict | None:
    db = get_db()
    cursor = await db.execute("SELECT * FROM users WHERE id=?", (user_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


# ── Operators ───────────────────────────────────────────────────────────────

async def add_operator(telegram_id: int, full_name: str) -> bool:
    db = get_db()
    try:
        await db.execute(
            "INSERT INTO operators (telegram_id, full_name) VALUES (?, ?)",
            (telegram_id, full_name),
        )
        await db.commit()
        return True
    except Exception:
        return False


async def remove_operator(operator_id: int) -> None:
    db = get_db()
    await db.execute("DELETE FROM operators WHERE id=?", (operator_id,))
    await db.commit()


async def get_all_operators() -> list:
    db = get_db()
    cursor = await db.execute("SELECT * FROM operators ORDER BY id")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_operator_by_telegram_id(telegram_id: int) -> dict | None:
    db = get_db()
    cursor = await db.execute("SELECT * FROM operators WHERE telegram_id=?", (telegram_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_operator_by_id(operator_id: int) -> dict | None:
    db = get_db()
    cursor = await db.execute("SELECT * FROM operators WHERE id=?", (operator_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


# ── Questions ───────────────────────────────────────────────────────────────

async def create_question(user_id: int, text: str) -> dict:
    db = get_db()
    cursor = await db.execute(
        "INSERT INTO questions (user_id, text) VALUES (?, ?)",
        (user_id, text),
    )
    last_id = cursor.lastrowid
    await db.commit()
    cursor = await db.execute("SELECT * FROM questions WHERE id=?", (last_id,))
    row = await cursor.fetchone()
    return dict(row)


async def claim_question(question_id: int, operator_id: int) -> bool:
    """Reserve a question for this operator. Returns False if already claimed."""
    db = get_db()
    cursor = await db.execute(
        "UPDATE questions SET answered_by=? WHERE id=? AND answered_by IS NULL",
        (operator_id, question_id),
    )
    await db.commit()
    return cursor.rowcount == 1


async def answer_question(question_id: int, answer_text: str) -> bool:
    db = get_db()
    cursor = await db.execute(
        "UPDATE questions SET answer_text=?, answered_at=CURRENT_TIMESTAMP WHERE id=?",
        (answer_text, question_id),
    )
    await db.commit()
    return cursor.rowcount == 1


async def get_question_by_id(question_id: int) -> dict | None:
    db = get_db()
    cursor = await db.execute("SELECT * FROM questions WHERE id=?", (question_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_unanswered_questions() -> list:
    db = get_db()
    cursor = await db.execute(
        "SELECT * FROM questions WHERE answered_by IS NULL ORDER BY created_at ASC"
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


# ── Live sessions ────────────────────────────────────────────────────────────

async def create_live_session(user_id: int) -> dict:
    db = get_db()
    cursor = await db.execute(
        "INSERT INTO live_sessions (user_id) VALUES (?)",
        (user_id,),
    )
    last_id = cursor.lastrowid
    await db.commit()
    cursor = await db.execute("SELECT * FROM live_sessions WHERE id=?", (last_id,))
    row = await cursor.fetchone()
    return dict(row)


async def claim_live_session(session_id: int, operator_id: int) -> bool:
    """Atomically claim a waiting session. Returns False if already claimed."""
    db = get_db()
    cursor = await db.execute(
        """UPDATE live_sessions
           SET operator_id=?, status='active'
           WHERE id=? AND operator_id IS NULL AND status='waiting'""",
        (operator_id, session_id),
    )
    if cursor.rowcount == 1:
        await db.execute(
            "UPDATE operators SET status='busy' WHERE id=?",
            (operator_id,),
        )
    await db.commit()
    return cursor.rowcount == 1


async def close_live_session(session_id: int) -> None:
    db = get_db()
    cursor = await db.execute(
        "SELECT operator_id FROM live_sessions WHERE id=?", (session_id,)
    )
    row = await cursor.fetchone()
    await db.execute(
        "UPDATE live_sessions SET status='closed', ended_at=CURRENT_TIMESTAMP WHERE id=?",
        (session_id,),
    )
    if row and row["operator_id"]:
        await db.execute(
            "UPDATE operators SET status='free' WHERE id=?",
            (row["operator_id"],),
        )
    await db.commit()


async def get_active_session_for_user(user_id: int) -> dict | None:
    db = get_db()
    cursor = await db.execute(
        "SELECT * FROM live_sessions WHERE user_id=? AND status IN ('waiting', 'active')",
        (user_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_active_session_for_operator(operator_id: int) -> dict | None:
    db = get_db()
    cursor = await db.execute(
        "SELECT * FROM live_sessions WHERE operator_id=? AND status='active'",
        (operator_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_waiting_sessions() -> list:
    db = get_db()
    cursor = await db.execute(
        "SELECT * FROM live_sessions WHERE status='waiting' ORDER BY started_at ASC"
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_session_by_id(session_id: int) -> dict | None:
    db = get_db()
    cursor = await db.execute("SELECT * FROM live_sessions WHERE id=?", (session_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_stale_waiting_sessions(timeout_seconds: int) -> list:
    db = get_db()
    cursor = await db.execute(
        """SELECT * FROM live_sessions
           WHERE status='waiting'
           AND (julianday('now') - julianday(started_at)) * 86400 > ?""",
        (timeout_seconds,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


# ── Statistics ───────────────────────────────────────────────────────────────

def _period_filter(period: str, col: str) -> str:
    if period == "day":
        return f"date({col}) = date('now')"
    elif period == "week":
        return f"{col} >= datetime('now', '-7 days')"
    else:  # month
        return f"{col} >= datetime('now', '-30 days')"


async def get_stats(period: str) -> dict:
    db = get_db()
    qf = _period_filter(period, "created_at")
    sf = _period_filter(period, "started_at")

    cursor = await db.execute(f"SELECT COUNT(*) as total FROM questions WHERE {qf}")
    total_questions = (await cursor.fetchone())["total"]

    cursor = await db.execute(
        f"SELECT COUNT(*) as cnt FROM questions WHERE answered_by IS NOT NULL AND {qf}"
    )
    answered_questions = (await cursor.fetchone())["cnt"]

    cursor = await db.execute(f"SELECT COUNT(*) as total FROM live_sessions WHERE {sf}")
    total_sessions = (await cursor.fetchone())["total"]

    cursor = await db.execute(
        f"""SELECT AVG((julianday(ended_at) - julianday(started_at)) * 86400) as avg_dur
            FROM live_sessions WHERE status='closed' AND {sf}"""
    )
    avg_dur = (await cursor.fetchone())["avg_dur"] or 0

    return {
        "total_questions": total_questions,
        "answered_questions": answered_questions,
        "pending_questions": total_questions - answered_questions,
        "total_sessions": total_sessions,
        "avg_session_duration": round(avg_dur),
    }


async def get_operator_activity(period: str) -> list:
    db = get_db()
    af = _period_filter(period, "q.answered_at")
    cursor = await db.execute(
        f"""SELECT o.full_name, o.telegram_id, COUNT(q.id) as answered_count
            FROM operators o
            LEFT JOIN questions q ON q.answered_by = o.id AND {af}
            GROUP BY o.id
            ORDER BY answered_count DESC"""
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]
