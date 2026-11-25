#!/usr/bin/env python3
import socket,sys,json
mode=sys.argv[1]
if mode=="wan":
    try:
        with socket.create_connection(("10.248.82.2",46180),timeout=2):
            raise AssertionError("transparent listener exposed on ordinary WAN address")
    except ConnectionRefusedError:print(json.dumps({"ordinary_wan_refused":True}))
else:
    with socket.create_connection(("127.0.0.1",46180),timeout=2) as c:
        c.settimeout(2)
        try:assert c.recv(1)==b""
        except ConnectionResetError:pass
    print(json.dumps({"direct_loopback_closed":True}))
