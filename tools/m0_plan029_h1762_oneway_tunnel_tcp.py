#!/usr/bin/env python3
"""H1762: real non-CN Windows -> Linux TUN TCP, scoped separately from 028 inbound."""
import json,socket,sys,time
role,local,remote=sys.argv[1:4]
if role not in ("server","client") or local==remote:
    raise RuntimeError("invalid physical TUN TCP role")
marker=b"WBD-PLAN029-H1762-WINDOWS-TUNNEL-TCP"
proof={"role":role,"local":local,"remote":remote}
if role=="server":
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind((local,45902));listener.listen(1);listener.settimeout(26)
        print("PLAN029_H1762_REAL_LINUX_TUN_TCP_READY",flush=True)
        accepted,peer=listener.accept()
        with accepted:
            accepted.settimeout(8)
            if peer[0]!=remote:raise RuntimeError("foreign real TUN TCP source")
            payload=b""
            while len(payload)<len(marker):
                chunk=accepted.recv(4096)
                if not chunk:break
                payload+=chunk
            if payload!=marker or accepted.recv(1)!=b"":
                raise RuntimeError("real Linux TUN TCP request/FIN mismatch")
            accepted.sendall(marker+b"-reply")
            accepted.shutdown(socket.SHUT_WR)
            proof["received_bytes"]=len(payload)
            proof["client_ip"]=peer[0]
else:
    first=None
    deadline=time.monotonic()+23
    while time.monotonic()<deadline:
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as client:
                client.bind((local,0));client.settimeout(3)
                client.connect((remote,45902))
                if client.getsockname()[0]!=local or client.getpeername()!=(remote,45902):
                    raise RuntimeError("Windows real TUN TCP source/peer mismatch")
                client.sendall(marker)
                client.shutdown(socket.SHUT_WR)
                reply=b""
                while len(reply)<len(marker)+6:
                    chunk=client.recv(4096)
                    if not chunk:break
                    reply+=chunk
                if reply!=marker+b"-reply" or client.recv(1)!=b"":
                    raise RuntimeError("Windows TUN TCP echo/FIN mismatch")
                proof["echo_bytes"]=len(reply)
                proof["client_echo"]=True
            break
        except (OSError,TimeoutError) as exc:
            first=first or str(exc)
            time.sleep(.2)
    if not proof.get("client_echo"):
        raise RuntimeError("Windows->Linux nonCN TUN TCP delivery failed first="+str(first))
print("PLAN029_H1762_ONEWAY_TUN_TCP "+json.dumps(proof,sort_keys=True),flush=True)
