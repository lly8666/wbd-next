#!/usr/bin/env python3
"""PLAN029 real WSL2 physical TCP echo; no synthetic ACK/probe."""
import json,socket,sys,time,hashlib
physical,expected_windows_source=sys.argv[1:3]
listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
listener.bind((physical,46112));listener.listen(1);listener.settimeout(28)
print("PLAN029_H1760_PHYSICAL_KERNEL_TCP46112_READY",flush=True)
started=time.monotonic()
with listener:
    conn,peer=listener.accept()
    print("PLAN029_H1762_PHYSICAL_TCP_ACCEPT peer="+repr(peer),flush=True)
    if peer[0]!=expected_windows_source:
        raise RuntimeError("Direct TCP physical socket unexpected source "+repr(peer))
    with conn:
        conn.settimeout(20);data=bytearray()
        while True:
            try:
                chunk=conn.recv(4096)
            except TimeoutError:
                # H1906: no retry or widened TCP timeout. Record exactly
                # what the *real Linux kernel socket* had delivered before
                # the original 20-second FIN deadline, not an assumption
                # derived from Windows sendall() completion. Never log
                # application payload, secrets or raw TCP frames.
                try:
                    info=conn.getsockopt(socket.IPPROTO_TCP,socket.TCP_INFO,104)
                    tcp_state=info[0] if info else "EMPTY_TCP_INFO"
                except (AttributeError,OSError):
                    tcp_state="UNAVAILABLE"
                expected=(b"PLAN029-H1760-DIRECT-KERNEL-TCP-"*1024)[:32768]
                try:so_error=conn.getsockopt(socket.SOL_SOCKET,socket.SO_ERROR)
                except OSError:so_error="UNAVAILABLE"
                print("PLAN029_H1906_LINUX_PHYSICAL_TCP_FIN_STALL "+
                    json.dumps({
                        "received_bytes":len(data),
                        "payload_sha256_matches_if_full":(
                            len(data)==32768 and
                            hashlib.sha256(data).digest()==hashlib.sha256(expected).digest()),
                        "tcp_info_state_code":tcp_state,
                        "socket_so_error":so_error,
                        "recv_deadline_seconds":20,
                        "source":"REAL_WSL2_LINUX_PHYSICAL_KERNEL_TCP"
                    },sort_keys=True),flush=True)
                raise
            if not chunk:break
            data.extend(chunk)
            if len(data)>32768:raise RuntimeError("Direct TCP unbounded client bytes")
            if len(data)==32768:
                print("PLAN029_H1906_LINUX_FULL_32K_WAIT_FIN source=REAL_WSL2_KERNEL_TCP",
                      flush=True)
        print("PLAN029_H1762_PHYSICAL_TCP_FIN_RECEIVED bytes="+str(len(data)),flush=True)
        expected=(b"PLAN029-H1760-DIRECT-KERNEL-TCP-"*1024)[:32768]
        if data!=expected:
            raise RuntimeError("physical kernel TCP got wrong or partial app data")
        conn.sendall(data);conn.shutdown(socket.SHUT_WR)
print("PLAN029_H1760_LINUX_PHYSICAL_TCP_ECHO "+json.dumps({
    "source_physical":peer[0],"source_port":peer[1],
    "real_socket":physical,"port":46112,"received_bytes":len(data),
    "echo_sent_bytes":len(data),"elapsed_ms":round((time.monotonic()-started)*1000,3),
    "true_kernel_socket":True},sort_keys=True),flush=True)
