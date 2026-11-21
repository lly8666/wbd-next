#!/usr/bin/env python3
"""H2286 actual OS UDP on Windows original Wintun / native ARM Go/Rust TUN.

Pure socket fixture, never invents a fake authenticated READY/ACK/packet.
The Go client and Linux server must own real OS interfaces for this to work.
"""
import json
import pathlib
import socket
import sys
import time

PORT=45901


def run(local,remote,source,receipt):
    require= lambda cond,msg: cond or (_ for _ in ()).throw(RuntimeError(msg))
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try:
        until=time.monotonic()+105
        while True:
            try:
                sock.bind((local,PORT))
                break
            except OSError as err:
                if time.monotonic()>until:
                    raise RuntimeError("H2286_REAL_OS_TUN_IP_NOT_BOUND") from err
                time.sleep(.2)
        sock.setblocking(False)
        print("H2286_TRUE_OS_TUN_UDP_BIND role="+local,flush=True)
        deadline=time.monotonic()+350
        sent=received=0
        next_send=time.monotonic()
        peers=set()
        while time.monotonic()<deadline:
            now=time.monotonic()
            if now>=next_send:
                try:
                    sock.sendto(("H2286-REAL-UDP-"+source[:12]+"-"+str(sent)).encode(),
                                (remote,PORT))
                    sent+=1
                except OSError:pass
                next_send+=.09
                if next_send<now-.02:next_send=now
            while True:
                try: packet,peer=sock.recvfrom(1024)
                except BlockingIOError:break
                if peer[0]==remote and packet.startswith(("H2286-REAL-UDP-"+source[:12]).encode()):
                    received+=1
                    peers.add(peer[0])
                    if received in (1,12,100):
                        print("H2286_NATIVE_REAL_TUN_UDP_RX_COUNT="+str(received),
                              flush=True)
            if pathlib.Path(receipt).exists() and received>=12 and sent>=24:
                result={"local":local,"remote":remote,"source_sha":source,
                        "real_native_os_udp_sent":sent,"real_native_os_udp_received":received,
                        "remote_lease_ips":sorted(peers),
                        "original_product_tun_required":True,
                        "status":"PASS_H2286_TRUE_KERNEL_WINTUN_ARM_TUN_UDP"}
                pathlib.Path(str(receipt)+".udp.json").write_text(json.dumps(result,indent=2)+"\n")
                print("H2286_REAL_WINTUN_ARM_TUN_UDP_APP_DONE "+json.dumps(result),flush=True)
                return
            time.sleep(.015)
        raise RuntimeError("H2286_ORIGINAL_PRODUCT_NATIVE_TUN_UDP_NOT_DUPLEX "+
                           json.dumps({"sent":sent,"received":received}))
    finally:sock.close()


if __name__=="__main__":
    if len(sys.argv)!=5:raise SystemExit("usage: udp.py local remote source receipt_flag")
    run(*sys.argv[1:])
