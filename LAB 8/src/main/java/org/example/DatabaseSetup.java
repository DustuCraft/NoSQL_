package org.example;

import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import com.mongodb.client.model.Indexes;
import org.bson.Document;

import java.util.List;

public class DatabaseSetup {
    public static void createCollectionsAndIndexes(MongoDatabase db) {
        List<String> names = List.of("customers", "orders", "couriers", "zones", "events");
        for (String name : names) {
            if (!db.listCollectionNames().into(new java.util.ArrayList<>()).contains(name)) {
                db.createCollection(name);
            }
        }

        MongoCollection<Document> customers = db.getCollection("customers");
        MongoCollection<Document> orders = db.getCollection("orders");
        MongoCollection<Document> couriers = db.getCollection("couriers");
        MongoCollection<Document> zones = db.getCollection("zones");
        MongoCollection<Document> events = db.getCollection("events");

        customers.createIndex(Indexes.ascending("customerId"));
        orders.createIndex(Indexes.ascending("orderId"));
        orders.createIndex(Indexes.ascending("customerId", "createdAt"));
        orders.createIndex(Indexes.ascending("courierId", "status"));
        orders.createIndex(Indexes.ascending("zoneId", "status"));
        couriers.createIndex(Indexes.ascending("courierId"));
        zones.createIndex(Indexes.ascending("zoneId"));
        events.createIndex(Indexes.ascending("orderId", "createdAt"));
    }
}
