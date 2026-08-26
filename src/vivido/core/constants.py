import re
import urllib.parse

URL_PATTERN: re.Pattern[str] = re.compile(
    r"https?://(?:www\.|m\.|vm\.|vt\.)?(?:youtube\.com/shorts/[\w\-]+|youtube\.com/post/[\w\-]+|youtube\.com/(?:channel|c|user)/[\w\.\-]+/community\?lb=[\w\-]+|youtu\.be/[\w\-]+|twitter\.com/\w+/status/\d+|x\.com/\w+/status/\d+|tiktok\.com/@[\w\.\-]+/video/\d+|tiktok\.com/t/[\w\-]+|tiktok\.com/[\w\-]+|(?:vm|vt)\.tiktok\.com/[\w\-]+)\S*",
    re.IGNORECASE,
)


def clean_url(url: str) -> str:
    """Очищает URL от трекинг-параметров для стабильного кэширования."""
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path, "", "", ""))


def get_source_button_text(url: str) -> str:
    """Возвращает читаемый текст для инлайн-кнопки источника."""
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "🎬 Смотреть на YouTube"
    if "x.com" in url_lower or "twitter.com" in url_lower:
        return "𝕏 Смотреть в X"
    if "tiktok.com" in url_lower:
        return "🎵 Смотреть в TikTok"
    return "🔗 Смотреть оригинал"
