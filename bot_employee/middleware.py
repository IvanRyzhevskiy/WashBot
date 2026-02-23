from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from core.database import get_db_context
from core.models import User

class RoleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем telegram_id
        if isinstance(event, Message):
            telegram_id = event.from_user.id
        else:
            telegram_id = event.from_user.id
        
        # Проверяем пользователя
        async with get_db_context() as db:
            result = await db.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user or user.role not in ["admin", "washer", "owner"]:
                if isinstance(event, Message):
                    await event.answer("❌ Доступ запрещен. Этот бот только для сотрудников.")
                else:
                    await event.answer("Доступ запрещен", show_alert=True)
                return
            
            data["user"] = user
            data["user_role"] = user.role
        
        return await handler(event, data)
