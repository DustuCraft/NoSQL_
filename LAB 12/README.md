# Лабораторная №12 — воспроизводимый benchmark NoSQL (вариант 08: Кафе)

Коллекция `menu_items` (позиции меню кафе). Фильтр AP-01: `restaurantId + categoryId`.
Сравнение: без индекса vs составной индекс `{restaurantId: 1, categoryId: 1}`.

## Запуск
```bash
python -m venv .venv
# Windows 
pip install -r requirements.txt
.env.example .env            # MONGO_URI
python seed.py --count 50000    # данные (seed=42) + results/env_info.json
python benchmark.py --n 1000 --clients 1 4 8 --repeats 3
1 - seed.py 2 - benchmark.py # запускать по очереди
```
## Результаты
- `results/results.csv` — каждый прогон (RPS, P50/P95/P99, ошибки, длительность)
- `results/raw_latencies.csv` — сырые задержки (для P95 по объединённым данным)
- `results/summary.csv`, `results/p95_improvement.csv` — медианы трёх запусков и улучшение P95
- `results/explain.json` — winningPlan, totalDocsExamined, totalKeysExamined, executionTimeMillis
- `results/write_cost_and_index_size.json` — стоимость записи и размер индекса
- `charts/` — графики P95 и throughput

## Методика
closed-loop; warm-up 40 запросов перед каждым измерением (не входит в результаты); 3 повтора на режим;
одинаковые данные (seed) и одинаковый набор запросов в обоих режимах; ошибки считаются отдельно.
Ограничение: Python-клиент (GIL) и MongoDB на одной машине — throughput может выходить на плато из-за клиента.
