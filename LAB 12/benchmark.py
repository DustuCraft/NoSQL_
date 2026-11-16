"""Воспроизводимый closed-loop benchmark: без индекса vs составной индекс.
Запуск: python benchmark.py --n 1000 --clients 1 4 8 --repeats 3
"""
import argparse
import csv
import json
import math
import os
import random
import statistics
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import config

WARMUP = 40
LIMIT = 100


# ---------- метрики ----------
def percentile(values, p):
    v = sorted(values)
    if not v:
        return float("nan")
    idx = (len(v) - 1) * p / 100
    lo, hi = math.floor(idx), math.ceil(idx)
    return v[lo] + (v[hi] - v[lo]) * (idx - lo)


# ---------- индекс ----------
def drop_lab_index(coll):
    """Удаляет только индекс этой лабораторной."""
    if config.INDEX_NAME in {i["name"] for i in coll.list_indexes()}:
        coll.drop_index(config.INDEX_NAME)


def create_lab_index(coll):
    coll.create_index(config.INDEX_KEYS, name=config.INDEX_NAME)


def index_size_bytes(coll):
    stats = coll.database.command("collStats", coll.name)
    return stats.get("indexSizes", {}).get(config.INDEX_NAME, 0), stats.get("totalIndexSize", 0)


# ---------- explain ----------
def collect_stages(plan):
    stages = [plan.get("stage")]
    if "inputStage" in plan:
        stages += collect_stages(plan["inputStage"])
    for s in plan.get("inputStages", []):
        stages += collect_stages(s)
    return [s for s in stages if s]


def run_explain(coll, mode):
    res = coll.database.command({
        "explain": {"find": coll.name, "filter": config.EXPLAIN_QUERY},
        "verbosity": "executionStats"})
    wp = res["queryPlanner"]["winningPlan"]
    wp = wp.get("queryPlan", wp)  # новые версии (slot-based execution)
    es = res["executionStats"]
    out = {"mode": mode,
           "winningPlan": " -> ".join(collect_stages(wp)),
           "totalDocsExamined": es["totalDocsExamined"],
           "totalKeysExamined": es["totalKeysExamined"],
           "executionTimeMillis": es["executionTimeMillis"],
           "nReturned": es["nReturned"]}
    print("EXPLAIN", out)
    return out


# ---------- нагрузка ----------
def run_load(coll, workers, n, queries):
    def one(i):
        q = queries[i % len(queries)]
        t = perf_counter()
        try:
            list(coll.find(q).limit(LIMIT))
            return (perf_counter() - t) * 1000, True
        except Exception:
            return (perf_counter() - t) * 1000, False

    for i in range(WARMUP):          # warm-up отдельно, в измерения не входит
        one(i)
    t0 = perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, range(n)))
    seconds = perf_counter() - t0
    lat = [ms for ms, ok in results if ok]
    return {
        "workers": workers, "attempts": n, "success": len(lat),
        "errors": n - len(lat), "error_pct": (n - len(lat)) / n * 100,
        "duration_s": seconds, "rps": len(lat) / seconds,
        "p50": percentile(lat, 50), "p95": percentile(lat, 95),
        "p99": percentile(lat, 99),
    }, lat


def write_cost(coll, mode, repeats=3, batch=5000):
    """Стоимость записи: время insert_many пачки синтетических документов."""
    rng = random.Random(config.SEED + 1)
    times = []
    for _ in range(repeats):
        docs = [{"restaurantId": rng.randint(1, config.N_RESTAURANTS),
                 "categoryId": rng.randint(1, config.N_CATEGORIES),
                 "title": "bench", "price": 1.0, "calories": 100,
                 "chefId": 1, "_bench": True} for _ in range(batch)]
        t = perf_counter()
        coll.insert_many(docs, ordered=False)
        times.append((perf_counter() - t) * 1000)
        coll.delete_many({"_bench": True})
    return {"mode": mode, "batch": batch, "insert_ms_median": statistics.median(times)}


def run_mode(coll, mode, clients, repeats, n, queries, rows, raw):
    for w in clients:
        for r in range(1, repeats + 1):
            row, lat = run_load(coll, w, n, queries)
            row.update({"mode": mode, "repeat": r})
            rows.append(row)
            raw.extend({"mode": mode, "workers": w, "repeat": r, "latency_ms": x} for x in lat)
            print(f"[{mode}] clients={w} repeat={r} rps={row['rps']:.0f} "
                  f"p50={row['p50']:.2f} p95={row['p95']:.2f} p99={row['p99']:.2f} "
                  f"errors={row['errors']}")


# ---------- отчёт ----------
def make_summary_and_charts(df, raw_df):
    med = (df.groupby(["mode", "workers"])[["rps", "p50", "p95", "p99", "error_pct"]]
             .median().reset_index())
    pooled = (raw_df.groupby(["mode", "workers"])["latency_ms"]
                    .agg(pooled_p95=lambda s: percentile(s.tolist(), 95),
                         pooled_p99=lambda s: percentile(s.tolist(), 99)).reset_index())
    summary = med.merge(pooled, on=["mode", "workers"])
    summary.to_csv("results/summary.csv", index=False)

    # относительное улучшение P95 по медиане трёх запусков
    base = summary[summary["mode"] == "no_index"].set_index("workers")["p95"]
    idx = summary[summary["mode"] == "with_index"].set_index("workers")["p95"]
    impr = ((base - idx) / base * 100).round(1)
    impr.to_csv("results/p95_improvement.csv", header=["p95_improvement_pct"])
    print("\nSUMMARY\n", summary.to_string(index=False))
    print("\nP95 improvement, %:\n", impr.to_string())

    for metric, title, ylabel, fname in [
            ("p95", "P95 latency vs clients (median of 3 runs)", "P95, ms", "charts/p95_by_clients.png"),
            ("rps", "Throughput vs clients (median of 3 runs)", "RPS", "charts/throughput_by_clients.png")]:
        plt.figure(figsize=(7, 4.5))
        for mode, label in [("no_index", "Без индекса"), ("with_index", "С индексом")]:
            d = summary[summary["mode"] == mode]
            plt.plot(d["workers"], d[metric], marker="o", label=label)
        plt.xlabel("Число клиентов")
        plt.ylabel(ylabel)
        plt.title(title)
        plt.xticks(sorted(summary["workers"].unique()))
        plt.grid(True, alpha=.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(fname, dpi=150)
        plt.close()


def main():
    os.makedirs("results", exist_ok=True)
    os.makedirs("charts", exist_ok=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000, help="запросов на один прогон")
    ap.add_argument("--clients", type=int, nargs="+", default=[1, 4, 8])
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()

    coll = config.get_collection()
    docs = coll.count_documents({"_bench": {"$exists": False}})
    print("Документов:", docs, "| MongoDB", coll.database.client.server_info()["version"])
    if docs < 5000:
        raise SystemExit("Сначала запустите: python seed.py")
    queries = config.make_queries()

    rows, raw, explains, writes, sizes = [], [], [], [], {}

    # 1) baseline
    drop_lab_index(coll)
    explains.append(run_explain(coll, "no_index"))
    writes.append(write_cost(coll, "no_index"))
    run_mode(coll, "no_index", args.clients, args.repeats, args.n, queries, rows, raw)

    # 2) с индексом
    create_lab_index(coll)
    sizes["lab_index_bytes"], sizes["total_index_bytes"] = index_size_bytes(coll)
    explains.append(run_explain(coll, "with_index"))
    writes.append(write_cost(coll, "with_index"))
    run_mode(coll, "with_index", args.clients, args.repeats, args.n, queries, rows, raw)

    # сохранение
    df = pd.DataFrame(rows)[["mode", "workers", "repeat", "attempts", "success", "errors",
                             "error_pct", "duration_s", "rps", "p50", "p95", "p99"]]
    df.to_csv("results/results.csv", index=False)
    raw_df = pd.DataFrame(raw)
    raw_df.to_csv("results/raw_latencies.csv", index=False)
    with open("results/explain.json", "w", encoding="utf-8") as f:
        json.dump(explains, f, ensure_ascii=False, indent=2)
    with open("results/write_cost_and_index_size.json", "w", encoding="utf-8") as f:
        json.dump({"write_cost": writes, "index_size": sizes}, f, indent=2)
    make_summary_and_charts(df, raw_df)
    print("\nWrite cost:", writes, "\nIndex size:", sizes)
    print("Готово: results/ и charts/")


if __name__ == "__main__":
    main()