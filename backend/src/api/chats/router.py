"""Endpoint to list group chats found in an uploaded ZIP."""

import json
import zipfile
from pathlib import PurePosixPath

from fastapi import APIRouter, HTTPException

from src.pipeline.utils.instagram_parser import MESSAGES_INBOX_PATH, _is_safe_path

router = APIRouter()


@router.get("")
async def list_chats(file_url: str) -> list[dict]:
    """List all chats found in an uploaded Instagram export ZIP.

    Returns chat name, participant count, and message count for each.
    """
    try:
        chats: list[dict] = []

        with zipfile.ZipFile(file_url, "r") as zf:
            # Find all message_1.json files (one per chat)
            chat_dirs: list[str] = []
            for name in zf.namelist():
                if not _is_safe_path(name):
                    continue
                if name.startswith(MESSAGES_INBOX_PATH) and name.endswith("message_1.json"):
                    chat_dirs.append(str(PurePosixPath(name).parent))

            for chat_dir in chat_dirs:
                # Read first message file to get metadata
                first_file = f"{chat_dir}/message_1.json"
                try:
                    raw = zf.read(first_file)
                    data = json.loads(raw)
                except (KeyError, json.JSONDecodeError):
                    continue

                title = data.get("title", "Unknown Chat")
                # Decode Instagram's weird encoding
                try:
                    title = title.encode("latin-1").decode("utf-8")
                except (UnicodeDecodeError, UnicodeEncodeError):
                    pass

                participants = data.get("participants", [])
                message_count = len(data.get("messages", []))

                # Count messages across all message_N.json files
                all_msg_files = [
                    n for n in zf.namelist()
                    if n.startswith(chat_dir) and n.endswith(".json") and "message_" in n
                ]
                if len(all_msg_files) > 1:
                    for msg_file in all_msg_files[1:]:
                        try:
                            extra = json.loads(zf.read(msg_file))
                            message_count += len(extra.get("messages", []))
                        except (KeyError, json.JSONDecodeError):
                            pass

                chats.append({
                    "chat_dir": chat_dir,
                    "title": title,
                    "participant_count": len(participants),
                    "participants": [
                        p.get("name", "Unknown") for p in participants[:10]
                    ],
                    "message_count": message_count,
                })

        # Sort by message count descending (biggest chats first)
        chats.sort(key=lambda c: c["message_count"], reverse=True)
        return chats

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Uploaded file not found")
