from aiogram import Bot, Router, types
from aiogram.types import ChatJoinRequest
from datetime import datetime, timedelta
from sqlalchemy import delete
from sqlalchemy.future import select
from aiogram.exceptions import TelegramBadRequest

# from database.db import async_session
from database.models import GroupSettings, PendingRequest
from utils.service import scheduler
from keyboards.inline import verify_kb

requests_router = Router()


# Временное хранилище для заявок
# pending_users = {}

@requests_router.chat_join_request()
async def handle_chat_join_request(event: ChatJoinRequest, bot: Bot):
    async_session = bot.workflow_data['async_session']
    chat_id = event.chat.id
    user_id = event.from_user.id

    async with async_session() as session:
        result = await session.execute(select(GroupSettings)
            .where(GroupSettings.group_id == chat_id)
            )
        group = result.scalar()

        if not group or not group.approve_requests or group.captcha_timeout <= 0:
            # print(f"⚠️ Заявки для группы {chat_id} не обрабатываются или капча отключена")
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

            existing_job = scheduler.get_job(job_id)
            if existing_job:
                print(f"Задача {job_id} уже существует, не создаём новую.")
            else:
            # if not scheduler.get_job(job_id):
                print(f"[LOG] Добавлена задача {job_id} на {run_time}")
                scheduler.add_job(
                    reject_request,
                    # lambda: reject_request(bot, chat_id, user_id, msg.message_id),
                    "date",
                    run_date=run_time,
                    args=[bot, chat_id, user_id, msg.message_id],
                    id=job_id,
                    misfire_grace_time=10,
                    max_instances=1
                )

        except TelegramBadRequest:
            # Если пользователь запретил отправку сообщений от бота
            print(f"Не удалось отправить сообщение пользователю {user_id} ⚠️")
            # Опционально: сразу отклоните заявку
            await bot.decline_chat_join_request(chat_id, user_id)

# Если пользователь не подтвердил себя
async def reject_request(bot: Bot, group_id: int, user_id: int, message_id: int):
    # print(f"Запуск reject_request для user_id={user_id}, group_id={group_id}")
    async_session = bot.workflow_data['async_session']

    async with async_session() as session:
        result = await session.execute(
            select(PendingRequest)
            .where(PendingRequest.user_id == user_id)
            .where(PendingRequest.chat_id == group_id)
        )
        request = result.scalar()

        if not request:
            # print(f"⚠️ Заявка {user_id} в {group_id} уже удалена.")
            return

        try:
            # Отклоняем заявку
            # print("Пытаюсь отклонить заявку через decline_chat_join_request")
            await bot.decline_chat_join_request(group_id, user_id)
            # print("Отклонение заявки прошло успешно.")

            # Удаляем пользователя из временного хранилища
            # print("Удаляю запись заявки из БД")
            await session.execute(
                    delete(PendingRequest)
                    .where(PendingRequest.user_id == user_id)
                    .where(PendingRequest.chat_id == group_id)
                )
            await session.commit()
            # print(f"[LOG]Задача выполнена: удаление заявки {user_id} в {group_id}")

            # Уведомляем пользователя
            # print("Пытаюсь отправить уведомление пользователю о том, что заявка отклонена")
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text="<b>Вы не подтвердили вход, заявка отклонена 🛑</b>",
                parse_mode="HTML"
            )
            # print("Уведомление успешно отправлено.")

        except Exception as e:
            # Не подавляем ошибку, а логируем её
            print(f"❌ Ошибка в reject_request для user_id={user_id}, group_id={group_id}: {e}")



# Пользователь подтвердил себя
@requests_router.callback_query(lambda c: c.data == "not_a_bot")
async def verify_user(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    async_session = bot.workflow_data['async_session']

    async with async_session() as session:
        result = await session.execute(
            select(PendingRequest).where(
                PendingRequest.user_id == user_id,
                PendingRequest.message_id == message_id
            )
        )
        request = result.scalar()

        if not request:
            await callback.answer("❌ Ошибка: заявка не найдена или время истекло!")
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