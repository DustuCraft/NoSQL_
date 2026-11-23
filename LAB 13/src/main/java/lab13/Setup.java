package lab13;

import com.mongodb.MongoCommandException;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoDatabase;
import org.bson.Document;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.List;

/** Создаёт данные, роли и пользователей. Запускается под администратором. */
final class Setup {

    static void run(MongoClient admin) {
        MongoDatabase db = admin.getDatabase(Config.DB);
        seed(db);
        createRoles(db);
        createUsers(db);
        System.out.println("Setup finished.");
    }

    private static void seed(MongoDatabase db) {
        db.getCollection(Config.WORK).drop();
        db.getCollection(Config.PROTECTED).drop();
        db.getCollection(Config.AUDIT).drop();

        String[] statuses = {"open", "in_progress", "closed"};
        List<Document> tickets = new ArrayList<>();
        List<Document> notes = new ArrayList<>();
        for (int i = 1; i <= 12; i++) {
            tickets.add(new Document("ticketId", 2000 + i)
                    .append("customer", "Customer-" + i)
                    .append("subject", "Synthetic issue #" + i)
                    .append("status", statuses[i % 3])
                    .append("priority", i % 2 == 0 ? "high" : "low")
                    .append("createdAt", new Date()));
            notes.add(new Document("ticketId", 2000 + i)
                    .append("author", "agent-" + (i % 3 + 1))
                    .append("note", "INTERNAL: synthetic confidential note #" + i)
                    .append("createdAt", new Date()));
        }
        db.getCollection(Config.WORK).insertMany(tickets);
        db.getCollection(Config.PROTECTED).insertMany(notes);
        db.getCollection(Config.AUDIT).insertMany(Arrays.asList(
                new Document("event", "seed").append("source", "lab").append("at", new Date()),
                new Document("event", "login").append("source", "support-portal").append("at", new Date()),
                new Document("event", "ticket_closed").append("source", "support-portal").append("at", new Date())));
        System.out.println("Seeded: tickets=12, internal_notes=12, audit_events=3");
    }

    private static Document privilege(String collection, String... actions) {
        return new Document("resource", new Document("db", Config.DB).append("collection", collection))
                .append("actions", Arrays.asList(actions));
    }

    private static void createRole(MongoDatabase db, String role, Document privilege) {
        try { db.runCommand(new Document("dropRole", role)); } catch (MongoCommandException ignored) { }
        db.runCommand(new Document("createRole", role)
                .append("privileges", List.of(privilege))
                .append("roles", List.of()));
        System.out.println("Role created: " + role);
    }

    private static void createRoles(MongoDatabase db) {
        // viewer: только чтение рабочей коллекции
        createRole(db, Config.ROLE_VIEWER, privilege(Config.WORK, "find"));
        // editor: чтение/запись; remove не выдан (тикет закрывается сменой статуса)
        createRole(db, Config.ROLE_EDITOR, privilege(Config.WORK, "find", "insert", "update"));
        // auditor: чтение отдельного журнала
        createRole(db, Config.ROLE_AUDITOR, privilege(Config.AUDIT, "find"));
    }

    private static void createUser(MongoDatabase db, String user, String role) {
        String pwd = Io.password("Set password for " + user);
        try { db.runCommand(new Document("dropUser", user)); } catch (MongoCommandException ignored) { }
        db.runCommand(new Document("createUser", user)
                .append("pwd", pwd)
                .append("roles", List.of(new Document("role", role).append("db", Config.DB))));
        System.out.println("User created: " + user);
    }

    private static void createUsers(MongoDatabase db) {
        createUser(db, Config.USER_VIEWER, Config.ROLE_VIEWER);
        createUser(db, Config.USER_EDITOR, Config.ROLE_EDITOR);
        createUser(db, Config.USER_AUDITOR, Config.ROLE_AUDITOR);
    }

    /** Удаляет тестовые документы editor19 (у него нет права remove). */
    static void cleanup(MongoClient admin) {
        long n = admin.getDatabase(Config.DB).getCollection(Config.WORK)
                .deleteMany(new Document("ticketId", new Document("$in", List.of(2998, 2999))))
                .getDeletedCount();
        System.out.println("Test documents removed: " + n);
    }

    private Setup() {}
}
