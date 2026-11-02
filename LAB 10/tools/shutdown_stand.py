"""Gracefully shut down all three lab nodes (used by stop_stand.ps1)."""
import sys
import time

import minimongo as m

for port in (27101, 27102, 27103):
    try:
        with m.Client(port=port, timeout=5) as c:
            c.command("admin", {"shutdown": 1, "force": True, "timeoutSecs": 5}, check=False)
        print("shutdown sent to %d" % port)
    except Exception as e:
        print("port %d: %s" % (port, type(e).__name__))
    time.sleep(1.0)

end = time.time() + 30
while time.time() < end:
    alive = 0
    for port in (27101, 27102, 27103):
        try:
            with m.Client(port=port, timeout=0.5) as c:
                c.command("admin", {"hello": 1})
            alive += 1
        except Exception:
            pass
    if alive == 0:
        print("all nodes stopped")
        sys.exit(0)
    time.sleep(1.0)
print("some nodes still answering")
sys.exit(1)
