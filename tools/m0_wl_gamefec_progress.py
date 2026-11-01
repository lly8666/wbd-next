"""Game FEC native test stage sampler, not a watchdog or product control.

Read only bounded NEW bytes from existing original Go/Rust child logs and
emit stage names plus de-identified worker first fault, without packet data.
"""
import os
import pathlib
import re
import subprocess
import time

MARKERS = (
    ("WBD_WINDOWS_CLIENT_READY", "CLIENT_READY"),
    ("V4_ORIGINAL_GO_GAME_NATIVE_READY", "SERVER_READY"),
    ("WBD_WINDOWS_OS_APPLIED", "OS_APPLIED"),
    ("M0_PLAN027_GAME_DUE_FAULT stage=send_records_entry", "FEC_DUE_ENTRY"),
    ("M0_PLAN027_GAME_NATIVE_STOP_JOIN", "NATIVE_WORKERS_JOINED"),
    ("M0_PLAN027_GAME_NATIVE_STOP_NOT_DRAINED", "NATIVE_STOP_NOT_DRAINED"),
    ("WBD_WINDOWS_GAME_NATIVE_DISCONNECTED", "WAL_RESTORED"),
    ("V4_PUBLIC_GAME_NATIVE_STOP_DRAINED", "LINUX_NATIVE_STOP"),
)
FAULT = re.compile(
    r"M0_PLAN027_GAME_DUE_FAULT first_failure=1"
    r"|M0_PLAN026_GAME_NATIVE_FIRST_ERROR"
    r"|M0_PLAN027_GAME_NATIVE_STOP_NOT_DRAINED"
    r"|M0_PLAN027_NATIVE_STOP_RESULT stage=wal_disconnect result=FAIL"
    r"|WL_GAME_ORIGINAL_STOP_FAILURE"
)
SAFE_FIELD = re.compile(r"\b(stage|origin|lane|rc|cipher_len|path_mtu|tx_finished|rx_finished)=([A-Za-z0-9_-]{1,36})")

def _safe(value, n=80):
    return re.sub(r"[^A-Za-z0-9_.:-]", "_", str(value or "UNKNOWN"))[:n]

class GameFecProgress:
    def __init__(self, output, *, env=None, relay=None, now=None):
        self.out = pathlib.Path(output)
        self.env = os.environ if env is None else env
        self.relay = relay
        self.now = now or time.monotonic
        self.offset = {}
        self.partials = {}
        self.stage = "MODE_STARTED"
        self.first_error = "UNKNOWN"
        self.markers = set()
        self.last_heartbeat = self.now()
        self.signalled = set()

    def snapshot(self, event):
        if event in self.signalled:
            return
        self.signalled.add(event)
        detail = _safe(self.first_error if event == "FIRST_ERROR" else self.stage)
        print("WL_GAME_RESCUE_INTENT event="+event+" stage="+_safe(self.stage)+
              " first_error="+_safe(self.first_error), flush=True)
        if self.relay is not None:
            self.relay(event, detail)
        elif self.env.get("WBD_WL_GAME_FEC_RESCUE") == "1":
            args = ["gh", "workflow", "run",
                    "m0-plan027-gamefec-rescue-record.yml", "--repo",
                    self.env.get("GITHUB_REPOSITORY", "lly8666/wbd-next"),
                    "--ref", "main",
                    "-f", "target_run="+_safe(self.env.get("GITHUB_RUN_ID"), 30),
                    "-f", "source="+_safe(self.env.get("WBD_WL_BINARY_SOURCE")
                                         or self.env.get("GITHUB_SHA"), 60),
                    "-f", "stage="+event, "-f", "detail="+detail]
            try:
                result = subprocess.run(args, capture_output=True, timeout=8, check=False)
                print("WL_GAME_RESCUE_DISPATCH event="+event+
                      " status="+("QUEUED_NOT_PRODUCT_PASS" if result.returncode == 0
                                 else "UNAVAILABLE"), flush=True)
            except (OSError, subprocess.TimeoutExpired):
                print("WL_GAME_RESCUE_DISPATCH event="+event+" status=UNAVAILABLE", flush=True)

    def poll(self):
        for name in ("client.log", "server.log", "windows-app.log", "linux-app.log"):
            path = self.out/name
            try:
                with path.open("rb") as handle:
                    handle.seek(0, 2)
                    end = handle.tell()
                    previous = self.offset.get(name, 0)
                    if end < previous:
                        previous = 0
                        self.partials[name] = b""
                    handle.seek(previous)
                    chunk = handle.read(65536)
                    self.offset[name] = previous + len(chunk)
            except OSError:
                continue
            if not chunk:
                continue
            fragments = (self.partials.get(name, b"")+chunk).split(b"\n")
            self.partials[name] = fragments.pop()[-1024:]
            for raw in fragments:
                line = raw.decode("utf-8", "replace")[:2048]
                for marker, stage in MARKERS:
                    if marker in line and stage not in self.markers:
                        self.markers.add(stage)
                        self.stage = stage
                        print("WL_GAME_NATIVE_STAGE file="+name+" stage="+stage, flush=True)
                        if stage in ("CLIENT_READY","SERVER_READY") and (
                            "CLIENT_READY" in self.markers and "SERVER_READY" in self.markers):
                            self.snapshot("BOTH_READY")
                if name.endswith("app.log") and '"phase": "udp_1hz"' in line:
                    self.stage = "REAL_UDP_IN_PROGRESS"
                if FAULT.search(line) and self.first_error=="UNKNOWN":
                    fields = {k:v for k,v in SAFE_FIELD.findall(line)}
                    self.first_error = _safe(fields.get("stage", "WORKER_FATAL"))
                    self.stage = "FIRST_FAULT"
                    print("WL_GAME_NATIVE_FIRST_FAULT file="+name+
                          " kind="+self.first_error+
                          " lane="+_safe(fields.get("lane"))+
                          " rc="+_safe(fields.get("rc"))+
                          " cipher_len="+_safe(fields.get("cipher_len"))+
                          " path_mtu="+_safe(fields.get("path_mtu")), flush=True)
                    self.snapshot("FIRST_ERROR")
        now = self.now()
        if now-self.last_heartbeat>=10:
            print("WL_GAME_NATIVE_STAGE_HEARTBEAT stage="+_safe(self.stage)+
                  " first_error="+_safe(self.first_error)+
                  " files="+",".join(sorted(self.offset)), flush=True)
            self.last_heartbeat = now
