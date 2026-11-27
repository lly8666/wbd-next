"""Actual Linux kernel SYNs to five ports in three announced phases."""
import concurrent.futures, pathlib, socket, sys, time
host, log = sys.argv[1:]
log=pathlib.Path(log)
def attempt(item):
    phase,slot,i=item
    with socket.socket() as s:
        s.settimeout(.25)
        src=46000+phase*100+slot*6+i
        s.bind(("",src))
        try:
            s.connect((host,39461+slot))
        except (TimeoutError,ConnectionRefusedError):
            return src
        raise RuntimeError("fixture port unexpectedly accepted TCP")
for phase in range(3):
    until=time.monotonic()+20
    while f"PORTSET_PHASE {phase}" not in log.read_text(errors="replace"):
        if time.monotonic()>=until:raise RuntimeError("phase marker missing")
        time.sleep(.05)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        sources=list(pool.map(attempt,[(phase,slot,i) for slot in range(5) for i in range(6)]))
    print(f"LINUX_PORTSET_SYN phase={phase} sources={sources}",flush=True)
