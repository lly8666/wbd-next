#!/usr/bin/env python3
"""Ordinary TCP/UDP/DNS sockets only, isolated network namespaces."""
import socket
import sys
import threading
import struct
import ipaddress

def exact(s,n):
    out=bytearray()
    while len(out)<n:
        part=s.recv(n-len(out))
        if not part: raise EOFError("early TCP close")
        out.extend(part)
    return bytes(out)

Q=bytes.fromhex("123401000001000000000000")+b"\x05local\x04test\x00"+bytes.fromhex("00010001")
A=Q[:2]+bytes.fromhex("81800001000100000000")+Q[12:]+bytes.fromhex("c00c000100010000003c0004c0000237")
def sockets(addr,port):
    family=socket.AF_INET6 if ":" in addr else socket.AF_INET
    return family,(addr,int(port))

def serve(addr,port,source,kind):
    family,bound=sockets(addr,port)
    tcp=socket.socket(family,socket.SOCK_STREAM);tcp.bind(bound);tcp.listen(8)
    udp=socket.socket(family,socket.SOCK_DGRAM);udp.bind(bound)
    def accepted(peer,address):
        with peer:
            peer.settimeout(10)
            if ipaddress.ip_address(address[0])!=ipaddress.ip_address(source):return
            if kind=="dns":
                n=struct.unpack("!H",exact(peer,2))[0]
                if exact(peer,n)==Q:peer.sendall(struct.pack("!H",len(A))+A)
            else:
                peer.sendall(kind.encode()+b"\n")
                while True:
                    b=peer.recv(65536)
                    if not b:break
                    peer.sendall(b)
    def udp_loop():
        while True:
            b,a=udp.recvfrom(65535)
            if ipaddress.ip_address(a[0])!=ipaddress.ip_address(source):continue
            if kind=="dns":
                if b==Q:udp.sendto(A,a)
            else:udp.sendto(kind.encode()+b":"+b,a)
    threading.Thread(target=udp_loop,daemon=True).start()
    print("B104_SOCKET_READY",flush=True)
    while True:
        p,a=tcp.accept()
        threading.Thread(target=accepted,args=(p,a),daemon=True).start()

def client(addr,port,kind):
    family,bound=sockets(addr,port)
    with socket.socket(family,socket.SOCK_DGRAM) as u:
        u.settimeout(5);u.connect(bound)
        if kind=="dns":
            u.send(Q);assert u.recv(512)==A
        else:
            for i in range(8):
                q=("ordinary-udp-%d"%i).encode();u.send(q)
                assert u.recv(1024)==kind.encode()+b":"+q
    with socket.socket(family,socket.SOCK_STREAM) as t:
        t.settimeout(8);t.connect(bound)
        if kind=="dns":
            t.sendall(struct.pack("!H",len(Q))+Q)
            assert exact(t,struct.unpack("!H",exact(t,2))[0])==A
        else:
            assert exact(t,len(kind)+1)==kind.encode()+b"\n"
            data=bytes(range(256))*4096
            t.sendall(data[:65536])
            assert exact(t,65536)==data[:65536]
            for i in range(65536,len(data),65536):
                part=data[i:i+65536];t.sendall(part);assert exact(t,len(part))==part
    print("B104_SOCKET_ROUNDTRIP_PASS",kind,addr,"udp_tcp=1",flush=True)
if __name__=="__main__":
    if sys.argv[1]=="serve":serve(*sys.argv[2:])
    elif sys.argv[1]=="client":client(*sys.argv[2:])
    else:raise SystemExit(2)
