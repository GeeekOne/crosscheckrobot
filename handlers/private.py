import asyncio

from aiogram import Bot, Router, types
from aiogram.types import ChatJoinRequest
from aiogram.filters import Command
from datetime import datetime, timedelta
from aiogram.exceptions import TelegramBadRequest
from apscheduler.jobstores.base import JobLookupError

from utils.service import scheduler
from keyboards.inline import verify_kb

private_router = Router()

# Временное хранилище для заявок
pending_users = {}

@private_router.chat_join_request()
async def handle_chat_join_request(event: ChatJoinRequest, bot: Bot):
    chat_id = event.chat.id
    user_id = event.from_user.id

    try:
        # Отправляем сообщение в ЛС пользователя
        msg = await bot.send_message(
            user_id,
            f"Привет, {event.from_user.first_name}! Чтобы попасть в чат "
            "<b>Real_Petrovskii Днепр чат</b>, подтвердите, что вы не бот 👇",
            reply_markup=verify_kb,
            parse_mode="HTML"
        )

        # Сохраняем id сообщения и пользователя во временное хранилище
        pending_users[user_id] = (chat_id, msg.message_id)

        # Запускаем таймер на 30 минут
        run_time = datetime.utcnow() + timedelta(minutes=1)
        job_id = f"reject_{user_id}"
        scheduler.add_job(
            reject_request,
            "date",
            run_date=run_time,
            args=[bot, chat_id, user_id, msg.message_id],
            id=job_id
        )
    except TelegramBadRequest:
        # Если пользователь запретил отправку сообщений от бота
        print(f"Не удалось отправить сообщение пользователю {user_id}.")
        # Опционально: сразу отклоните заявку
        await bot.decline_chat_join_request(chat_id, user_id)


async def reject_request(bot: Bot, group_id: int, user_id: int, message_id: int):
    #Функция для отклонения заявки
    if user_id in pending_users:
        try:
            # Отклоняем заявку
            await bot.decline_chat_join_request(group_id, user_id)

            # Уведомляем пользователя
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text="🛑 Вы не подтвердили свою личность, заявка отклонена.",
                parse_mode="HTML"
            )

        except TelegramBadRequest:
            pass

        # Удаляем пользователя из временного хранилища
        pending_users.pop(user_id, None)

@private_router.callback_query(lambda c: c.data == "not_a_bot")
async def verify_user(callback: types.CallbackQuery, bot: Bot, group_id: int):
    user_id = callback.from_user.id

    if user_id in pending_users:
        group_id, msg_id = pending_users[user_id]
        job_id = f"reject_{user_id}"

        try:
            # Подтверждаем заявку
            await bot.approve_chat_join_request(group_id, user_id)
            await callback.message.edit_text(
                "✅ Вы успешно прошли проверку, добро пожаловать в чат")

            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)

        except TelegramBadRequest as e:
            print(f"Ошибка: {e}")

        # Удаляем пользователя из временного хранилища
        pending_users.pop(user_id, None)

    await callback.answer()


@private_router.message(Command("about"))
async def cmd_start(message: types.Message):
    await message.answer("Привет, я бот помощник по администрированию чата 👀")


