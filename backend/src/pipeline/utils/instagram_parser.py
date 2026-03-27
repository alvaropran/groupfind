"""Parse Instagram data export ZIP files.

Instagram exports contain messages in JSON files located at:
  your_instagram_activity/messages/inbox/<chat_name>/message_1.json
  your_instagram_activity/messages/inbox/<chat_name>/message_2.json
  ...

Each message JSON has the structure:
{
  "participants": [{"name": "User1"}, {"name": "User2"}],
  "messages": [
    {
      "sender_name": "User1",
      "timestamp_ms": 1234567890000,
      "content": "Hello!",
      "type": "Generic",
      "share": {"link": "https://instagram.com/reel/..."}
    }
  ],
  "title": "Chat Name",
  "thread_path": "inbox/chatname_12345"
}
"""

import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import PurePosixPath


@dataclass(frozen=True)
class ParsedMessage:
    sender_name: str
    content: str
    timestamp_ms: int
    message_type: str
    raw_json: dict


@dataclass(frozen=True)
class ParsedChat:
    title: str
    participants: list[str]
    messages: list[ParsedMessage]
    reel_urls: list[str]


REEL_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:reel|p)/[A-Za-z0-9_-]+/?",
)

MESSAGES_INBOX_PATH = "your_instagram_activity/messages/inbox/"


def _is_safe_path(path: str) -> bool:
    """Prevent ZIP path traversal attacks."""
    resolved = PurePosixPath(path)
    return ".." not in resolved.parts and not resolved.is_absolute()


def _decode_instagram_text(text: str) -> str:
    """Instagram exports encode non-ASCII as escaped UTF-8 bytes in latin-1."""
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def _classify_message(msg: dict) -> str:
    """Determine message type from Instagram JSON structure."""
    if "share" in msg and "link" in msg.get("share", {}):
        link = msg["share"]["link"]
        if REEL_URL_PATTERN.search(link):
            return "reel_share"
        return "link"
    if "photos" in msg or "videos" in msg:
        return "media"
    if "content" in msg:
        return "text"
    return "other"


def _extract_reel_urls(msg: dict) -> list[str]:
    """Extract Instagram reel/post URLs from a message."""
    urls: list[str] = []

    # Check share link
    share_link = msg.get("share", {}).get("link", "")
    if REEL_URL_PATTERN.search(share_link):
        urls.append(share_link)

    # Check message content for URLs
    content = msg.get("content", "")
    urls.extend(match.group(0) for match in REEL_URL_PATTERN.finditer(content))

    return list(dict.fromkeys(urls))  # deduplicate preserving order


def find_group_chats(zip_path: str) -> list[str]:
    """List all group chat directories in the ZIP."""
    chats: list[str] = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if not _is_safe_path(name):
                continue
            if name.startswith(MESSAGES_INBOX_PATH) and name.endswith("message_1.json"):
                chat_dir = str(PurePosixPath(name).parent)
                chats.append(chat_dir)

    return chats


def parse_chat_from_zip(zip_path: str, chat_dir: str | None = None) -> ParsedChat:
    """Parse a group chat from an Instagram data export ZIP.

    Args:
        zip_path: Path to the Instagram data export ZIP file.
        chat_dir: Specific chat directory within the ZIP. If None, uses the
                  largest chat (most messages).

    Returns:
        ParsedChat with all messages and extracted reel URLs.

    Raises:
        ValueError: If no valid chat is found in the ZIP.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        if chat_dir is None:
            chats = find_group_chats(zip_path)
            if not chats:
                raise ValueError("No Instagram group chats found in this export")
            chat_dir = chats[0]  # Default to first; we'll pick largest below

        # Find all message_N.json files in this chat
        message_files = sorted(
            name
            for name in zf.namelist()
            if (
                _is_safe_path(name)
                and name.startswith(chat_dir)
                and name.endswith(".json")
                and "message_" in name
            )
        )

        if not message_files:
            raise ValueError(f"No message files found in {chat_dir}")

        all_messages: list[ParsedMessage] = []
        all_reel_urls: list[str] = []
        title = ""
        participants: list[str] = []

        for msg_file in message_files:
            raw = zf.read(msg_file)
            data = json.loads(raw)

            if not title and "title" in data:
                title = _decode_instagram_text(data["title"])

            if not participants and "participants" in data:
                participants = [
                    _decode_instagram_text(p.get("name", "Unknown"))
                    for p in data["participants"]
                ]

            for msg in data.get("messages", []):
                content = _decode_instagram_text(msg.get("content", ""))
                sender = _decode_instagram_text(msg.get("sender_name", "Unknown"))
                msg_type = _classify_message(msg)
                timestamp_ms = msg.get("timestamp_ms", 0)

                all_messages.append(
                    ParsedMessage(
                        sender_name=sender,
                        content=content,
                        timestamp_ms=timestamp_ms,
                        message_type=msg_type,
                        raw_json=msg,
                    )
                )

                all_reel_urls.extend(_extract_reel_urls(msg))

    # Deduplicate reel URLs
    unique_reel_urls = list(dict.fromkeys(all_reel_urls))

    # Sort messages by timestamp (oldest first)
    sorted_messages = sorted(all_messages, key=lambda m: m.timestamp_ms)

    return ParsedChat(
        title=title,
        participants=participants,
        messages=sorted_messages,
        reel_urls=unique_reel_urls,
    )
