from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Кнопка для проверки
verify_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Подтвердить вход ✅", callback_data="not_a_bot")]]
)

# Кнопка для управления настройками
def admin_control_keyboard(cleansrv_status: bool, joinrequest_status: bool):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🧹 Удаление сервисных сообщений: {'🟢 Вкл' if cleansrv_status else '🔴 Выкл'}",
            callback_data="toggle_cleansrv"
        )],
        [InlineKeyboardButton(
            text=f"🔑 Обработка заявок: {'🟢 Вкл' if joinrequest_status else '🔴 Выкл'}",
            callback_data="toggle_joinrequest"
        )],
        [InlineKeyboardButton(
            text="🔄 Обновить статус",
            callback_data="refresh_status"
        )]
    ])

# admin_menu = InlineKeyboardMarkup(inline_keyboard=[
#     [InlineKeyboardButton(text="Посты", callback_data="posts_menu")],
# ])
