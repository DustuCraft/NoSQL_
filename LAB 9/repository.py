"""Доступ к MongoDB. Слой ничего не знает про HTTP: возвращает данные
или поднимает доменные исключения."""
import logging
import re
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError, PyMongoError

from config import Settings

log = logging.getLogger("repository")


class RepositoryError(Exception):
    """Базовая ошибка repository."""


class NotFoundError(RepositoryError):
    pass


class DuplicateError(RepositoryError):
    pass


class StorageUnavailableError(RepositoryError):
    pass


def _to_dict(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


def _oid(item_id: str) -> ObjectId:
    try:
        return ObjectId(item_id)
    except (InvalidId, TypeError):
        raise NotFoundError(item_id)


class ItemRepository:
    def __init__(self, settings: Settings):
        self._client = MongoClient(
            settings.mongo_uri,
            serverSelectionTimeoutMS=settings.timeout_ms,
            connectTimeoutMS=settings.timeout_ms,
            socketTimeoutMS=settings.timeout_ms,
        )
        self._col = self._client[settings.db_name][settings.collection]
        self._indexed = False

    # --- служебное ---------------------------------------------------
    def _run(self, func, *args, **kwargs):
        """Выполняет операцию драйвера и переводит его ошибки в доменные."""
        try:
            if not self._indexed:
                self._col.create_index([("code", ASCENDING)], unique=True)
                self._indexed = True
            return func(*args, **kwargs)
        except DuplicateKeyError as exc:
            log.warning("Duplicate key: %s", exc)
            raise DuplicateError("duplicate") from exc
        except ConnectionFailure as exc:  # включает ServerSelectionTimeoutError
            log.error("Storage unavailable: %s", exc)
            raise StorageUnavailableError("storage unavailable") from exc
        except PyMongoError as exc:
            log.exception("Driver error")
            raise RepositoryError("storage error") from exc

    def close(self) -> None:
        self._client.close()

    # --- операции ----------------------------------------------------
    def create(self, data: dict) -> dict:
        def op():
            doc = dict(data)
            res = self._col.insert_one(doc)
            doc["_id"] = res.inserted_id
            return _to_dict(doc)
        return self._run(op)

    def get(self, item_id: str) -> dict:
        oid = _oid(item_id)
        doc = self._run(self._col.find_one, {"_id": oid})
        if doc is None:
            raise NotFoundError(item_id)
        return _to_dict(doc)

    def list(self, name_filter: Optional[str] = None, skip: int = 0, limit: int = 50) -> list[dict]:
        query = {}
        if name_filter:
            query["name"] = {"$regex": re.escape(name_filter), "$options": "i"}

        def op():
            return [_to_dict(d) for d in self._col.find(query).sort("_id", ASCENDING).skip(skip).limit(limit)]
        return self._run(op)

    def update(self, item_id: str, changes: dict) -> dict:
        oid = _oid(item_id)
        if changes:
            res = self._run(self._col.update_one, {"_id": oid}, {"$set": changes})
            if res.matched_count == 0:
                raise NotFoundError(item_id)
        return self.get(item_id)

    def delete(self, item_id: str) -> None:
        oid = _oid(item_id)
        res = self._run(self._col.delete_one, {"_id": oid})
        if res.deleted_count == 0:
            raise NotFoundError(item_id)
