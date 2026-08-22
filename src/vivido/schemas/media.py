from pydantic import BaseModel


class MediaResult(BaseModel):
    media_type: str = "video"  # "video", "photo", "photos"
    file_path: str | None = None
    file_paths: list[str] = []
    video_url: str | None = None
    caption: str
    title: str = ""
    uploader: str = ""


