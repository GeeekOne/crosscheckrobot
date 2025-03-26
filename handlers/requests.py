from aiogram import Bot, Router, types
from aiogram.types import ChatJoinRequest
from datetime import datetime, timedelta
from sqlalchemy import delete
from sqlalchemy.future import select
from aiogram.exceptions import TelegramBadRequest

from database.db import async_session
from database.models import GroupSettings, PendingRequest
from keyboards.inline import verify_kb
from utils.service import scheduler

requests_router = Router()


# Временное хранилище для заявок
# pending_users = {}

@requests_router.chat_join_request()
async def handle_chat_join_request(event: ChatJoinRequest, bot: Bot):
    chat_id = event.chat.id
    user_id = event.from_user.id

    async with async_session() as session:
        result = await session.execute(select(GroupSettings)
            .where(GroupSettings.group_id == chat_id)
            )
        group = result.scalar()

        if not group or not group.approve_requests or group.captcha_timeout <= 0:
            print(f"⚠️ Заявки для группы {chat_id} не обрабатываются или капча отключена")
            return

        # Удаляем старую заявку, если она есть
        await session.execute(
                delete(PendingRequest)
                .where(PendingRequest.user_id == user_id)
                .where(PendingRequest.chat_id == chat_id)
            )

        try:
            # Отправляем сообщение в ЛС пользователя
            msg = await bot.send_message(
                user_id,
                f"Привет, <b>{event.from_user.first_name}</b>!\n"
                f"Для вступления в чат <b>{event.chat.title}</b>, "
                f"подтверди вход в течение <b>{group.captcha_timeout} минут</b> ⤵️",
                reply_markup=verify_kb,
                parse_mode="HTML"
            )

            # Добавлям ноую заявку
            new_request = PendingRequest(
                user_id=user_id, chat_id=chat_id, message_id=msg.message_id
            )
            session.add(new_request)
            await session.commit()


            # Запускаем таймер на 30 минут
            run_time = datetime.now() + timedelta(minutes=group.captcha_timeout)
            job_id = f"reject_{user_id}_{chat_id}"

            if not scheduler.get_job(job_id):
                scheduler.add_job(
                    reject_request,
                    "date",
                    run_date=run_time,
                    args=[bot, chat_id, user_id, msg.message_id],
                    id=job_id
                )

        except TelegramBadRequest:
            # Если пользователь запретил отправку сообщений от бота
            print(f"Не удалось отправить сообщение пользователю {user_id} ⚠️")
            # Опционально: сразу отклоните заявку
            await bot.decline_chat_join_request(chat_id, user_id)

# Если пользователь не подтвердил себя
async def reject_request(bot: Bot, group_id: int, user_id: int, message_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(PendingRequest)
            .where(PendingRequest.user_id == user_id)
            .where(PendingRequest.chat_id == group_id)
        )
        request = result.scalar()

        if not request:
            print(f"⚠️ Заявка {user_id} в {group_id} уже удалена.")
            return

        try:
            # Отклоняем заявку
            await bot.decline_chat_join_request(group_id, user_id)

            # Уведомляем пользователя
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text="Вы не подтвердили вход, заявка отклонена 🛑",
                parse_mode="HTML"
            )

        except TelegramBadRequest:
            pass

        # Удаляем пользователя из временного хранилища
        await session.execute(
                delete(PendingRequest)
                .where(PendingRequest.user_id == user_id)
                .where(PendingRequest.chat_id == group_id)
            )
        await session.commit()


# Пользователь подтвердил себя
@requests_router.callback_query(lambda c: c.data == "not_a_bot")
async def verify_user(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    message_id = callback.message.message_id

    async with async_session() as session:
        result = await session.execute(
            select(PendingRequest).where(
                PendingRequest.user_id == user_id,
                PendingRequest.message_id == message_id
            )
        )
        request = result.scalar()

        if not request:
            await callback.answer("❌ Ошибка: заявка не найдена!")
            return

        group_id = request.chat_id
        job_id = f"reject_{user_id}_{group_id}"

        try:
            # Подтверждаем заявку
            await bot.approve_chat_join_request(group_id, user_id)
            await callback.message.edit_text(
                "Вы успешно подтвердили вход, добро пожаловать в чат ✅")

            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)

            # Удаляем заявку из БД
            await session.execute(
                delete(PendingRequest)
                .where(PendingRequest.user_id == user_id)
                .where(PendingRequest.chat_id == group_id)
            )
            await session.commit()

        except TelegramBadRequest as e:
            print(f"Ошибка: {e}")

    await callback.answer()