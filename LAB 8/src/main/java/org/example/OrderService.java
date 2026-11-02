package org.example;

import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import com.mongodb.client.model.Filters;
import com.mongodb.client.model.Sorts;
import org.bson.Document;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

public class OrderService {
    private final MongoDatabase db;
    private final MongoCollection<Document> orders;
    private final MongoCollection<Document> events;

    public OrderService(MongoDatabase db) {
        this.db = db;
        this.orders = db.getCollection("orders");
        this.events = db.getCollection("events");
    }

    public void printCustomerOrders(String customerId) {
        System.out.println("\nЗаказы клиента " + customerId + ":");
        for (Document order : orders.find(Filters.eq("customerId", customerId))
                .sort(Sorts.descending("createdAt"))) {
            System.out.println(order.toJson());
        }
    }

    public void printActiveCourierOrders(String courierId) {
        List<String> active = List.of("ASSIGNED", "IN_TRANSIT");
        System.out.println("\nАктивные заказы курьера " + courierId + ":");
        for (Document order : orders.find(Filters.and(
                Filters.eq("courierId", courierId),
                Filters.in("status", active)))) {
            System.out.println(order.toJson());
        }
    }

    public void printOrdersByStatus(String status) {
        System.out.println("\nЗаказы со статусом " + status + ":");
        for (Document order : orders.find(Filters.eq("status", status))) {
            System.out.println(order.toJson());
        }
    }

    public void changeStatus(String orderId, String newStatus) {
        String now = Instant.now().toString();
        var result = orders.updateOne(Filters.eq("orderId", orderId),
                new Document("$set", new Document("status", newStatus).append("updatedAt", now)));
        if (result.getModifiedCount() > 0) {
            events.insertOne(new Document("eventId", "EV-" + System.currentTimeMillis())
                    .append("orderId", orderId)
                    .append("status", newStatus)
                    .append("description", "Статус изменён на " + newStatus)
                    .append("createdAt", now));
            System.out.println("Статус заказа " + orderId + " изменён на " + newStatus);
        } else {
            System.out.println("Заказ не найден или статус не изменился: " + orderId);
        }
    }

    public void cancelOrderSafely(String orderId) {
        changeStatus(orderId, "CANCELLED");
    }

    public void printZoneAnalytics() {
        System.out.println("\nАналитика заказов по зонам:");
        List<Document> pipeline = List.of(
                new Document("$group", new Document("_id", "$zoneId")
                        .append("ordersCount", new Document("$sum", 1))
                        .append("averageAmount", new Document("$avg", "$amount"))
                        .append("totalAmount", new Document("$sum", "$amount"))),
                new Document("$sort", new Document("ordersCount", -1))
        );
        for (Document row : orders.aggregate(pipeline)) {
            System.out.println(row.toJson());
        }
    }

    public void printOrderHistory(String orderId) {
        System.out.println("\nИстория заказа " + orderId + ":");
        for (Document event : events.find(Filters.eq("orderId", orderId))
                .sort(Sorts.ascending("createdAt"))) {
            System.out.println(event.toJson());
        }
    }

    public void addDemoOrder() {
        String id = "O-" + System.currentTimeMillis();
        String now = Instant.now().toString();
        Document order = new Document("orderId", id)
                .append("customerId", "C001")
                .append("courierId", null)
                .append("zoneId", "Z001")
                .append("description", "Новый демонстрационный заказ")
                .append("amount", 5000)
                .append("deliveryFee", 800)
                .append("status", "NEW")
                .append("createdAt", now)
                .append("updatedAt", now);
        orders.insertOne(order);
        events.insertOne(new Document("eventId", "EV-" + System.currentTimeMillis())
                .append("orderId", id).append("status", "NEW")
                .append("description", "Заказ создан").append("createdAt", now));
        System.out.println("Добавлен заказ: " + id);
    }
}
