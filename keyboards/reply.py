from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

kb_admin = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Сервисные настройки'), KeyboardButton(text='Время капчи')],
    [KeyboardButton(text='Помощь')]
],
                            resize_keyboard=True,
                            input_field_placeholder='Выберите пункт меню 🔽')