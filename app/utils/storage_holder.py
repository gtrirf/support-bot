from typing import Optional
from aiogram.fsm.storage.base import BaseStorage

_storage: Optional[BaseStorage] = None


def set_storage(storage: BaseStorage) -> None:
    global _storage
    _storage = storage


def get_storage() -> BaseStorage:
    if _storage is None:
        raise RuntimeError("Storage not set. Call set_storage() first.")
    return _storage
