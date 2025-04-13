from aiogram import Bot, Router, F, types
from aiogram.filters import Command, CommandStart

from filters.chat_types import ChatTypeFilter
from database.models import AdminSession
from utils.db_utils import save_user_in_db
from keyboards.reply import kb_admin


user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(['private']))


@user_private_router.message(CommandStart())
async def cmd_start(message: types.Message, bot: Bot):
    async_session = bot.workflow_data['async_session']
    botname = await bot.get_my_name()

    async with async_session() as session:
        await save_user_in_db(bot, message.from_user)

    await message.answer(
        f"Привет, я *{botname.name}* 🤖\n"
        "Создан для помощи в администрировании групп 🔧\n"
        "Для начала работы введи в группе команду `/admininit` и следуй инструкциям ℹ️",
        parse_mode="Markdown"
    )


@user_private_router.message(F.text.lower() == "поддержка")
@user_private_router.message(Command("support"))
async def cmd_help_admin(message: types.Message):
    await message.answer(
        "По всем вопросам/предложениям/разработке обращайтесь в @onetechsupbot",
        parse_mode="HTML"
    )


@user_private_router.message(Command("connect"))
async def connect_group(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    text = message.text.strip()
    async_session = bot.workflow_data['async_session']

    # Проверка правильности команды
    if not text.startswith("/connect -"):
        await message.answer("❌ Неверный формат команды. Используйте: `/connect -100..`")
        return

    try:
        group_id = int(text.split()[1])
    except (IndexError, ValueError):
        await message.answer("❌ Некорректный ID группы.")
        return

    # Сохраняем выбранную группу в БД
    async with async_session() as session:
        try:
            await session.merge(AdminSession(admin_id=user_id, group_id=group_id))
            await session.commit()

        finally:
            await session.close()

    await message.answer(
        f"✅ Вы подключены к группе с ID {group_id}\n"
        "⌨️ Теперь вы можете управлять настройками бота через клавиатуру",
        reply_markup=kb_admin
        )