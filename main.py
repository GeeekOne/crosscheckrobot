import asyncio
import aiohttp
import logging
import betterlogging as bl

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
from aiogram.fsm.middleware import FSMContextMiddleware


from config import load_config
from database.db import create_engine, create_session, init_db, close_db
# from utils.session import SessionMiddleware
from utils.service import scheduler
from utils.bot_cmd_list import private

from handlers.user_private import user_private_router
from handlers.admin_private import admin_private_router
from handlers.requests import requests_router
from handlers.group import group_router


async def on_startup(engine):
    await init_db(engine)
    # logging.info("[LOG] База данных инициализирована")


async def on_shutdown(bot: Bot, engine):
    await bot.session.close()  # Закрываем сессию бота
    await close_db(engine)  # Закрываем соединение с БД
    # logging.info("[LOG] Bot session and aiohttp session closed")

async def main():
    bl.basic_colorized_config(level=logging.INFO)
    # bl.basic_colorized_config(level=logging.WARNING)

    config = load_config('.env')
    bot = Bot(token=config.tg_bot.token)

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.update.middleware(FSMContextMiddleware(storage=storage, events_isolation=SimpleEventIsolation()))

    engine = create_engine(config.tg_bot.db_url)
    async_session = create_session(engine)

    dp.workflow_data.update({
        'bot': bot,
        'db_url': config.tg_bot.db_url,
        'async_session': async_session
        })
    bot.workflow_data = dp.workflow_data

    dp.include_router(user_private_router)
    dp.include_router(admin_private_router)
    dp.include_router(requests_router)
    dp.include_router(group_router)

    await on_startup(engine)  # Инициализируем БД перед стартом бота
    
    scheduler.start()
    # await bot.delete_my_commands(scope=types.BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot, allowed_updates=[
            "chat_join_request",
            "message",
            "callback_query",
            "my_chat_member"
            ])
    finally:
        await on_shutdown(bot, engine)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped.")
