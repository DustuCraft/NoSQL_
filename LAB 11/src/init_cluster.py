"""Инициализация учебного шардированного кластера из docker-compose.yml.
Запуск: python -m src.init_cluster
"""
import time
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from src.config import MONGO_URI

REPLICA_SETS = [  # (порт на хосте, имя replica set, адрес внутри docker-сети, configsvr)
    (27019, "cfgrs", "cfg1:27019", True),
    (27021, "shard1rs", "shard1:27018", False),
    (27022, "shard2rs", "shard2:27018", False),
    (27023, "shard3rs", "shard3:27018", False),
]


def init_rs(port, rs_name, member, configsvr):
    c = MongoClient("localhost", port, directConnection=True, serverSelectionTimeoutMS=30000)
    cfg = {"_id": rs_name, "members": [{"_id": 0, "host": member}]}
    if configsvr:
        cfg["configsvr"] = True
    try:
        c.admin.command("replSetInitiate", cfg)
        print(f"[ok] {rs_name} инициализирован")
    except OperationFailure as e:
        print(f"[skip] {rs_name}: {e.details.get('errmsg', e)}")
    for _ in range(60):
        if c.admin.command("hello").get("isWritablePrimary"):
            return
        time.sleep(1)
    raise RuntimeError(f"{rs_name}: primary не появился")


def main():
    for args in REPLICA_SETS:
        init_rs(*args)
    mongos = MongoClient(MONGO_URI, serverSelectionTimeoutMS=60000)
    for _ in range(60):  # mongos может перезапускаться, пока config server не готов
        try:
            mongos.admin.command("ping")
            break
        except Exception:
            time.sleep(2)
    for _, rs_name, member, configsvr in REPLICA_SETS:
        if configsvr:
            continue
        try:
            mongos.admin.command("addShard", f"{rs_name}/{member}")
            print(f"[ok] addShard {rs_name}")
        except OperationFailure as e:
            print(f"[warn] addShard {rs_name}: {e}")
    print("Готово. Проверьте: sh.status() в mongosh или python -m src.check_distribution")


if __name__ == "__main__":
    main()
