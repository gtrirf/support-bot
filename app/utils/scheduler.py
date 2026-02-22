import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from app.db.queries import get_stale_waiting_sessions, close_live_session, get_user_by_id
from app.keyboards.user_kb import main_menu_kb
from app.utils.storage_holder import get_storage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

scheduler = AsyncIOScheduler()


async def close_stale_sessions(bot: Bot, session_timeout: int) -> None:
    stale = await get_stale_waiting_sessions(session_timeout)
    for session in stale:
        s_id = session["id"]
        user_id = session["user_id"]

        await close_live_session(s_id)

        user = await get_user_by_id(user_id)
        if not user:
            continue

        user_tg_id = user["telegram_id"]
        try:
            await bot.send_message(
                user_tg_id,
                "Kechirasiz, operator topilmadi. Chat avtomatik yakunlandi.",
                reply_markup=main_menu_kb(),
            )
        except Exception as e:
            logging.error(f"Scheduler: failed to notify user {user_tg_id}: {e}")

        try:
            storage = get_storage()
            key = StorageKey(bot_id=bot.id, chat_id=user_tg_id, user_id=user_tg_id)
            ctx = FSMContext(storage=storage, key=key)
            await ctx.clear()
        except Exception as e:
            logging.error(f"Scheduler: failed to clear FSM for user {user_tg_id}: {e}")


def start_scheduler(bot: Bot, session_timeout: int) -> None:
    scheduler.add_job(
        close_stale_sessions,
        trigger="interval",
        seconds=60,
        args=[bot, session_timeout],
        id="close_stale_sessions",
        replace_existing=True,
    )
    scheduler.start()
    logging.info("Scheduler started.")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
        logging.info("Scheduler stopped.")
