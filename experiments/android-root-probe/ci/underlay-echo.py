#!/usr/bin/env python3
"""One ephemeral emulator-host plain TCP plus authenticated TLS nonce echo."""
import socketserver
import ssl
import threading
import sys

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True

class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        raw=self.rfile.readline(160)
        tokenline=raw.decode("ascii",errors="replace").strip()
        if not tokenline.startswith("wbd-host-") or len(tokenline)>128:
            self.wfile.write(b"INVALID\n")
            return
        token=tokenline[len("wbd-host-"):]
        self.wfile.write(("wbd-underlay-ok-"+token+"\n").encode("ascii"))
        self.wfile.flush()
        print("HOST_ACCEPT "+token,flush=True)

class TLSHandler(socketserver.StreamRequestHandler):
    def handle(self):
        tokenline=self.rfile.readline(160).decode("ascii",errors="replace").strip()
        if not tokenline.startswith("wbd-tls-") or len(tokenline)>128:
            self.wfile.write(b"INVALID\n")
            return
        token=tokenline[len("wbd-tls-"):]
        version=self.connection.version()
        cipher=self.connection.cipher()[0]
        self.wfile.write(("wbd-tls-ok-"+token+"\n").encode("ascii"))
        self.wfile.flush()
        print("HOST_TLS_ACCEPT "+token+" protocol="+str(version)+" cipher="+str(cipher),flush=True)

class TLSServer(Server):
    def __init__(self, address, handler, context):
        self.context=context
        super().__init__(address,handler)
    def get_request(self):
        sock,addr=super().get_request()
        try:
            tls=self.context.wrap_socket(sock,server_side=True)
        except Exception:
            sock.close()
            raise
        return tls,addr

def main(cert,key):
    ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version=ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(cert,key)
    with Server(("0.0.0.0",18317),Handler) as plain, \
         TLSServer(("0.0.0.0",18318),TLSHandler,ctx) as tls:
        threading.Thread(target=plain.serve_forever,daemon=True).start()
        print("HOST_READY_18317",flush=True)
        print("HOST_TLS_READY_18318",flush=True)
        tls.serve_forever(poll_interval=0.25)

if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: underlay-echo.py <ephemeral-cert.pem> <ephemeral-key.pem>")
    main(sys.argv[1],sys.argv[2])
