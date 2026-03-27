import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

UPLOAD_DIR = Path(os.environ.get("GROUPFIND_UPLOAD_DIR", "/tmp/groupfind_uploads"))

router = APIRouter()


@router.post("")
async def upload_file(file: UploadFile) -> dict[str, str]:
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a .zip archive")

    if file.size and file.size > 500 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File must be under 500MB")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    file_path = UPLOAD_DIR / f"{file_id}.zip"

    content = await file.read()
    file_path.write_bytes(content)

    return {"file_url": str(file_path)}
