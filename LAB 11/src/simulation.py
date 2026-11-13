"""Запуск: python -m src.simulation   (из корня проекта)"""
import csv, json, random
from collections import Counter
from src.config import SEED, SHARDS, RESULTS_DIR
from src.data_gen import make_rows, make_skewed_rows, make_requests
from src.strategies import BASE_CANDIDATES, STEP4_CANDIDATES


def describe(name, assign, data, requests):
    docs = Counter(assign(r) for r in data)
    load = Counter(assign(r) for r in requests)
    d = [docs[i] for i in range(SHARDS)]
    q = [load[i] for i in range(SHARDS)]
    res = dict(name=name, docs=d, queries=q,
               doc_max_mean=round(max(d) / (sum(d) / SHARDS), 2),
               query_max_mean=round(max(q) / (sum(q) / SHARDS), 2),
               query_max_min=round(max(q) / min(q), 2) if min(q) else None)
    print(f"{name:30s} docs={d} queries={q} doc_max_mean={res['doc_max_mean']:.2f} "
          f"query_max_mean={res['query_max_mean']:.2f} query_max_min={res['query_max_min']}")
    return res


def run_block(title, rows, candidates):
    print(title)
    uniform, hot = make_requests(rows)
    out = []
    for name, fn in candidates:
        out.append(describe(f"{name}/uniform", fn, rows, uniform))
        out.append(describe(f"{name}/hot", fn, rows, hot))
    return out


def main():
    random.seed(SEED)
    base = run_block("=== Шаги 1-2: базовый набор ===", make_rows(), BASE_CANDIDATES)
    step4 = run_block("\n=== Шаг 4: 80% записей в одном отделении ===",
                      make_skewed_rows(), STEP4_CANDIDATES)

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "results.json").write_text(
        json.dumps(dict(base=base, step4=step4), ensure_ascii=False, indent=2), encoding="utf-8")
    with open(RESULTS_DIR / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["block", "name", "docs", "queries", "doc_max_mean", "query_max_mean", "query_max_min"])
        for block, items in (("base", base), ("step4", step4)):
            for r in items:
                w.writerow([block, r["name"], r["docs"], r["queries"],
                            r["doc_max_mean"], r["query_max_mean"], r["query_max_min"]])
    print(f"\nСохранено: {RESULTS_DIR / 'results.json'}, results.csv")


if __name__ == "__main__":
    main()
