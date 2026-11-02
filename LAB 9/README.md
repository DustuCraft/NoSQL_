# Лабораторная работа № 9. Проектирование и применение NoSQL-технологий

REST API (FastAPI) поверх MongoDB. Доступ к БД изолирован в слое `repository`, конфигурация и секреты вынесены в переменные окружения.

- **Среда разработки:** IntelliJ IDEA (плагин Python) / PyCharm
- **СУБД:** MongoDB
- **Драйвер:** PyMongo
- **Фреймворк API:** FastAPI + Uvicorn

## Структура проекта

```
lab9/
  main.py            # API: endpoints, HTTP-валидация, маппинг ошибок в HTTP-коды
  repository.py      # доступ к MongoDB (без знания про HTTP)
  models.py          # Pydantic-схемы входа/выхода
  config.py          # чтение конфигурации из окружения
  requirements.txt
  .env.example       # только имена переменных, без секретов
  README.md
```

Слои: `main.py` (HTTP) → `repository.py` (БД). Repository возвращает доменные результаты или доменные исключения (`NotFoundError`, `DuplicateError`, `StorageUnavailableError`) и ничего не знает про `HTTPException`.

## Запуск в Pycharm
   Установите зависимости: `pip install -r requirements.txt`
   ```bash
   docker run -d --name mongo -p 27017:27017 mongo:7
   ```
 Скопируйте `.env.example` в `.env` и заполните значения (файл `.env` добавлен в `.gitignore`).
 Создайте Run Configuration: **Run → Edit Configurations → + → Python**, Script/Module: `uvicorn`, Parameters: `main:app --reload`, Working directory: `lab9`. Для переменных окружения используйте поле *Environment variables* или плагин EnvFile.
 Документация и ручная проверка: http://127.0.0.1:8000/docs

## Конфигурация

`.env.example`:

```
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=lab9
MONGO_COLLECTION=items
MONGO_TIMEOUT_MS=2000
```

Реальные значения хранятся только в `.env` / переменных окружения и не попадают в Git.

`.gitignore` должен содержать:

```
.env
.venv/
__pycache__/
```

## Контракт API

| Операция | Метод | Пример | Ожидаемый код |
|---|---|---|---|
| Создание | POST | `/items` | 201 |
| Получение | GET | `/items/{id}` | 200 / 404 |
| Список/поиск | GET | `/items?filter=...` | 200 |
| Изменение | PUT/PATCH | `/items/{id}` | 200 / 404 |
| Удаление | DELETE | `/items/{id}` | 204 / 404 |

## Обработка ошибок

| Сценарий | Ожидаемое поведение |
|---|---|
| Нет объекта | 404, понятное сообщение |
| Неверные данные | 400/422 |
| Дубликат уникального ID | 409 |
| СУБД недоступна | 503 без раскрытия URI/пароля |
| Неожиданная ошибка | 500, подробности только в серверном логе |

Соответствие исключений и кодов:

| Исключение repository | HTTP-код |
|---|---|
| `NotFoundError` | 404 |
| `DuplicateError` (`DuplicateKeyError` драйвера) | 409 |
| `StorageUnavailableError` (`ServerSelectionTimeoutError`, `ConnectionFailure`) | 503 |
| любое другое | 500 (в клиент уходит общее сообщение) |

## Проверка отказа БД

1. Запустите API и выполните `GET /items` — ответ 200.
2. Остановите MongoDB: `docker stop mongo`.
3. Повторите запрос — ожидается 503 за время не более `MONGO_TIMEOUT_MS`, без URI и пароля в теле ответа.
4. Запустите БД: `docker start mongo` — API снова отвечает 200.

## Модель данных

Коллекция `items`, документ:

```json
{ "code": "A-1", "name": "Ноутбук", "description": "15 дюймов", "price": 999.9 }
```

`code` — уникальный (уникальный индекс создаётся при первом обращении к БД). Фильтр в `GET /items?filter=...` — поиск подстроки в `name` без учёта регистра; также поддерживаются `skip` и `limit`.

## Быстрый пример

```bash
curl -X POST localhost:8000/items -H "Content-Type: application/json" \
     -d '{"code":"A-1","name":"Ноутбук","price":999.9}'
curl localhost:8000/items?filter=ноут
```
