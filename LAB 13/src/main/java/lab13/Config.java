package lab13;

/** Константы варианта 19: Служба поддержки. Паролей здесь нет — они вводятся при запуске. */
final class Config {
    static final String DB = "support_lab13";
    static final String WORK = "tickets";
    static final String PROTECTED = "internal_notes";
    static final String AUDIT = "audit_events";

    static final String ROLE_VIEWER = "ticketViewer";
    static final String ROLE_EDITOR = "ticketEditor";
    static final String ROLE_AUDITOR = "eventAuditor";

    static final String USER_VIEWER = "viewer19";
    static final String USER_EDITOR = "editor19";
    static final String USER_AUDITOR = "auditor19";

    private Config() {}
}
