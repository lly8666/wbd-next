#!/usr/bin/env python3
"""Ephemeral host-only TCP echo for Android emulator 10.0.2.2, not Internet."""
import socketserver
import sys
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True
class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        data=self.rfile.readline(160).decode("ascii",errors="replace").strip()
        if not data.startswith("wbd-host-") or len(data)>128:
            self.wfile.write(b"INVALID\n")
            return
        token=data[len("wbd-host-"):]
        self.wfile.write(("wbd-underlay-ok-"+token+"\n").encode("ascii"))
        self.wfile.flush()
        print("HOST_ACCEPT "+token,flush=True)
if __name__=="__main__":
    with Server(("0.0.0.0",18317),Handler) as server:
        print("HOST_READY_18317",flush=True)
        server.serve_forever(poll_interval=0.25)
