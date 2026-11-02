package org.example;

import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoDatabase;

public final class MongoConnection {
    private static final String URI = "mongodb://localhost:27017";
    private static final String DATABASE_NAME = "DeliveryDB";
    private static final MongoClient CLIENT = MongoClients.create(URI);

    private MongoConnection() {}

    public static MongoDatabase database() {
        return CLIENT.getDatabase(DATABASE_NAME);
    }

    public static void close() {
        CLIENT.close();
    }
}
