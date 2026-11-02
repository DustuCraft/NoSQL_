package org.example;

import com.mongodb.client.MongoDatabase;
import org.bson.Document;

public class Main {
    public static void main(String[] args) {
        try {
            MongoDatabase db = MongoConnection.database();
            db.runCommand(new Document("ping", 1));
            System.out.println("MongoDB подключена. База: " + db.getName());

            DatabaseSetup.createCollectionsAndIndexes(db);
            DataSeeder.seed(db);

            OrderService service = new OrderService(db);

            System.out.println("\n=== 1. Заказы клиента ===");
            service.printCustomerOrders("C001");

            System.out.println("\n=== 2. Активные заказы курьера ===");
            service.printActiveCourierOrders("R002");

            System.out.println("\n=== 3. Поиск новых заказов ===");
            service.printOrdersByStatus("NEW");

            System.out.println("\n=== 4. Изменение статуса ===");
            service.changeStatus("O001", "ASSIGNED");

            System.out.println("\n=== 5. Безопасная отмена заказа ===");
            service.cancelOrderSafely("O020");

            System.out.println("\n=== 6. Аналитика по зонам ===");
            service.printZoneAnalytics();

            System.out.println("\n=== 7. История заказа ===");
            service.printOrderHistory("O001");

            System.out.println("\nГотово. Проверь коллекции в MongoDB Compass.");
        } catch (Exception e) {
            System.err.println("Ошибка: " + e.getMessage());
            e.printStackTrace();
        } finally {
            MongoConnection.close();
        }
    }
}
