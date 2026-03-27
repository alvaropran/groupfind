from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, db: Session, model_class: type[T]) -> None:
        self._db = db
        self._model_class = model_class

    def get_by_id(self, entity_id: UUID) -> T | None:
        return self._db.get(self._model_class, entity_id)

    def create_from_dict(self, data: dict) -> T:
        instance = self._model_class(**data)
        self._db.add(instance)
        self._db.commit()
        self._db.refresh(instance)
        return instance

    def delete(self, entity_id: UUID) -> bool:
        instance = self.get_by_id(entity_id)
        if instance is None:
            return False
        self._db.delete(instance)
        self._db.commit()
        return True
