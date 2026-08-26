from vivido.core import URL_PATTERN


def test_url_pattern_matches_youtube_shorts():
    samples = [
        (
            "Check this https://www.youtube.com/shorts/dQw4w9WgXcQ cool",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        ),
        ("Short youtu.be: https://youtu.be/dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ"),
    ]
    for text, expected in samples:
        match = URL_PATTERN.search(text)
        assert match is not None
        assert match.group(0).startswith(expected)


def test_url_pattern_matches_youtube_posts():
    samples = [
        (
            "Check post http://youtube.com/post/UgkxyGmewQdHkQGhAqdkv1OIfO94saBRUs7i?si=-HHrpyRMyYrJio7s",
            "http://youtube.com/post/UgkxyGmewQdHkQGhAqdkv1OIfO94saBRUs7i",
        ),
        (
            "https://www.youtube.com/post/UgkxyGmewQdHkQGhAqdkv1OIfO94saBRUs7i",
            "https://www.youtube.com/post/UgkxyGmewQdHkQGhAqdkv1OIfO94saBRUs7i",
        ),
    ]
    for text, expected in samples:
        match = URL_PATTERN.search(text)
        assert match is not None
        assert match.group(0).startswith(expected)


def test_url_pattern_matches_twitter():
    samples = [
        (
            "Look https://twitter.com/user/status/1234567890123456789 test",
            "https://twitter.com/user/status/1234567890123456789",
        ),
        (
            "X link: https://x.com/user/status/9876543210987654321?s=20",
            "https://x.com/user/status/9876543210987654321",
        ),
    ]
    for text, expected in samples:
        match = URL_PATTERN.search(text)
        assert match is not None
        assert match.group(0).startswith(expected)


def test_url_pattern_matches_tiktok():
    samples = [
        (
            "TikTok video https://www.tiktok.com/@username/video/7123456789012345678?is_from_webapp=1",
            "https://www.tiktok.com/@username/video/7123456789012345678",
        ),
        (
            "Check vt: https://vt.tiktok.com/ZS2xYabcd/ cool",
            "https://vt.tiktok.com/ZS2xYabcd/",
        ),
        (
            "Check vm: https://vm.tiktok.com/ZM8xYabcd/",
            "https://vm.tiktok.com/ZM8xYabcd/",
        ),
        (
            "Short t: https://www.tiktok.com/t/ZT8xYabcd/",
            "https://www.tiktok.com/t/ZT8xYabcd/",
        ),
    ]
    for text, expected in samples:
        match = URL_PATTERN.search(text)
        assert match is not None
        assert match.group(0).startswith(expected)


def test_url_pattern_ignores_non_media():
    non_matches = [
        "https://google.com",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://facebook.com/post/123",
        "Просто текст без ссылок",
    ]
    for text in non_matches:
        match = URL_PATTERN.search(text)
        assert match is None
