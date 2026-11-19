import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

logger = logging.getLogger("app.updates")


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Update):
            update_type = event.event_type
            user = data.get("event_from_user")
            user_info = f"user_id={user.id}" if user else "no_user"
            logger.info(f"Incoming update: type={update_type}, {user_info}")

        return await handler(event, data)
