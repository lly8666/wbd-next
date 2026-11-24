#!/usr/bin/env python3
"""Explicitly run on a test server's tunnel-side address, never auto-deployed."""
import argparse
import socket
import socketserver
import subprocess
import threading
from contextlib import ExitStack

class TCP(socketserver.BaseRequestHandler):
    def handle(self):
        while True:
            data=self.request.recv(65536)
            if not data:return
            self.request.sendall(data)

class UDP(socketserver.BaseRequestHandler):
    def handle(self):
        data,sock=self.request
        sock.sendto(data,self.client_address)

class TCPServer(socketserver.ThreadingTCPServer):
    daemon_threads=True
    allow_reuse_address=True

class UDPServer(socketserver.UDPServer):
    allow_reuse_address=True

def serve(host,port,classes=None):
    family=socket.AF_INET6 if ":" in host else socket.AF_INET
    TCPServer.address_family=UDPServer.address_family=family
    with ExitStack() as stack:
        tcp=stack.enter_context(TCPServer((host,port),TCP))
        port=tcp.server_address[1]
        udp=stack.enter_context(UDPServer((host,port),UDP))
        for s in (tcp,udp):
            threading.Thread(target=s.serve_forever,daemon=True).start()
        try:
            if classes:
                result=subprocess.check_output(["java","-cp",classes,
                    "org.wbdnext.testtraffic.TrafficProbe",host,str(port),"8","1"],
                    text=True,timeout=30)
                print(result.strip())
                assert "tcp_ok=8 udp_ok=8 samples=8" in result
                assert "echo_bytes_each_direction=1048576" in result
                print("WBD_TRAFFIC_FIXTURE_HOST_LOOPBACK_PASS")
            else:
                print(f"WBD test echo TCP+UDP {host}:{port}",flush=True)
                threading.Event().wait()
        finally:
            tcp.shutdown();udp.shutdown()

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bind",required=True)
    p.add_argument("--port",type=int,default=18080)
    p.add_argument("--java-classes",help="local fixture self-test, not WBD qualification")
    a=p.parse_args()
    serve(a.bind,a.port,a.java_classes)
