import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from app.config import settings
from app.db import init_db, close_db
from app.db.queries import get_all_operators
from app.logging import setup_logging
from app.routers import setup_routers
from app.utils.scheduler import start_scheduler, stop_scheduler
from app.utils.storage_holder import set_storage


async def _setup_commands(bot: Bot) -> None:
    """Register bot command menu for each role."""
    # Default: all users see /start
    await bot.set_my_commands(
        [BotCommand(command="start", description="Botni boshlash / Asosiy menyu")],
        scope=BotCommandScopeDefault(),
    )

    operators = await get_all_operators()
    operator_ids = {op["telegram_id"] for op in operators}

    # Admins: /start + /admin (+ /panel if also an operator)
    for admin_id in settings.admins:
        commands = [
            BotCommand(command="start", description="Asosiy menyu"),
            BotCommand(command="admin", description="🛠 Admin panel"),
        ]
        if admin_id in operator_ids:
            commands.append(BotCommand(command="panel", description="📋 Operator paneli"))
        try:
            await bot.set_my_commands(
                commands, scope=BotCommandScopeChat(chat_id=admin_id)
            )
        except Exception as e:
            logging.error(f"Failed to set commands for admin {admin_id}: {e}")

    # Operators (non-admin): /start + /panel
    for op in operators:
        if op["telegram_id"] in settings.admins:
            continue  # already handled above
        try:
            await bot.set_my_commands(
                [
                    BotCommand(command="start", description="Asosiy menyu"),
                    BotCommand(command="panel", description="📋 Operator paneli"),
                ],
                scope=BotCommandScopeChat(chat_id=op["telegram_id"]),
            )
        except Exception as e:
            logging.error(f"Failed to set commands for operator {op['telegram_id']}: {e}")


async def on_startup(bot: Bot) -> None:
    await init_db(settings.database_url)
    start_scheduler(bot, settings.session_timeout)
    await _setup_commands(bot)

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
