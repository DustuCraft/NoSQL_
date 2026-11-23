package lab13;

import com.mongodb.MongoException;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoDatabase;
import com.mongodb.client.model.Filters;
import com.mongodb.client.model.Updates;
import org.bson.Document;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/** 11 проверок: 5 разрешённых и 6 запрещённых. Каждый пользователь подключается отдельно. */
final class AccessTests {

    private interface Op { void run(MongoDatabase db); }

    private record Case(String user, String action, boolean expectAllowed, Op op) {}

    private static final List<Case> CASES = List.of(
            new Case(Config.USER_VIEWER, "find tickets", true,
                    db -> db.getCollection(Config.WORK).find(Filters.eq("ticketId", 2001)).first()),
            new Case(Config.USER_VIEWER, "insert tickets", false,
                    db -> db.getCollection(Config.WORK).insertOne(new Document("ticketId", 2999))),
            new Case(Config.USER_VIEWER, "find internal_notes", false,
                    db -> db.getCollection(Config.PROTECTED).find(Filters.eq("ticketId", 2001)).first()),

            new Case(Config.USER_EDITOR, "find tickets", true,
                    db -> db.getCollection(Config.WORK).find(Filters.eq("ticketId", 2001)).first()),
            new Case(Config.USER_EDITOR, "insert tickets", true,
                    db -> db.getCollection(Config.WORK).insertOne(new Document("ticketId", 2998).append("subject", "test"))),
            new Case(Config.USER_EDITOR, "update tickets", true,
                    db -> db.getCollection(Config.WORK).updateOne(Filters.eq("ticketId", 2998), Updates.set("status", "closed"))),
            new Case(Config.USER_EDITOR, "remove tickets", false,
                    db -> db.getCollection(Config.WORK).deleteOne(Filters.eq("ticketId", 2998))),
            new Case(Config.USER_EDITOR, "find internal_notes", false,
                    db -> db.getCollection(Config.PROTECTED).find(Filters.eq("ticketId", 2001)).first()),

            new Case(Config.USER_AUDITOR, "find audit_events", true,
                    db -> db.getCollection(Config.AUDIT).find(Filters.eq("event", "seed")).first()),
            new Case(Config.USER_AUDITOR, "insert audit_events", false,
                    db -> db.getCollection(Config.AUDIT).insertOne(new Document("event", "forged"))),
            new Case(Config.USER_AUDITOR, "find tickets", false,
                    db -> db.getCollection(Config.WORK).find(Filters.eq("ticketId", 2001)).first())
    );

    static void run(String hostPort) {
        List<String> rows = new ArrayList<>();
        int pass = 0;
        for (String user : List.of(Config.USER_VIEWER, Config.USER_EDITOR, Config.USER_AUDITOR)) {
            String pwd = Io.password("Password for " + user);
            try (MongoClient client = Mongo.connect(hostPort, user, Config.DB, pwd)) {
                MongoDatabase db = client.getDatabase(Config.DB);
                for (Case c : CASES) {
                    if (!c.user().equals(user)) continue;
                    String actual = execute(c.op(), db);
                    String expected = c.expectAllowed() ? "Allowed" : "Unauthorized";
                    boolean ok = expected.equals(actual);
                    if (ok) pass++;
                    String line = String.format("%-9s | %-20s | expected: %-12s | actual: %-12s | %s",
                            user, c.action(), expected, actual, ok ? "PASS" : "FAIL");
                    System.out.println(line);
                    rows.add("| " + user + " | " + c.action() + " | " + expected + " | " + actual
                            + " | " + (ok ? "PASS" : "FAIL") + " |");
                }
            } catch (MongoException e) {
                System.out.println("Cannot log in as " + user + ": " + e.getMessage());
            }
        }
        System.out.println("Result: " + pass + " / " + CASES.size() + " passed");
        save(rows);
    }

    private static String execute(Op op, MongoDatabase db) {
        try {
            op.run(db);
            return "Allowed";
        } catch (MongoException e) {
            boolean unauthorized = e.getCode() == 13
                    || (e.getMessage() != null && e.getMessage().toLowerCase().contains("not authorized"));
            return unauthorized ? "Unauthorized" : "Error: " + e.getMessage();
        }
    }

    /** Таблица для отчёта (без паролей). */
    private static void save(List<String> rows) {
        StringBuilder sb = new StringBuilder("| User | Action | Expected | Actual | Verdict |\n|---|---|---|---|---|\n");
        rows.forEach(r -> sb.append(r).append('\n'));
        try {
            Files.writeString(Path.of("test-results.md"), sb.toString());
            System.out.println("Table saved to test-results.md");
        } catch (IOException e) {
            System.out.println("Could not save test-results.md: " + e.getMessage());
        }
    }

    private AccessTests() {}
}
