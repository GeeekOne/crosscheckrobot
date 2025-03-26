from aiogram import types
from aiogram.filters import Filter
from sqlalchemy.future import select


from database.db import async_session
from database.models import GroupSettings, AdminSession

class ChatTypeFilter(Filter):
    def __init__(self, chat_types: list[str]) -> None:
        self.chat_types = chat_types

    async def __call__(self, message: types.Message) -> bool:
        return message.chat.type in self.chat_types

class IsAdmin(Filter):
    async def __call__(self, message: types.Message) -> bool:
        user_id = message.from_user.id

        async with async_session() as session:
            try:
                # Получаем выбранную группу из базы
                result = await session.execute(
                    select(AdminSession.group_id).where(AdminSession.admin_id == user_id)
                )
                admin_session = result.scalar()

                if not admin_session:
                    await message.answer("Группа не подключена. Используйте /start для получения информации.")
                    return False

                group_id = admin_session

                # Проверка, есть ли группа в настройках
                result = await session.execute(
                    select(GroupSettings).where(GroupSettings.group_id == group_id)
                )
                group_settings = result.scalar()

                if not group_settings:
                    await message.answer("⚠️ Группа не найдена или не подключена.")
                    return False

                # Проверка, является ли пользователь админом
                admin_ids = group_settings.admin_ids.split(",")

                if str(user_id) not in admin_ids:
                    await message.delete()
                    return False

                return True

            except Exception as e:
                print(f"Ошибка в IsAdmin: {e}")
                await message.answer("⚠ Произошла ошибка при проверке админа.")
                # await session.rollback()
                # print(f"❌ Ошибка в транзакции: {e}")
                return False

            # finally:
            #     await session.close()  # 🟢 Закрываем сессию
            #     print("[LOG] 🔒 Сессия в IsAdmin закрыта")
