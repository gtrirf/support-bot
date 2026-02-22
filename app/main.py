import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.config import settings
from app.db import init_db, close_db
from app.logging import setup_logging
from app.routers import setup_routers
from app.utils.scheduler import start_scheduler, stop_scheduler
from app.utils.storage_holder import set_storage


async def on_startup(bot: Bot) -> None:
    await init_db(settings.database_url)
    start_scheduler(bot, settings.session_timeout)

    if settings.admins:
        for admin_id in settings.admins:
            try:
                await bot.send_message(admin_id, "✅ Bot ishga tushdi.")
            except Exception as e:
                logging.error(f"Startup message failed for {admin_id}: {e}")


async def on_shutdown(bot: Bot) -> None:
    stop_scheduler()
    await close_db()

    if settings.admins:
        for admin_id in settings.admins:
            try:
                await bot.send_message(admin_id, "⛔️ Bot to'xtatildi.")
            except Exception as e:
                logging.error(f"Shutdown message failed for {admin_id}: {e}")


async def main() -> None:
    setup_logging(logging.INFO)

    storage = RedisStorage.from_url(settings.redis_url)
    set_storage(storage)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=storage)
    dp.include_router(setup_routers())

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
