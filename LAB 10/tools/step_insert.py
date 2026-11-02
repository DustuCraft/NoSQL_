"""Step 3: create collection `publications`, unique index, insert 21 synthetic docs
with writeConcern {w:"majority", wtimeout:5000}, then record the control set."""
import hashlib
import json
import os
import sys

import minimongo as m

DB = "university_lab10"
COLL = "publications"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts")
os.makedirs(OUT, exist_ok=True)

ITYPES = ["post", "photo", "video", "repost"]
TOPICS = [
    "Итоги студенческой конференции", "Новый курс по базам данных",
    "Фотоотчёт с хакатона", "Запись вебинара по MongoDB",
    "Анонс лабораторной недели", "Подборка задач по алгоритмам",
    "Интервью с выпускником", "Итоги спортивного турнира",
    "Обзор нового корпуса", "Статья о репликации данных",
    "Видео с защиты проектов", "Советы по подготовке к экзамену",
    "Репортаж с дня открытых дверей", "Новости научного кружка",
    "Гайд по резервному копированию", "Фото с выездной практики",
    "Заметка о стажировках", "Разбор ошибок в курсовых",
    "Календарь мероприятий на семестр", "Итоги конкурса проектов",
    "Памятка по академической честности",
]
AUTHORS = ["u-1001", "u-1002", "u-1003", "u-1004", "u-1005", "u-1006", "u-1007"]


def content_hash(doc):
    raw = "|".join([
        doc["pubId"], doc["authorId"], doc["type"], doc["text"],
        str(doc["likes"]), doc["createdAt"],
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_docs():
    docs = []
    for i in range(1, 22):
        doc = {
            "pubId": "PUB-%04d" % i,
            "authorId": AUTHORS[(i - 1) % len(AUTHORS)],
            "type": ITYPES[(i - 1) % len(ITYPES)],
            "text": "%s (синтетическая запись №%d)" % (TOPICS[i - 1], i),
            "tags": ["lab10", "synthetic", "%s-type" % ITYPES[(i - 1) % len(ITYPES)]],
            "createdAt": "2026-11-02T%02d:%02d:00Z" % (9 + (i - 1) // 4, (i * 7) % 60),
            "likes": 10 * i,
            "comments": i % 5,
            "visibility": "public",
            "status": "published",
            "schemaVersion": 1,
            "rev": 1,
        }
        doc["contentHash"] = content_hash(doc)
        doc["_id"] = m.ObjectId()
        docs.append(doc)
    return docs


def main():
    docs = build_docs()
    print('mongosh --port 27101')
    print('use %s' % DB)
    print('db.%s.createIndex({pubId: 1}, {unique: true, name: "ux_pubId"})' % COLL)
    print('db.%s.insertMany([... %d docs ...], '
          '{writeConcern: {w: "majority", wtimeout: 5000}})' % (COLL, len(docs)))
    print()

    with m.Client(port=27101) as c:
        idx = c.command(DB, {
            "createIndexes": COLL,
            "indexes": [{"key": {"pubId": 1}, "name": "ux_pubId", "unique": True}],
            "writeConcern": {"w": "majority", "wtimeout": 5000},
        })
        print("createIndexes: ok=%s, created=%s" % (idx.get("ok"), idx.get("numIndexesAfter")))

        res = c.command(DB, {
            "insert": COLL,
            "documents": docs,
            "ordered": True,
            "writeConcern": {"w": "majority", "wtimeout": 5000},
        })
        print("insertMany: ok=%s, inserted=%d, writeErrors=%s, writeConcernError=%s" % (
            res.get("ok"), len(res.get("insertedIds", {})),
            res.get("writeErrors"), res.get("writeConcernError")))

        cnt = c.command(DB, {"count": COLL})
        print("countDocuments:", cnt.get("n"))

        found = c.command(DB, {
            "find": COLL,
            "filter": {},
            "projection": {"_id": 0, "pubId": 1, "authorId": 1, "type": 1,
                           "likes": 1, "contentHash": 1},
            "sort": {"pubId": 1},
            "limit": 25,
        })
        batch = found["cursor"]["firstBatch"]
        print("sample:", json.dumps(batch[:3], ensure_ascii=False, indent=2))

        status = c.command("admin", {"replSetGetStatus": 1})
        members = [{"name": x["name"], "state": x["stateStr"], "health": x.get("health")}
                   for x in status["members"]]
        print("roles:", members)

    control = {
        "db": DB,
        "collection": COLL,
        "documents": len(docs),
        "pubIds": [d["pubId"] for d in docs],
        "contentHashes": {d["pubId"]: d["contentHash"] for d in docs},
        "totalChecksum": hashlib.sha256(
            "".join(d["pubId"] + d["contentHash"] for d in docs).encode()).hexdigest(),
        "lastConfirmedPubId": max(d["pubId"] for d in docs),
    }
    with open(os.path.join(OUT, "control_before.json"), "w", encoding="utf-8") as f:
        json.dump(control, f, ensure_ascii=False, indent=2)
    print("\nCONTROL totalChecksum:", control["totalChecksum"])
    print("CONTROL lastConfirmedPubId:", control["lastConfirmedPubId"])


if __name__ == "__main__":
    main()
