from aiogram import Bot, Router, F, types
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
# from aiogram.types.chat_member_updated import ChatMemberUpdated
# from aiogram.enums.chat_member_status import ChatMemberStatus
from aiogram.types import ChatMemberUpdated
from aiogram.enums import ChatMemberStatus
from datetime import timedelta
from sqlalchemy.future import select

from filters.chat_types import ChatTypeFilter, IsAdmin
from database.db import async_session
from database.models import GroupSettings


group_router = Router()
group_router.message.filter(ChatTypeFilter(['group', 'supergroup']))
group_router.edited_message.filter(ChatTypeFilter(['group', 'supergroup']))


@group_router.my_chat_member()
async def bot_removed_from_group(event: types.ChatMemberUpdated, bot: Bot):
    print(f"🔍 ПОЛУЧЕНО СОБЫТИЕ: {event}")
    """Удаляет данные о группе, если бота исключили."""
    # Проверяем, что бот был удален
    if event.new_chat_member.user.id == (await bot.get_me()).id:
       if event.new_chat_member.status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}:

        group_id = event.chat.id
        print(f"⚠️ Бота удалили из группы {group_id}, очищаем БД...")

        async with async_session() as session:
            try:
                result = await session.execute(
                    select(GroupSettings).where(GroupSettings.group_id == group_id))
                group = result.scalar()

                if group:
                    print(f"[LOG]🔄 Найдено в БД, удаляю группу {group_id}")
                    await session.delete(group)
                    await session.commit()
                    print(f"✅ Данные группы {group_id} удалены из БД.")
                else:
                    print(f"⚠️ Группа {group_id} не найдена в БД, удаление не требуется.")
            except Exception as e:
                await session.rollback()  # Откат, если ошибка
                print(f"❌ Ошибка при удалении группы {group_id} из БД: {e}")


# Удаление сообщений о входе/выходе
@group_router.message(lambda message: message.new_chat_members or message.left_chat_member)
async def delete_service_messages(message: types.Message, bot: Bot):
    if message.chat.type != "supergroup":
        return

    async with async_session() as session:
        result = await session.execute(
            select(GroupSettings).where(GroupSettings.group_id == message.chat.id))
        group = result.scalar()

        if group and group.delete_join_leave_messages == 1:
            if message.new_chat_members or message.left_chat_member:
                try:
                    await bot.delete_message(message.chat.id, message.message_id)
                except TelegramForbiddenError:
                    print(f"⚠️ Бот был удален из группы {message.chat.id}, не могу удалить сообщение.")
                except TelegramBadRequest as e:
                    if "CHANNEL_PRIVATE" in str(e):
                        print("⚠️ Бот не может удалить сообщение, возможно, это канал или недостаточно прав.")
                    else:
                        print(f"❌ Ошибка при удалении сообщения: {e}")


@group_router.message(Command("admininit"))
async def get_admins(message: types.Message, bot: Bot):
    if message.chat.type != "supergroup":
        await message.answer("❌Эта команда работает только в супергруппах.")
        return

    group_id = message.chat.id
    group_name = message.chat.title
    # print(f"[LOG] Полученный group_id: {group_id}")
    user_id = message.from_user.id

    # Получаем список админов группы
    try:
        chat_admins = await bot.get_chat_administrators(group_id)
        admin_ids = [admin.user.id for admin in chat_admins if admin.status in (
            "creator", "administrator")]

        if user_id not in admin_ids:
            await message.delete()
            return

        admin_list = ",".join(map(str, admin_ids))
        # print(f"[LOG] Сохранённые админы: {admin_list}")

        if not admin_ids:
            await message.answer("⚠️ В группе не найдено администраторов.")
            return

    except TelegramBadRequest:
        await message.answer("⚠️ Не удалось получить список админов группы.")
        return

    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при получении списка админов: {e}")
        return

    # Сохраняем данные в БД
    async with async_session() as session:
        result = await session.execute(
            select(GroupSettings).where(GroupSettings.group_id == int(group_id))
            )
        existing_group = result.scalar()

        if existing_group:
            existing_group.admin_ids = admin_list
        else:
            new_group = GroupSettings(group_id=group_id, admin_ids=admin_list)
            session.add(new_group)

        await session.commit()
        # print(f"[LOG] Группа {group_id} сохранена в БД с админами: {admin_list}")

    await message.answer("✅ Список администраторов сохранен")

    # Отправка ID группы в лиичку тому кто вызвал команду
    try:
        await bot.send_message(
            user_id,
            f"✅ Группа {group_name} зарегистрирована\n\n"
            f"🔹 ID вашей группы: `{group_id}`\n\n"
            f"⏩ Отправь мне команду для подключения к настройкам группы: `/connect {group_id}`",
            parse_mode="Markdown"
        )
    except TelegramBadRequest:
        print(f"⚠️ Не удалось отправить сообщение админу {user_id}. Возможно, у него закрыты ЛС.")



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
@group_router.message(Command("mute"), IsAdmin())
async def mute_user(message: types.Message, bot: Bot):
    print(f"Получена команда /mute от {message.from_user.id} в чате {message.chat.id}")
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

    except Exception as e:
        await message.reply(f"Ошибка: {e}")

    except TelegramBadRequest as e:
        await message.reply(f"Ошибка: {e}")

# Команда /ban
@group_router.message(Command("ban"), IsAdmin())
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
@group_router.message(Command("unmute"), IsAdmin())
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
