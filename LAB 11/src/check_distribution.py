"""Распределение документов по шардам и план запросов.
Запуск: python -m src.check_distribution
"""
from src.config import COLLECTION
from src.db import get_client, get_collection, is_mongos


def plan_stage(coll, flt):
    plan = coll.find(flt).explain()["queryPlanner"]["winningPlan"]
    shards = [s.get("shardName") for s in plan.get("shards", [])]
    return plan.get("stage"), shards


def main():
    client = get_client()
    coll = get_collection(client)
    if not is_mongos(client):
        print("Не mongos: шардирования нет. Всего документов:", coll.count_documents({}))
        return
    stats = client[coll.database.name].command("collStats", COLLECTION)
    counts = {name: s["count"] for name, s in stats.get("shards", {}).items()}
    print("Документы по шардам:", counts)
    if counts:
        v = list(counts.values())
        print(f"max/mean = {max(v) / (sum(v) / len(v)):.2f}",
              f"max/min = {max(v) / min(v):.2f}" if min(v) else "")
    for label, flt in [("AP-01 accountId=1001", {"accountId": 1001}),
                       ("AP-03 branchId=0", {"branchId": 0})]:
        stage, shards = plan_stage(coll, flt)
        print(f"{label}: stage={stage}, shards={shards}")
    print("SINGLE_SHARD = targeted, SHARD_MERGE = scatter-gather")


if __name__ == "__main__":
    main()
