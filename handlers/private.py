import asyncio

from aiogram import Bot, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatJoinRequest
from aiogram.filters import CommandStart, Command, ChatMemberUpdatedFilter
from aiogram.exceptions import TelegramBadRequest

private_router = Router()


# Кнопка для проверки
inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Я не бот", callback_data="not_a_bot")]]
)


@private_router.chat_join_request()
async def handle_chat_join_request(event: ChatJoinRequest, bot: Bot):
    chat_id = event.chat.id
    user_id = event.from_user.id

    try:
        # Отправляем сообщение в ЛС пользователя
        await bot.send_message(
            user_id,
            f"Привет, {event.from_user.first_name}! Чтобы попасть в чат "
            "<b>Real_Petrovskii Днепр чат</b>, подтвердите, что вы не бот 👇",
            reply_markup=inline_kb,
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        # Если пользователь запретил отправку сообщений от бота
        print(f"Не удалось отправить сообщение пользователю {user_id}.")
        # Опционально: сразу отклоните заявку
        await bot.decline_chat_join_request(chat_id, user_id)


@private_router.callback_query(lambda c: c.data == "not_a_bot")
async def verify_user(callback: types.CallbackQuery, bot: Bot, group_id: int):
    # chat_id = callback.message.chat.id
    user_id = callback.from_user.id

    try:
        # Подтверждаем заявку
        await bot.approve_chat_join_request(group_id, user_id)
        await callback.message.edit_text(
            "Вы успешно прошли проверку, добро пожаловать в чат нашего района ⚡")
    except TelegramBadRequest as e:
        print(f"Ошибка: {e}")


@private_router.message(Command("help"))
async def cmd_start(message: types.Message):
    await message.answer("Привет, я бот помощник для фильтрации спама в чате 👀")