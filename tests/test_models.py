from vivido.core import Settings
from vivido.schemas import MediaResult



def test_media_result_model():
    result = MediaResult(
        video_url="https://video.twimg.com/ext_tw_video/123/pu/vid/720x1280/video.mp4",
        caption="<b>Test Author</b>\n\n<blockquote>Some caption</blockquote>",
        title="Test Title",
        uploader="Test Author",
    )
    assert result.video_url is not None
    assert result.video_url.startswith("https://")
    assert "Test Author" in result.caption
    assert result.title == "Test Title"
    assert result.uploader == "Test Author"



def test_settings_defaults():
    settings = Settings(bot_token="123456:ABC-DEF")
    assert settings.bot_token.get_secret_value() == "123456:ABC-DEF"
    assert settings.redis_url == "redis://localhost:6379/0"
