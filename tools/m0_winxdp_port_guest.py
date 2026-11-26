"""Real WSL TCP stack, two distinct connections to an exclusively owned port."""
import socket,sys,threading
host=sys.argv[1]
with socket.create_connection((host,39462),timeout=6) as s:
    assert s.recv(64)==b"ORDINARY_TCP_OK"
print("ORDINARY_TCP_RECEIPT=1",flush=True)
def attempt(port):
    with socket.socket() as s:
        s.settimeout(2)
        s.bind(("",port))
        try:
            s.connect((host,39461))
            raise AssertionError("owned raw destination unexpectedly accepted TCP")
        except (TimeoutError,ConnectionRefusedError):
            pass
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(attempt,(39501,39502)))
print("TWO_REAL_SYN_SOURCES=1",flush=True)
