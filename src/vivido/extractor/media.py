from vivido.extractor.photo import extract_photo_info
from vivido.extractor.video import extract_video_info
from vivido.logger import logger
from vivido.schemas import MediaResult



def extract_media_info(url: str, max_height: int = 1080) -> MediaResult | None:
    """
    Универсальная точка входа для извлечения медиа.
    Сначала пытается скачать видео; если видео не найдено (например, твит с картинками),
    переключается на извлечение фотографий.
    """
    # 1. Пробуем скачать как видео
    video_res = extract_video_info(url=url, max_height=max_height)
    if video_res:
        return video_res

    # 2. Если видео не найдено и это ссылка на пост с фото — извлекаем фото
    logger.info(f"Видео не найдено для {url}, проверяем наличие фотографий...")
    photo_res = extract_photo_info(url=url)
    if photo_res:
        return photo_res

    logger.warning(f"Не удалось извлечь ни видео, ни фото для URL: {url}")
    return None
