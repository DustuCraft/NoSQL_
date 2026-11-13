"""Столбчатый график нагрузки по шардам. Запуск: python -m src.plot_results"""
import json
import matplotlib.pyplot as plt
from src.config import RESULTS_DIR, SHARDS


def main():
    data = json.loads((RESULTS_DIR / "results.json").read_text(encoding="utf-8"))["base"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, mode in zip(axes, ("uniform", "hot")):
        items = [r for r in data if r["name"].endswith("/" + mode)]
        width = 0.8 / len(items)
        for k, r in enumerate(items):
            xs = [i + k * width for i in range(SHARDS)]
            ax.bar(xs, r["queries"], width, label=r["name"].split("/")[0])
        ax.set_xticks([i + 0.4 - width / 2 for i in range(SHARDS)])
        ax.set_xticklabels(["Shard A", "Shard B", "Shard C"])
        ax.set_title(f"Нагрузка по шардам ({mode})")
        ax.set_ylabel("Запросов")
        ax.legend()
    plt.tight_layout()
    out = RESULTS_DIR / "load_distribution.png"
    plt.savefig(out, dpi=150)
    print("Сохранено:", out)


if __name__ == "__main__":
    main()
