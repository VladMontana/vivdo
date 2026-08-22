import json
import os

import redis
import requests

from vivido.celery_worker.celery_app import celery_app
from vivido.core import clean_url, get_settings, get_source_button_text
from vivido.extractor import extract_media_info
from vivido.logger import logger


settings = get_settings()
_redis_client: redis.Redis | None = None


def get_sync_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_media_url(
    self, chat_id: int, reply_to_message_id: int, url: str, quality: int = 1080
) -> bool:
    """
    Celery-задача для обработки ссылки на медиа и отправки видео в Telegram.
    """
    logger.info(
        f"[Task {self.request.id}] Начинаем обработку URL: {url} (качество {quality}p) для чата {chat_id}"
    )

    normalized_url = clean_url(url)
    cache_key = f"app:cache:{quality}:{normalized_url}"

    bot_token = settings.bot_token.get_secret_value()
    if not bot_token:
        logger.error(f"[Task {self.request.id}] BOT_TOKEN не настроен!")
        return False

    send_video_url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    reply_markup_json = json.dumps(
        {
            "inline_keyboard": [
                [{"text": get_source_button_text(url), "url": url}]
            ]
        }
    )

    # 1. Проверяем кэш Redis (если медиа уже загружалось ранее)
    try:
        r = get_sync_redis()
        cached = r.get(cache_key)
        if cached:
            cached_data = json.loads(cached)
            media_type = cached_data.get("media_type", "video")

            if media_type == "photo":
                send_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                payload = {
                    "chat_id": chat_id,
                    "reply_to_message_id": reply_to_message_id,
                    "photo": cached_data["file_id"],
                    "caption": cached_data.get("caption", ""),
                    "parse_mode": "HTML",
                    "reply_markup": reply_markup_json,
                }
            else:
                send_url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
                payload = {
                    "chat_id": chat_id,
                    "reply_to_message_id": reply_to_message_id,
                    "video": cached_data["file_id"],
                    "caption": cached_data.get("caption", ""),
                    "parse_mode": "HTML",
                    "reply_markup": reply_markup_json,
                }

            resp = requests.post(send_url, data=payload, timeout=20)
            if resp.ok and resp.json().get("ok"):
                logger.info(f"[Task {self.request.id}] Медиа ({media_type}) отправлено мгновенно из кэша Redis!")
                return True
    except Exception as cache_err:
        logger.warning(f"[Task {self.request.id}] Ошибка чтения кэша Redis: {cache_err}")

    # 2. Скачиваем и отправляем медиа (видео или фото)
    media = None
    try:
        media = extract_media_info(url, max_height=quality)

        if not media or not media.file_path or not os.path.exists(media.file_path):
            logger.warning(
                f"[Task {self.request.id}] Не удалось получить файл медиа для URL: {url}"
            )
            return False

        # Отправляем точный статус в чат (upload_photo или upload_video)
        action_name = (
            "upload_photo" if media.media_type in ("photo", "photos") else "upload_video"
        )
        try:
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendChatAction",
                data={"chat_id": chat_id, "action": action_name},
                timeout=5,
            )
        except Exception:
            pass

        if media.media_type == "photos" and len(media.file_paths) > 1:

            send_url = f"https://api.telegram.org/bot{bot_token}/sendMediaGroup"
            media_items = []
            files = {}
            opened_files = []
            try:
                for i, fpath in enumerate(media.file_paths):
                    attach_name = f"photo_{i}"
                    item = {
                        "type": "photo",
                        "media": f"attach://{attach_name}",
                        "parse_mode": "HTML",
                    }
                    if i == 0:
                        item["caption"] = media.caption
                    media_items.append(item)
                    f_obj = open(fpath, "rb")
                    opened_files.append(f_obj)
                    files[attach_name] = (f"photo_{i}.jpg", f_obj, "image/jpeg")

                payload = {
                    "chat_id": chat_id,
                    "reply_to_message_id": reply_to_message_id,
                    "media": json.dumps(media_items),
                }
                response = requests.post(send_url, data=payload, files=files, timeout=120)
            finally:
                for f_obj in opened_files:
                    f_obj.close()
        elif media.media_type == "photo":
            send_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            payload = {
                "chat_id": chat_id,
                "reply_to_message_id": reply_to_message_id,
                "caption": media.caption,
                "parse_mode": "HTML",
                "reply_markup": reply_markup_json,
            }
            with open(media.file_path, "rb") as photo_file:
                files = {"photo": ("photo.jpg", photo_file, "image/jpeg")}
                response = requests.post(send_url, data=payload, files=files, timeout=120)
        else:
            send_url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
            payload = {
                "chat_id": chat_id,
                "reply_to_message_id": reply_to_message_id,
                "caption": media.caption,
                "parse_mode": "HTML",
                "supports_streaming": True,
                "reply_markup": reply_markup_json,
            }
            with open(media.file_path, "rb") as video_file:
                files = {"video": ("video.mp4", video_file, "video/mp4")}
                response = requests.post(send_url, data=payload, files=files, timeout=120)

        response_json = response.json()

        if not response.ok or not response_json.get("ok"):
            logger.error(f"[Task {self.request.id}] Ошибка от Telegram API: {response_json}")
            return False

        # Сохраняем file_id в Redis на 7 дней
        try:
            res = response_json.get("result", {})
            file_id = None
            if media.media_type == "video":
                file_id = res.get("video", {}).get("file_id")
            elif media.media_type == "photo":
                photos = res.get("photo", [])
                if photos:
                    file_id = photos[-1].get("file_id")

            if file_id:
                r = get_sync_redis()
                r.set(
                    cache_key,
                    json.dumps({
                        "media_type": media.media_type,
                        "file_id": file_id,
                        "caption": media.caption,
                    }),
                    ex=604800,
                )
                logger.info(f"[Task {self.request.id}] file_id ({media.media_type}) успешно сохранен в кэш Redis.")
        except Exception as save_cache_err:
            logger.warning(f"Не удалось сохранить в кэш: {save_cache_err}")

        logger.info(f"[Task {self.request.id}] Медиа успешно отправлено в чат {chat_id}!")
        return True

    except requests.RequestException as req_err:
        logger.warning(
            f"[Task {self.request.id}] Сетевая ошибка при отправке ({req_err}), пробуем снова..."
        )
        raise self.retry(exc=req_err) from req_err
    except Exception as exc:
        logger.exception(
            f"[Task {self.request.id}] Непредвиденная ошибка при обработке {url}: {exc}"
        )
        raise self.retry(exc=exc) from exc
    finally:
        paths_to_clean = []
        if media:
            if media.file_paths:
                paths_to_clean.extend(media.file_paths)
            elif media.file_path:
                paths_to_clean.append(media.file_path)
        for p in paths_to_clean:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                    logger.debug(f"Временный файл {p} успешно удален.")
                except Exception as e:
                    logger.warning(f"Не удалось удалить временный файл {p}: {e}")



