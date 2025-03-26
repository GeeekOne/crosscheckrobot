from aiogram import Bot, Router, types
from aiogram.filters import Command, CommandStart

from filters.chat_types import ChatTypeFilter


user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(['private']))


@user_private_router.message(CommandStart())
async def cmd_start(message: types.Message, bot: Bot):
    botname = await bot.get_my_name()
    await message.answer(
        f"Привет, я *{botname.name}* 🤖\n"
        "Создан для упрощения в администрировании групп 🔧\n"
        "Для начала работы введи в группе команду `/admininit` и следуй инструкциям ℹ️",
        parse_mode="Markdown"
        )
