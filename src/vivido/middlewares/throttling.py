from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from vivido.connector import redis_manager
from vivido.core import URL_PATTERN
from vivido.logger import logger



class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware для ограничения частоты обработки медиа-ссылок от одного чата.
    Использует атомарный ключ в Redis с TTL.
    """

    def __init__(self, rate_limit_seconds: int = 3) -> None:
        self.rate_limit_seconds = rate_limit_seconds

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.text:
            return await handler(event, data)

        # Применяем throttling только к сообщениям, содержащим медиа-ссылки
        if not URL_PATTERN.search(event.text):
            return await handler(event, data)

        chat_id = event.chat.id
        throttle_key = f"throttle:chat:{chat_id}"

        try:
            # Атомарная установка блокировки в Redis
            is_allowed = await redis_manager.set_if_not_exists(
                key=throttle_key,
                value="1",
                expire=self.rate_limit_seconds,
            )

            if not is_allowed:
                logger.warning(
                    f"[Throttling] Сообщение со ссылкой проигнорировано: чат {chat_id} отправляет запросы слишком часто (лимит {self.rate_limit_seconds}с)."
                )
                return None
        except Exception as exc:
            # В случае сбоя Redis не блокируем пользователя, а логируем ошибку
            logger.warning(f"[Throttling] Ошибка проверки Redis: {exc}")

        return await handler(event, data)
