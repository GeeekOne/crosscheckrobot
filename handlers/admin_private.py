import logging

from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from sqlalchemy.future import select
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove


from filters.chat_types import ChatTypeFilter, IsAdmin
# from database.db import async_session
from database.models import GroupSettings, AdminSession
from keyboards.inline import admin_control_keyboard
from keyboards.reply import kb_admin

from utils.states import SetCaptchaTimeStates

admin_private_router = Router()
admin_private_router.message.filter(ChatTypeFilter(['private']), IsAdmin())



# Хендлер для сброса состояний и возврата в главное меню
@admin_private_router.message(Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext) -> None:

    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("Cancelling state %r", current_state)
    await state.clear()
    await message.answer("Действие отменено", reply_markup=kb_admin)


@admin_private_router.message(F.text.lower() == "админка")
@admin_private_router.message(Command("admpanel"))
async def cmd_admin_panel(message: types.Message):
    await message.answer("Админ панель:", reply_markup=kb_admin)


@admin_private_router.message(F.text.lower() == "помощь")
@admin_private_router.message(Command("admhelp"))
async def cmd_help_admin(message: types.Message):
    await message.answer(
        "<b>Функции в боте:</b>\n"
        "Сервсиные настройки - управление системными функциями бота\n"
        "Установка времени прохождения капчи\n\n"
        "<b>Функции бота в группе:</b>\n"
        "/mute - выдать мут участнику группы\n"
        "/unmute - убрать мут у участника группы\n"
        "/ban - забанить участника группы\n",
        parse_mode="HTML"
    )

@admin_private_router.message(F.text.lower() == "сервисные настройки")
@admin_private_router.message(Command("settings"))
async def show_admin_panel(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    async_session = bot.workflow_data['async_session']

    async with async_session() as session:
        try:
            # Получаем выбранную группу для админа
            result = await session.execute(
                select(AdminSession.group_id).where(AdminSession.admin_id == user_id)
                )
            selected_group = result.scalar()

            if not selected_group:
                await message.answer("⚠️ Вы не подключились к группе. Используйте команду `/connect`.")
                return

            # Получаем настройки выбранной группы
            result = await session.execute(
                select(GroupSettings).where(GroupSettings.group_id == selected_group)
            )
            group = result.scalar()

            if not group:
                await message.answer("🔎 Настройки группы не найдены в базе данных.")
                return

            # Получаем статусы из БД
            cleansrv_status = group.delete_join_leave_messages
            joinrequest_status = group.approve_requests

            # Отправляем клавиатуру
            await message.answer(
                "⚙️ Управление функциями бота:",
                reply_markup=admin_control_keyboard(cleansrv_status, joinrequest_status)
            )
        except Exception as e:
            await session.rollback()
            print(f"Ошибка при обработке настроек: {e}")
        finally:
            await session.close()



@admin_private_router.callback_query(lambda c: c.data in [
    "toggle_cleansrv",
    "toggle_joinrequest",
    "refresh_status"
    ])
async def handle_admin_callback(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    async_session = bot.workflow_data['async_session']

    async with async_session() as session:
        try:


            result = await session.execute(
                select(GroupSettings)
                .join(AdminSession, GroupSettings.group_id == AdminSession.group_id)
                .where(AdminSession.admin_id == user_id)
            )
            group = result.scalar()

            if not group:
                await callback.answer("Группа не найдена в базе данных.")
                return

            if callback.data == "toggle_cleansrv":
                group.delete_join_leave_messages = not group.delete_join_leave_messages
                await session.commit()
                status_text = "🟢 Включено" if group.delete_join_leave_messages else "🔴 Выключено"
                await callback.answer(f"Удаление сервисных сообщений: {status_text}")

            elif callback.data == "toggle_joinrequest":
                group.approve_requests = not group.approve_requests
                await session.commit()
                status_text = "🟢 Включено" if group.approve_requests else "🔴 Выключено"
                await callback.answer(f"Обработка заявок: {status_text}")

            elif callback.data == "refresh_status":
                await callback.answer("🔄 Статусы обновлены!")

            # Обновляем клавиатуру
            await callback.message.edit_text(
                 "⚙️ Управление функциями бота:",
                reply_markup=admin_control_keyboard(group.delete_join_leave_messages, group.approve_requests)
            )

        except Exception as e:
            await callback.answer("Произошла ошибка при обновлении настроек.")
            print(f"Ошибка в обработке переключателей: {e}")

        finally:
            await session.close()  # 🟢 ВАЖНО! Закрываем сессию



@admin_private_router.message(F.text.lower() == "время капчи")
async def set_captcha_time(message: types.Message, state: FSMContext):
    await message.answer(
        "Напишите время ожидания капчи в минутах от 1 до 60:\n"
        "Для отмены нажмите /cancel",
        reply_markup=ReplyKeyboardRemove()
        )
    await state.set_state(SetCaptchaTimeStates.waiting_for_captcha_time)


@admin_private_router.message(SetCaptchaTimeStates.waiting_for_captcha_time)
async def enter_captcha_time(message: types.Message, bot: Bot, state: FSMContext):
    user_id = message.from_user.id
    async_session = bot.workflow_data['async_session']

    if not message.text.isdigit():
        await message.answer("⚠️ Введите число от 1 до 60.")
        return

    timeout = int(message.text)

    if timeout < 1 or timeout > 60:
        await message.answer("⚠️ Введите число в диапазоне от 1 до 60.")
        return

    async with async_session() as session:
        try:
            result = await session.execute(
                select(GroupSettings)
                .join(AdminSession, GroupSettings.group_id == AdminSession.group_id)
                .where(AdminSession.admin_id == user_id)
            )
            group = result.scalar()

            if not group:
                await message.answer("⚠️ Группа не найдена или не подключена.")
                return

            group.captcha_timeout = timeout
            await session.commit()

            await message.answer(
                f"⏳ Время ожидания капчи установлено: {timeout} минут.",
                reply_markup=kb_admin
                )
            await state.clear()

        except Exception as e:
                await message.answer(f"❌ Ошибка: {e}")





















# @admin_private_router.message(Command("disconnect"))
# async def disconnect_group(message: types.Message):
#     user_id = message.from_user.id

#     async with async_session() as session:
#         try:
#             # Проверяем, есть ли активная сессия админа
#             result = await session.get(AdminSession, user_id)

#             if not result:
#                 await message.answer("⚠️ У вас нет подключенной группы.")
#                 return

#             # Удаляем запись из AdminSession
#             await session.delete(result)
#             await session.commit()

#             await message.answer("🔌 Вы успешно отключились от группы.")

#         finally:
#             await session.close()
