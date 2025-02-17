from aiogram import Router, F, types

group_router = Router()

# Удаление сообщений о входе в чат
@group_router.message(F.new_chat_members)
async def delete_join_message(message: types.Message):
    await message.delete()


# Удаление сообщений о выходе из чата
@group_router.message(F.left_chat_member)
async def delete_leave_message(message: types.Message):
    await message.delete()
