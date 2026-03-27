"""Tests for Instagram data export ZIP parser."""

import io
import json
import zipfile
from pathlib import Path

import pytest

from src.pipeline.utils.instagram_parser import (
    REEL_URL_PATTERN,
    ParsedChat,
    _classify_message,
    _decode_instagram_text,
    _extract_reel_urls,
    _is_safe_path,
    parse_chat_from_zip,
)


def _create_test_zip(tmp_path: Path, messages: list[dict], title: str = "Test Chat") -> str:
    """Create a minimal Instagram export ZIP for testing."""
    zip_path = str(tmp_path / "export.zip")
    chat_data = {
        "participants": [{"name": "Alice"}, {"name": "Bob"}],
        "messages": messages,
        "title": title,
        "thread_path": "inbox/testchat_123",
    }

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(
            "your_instagram_activity/messages/inbox/testchat_123/message_1.json",
            json.dumps(chat_data),
        )

    return zip_path


class TestSafePath:
    def test_normal_path(self) -> None:
        assert _is_safe_path("your_instagram_activity/messages/inbox/chat/message_1.json")

    def test_traversal_rejected(self) -> None:
        assert not _is_safe_path("../../etc/passwd")

    def test_absolute_rejected(self) -> None:
        assert not _is_safe_path("/etc/passwd")


class TestDecodeInstagramText:
    def test_ascii_unchanged(self) -> None:
        assert _decode_instagram_text("Hello world") == "Hello world"

    def test_emoji_decoded(self) -> None:
        # Instagram encodes "😀" as latin-1 encoded UTF-8 bytes
        encoded = "😀".encode("utf-8").decode("latin-1")
        assert _decode_instagram_text(encoded) == "😀"


class TestClassifyMessage:
    def test_text_message(self) -> None:
        assert _classify_message({"content": "Hello"}) == "text"

    def test_reel_share(self) -> None:
        msg = {"share": {"link": "https://www.instagram.com/reel/ABC123/"}}
        assert _classify_message(msg) == "reel_share"

    def test_link_share(self) -> None:
        msg = {"share": {"link": "https://example.com"}}
        assert _classify_message(msg) == "link"

    def test_media_message(self) -> None:
        assert _classify_message({"photos": [{}]}) == "media"

    def test_empty_message(self) -> None:
        assert _classify_message({}) == "other"


class TestExtractReelUrls:
    def test_share_link(self) -> None:
        msg = {"share": {"link": "https://www.instagram.com/reel/ABC123/"}}
        assert _extract_reel_urls(msg) == ["https://www.instagram.com/reel/ABC123/"]

    def test_url_in_content(self) -> None:
        msg = {"content": "Check this out https://instagram.com/reel/XYZ789/"}
        assert _extract_reel_urls(msg) == ["https://instagram.com/reel/XYZ789/"]

    def test_no_urls(self) -> None:
        msg = {"content": "Just a normal message"}
        assert _extract_reel_urls(msg) == []

    def test_deduplication(self) -> None:
        url = "https://www.instagram.com/reel/ABC123/"
        msg = {"share": {"link": url}, "content": f"Look at this {url}"}
        assert _extract_reel_urls(msg) == [url]


class TestReelUrlPattern:
    def test_reel_url(self) -> None:
        assert REEL_URL_PATTERN.search("https://www.instagram.com/reel/ABC123/")

    def test_post_url(self) -> None:
        assert REEL_URL_PATTERN.search("https://instagram.com/p/DEF456/")

    def test_non_instagram(self) -> None:
        assert not REEL_URL_PATTERN.search("https://example.com/reel/ABC123/")


class TestParseChatFromZip:
    def test_basic_parse(self, tmp_path: Path) -> None:
        messages = [
            {
                "sender_name": "Alice",
                "timestamp_ms": 1000,
                "content": "Let's go to Tatiana",
                "type": "Generic",
            },
            {
                "sender_name": "Bob",
                "timestamp_ms": 2000,
                "content": "Check this place",
                "share": {"link": "https://www.instagram.com/reel/FOOD123/"},
                "type": "Generic",
            },
        ]
        zip_path = _create_test_zip(tmp_path, messages)
        result = parse_chat_from_zip(zip_path)

        assert result.title == "Test Chat"
        assert len(result.participants) == 2
        assert len(result.messages) == 2
        assert result.messages[0].sender_name == "Alice"
        assert result.messages[0].message_type == "text"
        assert result.messages[1].message_type == "reel_share"
        assert len(result.reel_urls) == 1
        assert "FOOD123" in result.reel_urls[0]

    def test_messages_sorted_by_timestamp(self, tmp_path: Path) -> None:
        messages = [
            {"sender_name": "Bob", "timestamp_ms": 2000, "content": "Second"},
            {"sender_name": "Alice", "timestamp_ms": 1000, "content": "First"},
        ]
        zip_path = _create_test_zip(tmp_path, messages)
        result = parse_chat_from_zip(zip_path)

        assert result.messages[0].content == "First"
        assert result.messages[1].content == "Second"

    def test_empty_zip_raises(self, tmp_path: Path) -> None:
        zip_path = str(tmp_path / "empty.zip")
        with zipfile.ZipFile(zip_path, "w"):
            pass  # empty zip

        with pytest.raises(ValueError, match="No Instagram group chats found"):
            parse_chat_from_zip(zip_path)
