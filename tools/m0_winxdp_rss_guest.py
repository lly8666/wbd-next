"""Real guest TCP SYNs, identical 32 source-port tuples across both arms."""
import socket,sys
from concurrent.futures import ThreadPoolExecutor
host=sys.argv[1]
with socket.create_connection((host,39464),timeout=5) as s:
    assert s.recv(64)==b"ORDINARY_TCP_OK"
print("ORDINARY_TCP_RECEIPT=1",flush=True)
def attempt(port):
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        s.settimeout(1.5)
        s.bind(("",port))
        try:
            s.connect((host,39463))
            raise AssertionError("reserved non-listening port connected")
        except (TimeoutError,ConnectionRefusedError) as e:
            return (port,type(e).__name__)
with ThreadPoolExecutor(max_workers=32) as pool:
    rows=list(pool.map(attempt,range(39500,39532)))
print("REAL_SYN_ROSTER="+str(rows),flush=True)
