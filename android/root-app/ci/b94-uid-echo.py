#!/usr/bin/env python3
# Local-only fixture on a disposable Actions host. The two exact addresses
# are assigned to host lo by the test script before any guest request.
import select
import socket
sockets=[]
try:
    for ip in ("127.0.0.1","192.0.2.1","1.0.1.1"):
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.bind((ip,43999));sockets.append(s)
    print("B94_UID_FIXTURE_READY",flush=True)
    while True:
        ready,_,_=select.select(sockets,[],[],10)
        for s in ready:
            data,peer=s.recvfrom(2048)
            if data in (b"WBD_B90_UID",b"WBD_B94_UID4") and s.getsockname()[0]=="127.0.0.1":
                s.sendto(data,peer)
                print("B94_UID_HOST_ECHO",data.decode("ascii"),flush=True)
            elif data.startswith(b"WBD_B99_") and data[8:].isdigit() and s.getsockname()[0]!="127.0.0.1":
                s.sendto(b"HOST_"+data,peer)
                print("B99_UID_HOST_ECHO",s.getsockname()[0],data.decode("ascii"),flush=True)
finally:
    for s in sockets:s.close()
