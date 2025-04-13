import logging

from aiogram import Bot
from sqlalchemy import select
from database.models import UserData, UserGroup
from aiogram.types import User as TelegramUser


async def save_user_in_db(
    bot: Bot,
    tg_user: TelegramUser,
    passed_captcha: bool = False,
    group_id: int | None = None,
    group_username: str | None = None
):
    async_session = bot.workflow_data['async_session']

    async with async_session() as session:
        stmt = select(UserData).where(UserData.tg_id == tg_user.id)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            existing_user.passed_captcha = passed_captcha
        else:
            new_user = UserData(
                tg_id=tg_user.id,
                full_name=tg_user.full_name,
                username=tg_user.username,
                passed_captcha=passed_captcha,
            )
            session.add(new_user)
            logging.info(f"👤 Добавлен пользователь: {tg_user.full_name} (@{tg_user.username}) | ID: {tg_user.id}")


        if group_id:
            stmt = select(UserGroup).where(
                UserGroup.tg_id == tg_user.id,
                UserGroup.group_id == group_id
            )
            result = await session.execute(stmt)
            existing_relation = result.scalar_one_or_none()

            if not existing_relation:
                session.add(UserGroup(
                    tg_id=tg_user.id,
                    group_id=group_id,
                    group_username=group_username
                    ))

        await session.commit()
