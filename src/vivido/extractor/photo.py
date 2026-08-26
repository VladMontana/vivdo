import html
import json
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

YOUTUBE_POST_REGEX = re.compile(
    r"youtube\.com/(?:post/|channel/[^/]+/community\?lb=|c/[^/]+/community\?lb=)([a-zA-Z0-9_-]+)",
    re.IGNORECASE,
)


def extract_twitter_photos(url: str) -> MediaResult | None:
    """
    Извлекает фотографии из твитов X/Twitter в оригинальном качестве.
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
        logger.warning(f"Ошибка при извлечении фото из твита {url}: {exc}")
        return None


def extract_youtube_post(url: str) -> MediaResult | None:
    """
    Извлекает текст и фотографии из постов сообщества YouTube (Community Posts).
    """
    match = YOUTUBE_POST_REGEX.search(url)
    if not match:
        return None

    post_id = match.group(1)
    clean_post_url = f"https://www.youtube.com/post/{post_id}"
    temp_dir = tempfile.gettempdir()
    temp_id = f"tg_bot_yt_post_{uuid.uuid4().hex}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        resp = requests.get(clean_post_url, headers=headers, timeout=15)
        if not resp.ok:
            logger.warning(f"Не удалось загрузить YouTube пост {clean_post_url}: HTTP {resp.status_code}")
            return None

        match_data = re.search(r"var ytInitialData = ({.*?});</script>", resp.text)
        if not match_data:
            match_data = re.search(r"ytInitialData\s*=\s*({.+?});", resp.text)

        if not match_data:
            logger.warning(f"ytInitialData не найден для YouTube поста: {url}")
            return None

        data = json.loads(match_data.group(1))
        post = None
        tabs = data.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])
        if tabs:
            contents = tabs[0].get("tabRenderer", {}).get("content", {}).get("sectionListRenderer", {}).get("contents", [])
            if contents:
                items = contents[0].get("itemSectionRenderer", {}).get("contents", [])
                if items:
                    post = items[0].get("backstagePostThreadRenderer", {}).get("post", {}).get("backstagePostRenderer")

        if not post:
            logger.warning(f"backstagePostRenderer не найден в ytInitialData для {url}")
            return None

        author_runs = post.get("authorText", {}).get("runs", [])
        author_name = author_runs[0].get("text", "YouTube") if author_runs else "YouTube"

        text_parts = [r.get("text", "") for r in post.get("contentText", {}).get("runs", [])]
        text_raw = "".join(text_parts).strip()

        img_urls = []
        attachment = post.get("backstageAttachment", {})
        if "postMultiImageRenderer" in attachment:
            for img in attachment["postMultiImageRenderer"].get("images", []):
                thumbs = img.get("backstageImageRenderer", {}).get("image", {}).get("thumbnails", [])
                if thumbs:
                    img_urls.append(thumbs[-1].get("url"))
        elif "backstageImageRenderer" in attachment:
            thumbs = attachment["backstageImageRenderer"].get("image", {}).get("thumbnails", [])
            if thumbs:
                img_urls.append(thumbs[-1].get("url"))

        photo_paths: list[str] = []
        for i, img_url in enumerate(img_urls):
            # Заменяем размер на оригинальное качество =s0 если возможно
            high_res_url = re.sub(r"=s\d+.*", "=s0", img_url) if "=s" in img_url else img_url
            photo_file = os.path.join(temp_dir, f"{temp_id}_p{i}.jpg")
            img_resp = requests.get(high_res_url, timeout=15)
            if img_resp.ok:
                with open(photo_file, "wb") as f:
                    f.write(img_resp.content)
                photo_paths.append(photo_file)

        if not photo_paths:
            logger.warning(f"В YouTube посте {url} не найдено изображений для отправки")
            return None

        uploader = html.escape(author_name)
        safe_text = html.escape(text_raw)
        if len(safe_text) > 400:
            safe_text = safe_text[:397] + "..."

        header = f"<b>{uploader}</b>"
        if safe_text:
            caption = f"{header}\n\n<blockquote>{safe_text}</blockquote>"
        else:
            caption = header

        if len(caption) > 1024:
            caption = caption[:1020] + "..."

        media_type = "photos" if len(photo_paths) > 1 else "photo"
        logger.info(
            f"Успешно извлечено {len(photo_paths)} фото для YouTube поста: {url}"
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
        logger.warning(f"Ошибка при извлечении YouTube поста {url}: {exc}")
        return None


def extract_photo_info(url: str) -> MediaResult | None:
    """
    Универсальное извлечение фото-постов и галерей (X / Twitter, YouTube Community Posts).
    """
    if "youtube.com" in url.lower():
        return extract_youtube_post(url)
    return extract_twitter_photos(url)
