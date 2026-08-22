import asyncio
import sys

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from vivido.bot import dp
from vivido.core import get_settings
from vivido.logger import logger, setup_logger


setup_logger()


async def run_bot() -> None:
    settings = get_settings()
    bot_token = settings.bot_token.get_secret_value()

    if not bot_token or bot_token == "your_telegram_bot_token_here":
        logger.error("BOT_TOKEN не задан в .env файле! Пожалуйста, укажите токен от @BotFather.")
        print(
            "\n[!] Ошибка: BOT_TOKEN не задан. Создайте файл .env и добавьте туда токен от @BotFather.\n",
            file=sys.stderr,
        )
        return

    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    logger.info("Запуск бота в режиме long-polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


def main() -> None:
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    main()
