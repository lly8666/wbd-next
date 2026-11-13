#!/usr/bin/env python3
"""PLAN029 real Windows app FakeIP -> original Wintun -> kernel TCP."""
import json,socket,sys,time
lease,fake=sys.argv[1:3]
if not fake.startswith("198.18.") or lease!="10.66.0.2":
    raise RuntimeError("wrong bounded original Wintun lease or CN FakeIP")
payload=(b"PLAN029-H1760-DIRECT-KERNEL-TCP-"*1024)[:32768]
started=time.monotonic()
with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
    s.settimeout(20);s.bind((lease,0));s.connect((fake,46112))
    connected=time.monotonic()
    if s.getsockname()[0]!=lease or s.getpeername()!=(fake,46112):
        raise RuntimeError("Windows original kernel socket escaped FakeIP")
    s.sendall(payload);s.shutdown(socket.SHUT_WR)
    returned=bytearray()
    while len(returned)<len(payload):
        chunk=s.recv(4096)
        if not chunk:break
        returned.extend(chunk)
    if returned!=payload:
        raise RuntimeError("Windows Direct kernel TCP two-leg/half-close echo mismatch")
print("PLAN029_H1760_WINDOWS_FAKEIP_DIRECT_TCP_ECHO "+json.dumps({
    "source_lease":lease,"presented_peer":fake,
    "app_bytes_sent":len(payload),"app_bytes_echoed":len(returned),
    "tcp_connect_ms":round((connected-started)*1000,3),
    "tcp_total_ms":round((time.monotonic()-started)*1000,3),
    "tcp_two_leg_echo":True,"tcp_half_close":True,
    "socket":"REAL_WINDOWS_KERNEL_TCP_ORIGINAL_WINTUN"},sort_keys=True),flush=True)
