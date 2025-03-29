from aiogram import BaseMiddleware
from typing import Any, Callable, Dict, Awaitable
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import async_session

class SessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        async with async_session() as session:
            data['session'] = session
            return await handler(event, data)