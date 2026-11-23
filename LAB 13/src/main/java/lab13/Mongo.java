package lab13;

import com.mongodb.MongoClientSettings;
import com.mongodb.MongoCredential;
import com.mongodb.ServerAddress;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import org.bson.Document;

import java.util.List;

final class Mongo {
    /** hostPort вида "localhost:27017". */
    static MongoClient connect(String hostPort, String user, String authDb, String password) {
        MongoClientSettings settings = MongoClientSettings.builder()
                .applyToClusterSettings(b -> b.hosts(List.of(new ServerAddress(hostPort))))
                .credential(MongoCredential.createCredential(user, authDb, password.toCharArray()))
                .build();
        MongoClient client = MongoClients.create(settings);
        client.getDatabase(authDb).runCommand(new Document("ping", 1)); // проверка логина
        return client;
    }

    private Mongo() {}
}
