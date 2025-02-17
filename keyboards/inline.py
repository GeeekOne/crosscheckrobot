from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Кнопка для проверки
verify_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Я не бот", callback_data="not_a_bot")]]
)

admin_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Посты", callback_data="posts_menu")],
])
