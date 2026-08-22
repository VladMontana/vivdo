import json

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from vivido.celery_worker import process_media_url
from vivido.connector import redis_manager
from vivido.core import URL_PATTERN, clean_url
from vivido.keyboards import get_quality_keyboard, get_source_keyboard
from vivido.logger import logger
from vivido.middlewares import ThrottlingMiddleware


dp = Dispatcher()
dp.message.middleware(ThrottlingMiddleware(rate_limit_seconds=3))



@dp.startup()
async def on_startup():
    try:
        await redis_manager.connect()
        logger.info("Соединение с Redis успешно установлено.")
    except Exception as exc:
        logger.warning(
            f"Предупреждение: не удалось подключиться к Redis на старте ({exc}). Убедитесь, что Redis запущен."
        )


@dp.shutdown()
async def on_shutdown():
    try:
        await redis_manager.close()
        logger.info("Соединение с Redis закрыто.")
    except Exception as exc:
        logger.warning(f"Ошибка при закрытии Redis: {exc}")


@dp.message(CommandStart())
async def handle_start(message: Message, bot: Bot):
    if message.chat.type == "private":
        bot_info = await bot.get_me()
        add_to_group_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Добавить в группу",
                        url=f"https://t.me/{bot_info.username}?startgroup=true",
                    )
                ]
            ]
        )
        welcome_text = (
            "👋 <b>Привет!</b>\n\n"
            "🔒 Этот бот работает <b>только в группах</b>.\n"
            "Добавьте меня в вашу группу, чтобы автоматически скачивать видео из <b>TikTok</b>, <b>YouTube Shorts</b> и <b>X (Twitter)</b>!"
        )
        await message.answer(welcome_text, reply_markup=add_to_group_kb, parse_mode="HTML")
        return

    await message.answer(
        "👋 <b>Привет!</b> Я готов к работе в этой группе.\n"
        "Отправляйте ссылки на TikTok, YouTube Shorts и X (Twitter)!\n\n"
        "⚙️ Настройка качества: /quality",
        parse_mode="HTML",
    )


@dp.message(Command("help"))
async def handle_help(message: Message, bot: Bot):
    if message.chat.type == "private":
        bot_info = await bot.get_me()
        add_to_group_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Добавить в группу",
                        url=f"https://t.me/{bot_info.username}?startgroup=true",
                    )
                ]
            ]
        )
        await message.answer(
            "🔒 Бот работает только в группах. Добавьте его в группу для работы:",
            reply_markup=add_to_group_kb,
        )
        return

    help_text = (
        "ℹ️ <b>Как пользоваться в группе:</b>\n\n"
        "Отправьте сообщение, содержащее ссылку на:\n"
        "• TikTok (<code>tiktok.com/@...</code>, <code>vt.tiktok.com/...</code>, <code>vm.tiktok.com/...</code>)\n"
        "• YouTube Shorts (<code>youtube.com/shorts/...</code>)\n"
        "• X / Twitter (<code>x.com/.../status/...</code> или <code>twitter.com/.../status/...</code>)\n\n"
        "Команды для администраторов:\n"
        "/quality или /settings — выбрать качество видео (1080p или 720p) для этой группы."
    )
    await message.answer(help_text, parse_mode="HTML")



@dp.message(Command("quality"))
@dp.message(Command("settings"))
async def handle_quality_command(message: Message, bot: Bot):
    if message.chat.type == "private":
        bot_info = await bot.get_me()
        add_to_group_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Добавить в группу",
                        url=f"https://t.me/{bot_info.username}?startgroup=true",
                    )
                ]
            ]
        )
        await message.answer(
            "⚠️ Настройка качества доступна только внутри групп. Добавьте бота в группу для использования:",
            reply_markup=add_to_group_kb,
        )
        return

    quality_str = await redis_manager.get(f"chat_quality:{message.chat.id}")
    quality = int(quality_str) if quality_str and quality_str.isdigit() else 1080

    text = (
        "⚙️ <b>Настройка качества видео для этой группы:</b>\n\n"
        f"Текущий выбор: <b>{quality}p</b>\n\n"
        "• <b>1080p (Full HD)</b> — максимальная четкость (по умолчанию).\n"
        "• <b>720p (Быстрее)</b> — меньший размер и быстрая загрузка.\n\n"
        "<i>Выберите нужное качество кнопкой ниже:</i>"
    )
    await message.answer(
        text, reply_markup=get_quality_keyboard(quality), parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("set_quality:"))
async def handle_quality_callback(callback: CallbackQuery, bot: Bot):
    if not isinstance(callback.message, Message) or not callback.data:
        return

    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    chat_type = callback.message.chat.type

    # Проверка прав администратора в группах
    if chat_type in ("group", "supergroup"):
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status not in ("creator", "administrator"):
                await callback.answer(
                    "⚠️ Только администраторы чата могут изменять качество видео!",
                    show_alert=True,
                )
                return
        except Exception as err:
            logger.warning(f"Не удалось проверить права администратора: {err}")

    quality = int(callback.data.split(":")[1])
    await redis_manager.set(f"chat_quality:{chat_id}", str(quality))
    logger.info(f"Для чата {chat_id} установлено качество {quality}p")

    await callback.answer(f"✅ Качество для этой группы: {quality}p!")
    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_quality_keyboard(current_quality=quality)
        )
    except Exception:
        pass


@dp.message(F.text)
async def handle_media_links(message: Message, bot: Bot):
    if not message.text:
        return

    match = URL_PATTERN.search(message.text)
    if not match:
        return

    # Ограничение: бот обрабатывает ссылки ТОЛЬКО в группах
    if message.chat.type == "private":
        bot_info = await bot.get_me()
        add_to_group_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Добавить в группу",
                        url=f"https://t.me/{bot_info.username}?startgroup=true",
                    )
                ]
            ]
        )
        await message.answer(
            "🔒 <b>Бот работает только в группах!</b>\n\n"
            "Добавьте меня в вашу группу или чат, и я буду автоматически встраивать видео из <b>TikTok</b>, <b>YouTube Shorts</b> и <b>X (Twitter)</b>.",
            reply_markup=add_to_group_kb,
            parse_mode="HTML",
        )

        return

    raw_url = match.group(0)
    logger.info(f"Получена ссылка {raw_url} из чата {message.chat.id}")

    # Определяем выбранное качество для чата (по умолчанию 1080p)
    quality = 1080
    try:
        quality_str = await redis_manager.get(f"chat_quality:{message.chat.id}")
        if quality_str and quality_str.isdigit():
            quality = int(quality_str)
    except Exception as exc:
        logger.warning(f"Ошибка при получении качества чата: {exc}")

    # 1. Проверяем кэш Redis для мгновенной отдачи с учетом качества
    try:
        clean_key = f"cache:{quality}:{clean_url(raw_url)}"
        cached_data = await redis_manager.get(clean_key)
        if cached_data:
            data = json.loads(cached_data)
            media_type = data.get("media_type", "video")
            logger.info(
                f"Найден кэш ({media_type}) для {raw_url}, мгновенная отправка по file_id..."
            )
            if media_type == "photo":
                await message.answer_photo(
                    photo=data["file_id"],
                    caption=data.get("caption", ""),
                    parse_mode="HTML",
                    reply_to_message_id=message.message_id,
                    reply_markup=get_source_keyboard(raw_url),
                )
            else:
                await message.answer_video(
                    video=data["file_id"],
                    caption=data.get("caption", ""),
                    parse_mode="HTML",
                    reply_to_message_id=message.message_id,
                    reply_markup=get_source_keyboard(raw_url),
                )
            return

    except Exception as exc:
        logger.warning(f"Ошибка при чтении кэша: {exc}")

    # 2. Показываем начальный статус обработки
    try:
        url_lower = raw_url.lower()
        if "youtube.com" in url_lower or "youtu.be" in url_lower or "tiktok.com" in url_lower:
            action = ChatAction.UPLOAD_VIDEO
        else:
            action = ChatAction.TYPING

        await bot.send_chat_action(
            chat_id=message.chat.id,
            action=action,
        )
    except Exception:
        pass


    # 3. Неблокирующая постановка задачи в очередь Celery с учетом качества
    try:
        task = process_media_url.delay(
            chat_id=message.chat.id,
            reply_to_message_id=message.message_id,
            url=raw_url,
            quality=quality,
        )
        logger.info(f"Задача Celery создана: ID={task.id} (качество {quality}p)")
    except Exception as exc:
        logger.error(f"Ошибка при постановке задачи в Celery: {exc}")



