"""Общие настройки. Вариант 08: Кафе, фильтр restaurantId + categoryId."""
import os
import random
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "nosql_lab12")
COLLECTION = os.getenv("COLLECTION", "menu_items")
SEED = int(os.getenv("SEED", "42"))

INDEX_KEYS = [("restaurantId", ASCENDING), ("categoryId", ASCENDING)]
INDEX_NAME = "lab12_restaurant_category"

N_RESTAURANTS = 20
N_CATEGORIES = 8

# Запрос для explain (AP-01)
EXPLAIN_QUERY = {"restaurantId": 10, "categoryId": 5}


def get_client() -> MongoClient:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command("ping")  # упадёт сразу, если MongoDB не запущена
    return client


def get_collection():
    return get_client()[DB_NAME][COLLECTION]


def make_queries(n: int = 200):
    """Фиксированный (по seed) набор запросов: одинаков для обоих режимов."""
    rng = random.Random(SEED)
    return [{"restaurantId": rng.randint(1, N_RESTAURANTS),
             "categoryId": rng.randint(1, N_CATEGORIES)} for _ in range(n)]
