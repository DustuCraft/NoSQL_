package lab13;

import com.mongodb.MongoException;
import com.mongodb.client.MongoClient;

public class Main {
    public static void main(String[] args) {
        System.out.println("=== Lab 13: RBAC / least privilege, variant 19 (Support service) ===");
        String host = Io.ask("MongoDB host:port", "localhost:27017");

        while (true) {
            System.out.println();
            System.out.println("1 - Setup (seed data, roles, users)  [admin]");
            System.out.println("2 - Run access tests                 [viewer19, editor19, auditor19]");
            System.out.println("3 - Cleanup test documents           [admin]");
            System.out.println("0 - Exit");
            String choice = Io.ask("Choice", "1");
            try {
                switch (choice) {
                    case "1" -> withAdmin(host, Setup::run);
                    case "2" -> AccessTests.run(host);
                    case "3" -> withAdmin(host, Setup::cleanup);
                    case "0" -> { return; }
                    default -> System.out.println("Unknown option");
                }
            } catch (MongoException e) {
                System.out.println("MongoDB error: " + e.getMessage());
            }
        }
    }

    private static void withAdmin(String host, java.util.function.Consumer<MongoClient> action) {
        String user = Io.ask("Admin user", "labadmin");
        String authDb = Io.ask("Auth database", "admin");
        String pwd = Io.password("Admin password");
        try (MongoClient client = Mongo.connect(host, user, authDb, pwd)) {
            action.accept(client);
        }
    }
}
