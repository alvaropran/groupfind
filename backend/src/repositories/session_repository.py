from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from src.models.session import SessionModel
from src.repositories.base import BaseRepository


class SessionRepository(BaseRepository[SessionModel]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, SessionModel)

    def create(self, file_url: str) -> SessionModel:
        return self.create_from_dict({"file_url": file_url})

    def delete_expired(self) -> int:
        now = datetime.now(timezone.utc)
        result = self._db.execute(
            delete(SessionModel).where(SessionModel.expires_at < now)
        )
        self._db.commit()
        return result.rowcount  # type: ignore[return-value]
