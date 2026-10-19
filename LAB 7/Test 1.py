
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from itertools import combinations
from collections import defaultdict, deque

client = MongoClient(
    "mongodb://localhost:27017/",
    serverSelectionTimeoutMS=3000
)

db = client["internet_shop"]

customers = db["customers"]
products = db["products"]
categories = db["categories"]
bought = db["bought"]
viewed = db["viewed"]
belongs_to = db["belongs_to"]


def create_data():
    if customers.count_documents({}) == 0:
        customers.insert_many([
            {"id": 1, "name": "Али", "email": "ali@mail.com"},
            {"id": 2, "name": "Данияр", "email": "daniyar@mail.com"},
            {"id": 3, "name": "Алина", "email": "alina@mail.com"},
            {"id": 4, "name": "Ерлан", "email": "erlan@mail.com"},
            {"id": 5, "name": "Мадина", "email": "madina@mail.com"},
            {"id": 6, "name": "Тимур", "email": "timur@mail.com"}
        ])

    if products.count_documents({}) == 0:
        products.insert_many([
            {"id": 101, "name": "Ноутбук", "price": 350000},
            {"id": 102, "name": "Мышь", "price": 8000},
            {"id": 103, "name": "Клавиатура", "price": 15000},
            {"id": 104, "name": "Монитор", "price": 120000},
            {"id": 105, "name": "Наушники", "price": 25000},
            {"id": 106, "name": "Смартфон", "price": 280000},
            {"id": 107, "name": "Веб-камера", "price": 18000}
        ])

    if categories.count_documents({}) == 0:
        categories.insert_many([
            {"id": 201, "name": "Компьютеры"},
            {"id": 202, "name": "Периферия"},
            {"id": 203, "name": "Мобильные устройства"}
        ])

    if bought.count_documents({}) == 0:
        data = {
            1: [101, 102, 103],
            2: [101, 102, 104],
            3: [102, 103, 105],
            4: [101, 104, 106],
            5: [103, 105, 107],
            6: [102, 105, 106]
        }

        bought.insert_many([
            {"customer_id": cid, "product_id": pid}
            for cid, ids in data.items()
            for pid in ids
        ])

    if viewed.count_documents({}) == 0:
        data = {
            1: [104, 105],
            2: [103, 105],
            3: [101, 107],
            4: [102, 103],
            5: [101, 106],
            6: [103, 107]
        }

        viewed.insert_many([
            {"customer_id": cid, "product_id": pid}
            for cid, ids in data.items()
            for pid in ids
        ])

    if belongs_to.count_documents({}) == 0:
        data = {
            201: [101, 104],
            202: [102, 103, 105, 107],
            203: [106]
        }

        belongs_to.insert_many([
            {"product_id": pid, "category_id": cat_id}
            for cat_id, ids in data.items()
            for pid in ids
        ])

    customers.create_index("id", unique=True)
    products.create_index("id", unique=True)
    categories.create_index("id", unique=True)

    bought.create_index([("customer_id", 1), ("product_id", 1)])
    viewed.create_index([("customer_id", 1), ("product_id", 1)])
    belongs_to.create_index("product_id")

    print("Данные готовы.")


def get_product(product_id):
    return products.find_one({"id": product_id})


def get_customer(customer_id):
    return customers.find_one({"id": customer_id})


def get_product_name(product_id):
    product = get_product(product_id)
    return product["name"] if product else str(product_id)


def show_customers():
    print("\nВсе покупатели:")
    for c in customers.find({}, {"_id": 0}):
        print(c)


def expensive_products():
    print("\nТовары дороже 20000 тенге:")
    for p in products.find(
        {"price": {"$gt": 20000}},
        {"_id": 0}
    ):
        print(p["name"], "-", p["price"], "тенге")


def top_products():
    print("\nТри самых дорогих товара:")
    result = products.find(
        {},
        {"_id": 0}
    ).sort("price", -1).limit(3)

    for p in result:
        print(p["name"], "-", p["price"], "тенге")


def customer_products():
    try:
        customer_id = int(input("ID покупателя (1-6): "))
    except ValueError:
        print("Нужно ввести число.")
        return

    customer = get_customer(customer_id)

    if not customer:
        print("Покупатель не найден.")
        return

    print("\nПокупки:", customer["name"])

    for relation in bought.find({"customer_id": customer_id}):
        print("-", get_product_name(relation["product_id"]))


def shared_products():
    print("\nТовары, купленные одними покупателями:")

    purchases = defaultdict(set)

    for relation in bought.find():
        purchases[relation["customer_id"]].add(
            relation["product_id"]
        )

    pair_counts = defaultdict(int)

    for product_ids in purchases.values():
        for a, b in combinations(sorted(product_ids), 2):
            pair_counts[(a, b)] += 1

    for (a, b), count in sorted(
        pair_counts.items(),
        key=lambda item: item[1],
        reverse=True
    ):
        print(
            get_product_name(a),
            "<->",
            get_product_name(b),
            "| Общих покупателей:",
            count
        )


def two_step_search():
    laptop_id = 101

    # Первый шаг: найти покупателей ноутбука.
    customer_ids = [
        r["customer_id"]
        for r in bought.find({"product_id": laptop_id})
    ]

    # Второй шаг: найти товары, которые они просматривали.
    print("\nПросмотренные товары покупателей ноутбука:")

    found = set()

    for customer_id in customer_ids:
        customer = get_customer(customer_id)

        for relation in viewed.find(
            {"customer_id": customer_id}
        ):
            pid = relation["product_id"]

            if pid not in found:
                print(
                    customer["name"],
                    "смотрел товар:",
                    get_product_name(pid)
                )
                found.add(pid)


def variable_length_search():
    start_id = 102
    max_depth = 3

    # Строим граф из отношений BOUGHT.
    graph = defaultdict(list)

    for r in bought.find():
        cid = r["customer_id"]
        pid = r["product_id"]

        customer_node = ("customer", cid)
        product_node = ("product", pid)

        graph[product_node].append(customer_node)
        graph[customer_node].append(product_node)

    start = ("product", start_id)
    queue = deque([(start, [start])])
    visited = {start}

    print("\nОбход от товара Мышь, глубина до 3:")

    while queue:
        node, path = queue.popleft()
        depth = len(path) - 1

        if depth > 0:
            names = []

            for kind, item_id in path:
                if kind == "product":
                    names.append(get_product_name(item_id))
                else:
                    customer = get_customer(item_id)
                    names.append(customer["name"])

            print(" -> ".join(names))

        if depth == max_depth:
            continue

        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))


def aggregate_purchases():
    print("\nКоличество покупок каждого товара:")

    result = bought.aggregate([
        {
            "$group": {
                "_id": "$product_id",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}}
    ])

    for item in result:
        print(
            get_product_name(item["_id"]),
            "-",
            item["count"],
            "покупок"
        )


def change_price():
    result = products.update_one(
        {"id": 102},
        {"$set": {"price": 9000}}
    )

    product = get_product(102)

    if product:
        print("Товар:", product["name"])
        print("Новая цена:", product["price"], "тенге")
        print("Изменено документов:", result.modified_count)


def safe_delete():
    # Создаём отдельную тестовую связь.
    test_relation = {
        "customer_id": 1,
        "product_id": 107,
        "test": True
    }

    viewed.insert_one(test_relation)

    # Находим и показываем связь перед удалением.
    found = viewed.find_one(test_relation)

    if not found:
        print("Тестовая связь не найдена.")
        return

    customer = get_customer(found["customer_id"])

    print("\nСвязь перед удалением:")
    print("Покупатель:", customer["name"])
    print("Товар:", get_product_name(found["product_id"]))
    print("Тип: VIEWED")
    print("Тестовая связь:", found["test"])

    answer = input("Удалить только эту связь? (да/нет): ")

    if answer.lower() in ("да", "д", "yes", "y"):
        result = viewed.delete_one({"_id": found["_id"]})
        print("Удалено связей:", result.deleted_count)

        check = viewed.find_one({"_id": found["_id"]})
        print("Связь осталась в базе:", check is not None)
    else:
        print("Удаление отменено.")


def show_counts():
    print("\nКоличество узлов:")
    print("Customer:", customers.count_documents({}))
    print("Product:", products.count_documents({}))
    print("Category:", categories.count_documents({}))

    print("\nКоличество отношений:")
    print("BOUGHT:", bought.count_documents({}))
    print("VIEWED:", viewed.count_documents({}))
    print("BELONGS_TO:", belongs_to.count_documents({}))


def main():
    try:
        client.admin.command("ping")
        print("MongoDB: подключение успешно.")

        create_data()

        while True:
            print("""
========== ИНТЕРНЕТ-МАГАЗИН ==========
1. Показать покупателей
2. Найти товары дороже 20000
3. Три самых дорогих товара
4. Покупки выбранного покупателя
5. Найти связанные товары
6. Двухшаговый обход
7. Обход переменной длины
8. Подсчитать покупки
9. Изменить цену мыши
10. Безопасное удаление тестовой связи
11. Показать количество узлов и отношений
0. Выход
""")

            choice = input("Выбери действие: ")

            if choice == "1":
                show_customers()
            elif choice == "2":
                expensive_products()
            elif choice == "3":
                top_products()
            elif choice == "4":
                customer_products()
            elif choice == "5":
                shared_products()
            elif choice == "6":
                two_step_search()
            elif choice == "7":
                variable_length_search()
            elif choice == "8":
                aggregate_purchases()
            elif choice == "9":
                change_price()
            elif choice == "10":
                safe_delete()
            elif choice == "11":
                show_counts()
            elif choice == "0":
                print("Программа завершена.")
                break
            else:
                print("Неверный пункт меню.")

    except PyMongoError as error:
        print("Ошибка MongoDB:", error)
        print("Проверь, запущен ли MongoDB Server.")

    finally:
        client.close()


if __name__ == "__main__":
    main()
