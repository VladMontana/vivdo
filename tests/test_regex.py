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
        assert expected in match.group(0)


def test_url_pattern_matches_twitter_x():
    samples = [
        (
            "Twitter: https://twitter.com/user/status/1234567890123456789",
            "https://twitter.com/user/status/1234567890123456789",
        ),
        (
            "X link: https://x.com/user/status/9876543210987654321?s=20",
            "https://x.com/user/status/9876543210987654321?s=20",
        ),
    ]
    for text, expected in samples:
        match = URL_PATTERN.search(text)
        assert match is not None
        assert expected in match.group(0)


def test_url_pattern_matches_tiktok():
    samples = [
        (
            "TikTok web: https://www.tiktok.com/@username/video/7123456789012345678",
            "https://www.tiktok.com/@username/video/7123456789012345678",
        ),
        (
            "TikTok short vm: https://vm.tiktok.com/ZM8abc123/",
            "https://vm.tiktok.com/ZM8abc123/",
        ),
        (
            "TikTok short vt: https://vt.tiktok.com/ZS8xyz789/",
            "https://vt.tiktok.com/ZS8xyz789/",
        ),
    ]
    for text, expected in samples:
        match = URL_PATTERN.search(text)
        assert match is not None
        assert expected in match.group(0)


def test_url_pattern_ignores_non_matching_text():
    samples = [
        "Just a regular text without links",
        "https://google.com/search?q=test",
        "https://youtube.com/watch?v=12345",
    ]
    for text in samples:
        match = URL_PATTERN.search(text)
        assert match is None

