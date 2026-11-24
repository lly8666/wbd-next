#!/usr/bin/env python3
# Disposable emulator host ordinary UID UDP control; no privileged sockets.
import socket
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.bind(("127.0.0.1",43999))
    print("B94_UID_FIXTURE_READY",flush=True)
    while True:
        data,peer=s.recvfrom(2048)
        if data in (b"WBD_B90_UID",b"WBD_B94_UID4"):
            s.sendto(data,peer)
            print("B94_UID_HOST_ECHO",data.decode("ascii"),flush=True)
