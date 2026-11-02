"""Lab 10 (Variant 9, social network / publications) -- full reproducible run.

Starts a 3-node MongoDB replica set on 127.0.0.1:27101-27103, loads 21 synthetic
"publications" with writeConcern majority, performs a controlled primary shutdown,
measures failover time, restarts the node, then does a logical backup and restore
into a separate database and compares the control set.

All console output is duplicated into artifacts/transcript.txt.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import datetime as dt

import minimongo as m

MONGOD = r"A:\mongo\bin\mongod.exe"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(BASE, "artifacts")
PORTS = [27101, 27102, 27103]
DB, COLL = "university_lab10", "publications"
RESTORE_DB = "university_restore10"
CREATE_NO_WINDOW = 0x08000000

TRANSCRIPT = []
LOGF = None
DONE = False


def log(msg=""):
    print(msg, flush=True)
    TRANSCRIPT.append(msg)
    if LOGF:
        LOGF.write(msg + "\n")
        LOGF.flush()


def rule(title):
    log("")
    log("=" * 78)
    log(title)
    log("=" * 78)


def now_local():
    return dt.datetime.now().astimezone()


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def iso_local(t=None):
    return (t or now_local()).isoformat(timespec="milliseconds")


def hello(port, timeout=1.0):
    try:
        with m.Client(port=port, timeout=timeout) as c:
            return c.command("admin", {"hello": 1})
    except Exception:
        return None


def wait_port(port, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        if hello(port, 0.5):
            return True
        time.sleep(0.15)
    return False


def start_node(idx):
    port = 27100 + idx
    dbpath = os.path.join(BASE, "rs%d" % idx)
    logfile = os.path.join(BASE, "logs", "rs%d.log" % idx)
    p = subprocess.Popen(
        [MONGOD, "--replSet", "rsLab10", "--port", str(port),
         "--dbpath", dbpath, "--bind_ip", "127.0.0.1",
         "--logpath", logfile, "--logappend"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW, close_fds=True,
    )
    log("  mongod --replSet rsLab10 --port %d --dbpath %s --bind_ip 127.0.0.1  (pid %d)"
        % (port, dbpath, p.pid))
    return p


def stop_node(port, timeout=25):
    try:
        with m.Client(port=port, timeout=5) as c:
            c.command("admin", {"shutdown": 1, "force": True, "timeoutSecs": 5}, check=False)
    except Exception:
        pass
    end = time.time() + timeout
    while time.time() < end:
        if hello(port, 0.3) is None:
            return True
        time.sleep(0.1)
    return False


def find_primary(exclude=()):
    for p in PORTS:
        if p in exclude:
            continue
        h = hello(p, 0.5)
        if h and h.get("isWritablePrimary"):
            return p, h
    return None, None


def wait_primary(exclude=(), timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        p, h = find_primary(exclude)
        if p:
            return p, h
        time.sleep(0.1)
    return None, None


def status(port):
    with m.Client(port=port, timeout=10) as c:
        return c.command("admin", {"replSetGetStatus": 1})


def roles_from(st):
    return [{"name": x["name"], "state": x["stateStr"], "health": x.get("health")}
            for x in st.get("members", [])]


def log_event(port, needle):
    """Return first UTC timestamp in mongod JSON log containing needle."""
    path = os.path.join(BASE, "logs", "rs%d.log" % (port - 27100))
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if needle in line:
                try:
                    rec = json.loads(line)
                    return rec["t"]["$date"]
                except Exception:
                    continue
    return None


def read_all(port, db=DB, coll=COLL):
    docs = []
    with m.Client(port=port, timeout=15) as c:
        cur = c.command(db, {"find": coll, "filter": {}, "sort": {"pubId": 1},
                             "batchSize": 100})
        docs += cur["cursor"]["firstBatch"]
        cid = cur["cursor"].get("id")
        while cid:
            nxt = c.command(db, {"getMore": cid, "collection": coll})
            docs += nxt["cursor"]["nextBatch"]
            cid = nxt["cursor"]["id"]
    return docs


def checksum(docs):
    return hashlib.sha256("".join(
        d.get("pubId", "") + d.get("contentHash", "") for d in docs).encode()).hexdigest()


def control_docs():
    itypes = ["post", "photo", "video", "repost"]
    topics = [
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
    authors = ["u-1001", "u-1002", "u-1003", "u-1004", "u-1005", "u-1006", "u-1007"]
    docs = []
    for i in range(1, 22):
        d = {
            "pubId": "PUB-%04d" % i,
            "authorId": authors[(i - 1) % len(authors)],
            "type": itypes[(i - 1) % len(itypes)],
            "text": "%s (синтетическая запись №%d)" % (topics[i - 1], i),
            "tags": ["lab10", "synthetic", "%s-type" % itypes[(i - 1) % len(itypes)]],
            "createdAt": "2026-11-02T%02d:%02d:00Z" % (9 + (i - 1) // 4, (i * 7) % 60),
            "likes": 10 * i,
            "comments": i % 5,
            "visibility": "public",
            "status": "published",
            "schemaVersion": 1,
            "rev": 1,
        }
        raw = "|".join([d["pubId"], d["authorId"], d["type"], d["text"],
                        str(d["likes"]), d["createdAt"]])
        d["contentHash"] = hashlib.sha256(raw.encode()).hexdigest()[:16]
        docs.append(d)
    return docs


def main():
    global LOGF, DONE
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    os.makedirs(ART, exist_ok=True)
    os.makedirs(os.path.join(BASE, "logs"), exist_ok=True)
    LOGF = open(os.path.join(ART, "transcript.txt"), "w", encoding="utf-8-sig")

    # ---------------- environment
    rule("ЛАБОРАТОРНАЯ РАБОТА №10. ВАРИАНТ 9. СОЦИАЛЬНАЯ СЕТЬ / КОЛЛЕКЦИЯ PUBLICATIONS")
    ver = subprocess.run([MONGOD, "--version"], capture_output=True, text=True).stdout
    ver_line = [l for l in ver.splitlines() if l.startswith("db version")][0]
    log("Дата запуска (локальное время): " + iso_local())
    log("MongoDB: %s" % ver_line)
    log("ОС: Windows; узлы: 127.0.0.1:27101, 127.0.0.1:27102, 127.0.0.1:27103")
    log("Каталоги данных: %s\\rs1 .. rs3" % BASE)

    # ---------------- clean start
    rule("ШАГ 1. Подготовка каталогов и запуск трёх экземпляров mongod")
    pause = os.path.join(BASE, "logs", "watchdog.pause")
    try:
        open(pause, "w").close()
        log("  watchdog поставлен на паузу (logs\\watchdog.pause)")
    except Exception:
        pass
    # stop the persistent stand watchdog first, otherwise it restarts nodes mid-run
    wd = os.path.join(BASE, "logs", "watchdog.pid")
    had_watchdog = os.path.exists(wd)
    log("  постоянный стенд: %s" % ("watchdog найден, работаем через паузу" if had_watchdog
                                    else "watchdog не запущен"))
    for i in (1, 2, 3):
        stop_node(27100 + i, timeout=15)
    # wait until every port is really free (old process may still hold dbpath)
    for i in (1, 2, 3):
        end = time.time() + 30
        while hello(27100 + i, 0.3) is not None and time.time() < end:
            time.sleep(0.2)
    time.sleep(6)  # mongod closes the port before it exits and releases dbpath/logs
    for i in (1, 2, 3):
        dbpath = os.path.join(BASE, "rs%d" % i)
        for attempt in range(10):
            if not os.path.exists(dbpath):
                break
            try:
                shutil.rmtree(dbpath)
                break
            except PermissionError:
                time.sleep(1.0)
        os.makedirs(dbpath, exist_ok=True)
        logpath = os.path.join(BASE, "logs", "rs%d.log" % i)
        try:
            open(logpath, "w").close()
        except PermissionError:
            # the file is still held by a dying process -- just append instead
            log("  лог %s занят, продолжаю писать в него" % logpath)
    log("Каталоги rs1, rs2, rs3 созданы заново; старые процессы остановлены.")

    procs = {}
    for i in (1, 2, 3):
        procs[i] = start_node(i)
    for i in (1, 2, 3):
        ok = wait_port(27100 + i, 60)
        log("  узел %d:%d %s" % (127, 27100 + i, "отвечает" if ok else "НЕ отвечает"))
        if not ok:
            raise SystemExit("node did not start")

    # ---------------- initiate
    rule("ШАГ 2. Инициализация Replica Set rsLab10")
    cfg = {"_id": "rsLab10", "members": [
        {"_id": 0, "host": "127.0.0.1:27101"},
        {"_id": 1, "host": "127.0.0.1:27102"},
        {"_id": 2, "host": "127.0.0.1:27103"}]}
    log('rs.initiate({_id:"rsLab10", members:[{_id:0,host:"127.0.0.1:27101"},'
        '{_id:1,host:"127.0.0.1:27102"},{_id:2,host:"127.0.0.1:27103"}]})')
    with m.Client(port=27101) as c:
        r = c.command("admin", {"replSetInitiate": cfg})
    log("  ok=%s" % r.get("ok"))

    prim, ph = wait_primary(timeout=90)
    if not prim:
        raise SystemExit("no primary elected")
    st = status(prim)
    log("")
    log('rs.status()  ->  набор "%s", term=%s' % (st.get("set"), st.get("term")))
    for row in roles_from(st):
        log("  %-22s %-10s health=%s" % (row["name"], row["state"], row["health"]))
    log("PRIMARY: 127.0.0.1:%d" % prim)
    init_rec = {"set": st.get("set"), "term": st.get("term"), "roles": roles_from(st),
                "primary_port": prim}

    # ---------------- data
    rule("ШАГ 3. Тестовые данные: база university_lab10, коллекция publications")
    docs = control_docs()
    with m.Client(port=prim, timeout=20) as c:
        c.command(DB, {"dropDatabase": 1, "writeConcern": {"w": "majority"}})
    log("dropDatabase university_lab10 -> чистая база")
    log("db.publications.createIndex({pubId: 1}, {unique: true, name: \"ux_pubId\"})")
    with m.Client(port=prim, timeout=20) as c:
        idx = c.command(DB, {"createIndexes": COLL, "indexes": [
            {"key": {"pubId": 1}, "name": "ux_pubId", "unique": True}],
            "writeConcern": {"w": "majority", "wtimeout": 5000}})
        log("  createIndexes: ok=%s, indexes=%s" % (idx.get("ok"), idx.get("numIndexesAfter")))

        log('db.publications.insertMany([...], {writeConcern:{w:"majority", wtimeout:5000}})')
        res = c.command(DB, {"insert": COLL, "documents": docs, "ordered": True,
                             "writeConcern": {"w": "majority", "wtimeout": 5000}})
        log("  insertMany: ok=%s, n=%s, writeErrors=%s, writeConcernError=%s"
            % (res.get("ok"), res.get("n"), res.get("writeErrors"), res.get("writeConcernError")))
        cnt = c.command(DB, {"count": COLL})
        log("  db.publications.countDocuments(): %s" % cnt.get("n"))

    # replication check on secondaries (wait until they catch up, show lag)
    log("")
    log("Проверка репликации чтением со secondary (readPreference=secondaryPreferred):")
    for p in PORTS:
        if p == prim:
            continue
        t_start = time.time()
        got = 0
        while time.time() - t_start < 20:
            with m.Client(port=p, timeout=10) as c:
                rr = c.command(DB, {"find": COLL, "filter": {},
                                    "$readPreference": {"mode": "secondaryPreferred"}})
            got = len(rr["cursor"]["firstBatch"])
            if got >= len(docs):
                break
            time.sleep(0.3)
        log("  порт %d: получено %d документов (догнал за %.2f c)"
            % (p, got, time.time() - t_start))

    before = read_all(prim)
    csum_before = checksum(before)
    control = {
        "documents": len(before),
        "pubIds": [d["pubId"] for d in before],
        "contentHashes": {d["pubId"]: d["contentHash"] for d in before},
        "checksum": csum_before,
        "lastConfirmedPubId": max(d["pubId"] for d in before),
    }
    with open(os.path.join(ART, "control_before.json"), "w", encoding="utf-8") as f:
        json.dump(control, f, ensure_ascii=False, indent=2)
    log("")
    log("Контрольный набор: %d документов, checksum=%s" % (len(before), csum_before))
    log("Последний подтверждённый pubId: %s" % control["lastConfirmedPubId"])

    # ---------------- failover
    rule("ШАГ 4. Контролируемое моделирование отказа PRIMARY")
    risky = {"pubId": "PUB-0022", "authorId": "u-1007", "type": "post",
             "text": "Запись с w:1 непосредственно перед отказом primary",
             "createdAt": "2026-11-02T12:00:00Z", "likes": 0, "comments": 0,
             "visibility": "public", "status": "published", "schemaVersion": 1, "rev": 1}
    try:
        with m.Client(port=prim, timeout=5) as c:
            rr = c.command(DB, {"insert": COLL, "documents": [risky],
                                "writeConcern": {"w": 1, "wtimeout": 2000}})
        risky_ok = rr.get("ok") == 1
    except Exception as e:
        risky_ok = False
        log("  ошибка записи PUB-0022: %s" % e)
    log("Крайняя запись PUB-0022 с writeConcern {w:1}: %s"
        % ("подтверждена" if risky_ok else "не подтверждена"))

    t0_perf = time.perf_counter()
    t0_wall = iso_local()
    t0_utc = now_utc()
    log('Останавливаем процесс PRIMARY 127.0.0.1:%d (штатная команда shutdown, аналог Ctrl+C)' % prim)

    def _shutdown():
        try:
            with m.Client(port=prim, timeout=15) as c:
                c.command("admin", {"shutdown": 1, "force": True, "timeoutSecs": 5},
                          check=False)
        except Exception as e:
            log("  соединение закрыто: %s" % type(e).__name__)

    threading.Thread(target=_shutdown, daemon=True).start()

    down_t = None
    while time.perf_counter() - t0_perf < 30:
        if hello(prim, 0.4) is None:
            down_t = round(time.perf_counter() - t0_perf, 3)
            break
        time.sleep(0.05)
    log("  t0 = %s  (узел перестал отвечать через %s c)" % (t0_wall, down_t))

    # write attempt in the outage window
    write_error = None
    tmp_inserted = False
    for p in PORTS:
        if p == prim:
            continue
        try:
            with m.Client(port=p, timeout=2) as c:
                c.command(DB, {"insert": COLL, "documents": [
                    {"pubId": "PUB-TMP", "text": "запись в окне отказа"}],
                    "writeConcern": {"w": "majority", "wtimeout": 2000}})
            tmp_inserted = True
        except Exception as e:
            write_error = str(e)
            log("  попытка записи в окне отказа -> ошибка: %s" % write_error[:120])
            break

    new_prim, nh = wait_primary(exclude=(prim,), timeout=60)
    t1_perf = time.perf_counter()
    t1_wall = iso_local()
    if not new_prim:
        raise SystemExit("no new primary")
    rto = round(t1_perf - t0_perf, 3)
    log("  t1 = %s  новый PRIMARY: 127.0.0.1:%d" % (t1_wall, new_prim))
    log("  НАБЛЮДАЕМОЕ ВРЕМЯ ПЕРЕКЛЮЧЕНИЯ (t1 - t0) = %.3f c" % rto)

    if tmp_inserted:
        # the write succeeded during the window -- remove the marker to keep the control set clean
        with m.Client(port=new_prim, timeout=10) as c:
            c.command(DB, {"delete": COLL, "deletes": [
                {"q": {"pubId": "PUB-TMP"}, "limit": 1}],
                "writeConcern": {"w": "majority", "wtimeout": 5000}})
        log("  тестовая запись PUB-TMP удалена (в базу не входит)")

    st2 = status(new_prim)
    log("")
    log("rs.status() после выборов:")
    for row in roles_from(st2):
        log("  %-22s %-10s health=%s" % (row["name"], row["state"], row["health"]))

    after = read_all(new_prim)
    ctrl_ids = set(control["pubIds"])
    after_ctrl = [d for d in after if d["pubId"] in ctrl_ids]
    csum_after_ctrl = checksum(after_ctrl)
    log("")
    log("Проверка данных на новом primary:")
    log("  документов: %d (до отказа было %d)" % (len(after), len(before)))
    log("  документов контрольного набора: %d" % len(after_ctrl))
    log("  checksum контрольного набора после: %s" % csum_after_ctrl)
    log("  совпадение контрольного набора: %s" % ("ДА" if csum_after_ctrl == csum_before else "НЕТ"))
    log("  PUB-0022 (w:1) сохранилась: %s" % ("да" if any(d["pubId"] == "PUB-0022" for d in after) else "нет"))

    # log-based election timestamp of the new primary
    ev_t = log_event(new_prim, "Transition to primary complete")
    log("  метка в логе нового primary (Transition to primary complete): %s" % ev_t)

    fail = {
        "initial_primary": prim,
        "new_primary": new_prim,
        "t0_local": t0_wall,
        "t1_local": t1_wall,
        "t0_utc": t0_utc.isoformat(timespec="milliseconds"),
        "rto_seconds": rto,
        "down_detected_seconds": down_t,
        "documents_before": len(before),
        "documents_after": len(after),
        "control_docs_after": len(after_ctrl),
        "checksum_before": csum_before,
        "checksum_after": csum_after_ctrl,
        "control_match": csum_after_ctrl == csum_before,
        "risky_write_ok": risky_ok,
        "risky_survived": any(d["pubId"] == "PUB-0022" for d in after),
        "write_error_in_outage": write_error,
        "roles_after": roles_from(st2),
        "log_new_primary_election": ev_t,
    }
    with open(os.path.join(ART, "failover.json"), "w", encoding="utf-8") as f:
        json.dump(fail, f, ensure_ascii=False, indent=2)

    # ---------------- rejoin
    rule("ШАГ 5. Возврат остановленного узла в набор")
    log("Повторный запуск mongod с тем же dbpath, портом и replSet:")
    old_proc = procs.get(prim - 27100)
    if old_proc is not None:
        try:
            rc = old_proc.wait(timeout=120)
            log("  старый процесс завершился, exit code=%s (блокировка dbpath снята)" % rc)
        except subprocess.TimeoutExpired:
            old_proc.kill()
            old_proc.wait()
            log("  старый процесс не завершился за 120 c и был принудительно остановлен")
    time.sleep(1.0)
    procs[prim - 27100] = start_node(prim - 27100)
    ok = wait_port(prim, 60)
    log("  узел 127.0.0.1:%d снова отвечает: %s" % (prim, ok))
    if not ok:
        log("  ВНИМАНИЕ: mongod не поднялся; последние строки лога %s\\rs%d.log:"
            % (os.path.join(BASE, "logs"), prim - 27100))
        logfile = os.path.join(BASE, "logs", "rs%d.log" % (prim - 27100))
        try:
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                tail = f.readlines()[-5:]
            for line in tail:
                log("    " + line.strip()[:300])
        except Exception:
            pass

    rejoin = None
    end = time.time() + 90
    while time.time() < end:
        try:
            st3 = status(new_prim)
            me = [x for x in st3["members"] if x["name"].endswith(":%d" % prim)][0]
            if me["stateStr"] == "SECONDARY" and me.get("health") == 1:
                rejoin = {"state": me["stateStr"], "health": me["health"],
                          "optime": str(me.get("optimeDate"))}
                break
        except Exception:
            pass
        time.sleep(0.3)
    st3 = status(new_prim)
    log("  роли после возврата:")
    for row in roles_from(st3):
        log("    %-22s %-10s health=%s" % (row["name"], row["state"], row["health"]))
    if rejoin:
        log("  узел присоединился как SECONDARY; optime=%s" % rejoin["optime"])
        got = 0
        end = time.time() + 40
        while time.time() < end:
            try:
                with m.Client(port=prim, timeout=10) as c:
                    rr = c.command(DB, {"find": COLL, "filter": {},
                                        "$readPreference": {"mode": "secondaryPreferred"}})
                got = len(rr["cursor"]["firstBatch"])
                if got >= len(after):
                    break
            except Exception:
                pass
            time.sleep(0.5)
        log("  чтение с вернувшегося узла: %d документов" % got)
        rejoin["docs_read"] = got
    else:
        log("  ВНИМАНИЕ: узел не перешёл в SECONDARY за отведённое время")
        rejoin = {"state": "NOT_REJOINED", "docs_read": 0,
                  "note": "узел не поднялся или не присоединился"}

    rejoin["roles"] = roles_from(st3)
    rejoin["checksum_after_rejoin"] = checksum(read_all(new_prim))
    with open(os.path.join(ART, "rejoin.json"), "w", encoding="utf-8") as f:
        json.dump(rejoin, f, ensure_ascii=False, indent=2)

    # ---------------- backup
    rule("ШАГ 6. Резервное копирование и восстановление в отдельную базу")
    backup_dir = os.path.join(BASE, "backup_lab10", DB)
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)
    os.makedirs(backup_dir)
    dump = read_all(new_prim)
    with open(os.path.join(backup_dir, COLL + ".json"), "w", encoding="utf-8") as f:
        json.dump(m._to_jsonable(dump), f, ensure_ascii=False, indent=1)
    meta = {
        "created_local": iso_local(),
        "source": "mongodb://127.0.0.1:%d/?replicaSet=rsLab10" % new_prim,
        "db": DB, "collection": COLL,
        "documents": len(dump),
        "checksum": checksum(dump),
        "note": "логический дамп (find -> JSON), mongodump в среде отсутствует",
    }
    with open(os.path.join(backup_dir, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    log("Резервная копия: %s\\%s.json" % (backup_dir, COLL))
    log("  документов в копии: %d, checksum=%s" % (len(dump), checksum(dump)))

    # restore into a separate database
    with m.Client(port=new_prim, timeout=20) as c:
        c.command(RESTORE_DB, {"dropDatabase": 1})
        restored = []
        for d in dump:
            d = dict(d)
            d.pop("_id", None)
            restored.append(d)
        res = c.command(RESTORE_DB, {"insert": COLL, "documents": restored,
                                     "writeConcern": {"w": "majority", "wtimeout": 5000}})
        log("  mongorestore-эквивалент: insertMany в %s.%s, ok=%s, n=%s"
            % (RESTORE_DB, COLL, res.get("ok"), res.get("n")))
        cnt2 = c.command(RESTORE_DB, {"count": COLL})
        log("  документов в %s: %s" % (RESTORE_DB, cnt2.get("n")))

    restored_docs = read_all(new_prim, RESTORE_DB, COLL)
    ids_ok = sorted(d["pubId"] for d in restored_docs) == sorted(d["pubId"] for d in dump)
    csum_restored = checksum(restored_docs)
    diff = []
    orig = {d["pubId"]: {k: v for k, v in d.items() if k != "_id"} for d in dump}
    for d in restored_docs:
        o = orig.get(d["pubId"])
        if o != {k: v for k, v in d.items() if k != "_id"}:
            diff.append(d["pubId"])
    log("  совпадение набора pubId: %s" % ("ДА" if ids_ok else "НЕТ"))
    log("  checksum восстановленной базы: %s" % csum_restored)
    log("  совпадение checksum: %s" % ("ДА" if csum_restored == checksum(dump) else "НЕТ"))
    log("  расхождения по документам: %s" % (diff or "нет"))

    backup = {
        "backup_path": backup_dir,
        "backup_documents": len(dump),
        "backup_checksum": checksum(dump),
        "restore_db": RESTORE_DB,
        "restore_documents": len(restored_docs),
        "restore_checksum": csum_restored,
        "ids_match": ids_ok,
        "checksum_match": csum_restored == checksum(dump),
        "field_diff": diff,
        "meta": meta,
    }
    with open(os.path.join(ART, "backup_restore.json"), "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)

    # ---------------- summary
    rule("ИТОГИ")
    log("RTO наблюдаемое: %.3f c" % rto)
    log("Контрольный набор до/после: %d/%d, checksum совпал: %s"
        % (len(before), len(after_ctrl), csum_after_ctrl == csum_before))
    log("PUB-0022 (w:1): подтверждена=%s, сохранилась=%s" % (risky_ok, fail["risky_survived"]))
    log("Восстановление: %d док., checksum совпал: %s" % (len(restored_docs), csum_restored == checksum(dump)))

    # ---------------- stop everything
    rule("ЗАВЕРШЕНИЕ: штатная остановка всех узлов стенда")
    for p in PORTS:
        ok = stop_node(p)
        log("  127.0.0.1:%d остановлен: %s" % (p, ok))
    DONE = True

    if had_watchdog:
        try:
            os.remove(pause)
        except OSError:
            pass
        log("  пауза watchdog снята: узлы поднимутся автоматически через ~15 c")

    LOGF.close()
    print("\nArtifacts written to", ART)


if __name__ == "__main__":
    try:
        main()
    finally:
        # lift the watchdog pause in any case
        try:
            os.remove(os.path.join(BASE, "logs", "watchdog.pause"))
        except OSError:
            pass
        # do not leave orphan mongod processes behind (unless LAB10_KEEP=1)
        if not DONE and os.environ.get("LAB10_KEEP") != "1":
            for _p in PORTS:
                try:
                    stop_node(_p, timeout=10)
                except Exception:
                    pass
