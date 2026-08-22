import html
import os
import re
import tempfile
import uuid

import requests

from vivido.logger import logger
from vivido.schemas import MediaResult


TWITTER_STATUS_REGEX = re.compile(
    r"(?:twitter\.com|x\.com)/(\w+)/status/(\d+)", re.IGNORECASE
)


def extract_photo_info(url: str) -> MediaResult | None:
    """
    Извлекает фотографии из постов (например, твиты X/Twitter) в оригинальном качестве.
    """
    match = TWITTER_STATUS_REGEX.search(url)
    if not match:
        return None

    temp_dir = tempfile.gettempdir()
    temp_id = f"tg_bot_img_{uuid.uuid4().hex}"

    username, status_id = match.group(1), match.group(2)
    api_url = f"https://api.fxtwitter.com/{username}/status/{status_id}"

    try:
        resp = requests.get(
            api_url,
            timeout=10,
            headers={"User-Agent": "TelegramBot (like TwitterBot)"},
        )
        if not resp.ok:
            return None

        data = resp.json()
        tweet = data.get("tweet")
        if not tweet:
            return None

        photos = tweet.get("media", {}).get("photos", [])
        if not photos:
            return None

        author_name = tweet.get("author", {}).get("name") or username
        author_screen = tweet.get("author", {}).get("screen_name") or username
        text_raw = tweet.get("text", "")

        photo_paths: list[str] = []
        for i, photo_item in enumerate(photos):
            photo_url = photo_item.get("url")
            if not photo_url:
                continue
            photo_file = os.path.join(temp_dir, f"{temp_id}_p{i}.jpg")
            img_resp = requests.get(photo_url, timeout=15)
            if img_resp.ok:
                with open(photo_file, "wb") as f:
                    f.write(img_resp.content)
                photo_paths.append(photo_file)

        if not photo_paths:
            return None

        uploader = html.escape(author_name)
        safe_text = html.escape(text_raw.strip())
        if len(safe_text) > 350:
            safe_text = safe_text[:347] + "..."

        header = f"<b>{uploader}</b> (@{html.escape(author_screen)})"
        if safe_text:
            caption = f"{header}\n\n<blockquote>{safe_text}</blockquote>"
        else:
            caption = header

        if len(caption) > 1024:
            caption = caption[:1020] + "..."

        media_type = "photos" if len(photo_paths) > 1 else "photo"
        logger.info(
            f"Успешно извлечено {len(photo_paths)} фото для твита: {url}"
        )
        return MediaResult(
            media_type=media_type,
            file_path=photo_paths[0],
            file_paths=photo_paths,
            caption=caption,
            title="",
            uploader=author_name,
        )
    except Exception as exc:
        logger.warning(f"Ошибка при извлечении фото из поста {url}: {exc}")
        return None
