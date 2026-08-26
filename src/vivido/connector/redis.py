from typing import Any

import redis.asyncio as redis
from redis.asyncio import Redis

from vivido.core.config import get_settings


settings = get_settings()


class RedisManager:
    def __init__(self, redis_url: str, prefix: str = "app") -> None:
        self.redis_url = redis_url
        self.prefix = prefix
        self.client: Redis | None = None

    async def connect(self) -> None:
        self.client = redis.from_url(
            self.redis_url,
            decode_responses=True,
            retry_on_timeout=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        await self.client.ping()

    def _get_active_client(self) -> Redis:
        """
        Возвращает активный Redis-клиент.

        :raises RuntimeError: если connect() еще не был вызван.
        :return: Redis-клиент.
        """
        if self.client is None:
            raise RuntimeError("Redis не подключен. Сначала вызовите connect()")

        return self.client

    def _build_key(self, key: str) -> str:
        """
        Добавляет префикс к ключу Redis.

        Например:
        key='anything'
        prefix='app'

        Итоговый ключ:
        app:anything

        :param key: исходный ключ.
        :return: ключ с префиксом.
        """
        return f"{self.prefix}:{key}"

    async def exists(self, key: str) -> bool:
        """
        Проверка существования ключа в Redis.
        :return: True, если ключ существует
        """
        client = self._get_active_client()
        return bool(await client.exists(self._build_key(key)))

    async def set_if_not_exists(self, key: str, value: Any, expire: int | None = None) -> bool:
        """
        Установка значения в Redis, если ключ не существует.

        :return: True, если значение успешно установлено
        """
        client = self._get_active_client()
        result = await client.set(name=self._build_key(key), value=value, nx=True, ex=expire)
        return bool(result)

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Инкремент значения в Redis.

        :return: Новое значение
        """
        client = self._get_active_client()
        return await client.incrby(self._build_key(key), amount)

    async def expire(self, key: str, seconds: int) -> bool:
        """
        Установка времени жизни ключа в Redis.

        :return: True, если время жизни успешно установлено
        """
        client = self._get_active_client()
        return await client.expire(self._build_key(key), seconds)

    async def set(self, key: str, value: Any, expire: int | None = None, nx: bool = False) -> bool:
        """
        Сохранение значения в Redis.

        :return: True, если значение успешно сохранено
        """
        client = self._get_active_client()
        return bool(await client.set(name=self._build_key(key), value=value, ex=expire, nx=nx))

    async def get(self, key: str) -> Any:
        client = self._get_active_client()
        return await client.get(name=self._build_key(key))

    async def delete(self, key: str) -> int:
        client = self._get_active_client()
        return await client.delete(self._build_key(key))

    async def close(self) -> None:
        """
        Закрытие соединения с Redis.
        """
        if self.client is not None:
            await self.client.aclose()
            self.client = None


redis_manager: RedisManager = RedisManager(redis_url=settings.redis_url, prefix="app")
