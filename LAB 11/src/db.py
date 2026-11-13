from pymongo import MongoClient
from src.config import MONGO_URI, DB_NAME, COLLECTION


def get_client() -> MongoClient:
    return MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)


def is_mongos(client: MongoClient) -> bool:
    """True, если подключение идёт через mongos (шардированный кластер)."""
    return client.admin.command("hello").get("msg") == "isdbgrid"


def get_collection(client: MongoClient | None = None):
    client = client or get_client()
    return client[DB_NAME][COLLECTION]
