# Лабораторная работа №10 — Вариант 9

- **Дисциплина:** «Проектирование и применение NoSQL-технологий»
- **Тема:** настройка репликации MongoDB и моделирование отказа стенда
- **Вариант 9:** Социальная сеть, коллекция `publications` (публикации)

Стенд — локальный MongoDB Replica Set `rsLab10` из трёх узлов на `127.0.0.1:27101–27103`.
Эксперимент полностью воспроизводим одним скриптом: инициализация → 21 публикация с
`w:"majority"` → отказ PRIMARY → замер RTO → возврат узла → бэкап и восстановление.

---

## 1. Требования

| Компонент | Значение в этой системе |
|---|---|
| MongoDB |
| Python  |
| ОС | Windows, PowerShell |
| Порты | 27101, 27102, 27103 (только loopback) |
| Свободное место | ~50 МБ на каталоги данных |

`mongosh` и `mongodump`/`mongorestore` **не нужны**: клиент MongoDB реализован
в `tools/minimongo.py` по wire-протоколу (OP_MSG + BSON), бэкап — логический.

---

## 2. Структура проекта

```
lab10\
├── README.md                  этот файл
├── stand.ps1                  watchdog: держит три узла живыми
├── start_stand.cmd            запустить watchdog
├── stop_stand.ps1/.cmd        штатно погасить watchdog и узлы
├── install_autostart.ps1/.cmd автозапуск при входе в Windows
├── config\
│   ├── rs1.cfg                конфиг узла 27101 (dbpath, порт, replSetName)
│   ├── rs2.cfg                конфиг узла 27102
│   └── rs3.cfg                конфиг узла 27103
├── tools\
│   ├── minimongo.py           клиент MongoDB: BSON + OP_MSG
│   ├── run_lab.py             полный прогон лабораторной
│   ├── rscheck.py             состояние набора (роли, отставание)
│   ├── shutdown_stand.py      корректная остановка всех узлов
│   └── step_insert.py         только шаг вставки данных
├── artifacts\                 результаты прогона (JSON + transcript.txt)
├── backup_lab10\              логический дамп university_lab10
├── logs\                      rs1.log … rs3.log, watchdog.log, watchdog.pid
└── rs1\, rs2\, rs3\           каталоги данных WiredTiger
```

---

## 3. Быстрый старт

### 3.1. Прогон лабораторной (основной сценарий)

```powershell
C:\Users\erzan\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe `
  C:\Users\erzan\Documents\deepseek-harness\default-workspace\lab10\tools\run_lab.py
```

Занимает 1–2 минуты. Скрипт сам поднимает узлы, всё делает и в конце гасит их
(если запущен watchdog — ставит его на паузу и потом возвращает в работу).

Результаты — в `artifacts\`:

| Файл | Что внутри |
|---|---|
| `control_before.json` | 21 документ, список `pubId`, `contentHash`, общий checksum |
| `failover.json` | t0, t1, RTO, новый PRIMARY, проверка данных, ошибка записи в окне отказа |
| `rejoin.json` | роль вернувшегося узла, число прочитанных документов |
| `backup_restore.json` | размеры бэкапа и восстановления, совпадение checksum |
| `transcript.txt` | полный текст прогона (его удобно вставлять в отчёт) |

### 3.2. Постоянно работающий стенд

```powershell
lab10\start_stand.cmd     # запустить watchdog (узлы поднимутся сами)
lab10\stop_stand.cmd      # остановить всё
```

Проверка состояния:

```powershell
C:\Users\erzan\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe `
  lab10\tools\rscheck.py status
```

Пример вывода:

```
27101  PRIMARY   set=rsLab10
27102  SECONDARY set=rsLab10
27103  SECONDARY set=rsLab10
```

### 3.3. Автозапуск при входе в Windows

```powershell
lab10\install_autostart.cmd
```

Создаёт задачу Планировщика `MongoLab10Stand` и ярлык в «Автозагрузке».
При необходимости запускать от имени администратора. Удалить автозапуск —
удалить ярлык `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\MongoLab10.lnk`
и задачу `MongoLab10Stand`.

---

## 4. Как это работает

### 4.1. Реплика-сет

Каждый узел — отдельный процесс `mongod` со своим каталогом данных и портом:

```
mongod --config config\rs1.cfg     → 127.0.0.1:27101, dbpath rs1
mongod --config config\rs2.cfg     → 127.0.0.1:27102, dbpath rs2
mongod --config config\rs3.cfg     → 127.0.0.1:27103, dbpath rs3
```

Набор инициализируется один раз:

```js
rs.initiate({_id:"rsLab10", members:[
  {_id:0, host:"127.0.0.1:27101"},
  {_id:1, host:"127.0.0.1:27102"},
  {_id:2, host:"127.0.0.1:27103"}]})
```

Один узел становится PRIMARY (принимает запись), два — SECONDARY (повторяют oplog).
Кворум — 2 из 3: при потере одного узла набор продолжает работать.

### 4.2. Данные варианта 9

База `university_lab10`, коллекция `publications`, 21 синтетический документ:

```js
{
  _id: ObjectId("..."),
  pubId: "PUB-0007",            // бизнес-идентификатор, уникальный индекс
  authorId: "u-1007",
  type: "video",                // post | photo | video | repost
  text: "…",
  tags: ["lab10", "synthetic", "video-type"],
  createdAt: "2026-11-02T10:33:00Z",
  likes: 70, comments: 2,
  visibility: "public", status: "published",
  schemaVersion: 1, rev: 1,
  contentHash: "…"              // контрольная сумма полей
}
```

Уникальный индекс `ux_pubId` не даёт создать дубль и делает повторную запись
идемпотентной. Контрольный checksum считается по парам `pubId + contentHash`.

### 4.3. Шаги `run_lab.py`

| Шаг | Что делает | Что фиксирует |
|---|---|---|
| 1 | Ставит watchdog на паузу, гасит старые узлы, пересоздаёт `rs1–rs3`, запускает три `mongod` | версия, порты, каталоги |
| 2 | `replSetInitiate`, ждёт выборы | роли, term |
| 3 | `dropDatabase`, уникальный индекс, `insertMany` 21 документа с `w:"majority"`, чтение со secondary | количество, checksum |
| 4 | Пишет `PUB-0022` с `w:1`, фиксирует **t0**, шлёт `shutdown` PRIMARY в отдельном потоке, ждёт **t1** | RTO = t1 − t0, ошибка записи в окне отказа |
| 5 | Ждёт полного завершения старого процесса, поднимает узел заново, ждёт SECONDARY | роль, догон данных |
| 6 | Логический дамп в `backup_lab10`, восстановление в `university_restore10`, сверка | совпадение count, `pubId`, checksum |

Ключевые детали:

- `t0` фиксируется **до** отправки `shutdown`, `t1` — первое наблюдение узла
  с `isWritablePrimary: true` (опрос каждые 100 мс);
- `shutdown` выполняется в отдельном потоке, иначе клиент ждёт закрытия соединения
  и замер завышается;
- перед повторным запуском узла скрипт ждёт **выхода процесса**: `mongod` закрывает
  порт раньше, чем отпускает `dbpath` и лог;
- в окне отказа запись ожидаемо падает с `not master (code 10107)`;
- `PUB-0022` с `w:1` может сохраниться, но это не гарантия — в отчёте она вне
  контрольного набора.

### 4.4. Watchdog

`stand.ps1` каждые 5 секунд проверяет TCP-порты 27101–27103 и поднимает упавший
`mongod` (не чаще одной попытки в 15 с на узел). Пишет `logs\watchdog.log`,
свой PID — в `logs\watchdog.pid`, вторую копию не запускает.

Если существует файл `logs\watchdog.pause`, watchdog не перезапускает узлы —
это использует `run_lab.py`, чтобы эксперимент не сбивался. После прогона пауза
снимается, и стенд возвращается в работу автоматически.

### 4.5. Клиент вместо mongosh

`tools/minimongo.py` реализует минимальный клиент:

1. TCP-соединение с узлом;
2. заголовок сообщения (длина, requestId, responseTo, opcode `2013` = OP_MSG);
3. BSON-документ команды (`{"hello":1}`, `{"insert":…}`, `{"replSetGetStatus":1}`);
4. разбор ответа: флаги, секции kind 0/1, BSON → Python-объекты (`ObjectId`, `datetime`).

`mongodump`/`mongorestore` заменены логическим дампом: `find` → JSON-файл →
`insertMany` в `university_restore10`.

---

## 5. Результаты прогона (пример)

```
RTO наблюдаемое:            0.179 c   (штатная остановка, PRIMARY уступает роль сразу)
Новый PRIMARY:              27102
Контрольный набор:          21/21, checksum 51aabcd0… совпал
PUB-0022 (w:1):             сохранилась (не гарантия)
Запись в окне отказа:       not master (code 10107)
Возврат узла:               SECONDARY, health=1, прочитано 22 документа
Бэкап/восстановление:       22 → 22, checksum 417181f8… совпал
```

При аварийном обрыве (не `shutdown`, а падение процесса/сети) выборы ждут
`electionTimeoutMillis` (~10 с), и RTO будет заметно больше.

---

## 6. Ограничения стенда

- Три узла на одном компьютере: защита от падения процесса, но не от отказа диска,
  питания или перезагрузки. Для реальной HA нужны разные машины (или Atlas).
- Нет аутентификации и TLS — допустимо только для loopback в учебной среде.
- `w:"majority"` защищает подтверждённые записи, но **не заменяет бэкап**:
  ошибочное удаление тоже реплицируется.
- Логический бэкап не эквивалентен `mongodump` (нет BSON-типов и oplog), для
  учебных целей достаточен.

---

## 7. Типовые проблемы

| Симптом | Причина | Решение |
|---|---|---|
| `PermissionError: …\logs\rs1.log` | запущен постоянный стенд, файл занят `mongod` | обновлённый `run_lab.py` ставит паузу сам; вручную — `stop_stand.cmd` |
| `not master (code 10107)` | идёт переключение, PRIMARY ещё не выбран | нормально в окне отказа; повторить запись с тем же `pubId` |
| `no primary elected` | узлы не стартовали или нет кворума | смотреть `logs\rs*.log`, проверить порты |
| Порт занят | остался `mongod` от прошлого прогона | `stop_stand.cmd`, затем повторить |
| `watchdog already running` | уже запущена копия | ничего делать не нужно |
| Скрипт `.ps1` не запускается | политика выполнения | запускать через `.cmd`-обёртки или `powershell -ExecutionPolicy Bypass -File …` |
| Нет `mongosh`/`mongodump` | их нет в системе | не нужны, см. п. 4.5 |

---

## 8. Полезные команды

```powershell
# путь к интерпретатору (сократим как $py)
$py = 'C:\Users\erzan\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'

# состояние набора
& $py lab10\tools\rscheck.py status

# только вставка данных (без отказа)
& $py lab10\tools\step_insert.py

# прогон без остановки узлов в конце
$env:LAB10_KEEP = 1
& $py lab10\tools\run_lab.py

# принудительно погасить всё
lab10\stop_stand.cmd
```
