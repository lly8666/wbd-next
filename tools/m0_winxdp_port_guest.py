"""Real WSL TCP stack, two distinct connections to an exclusively owned port."""
import socket,sys,threading
host=sys.argv[1]
owned=int(sys.argv[2])
with socket.create_connection((host,owned+1),timeout=6) as s:
    assert s.recv(64)==b"ORDINARY_TCP_OK"
print("ORDINARY_TCP_RECEIPT=1",flush=True)
def attempt(port):
    with socket.socket() as s:
        s.settimeout(2)
        s.bind(("",port))
        try:
            s.connect((host,owned))
            raise AssertionError("owned raw destination unexpectedly accepted TCP")
        except (TimeoutError,ConnectionRefusedError) as e:
            print(f"SYN_ATTEMPT source={port} result={type(e).__name__}",flush=True)
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(attempt,(owned+40,owned+41)))
print("TWO_REAL_SYN_SOURCES=1",flush=True)
