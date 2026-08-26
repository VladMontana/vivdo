import html
import os
import tempfile
import uuid

import yt_dlp

from vivido.logger import logger
from vivido.schemas import MediaResult


def extract_video_info(url: str, max_height: int = 1080) -> MediaResult | None:
    """
    Скачивает видео через yt-dlp во временный файл и формирует метаданные для Telegram.
    Приоритет отдается кодеку H.264 (avc1) + AAC и флагу +faststart для полной совместимости с iOS / Android / Desktop.
    """
    temp_dir = tempfile.gettempdir()
    temp_id = f"tg_bot_vid_{uuid.uuid4().hex}"
    outtmpl = os.path.join(temp_dir, f"{temp_id}.%(ext)s")

    cookie_paths = [
        "src/vivido/cookies/cookies.txt",
        "/app/src/vivido/cookies/cookies.txt",
        "cookies/cookies.txt",
        "/app/cookies/cookies.txt",
        "src/vivido/cookies.txt",
        "/app/src/vivido/cookies.txt",
        "cookies.txt",
        "/app/cookies.txt",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "cookies.txt"),
    ]

    cookiefile = next((p for p in cookie_paths if os.path.exists(p)), None)

    ydl_opts = {
        "format": (
            f"bestvideo[vcodec^=avc1][height<={max_height}]+bestaudio[acodec^=mp4a]/"
            f"bestvideo[vcodec^=avc1][height<={max_height}]+bestaudio/"
            f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={max_height}]+bestaudio/"
            f"best[height<={max_height}][ext=mp4]/"
            f"best[height<={max_height}]/best"
        ),
        "merge_output_format": "mp4",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "concurrent_fragment_downloads": 4,
        "max_filesize": 50 * 1024 * 1024,
        "remote_components": ["ejs:github"],
        "postprocessor_args": {
            "Merger": ["-movflags", "+faststart"],
        },
    }

    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile
        logger.info(f"Используем файл cookies: {cookiefile}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                logger.warning(f"Не удалось извлечь информацию для URL: {url}")
                return None

            expected_mp4 = os.path.join(temp_dir, f"{temp_id}.mp4")
            downloaded_file = None
            if os.path.exists(expected_mp4):
                downloaded_file = expected_mp4
            else:
                for fname in os.listdir(temp_dir):
                    if fname.startswith(temp_id):
                        downloaded_file = os.path.join(temp_dir, fname)
                        break

            if not downloaded_file or not os.path.exists(downloaded_file):
                logger.warning(f"Файл видео не найден после скачивания: {url}")
                return None

            uploader_raw = (
                info.get("uploader")
                or info.get("channel")
                or info.get("uploader_id")
                or "Автор"
            )
            title_raw = info.get("title") or ""
            description_raw = info.get("description") or ""

            uploader = html.escape(uploader_raw)
            title = html.escape(title_raw)

            body_text = description_raw if description_raw else title_raw
            safe_text = html.escape(body_text.strip())
            if len(safe_text) > 350:
                safe_text = safe_text[:347] + "..."

            header = f"<b>{uploader}</b>"
            if title and title != uploader:
                header += f" — {title[:80]}"

            if safe_text:
                caption = f"{header}\n\n<blockquote>{safe_text}</blockquote>"
            else:
                caption = header

            # Лимит Telegram на подпись к медиа — 1024 символа
            if len(caption) > 1024:
                caption = caption[:1020] + "..."

            return MediaResult(
                media_type="video",
                file_path=downloaded_file,
                file_paths=[downloaded_file],
                video_url=info.get("url"),
                caption=caption,
                title=title_raw,
                uploader=uploader_raw,
            )

    except Exception as exc:
        logger.warning(f"Не удалось извлечь видео для {url}: {exc}")
        return None
