from aiogram import Bot, Router, types
from aiogram.filters import Command

from filters.chat_types import ChatTypeFilter, IsAdmin


admin_router = Router()
admin_router.message.filter(types.ChatTypeFilter(['private']), IsAdmin())


# @admin_router.message(Command("enable"))
# async def cmd_enable(message: types.Message, bot: Bot):
#     ch


# @admin_router.message(Command("admin"))
# async def cmd_admin(message: types.Message):
#     await message.answer("Настройки бота:")