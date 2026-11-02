package org.example;

import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import org.bson.Document;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

public class DataSeeder {
    public static void seed(MongoDatabase db) {
        MongoCollection<Document> customers = db.getCollection("customers");
        MongoCollection<Document> couriers = db.getCollection("couriers");
        MongoCollection<Document> zones = db.getCollection("zones");
        MongoCollection<Document> orders = db.getCollection("orders");
        MongoCollection<Document> events = db.getCollection("events");

        if (customers.countDocuments() > 0 || orders.countDocuments() > 0) {
            System.out.println("Тестовые данные уже существуют. Повторная загрузка пропущена.");
            return;
        }

        List<Document> customerDocs = new ArrayList<>();
        for (int i = 1; i <= 10; i++) {
            customerDocs.add(new Document("customerId", "C%03d".formatted(i))
                    .append("name", "Клиент " + i)
                    .append("phone", "+7701000%04d".formatted(i))
                    .append("address", "Алматы, улица Абая, дом " + (10 + i)));
        }
        customers.insertMany(customerDocs);

        List<Document> courierDocs = new ArrayList<>();
        for (int i = 1; i <= 5; i++) {
            courierDocs.add(new Document("courierId", "R%03d".formatted(i))
                    .append("name", "Курьер " + i)
                    .append("phone", "+7702000%04d".formatted(i))
                    .append("available", i % 2 == 1)
                    .append("zoneId", "Z00" + ((i % 3) + 1)));
        }
        couriers.insertMany(courierDocs);

        List<Document> zoneDocs = List.of(
                new Document("zoneId", "Z001").append("name", "Центр").append("deliveryFee", 800),
                new Document("zoneId", "Z002").append("name", "Юг").append("deliveryFee", 1000),
                new Document("zoneId", "Z003").append("name", "Север").append("deliveryFee", 1200)
        );
        zones.insertMany(zoneDocs);

        String[] statuses = {"NEW", "ASSIGNED", "IN_TRANSIT", "DELIVERED", "CANCELLED"};
        List<Document> orderDocs = new ArrayList<>();
        List<Document> eventDocs = new ArrayList<>();
        Instant now = Instant.now();

        for (int i = 1; i <= 20; i++) {
            String orderId = "O%03d".formatted(i);
            String customerId = "C%03d".formatted(((i - 1) % 10) + 1);
            String courierId = "R%03d".formatted(((i - 1) % 5) + 1);
            String zoneId = "Z00" + (((i - 1) % 3) + 1);
            String status = statuses[(i - 1) % statuses.length];
            Instant created = now.minusSeconds(i * 3600L);

            orderDocs.add(new Document("orderId", orderId)
                    .append("customerId", customerId)
                    .append("courierId", status.equals("NEW") || status.equals("CANCELLED") ? null : courierId)
                    .append("zoneId", zoneId)
                    .append("description", "Заказ №" + i)
                    .append("amount", 2500 + i * 350)
                    .append("deliveryFee", 700 + ((i - 1) % 3) * 200)
                    .append("status", status)
                    .append("createdAt", created.toString())
                    .append("updatedAt", created.toString()));

            eventDocs.add(new Document("eventId", "E%03d".formatted(i))
                    .append("orderId", orderId)
                    .append("status", status)
                    .append("description", "Создан тестовый заказ; текущий статус: " + status)
                    .append("createdAt", created.toString()));
        }
        orders.insertMany(orderDocs);
        events.insertMany(eventDocs);

        System.out.println("Добавлено: 10 клиентов, 5 курьеров, 3 зоны, 20 заказов, 20 событий.");
    }
}
