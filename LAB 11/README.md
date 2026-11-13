# Лабораторная №11, вариант 7 (банковский демо-сервис)

Кандидат shard key: `accountId`; низкокардинальный ключ: `branchId`; основной запрос — операции счёта.

## Структура
```
lab11_sharding_v7/
├── docker-compose.yml          # шардированный кластер (cfg + 3 шарда + mongos)
├── docker-compose.single.yml   # одиночный mongod (НЕ кластер)
├── requirements.txt
├── .env.example                # скопировать в .env
├── src/
│   ├── config.py               # параметры варианта и подключения
│   ├── db.py                   # MongoClient, проверка mongos
│   ├── data_gen.py             # синтетические данные и запросы
│   ├── strategies.py           # учебные функции размещения
│   ├── simulation.py           # Python-симуляция (шаги 1–4)
│   ├── plot_results.py         # столбчатый график
│   ├── init_cluster.py         # инициализация кластера
│   ├── load_to_mongo.py        # shardCollection + загрузка
│   └── check_distribution.py   # распределение и targeted/scatter-gather
├── results/                    # results.json/csv, график
└── report/                     # PDF-отчёт
```

## Настройка в PyCharm
1. File → Open → папка проекта. Создайте интерпретатор (Python 3.10+, venv).
2. Терминал PyCharm: `pip install -r requirements.txt`
3. Скопируйте `.env.example` в `.env`.
4. Run → Edit Configurations: для каждого скрипта выберите **Module name** (`src.simulation`),
   Working directory = корень проекта.

## Порядок запуска
Часть 1 (без MongoDB):
```
python -m src.simulation
python -m src.plot_results
```
Часть 2 (кластер, нужен Docker):
```
docker compose up -d
python -m src.init_cluster
python -m src.load_to_mongo --drop
python -m src.check_distribution
```
Остановить: `docker compose down -v`.
