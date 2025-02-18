import re

from aiogram import Bot, Router, F, types
from aiogram.filters import Command
from datetime import datetime, timedelta
from aiogram.exceptions import TelegramBadRequest

group_router = Router()


# Удаление сообщений о входе в чат
@group_router.message(F.new_chat_members)
async def delete_join_message(message: types.Message):
    await message.delete()


# Удаление сообщений о выходе из чата
@group_router.message(F.left_chat_member)
async def delete_leave_message(message: types.Message):
    await message.delete()


# Функция форматирования времени мута
def format_duration_with_emoji(duration: str) -> str:
    if duration.endswith("m"):
        return f"{duration[:-1]} минут ⏳"
    elif duration.endswith("h"):
        return f"{duration[:-1]} часов ⏰"
    elif duration.endswith("d"):
        return f"{duration[:-1]} дней 📅"
    return duration

# Команда /mute
@group_router.message(Command("mute"))
async def mute_user(message: types.Message, bot: Bot):
    if not message.reply_to_message:
        return await message.answer("Команда работает в ответ на сообщение пользователя")

    args = message.text.split()
    if len(args) < 2:
        return await message.reply("Использование: /mute <время> (например 10m, 2h, 1d)")

    duration = args[1]
    target_user = message.reply_to_message.from_user
    duration_seconds = None

    # Конвертация времени в секунды
    if duration.endswith("m"):
        duration_seconds = int(duration[:-1]) * 60
    elif duration.endswith("h"):
        duration_seconds = int(duration[:-1]) * 3600
    elif duration.endswith("d"):
        duration_seconds = int(duration[:-1]) * 86400
    else:
        return await message.reply(
            "Неверный формат времени, используйте:"
            "m - минуты"
            "h - часы"
            "d - дни")

    # Проверка никнейма у пользователя
    if target_user.username:
        mention = f"@{target_user.username}"
    else:
        mention = f'<a href="tg://user?id={target_user.id}">{target_user.full_name}</a>'

    try:
        until_date = message.date + timedelta(seconds=duration_seconds)
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user.id,
            permissions=types.ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        await message.reply(
            f"🔇 {mention} замьючен на <b>{format_duration_with_emoji(duration)}</b>.",
            parse_mode="HTML"
        )

    except TelegramBadRequest as e:
        await message.reply(f"Ошибка: {e}")

# Команда /ban
@group_router.message(Command("ban"))
async def ban_user(message: types.Message, bot: Bot):
    if not message.reply_to_message:
        return await message.answer("Команда работает в ответ на сообщение пользователя")

    target_user = message.reply_to_message.from_user

    # Проверка никнейма у пользователя
    if target_user.username:
        mention = f"@{target_user.username}"
    else:
        mention = f'<a href="tg://user?id={target_user.id}">{target_user.full_name}</a>'


    try:
        await bot.ban_chat_member(chat_id=message.chat.id, user_id=target_user.id)
        await message.reply(f"🚫 {mention} был забанен.", parse_mode="HTML")

    except TelegramBadRequest as e:
        await message.reply(f"Ошибка: {e}")

# Команда /unmute
@group_router.message(Command("unmute"))
async def unmute_user(message: types.Message, bot: Bot):
    if not message.reply_to_message:
        return await message.reply("Ответьте на сообщение пользователя, чтобы размьютить его.")

    target_user = message.reply_to_message.from_user

    # Проверка никнейма у пользователя
    if target_user.username:
        mention = f"@{target_user.username}"
    else:
        mention = f'<a href="tg://user?id={target_user.id}">{target_user.full_name}</a>'


    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user.id,
            permissions=types.ChatPermissions(can_send_messages=True)
        )
        await message.reply(f"🔊 {mention} теперь может писать в чат.", parse_mode="HTML")

    except TelegramBadRequest as e:
        await message.reply(f"Ошибка: {e}")


# @group_router.message(F.text.lower() == "Правила рекламы")
# async def add_rules(message: types.Message):
#     await message.answer()
