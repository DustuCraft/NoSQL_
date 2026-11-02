"""Poll replica set state; print compact role table and rs.status() summary."""
import sys
import time
import json
import minimongo as m

PORTS = [27101, 27102, 27103]


def hello_state(port, timeout=3):
    try:
        with m.Client(port=port, timeout=timeout) as c:
            h = c.command("admin", {"hello": 1})
            return h
    except Exception:
        return None


def role(port):
    h = hello_state(port)
    if h is None:
        return "DOWN", None
    if h.get("isWritablePrimary"):
        return "PRIMARY", h
    if h.get("secondary"):
        return "SECONDARY", h
    return "OTHER", h


def wait_primary(deadline=60.0):
    end = time.time() + deadline
    while time.time() < end:
        for p in PORTS:
            r, h = role(p)
            if r == "PRIMARY":
                return p
        time.sleep(0.2)
    return None


def print_table():
    for p in PORTS:
        r, h = role(p)
        extra = ""
        if h:
            extra = "set=%s" % h.get("setName")
        print("  %d  %-9s %s" % (p, r, extra))


def status_summary(port):
    with m.Client(port=port) as c:
        s = c.command("admin", {"replSetGetStatus": 1})
    rows = []
    for mem in s.get("members", []):
        rows.append({
            "name": mem.get("name"),
            "state": mem.get("stateStr"),
            "health": mem.get("health"),
            "optime": mem.get("optimeDate"),
            "lag": mem.get("optimeLag"),
        })
    return {
        "set": s.get("set"),
        "myState": s.get("myState"),
        "term": s.get("term"),
        "members": rows,
    }


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "wait":
        p = wait_primary(float(sys.argv[2]) if len(sys.argv) > 2 else 60)
        print("PRIMARY is on port", p)
        print_table()
    elif cmd == "status":
        print_table()
        for p in PORTS:
            try:
                print(json.dumps(status_summary(p), indent=2, default=str, ensure_ascii=False))
                break
            except Exception:
                continue
