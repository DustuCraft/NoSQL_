"""Генерация синтетических данных. Запуск: python seed.py --count 50000"""
import argparse
import json
import os
import platform
import random
import sys

import pymongo

import config


def make_docs(count: int, seed: int):
    rng = random.Random(seed)
    return [{
        "restaurantId": rng.randint(1, config.N_RESTAURANTS),
        "categoryId": rng.randint(1, config.N_CATEGORIES),
        "title": f"Dish {i}",
        "price": round(rng.uniform(3, 25), 2),
        "calories": rng.randint(80, 1200),
        "chefId": rng.randint(1, 150),
    } for i in range(count)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=50000, help="не менее 5000")
    args = ap.parse_args()
    if args.count < 5000:
        sys.exit("Нужно не менее 5000 документов")

    client = config.get_client()
    coll = client[config.DB_NAME][config.COLLECTION]
    coll.drop()  # только учебная коллекция!
    coll.insert_many(make_docs(args.count, config.SEED), ordered=False)

    info = {
        "mongodb_version": client.server_info()["version"],
        "pymongo_version": pymongo.version,
        "python_version": platform.python_version(),
        "os": platform.platform(),
        "seed": config.SEED,
        "documents": coll.count_documents({}),
        "db": config.DB_NAME,
        "collection": config.COLLECTION,
    }
    os.makedirs("results", exist_ok=True)
    with open("results/env_info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()