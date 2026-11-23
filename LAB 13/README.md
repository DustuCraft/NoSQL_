# Лабораторная работа №13

**Вариант 19:** Служба поддержки. Рабочая коллекция `tickets`, защищённая `internal_notes`, журнал `audit_events`. БД `support_lab13`.

## 1. MongoDB с включённой авторизацией
Нужен любой MongoDB с авторизацией и администратором. Локально через Docker (пароль задайте сами, в Git его не класть):
```bash
docker run -d --name mongo-rbac-lab -p 127.0.0.1:27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=labadmin \
  -e MONGO_INITDB_ROOT_PASSWORD=<ВАШ_ПАРОЛЬ> mongo:7
```

## 2. Открыть и запустить в IntelliJ IDEA
1. **File → Open** → выберите папку проекта (файл `pom.xml`), дождитесь загрузки Maven.
2. Откройте `src/main/java/lab13/Main.java` → зелёная стрелка **Run 'Main.main()'**.
3. В консоли: host:port (Enter = `localhost:27017`), затем меню:
   - **1** — создать данные, 3 роли и 3 пользователя (введите пароль админа и пароли `viewer19`, `editor19`, `auditor19`);
   - **2** — прогнать 11 проверок (пароли пользователей); таблица сохранится в `test-results.md`;
   - **3** — убрать тестовые документы editor19.

Пароли в коде и в Git не хранятся: вводятся при запуске. В консоли Run IDEA ввод виден — не делайте скриншот этого момента.

## 3. Подключить MongoDB к IDEA (просмотр данных)
**View → Tool Windows → Database → `+` → Data Source → MongoDB** (в Community — плагин MongoDB или внешний Compass).
- Host `localhost`, Port `27017`, User `labadmin`, Authentication database `admin`, пароль админа.
- Для проверки роли создайте второе подключение: User `viewer19`, Authentication database `support_lab13` — `internal_notes` не откроется (Unauthorized).

## Модель угроз
Нарушитель — рядовой сотрудник поддержки или скомпрометированная учётная запись. Риски: чтение конфиденциальных `internal_notes`, удаление тикетов, подделка журнала `audit_events`. Каждой роли выданы только действия над одной коллекцией; прав на всю БД нет; `internal_notes` недоступна всем ролям.

## Матрица доступа
| Роль | tickets | internal_notes | audit_events |
|---|---|---|---|
| viewer (`ticketViewer`) | find | нет | нет |
| editor (`ticketEditor`) | find, insert, update | нет | нет |
| auditor (`eventAuditor`) | нет | нет | find |

`remove` у editor убран сознательно: тикет закрывается сменой статуса. Если нужен полный набор — добавьте `"remove"` в `Setup.java` и измените ожидание теста №7.

## Таблица тестов
Колонки «Факт» и «Вывод» — из `test-results.md` после запуска.

| № | Пользователь | Действие | Ожидается | Факт | Вывод |
|---|---|---|---|---|---|
| 1 | viewer19 | find tickets | Allowed | | |
| 2 | viewer19 | insert tickets | Unauthorized | | |
| 3 | viewer19 | find internal_notes | Unauthorized | | |
| 4 | editor19 | find tickets | Allowed | | |
| 5 | editor19 | insert tickets | Allowed | | |
| 6 | editor19 | update tickets | Allowed | | |
| 7 | editor19 | remove tickets | Unauthorized | | |
| 8 | editor19 | find internal_notes | Unauthorized | | |
| 9 | auditor19 | find audit_events | Allowed | | |
| 10 | auditor19 | insert audit_events | Unauthorized | | |
| 11 | auditor19 | find tickets | Unauthorized | | |

## Вывод
Роли ограничены конкретными коллекциями и минимальным набором действий; защищённая коллекция недоступна. Рекомендации: отдельный view без чувствительных полей, аудит MongoDB, ротация паролей.

## Ответы на контрольные вопросы
1. **Аутентификация vs авторизация.** Аутентификация — «кто ты?» (проверка логина и пароля); авторизация — «что тебе разрешено?».
2. **RBAC и least privilege.** RBAC — права выдаются ролям, роли назначаются пользователям. Least privilege — только права, нужные для задачи.
3. **Зачем негативные тесты.** Доказывают, что запрещённое действительно запрещено; позитивные тесты лишние права не покажут.
4. **Почему readWrite на всю БД избыточна.** Даёт чтение и запись всех коллекций (включая защищённые) и действия, которые роли не нужны.
5. **Как не раскрывать секреты.** Пароли вводить интерактивно, не хранить в коде, отчёте, скриншотах и Git.
6. **Какие действия включает роль.** Набор привилегий: ресурс (БД/коллекция) + действия (`find`, `insert`, `update`, `remove` и др.).
7. **Как исправить лишнюю привилегию.** `revokePrivilegesFromRole` или пересоздать роль с нужным набором, затем повторить негативный тест.
