"""Конфигурация приложения. Все секреты читаются из окружения / .env."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    db_name: str
    collection: str
    timeout_ms: int


def get_settings() -> Settings:
    uri = os.getenv("MONGO_URI")
    if not uri:
        raise RuntimeError("Не задана переменная окружения MONGO_URI (см. .env.example)")
    return Settings(
        mongo_uri=uri,
        db_name=os.getenv("MONGO_DB_NAME") or "lab9",
        collection=os.getenv("MONGO_COLLECTION") or "items",
        timeout_ms=int(os.getenv("MONGO_TIMEOUT_MS") or 2000),
    )
