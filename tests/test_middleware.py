from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Chat, Message

from vivido.middlewares import ThrottlingMiddleware


@pytest.mark.asyncio
async def test_throttling_middleware_non_media_message():
    middleware = ThrottlingMiddleware(rate_limit_seconds=3)
    handler = AsyncMock(return_value="ok")

    chat = MagicMock(spec=Chat, id=123)
    message = MagicMock(spec=Message, text="Привет, как дела?", chat=chat)

    result = await middleware(handler, message, {})
    assert result == "ok"
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_throttling_middleware_media_allowed_and_blocked(monkeypatch):
    middleware = ThrottlingMiddleware(rate_limit_seconds=3)
    handler = AsyncMock(return_value="ok")

    chat = MagicMock(spec=Chat, id=999)
    message = MagicMock(
        spec=Message, text="https://youtube.com/shorts/SFUAD2d9mUs", chat=chat
    )

    # 1. Первый запрос разрешен
    monkeypatch.setattr(
        "vivido.connector.redis_manager.set_if_not_exists",
        AsyncMock(return_value=True),
    )
    res1 = await middleware(handler, message, {})
    assert res1 == "ok"
    assert handler.await_count == 1

    # 2. Второй запрос в течение интервала rate_limit отклоняется
    monkeypatch.setattr(
        "vivido.connector.redis_manager.set_if_not_exists",
        AsyncMock(return_value=False),
    )
    res2 = await middleware(handler, message, {})
    assert res2 is None
    assert handler.await_count == 1

