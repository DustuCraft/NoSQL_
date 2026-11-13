"""Заполнение коллекции и настройка шардирования.
Запуск: python -m src.load_to_mongo [--drop]
"""
import argparse
from src.config import DB_NAME, COLLECTION
from src.db import get_client, is_mongos
from src.data_gen import make_rows, to_mongo_docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drop", action="store_true", help="удалить коллекцию перед загрузкой")
    args = ap.parse_args()

    client = get_client()
    db = client[DB_NAME]
    if args.drop:
        db.drop_collection(COLLECTION)
    coll = db[COLLECTION]

    if is_mongos(client):
        coll.create_index([("accountId", "hashed")])
        try:
            client.admin.command("enableSharding", DB_NAME)
        except Exception as e:
            print("enableSharding:", e)
        try:
            client.admin.command("shardCollection", f"{DB_NAME}.{COLLECTION}",
                                 key={"accountId": "hashed"})
            print("shardCollection: accountId hashed — OK")
        except Exception as e:
            print("shardCollection:", e)
    else:
        print("ВНИМАНИЕ: подключение не через mongos — коллекция НЕ шардируется.")

    docs = to_mongo_docs(make_rows())
    for i in range(0, len(docs), 2000):
        coll.insert_many(docs[i:i + 2000])
    print(f"Вставлено {len(docs)} документов в {DB_NAME}.{COLLECTION}")


if __name__ == "__main__":
    main()
