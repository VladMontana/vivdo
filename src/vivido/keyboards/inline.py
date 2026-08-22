from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from vivido.core import get_source_button_text



def get_source_keyboard(url: str) -> InlineKeyboardMarkup:
    """Возвращает инлайн-кнопку для перехода к оригинальному видео."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_source_button_text(url), url=url)]
        ]
    )


def get_quality_keyboard(current_quality: int = 1080) -> InlineKeyboardMarkup:
    """Возвращает инлайн-клавиатуру выбора качества видео для чата."""
    btn_1080_text = (
        "🎬 1080p (Full HD) ✅" if current_quality == 1080 else "🎬 1080p (Full HD)"
    )
    btn_720_text = "⚡ 720p (Быстрее) ✅" if current_quality == 720 else "⚡ 720p (Быстрее)"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=btn_1080_text, callback_data="set_quality:1080"),
                InlineKeyboardButton(text=btn_720_text, callback_data="set_quality:720"),
            ]
        ]
    )
