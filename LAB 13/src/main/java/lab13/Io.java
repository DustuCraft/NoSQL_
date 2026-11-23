package lab13;

import java.io.Console;
import java.util.Scanner;

/** Ввод с консоли IDEA / терминала. Пароли нигде не сохраняются. */
final class Io {
    private static final Scanner IN = new Scanner(System.in);

    static String ask(String prompt, String def) {
        System.out.print(prompt + " [" + def + "]: ");
        String s = IN.nextLine().trim();
        return s.isEmpty() ? def : s;
    }

    static String password(String prompt) {
        Console c = System.console();
        if (c != null) {
            return new String(c.readPassword("%s: ", prompt));
        }
        // в консоли Run IntelliJ IDEA System.console() == null, ввод будет виден
        System.out.print(prompt + ": ");
        return IN.nextLine();
    }

    private Io() {}
}
