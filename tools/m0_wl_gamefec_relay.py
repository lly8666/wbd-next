"""Independent GameFEC diagnosis publisher: observes only, never stops processes.

No stdout, no product bytes, no main-PID file reads or GitHub calls. A distinct
daemon thread may block without affecting the sole PID owner or its deadline.
"""
import os
import pathlib
import queue
import re
import subprocess
import threading

SAFE = re.compile(r"[^A-Za-z0-9_.:-]")
MARKERS = (
    ("gamefec-cold-stage.txt", "COLD_E2E_STARTED", "COLD_E2E_STARTED"),
    ("gamefec-cold-stage.txt", "COLD_WSL_IP_READY", "COLD_WSL_IP_READY"),
    ("gamefec-cold-stage.txt", "COLD_TLS_CERT_READY", "COLD_TLS_CERT_READY"),
    ("gamefec-cold-stage.txt", "COLD_CLIENT_SPAWNED", "COLD_CLIENT_SPAWNED"),
    ("gamefec-cold-stage.txt", "COLD_READY_WAIT", "COLD_READY_WAIT"),
    ("gamefec-cold-stage.txt", "COLD_READY_COMPLETE", "COLD_READY_COMPLETE"),
    ("client.log", "WBD_WINDOWS_GAME_COLD_TLS_JOINED", "CLIENT_TLS_JOINED"),
    ("client.log", "WBD_WINDOWS_GAME_NATIVE_APPLIED", "CLIENT_OS_APPLIED"),
    ("client.log", "WBD_WINDOWS_OS_APPLIED", "OS_APPLIED"),
    ("client.log", "WBD_WINDOWS_CLIENT_READY", "CLIENT_READY"),
    ("server.log", "V4_ORIGINAL_GO_GAME_NATIVE_READY", "SERVER_READY"),
    ("client.log", "original Game2 lanes TCP:", "GAME_TCP_FAILED"),
    ("direct-full.log", "WBD_WL_TRUE_PUBLIC_MODE_FAIL", "E2E_FAILURE"),
    ("direct-full.log", "WL_PUBLIC_REAL_MODE_TIMEOUT", "MODE_TEST_TIMEOUT"),
    ("client.log", "M0_PLAN026_GAME_NATIVE_FIRST_ERROR", "GAME_FIRST_ERROR"),
    ("client.log", "M0_PLAN027_GAME_DUE_FAULT first_failure=1", "GAME_FIRST_ERROR"),
    ("client.log", "M0_PLAN027_GAME_NATIVE_STOP_NOT_DRAINED", "GAME_STOP_FAILED"),
    ("client.log", "WBD_WINDOWS_GAME_NATIVE_DISCONNECTED", "WINDOWS_STOP_DONE"),
    ("server.log", "V4_PUBLIC_GAME_NATIVE_STOP_DRAINED", "LINUX_STOP_DONE"),
    ("windows-app.log", '"phase": "udp_1hz"', "WINDOWS_UDP_ALIVE"),
    ("linux-app.log", '"phase": "udp_1hz"', "LINUX_UDP_ALIVE"),
)
STACKS = (
    ("gamefec-supervisor-stack.txt", "STACK_SUPERVISOR"),
    ("gamefec-mode-stack.txt", "STACK_MODE"),
    ("gamefec-e2e-stack.txt", "STACK_E2E"),
)

def stack_stage(data):
    """Only fixed, de-identified stack classifications leave the runner."""
    if "stop_linux" in data: return "STOP_LINUX"
    if "stop_windows" in data: return "STOP_WINDOWS"
    if "game_due_first_fault" in data: return "GAME_FAULT_CHECK"
    if "ready" in data and "m0_wl_public_normal_e2e.py" in data: return "READY_WAIT"
    if "m0_wl_windows_bounded_cmd.py" in data: return "WSL_COMMAND"
    if "wsl(" in data: return "WSL_COMMAND"
    if "block_actual_output" in data: return "STDOUT_BLOCKED"
    if "_diagnostic_tail" in data: return "DIAGNOSTIC_THREAD"
    if "subprocess.py" in data: return "PROCESS_WAIT"
    return "PYTHON_STACK_PRESENT"

class GameFecRelay:
    def __init__(self, output, events, stop, env=None, send=None):
        self.output = pathlib.Path(output)
        self.events = events
        self.stop = stop
        self.env = os.environ if env is None else env
        self.send = send if send is not None else self._send_to_actions
        self.seen = set()
        self._delivery_slots = threading.BoundedSemaphore(3)

    def _send_to_actions(self, event, detail):
        if self.env.get("WBD_WL_GAME_FEC_RESCUE") != "1": return
        source = self.env.get("WBD_WL_BINARY_SOURCE") or self.env.get("GITHUB_SHA","")
        run = self.env.get("GITHUB_RUN_ID","")
        if not re.fullmatch(r"[a-f0-9]{40}",source): return
        if not re.fullmatch(r"[0-9]{8,15}",run): return
        args = ["gh","workflow","run","m0-plan027-gamefec-rescue-record.yml",
                "--repo",self.env.get("GITHUB_REPOSITORY","lly8666/wbd-next"),
                "--ref","main", "-f","target_run="+run, "-f","source="+source,
                "-f","stage="+event,"-f","detail="+detail]
        def deliver():
            with self._delivery_slots:
                try:
                    subprocess.run(args,stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,
                                   stdin=subprocess.DEVNULL,timeout=8,check=False)
                except (OSError,subprocess.TimeoutExpired):
                    pass
        # Only diagnostic calls run in bounded daemon senders. One stalled
        # GitHub request cannot starve the next first-fault/heartbeat marker.
        threading.Thread(target=deliver,daemon=True,
                         name="gamefec-gh-evidence").start()

    def emit(self,event,detail):
        # Independent receiver accepts [A-Z_], not numbers. Previous
        # SUPERVISOR_20S_ALIVE / _60S_ALIVE were silently filtered.
        event = {"SUPERVISOR_20S_ALIVE":"SUPERVISOR_ALIVE_FIRST",
                 "SUPERVISOR_60S_ALIVE":"SUPERVISOR_ALIVE_SECOND"}.get(event,event)
        event = SAFE.sub("_",event)[:30]
        detail = SAFE.sub("_",detail)[:80]
        if not re.fullmatch(r"[A-Z0-9_]{3,30}",event) or not detail: return
        if event in self.seen: return
        self.seen.add(event)
        self.send(event,detail)

    def observe(self):
        for name,needle,event in MARKERS:
            if event in self.seen: continue
            try:
                path = self.output / name
                if not path.is_file(): continue
                with path.open("rb") as f:
                    f.seek(0,2)
                    count = f.tell()
                    f.seek(max(0,count-32768))
                    value = f.read(32768).decode("utf-8","replace")
                if needle in value:
                    self.emit(event,name.replace(".log","").upper())
                    return  # Never let a burst of API calls starve PID events
            except OSError: pass
        for name,event in STACKS:
            if event in self.seen: continue
            try:
                p = self.output / name
                if not p.is_file() or p.stat().st_size == 0: continue
                with p.open("rb") as f: data = f.read(32768).decode("utf-8","replace")
                if "Thread" in data or "Current thread" in data:
                    self.emit(event,stack_stage(data))
                    return
            except OSError: pass
        for name,event in (("client.log","CLIENT_LOG_STARTED"),
                           ("server.log","SERVER_LOG_STARTED"),
                           ("windows-app.log","WINDOWS_APP_STARTED"),
                           ("linux-app.log","LINUX_APP_STARTED")):
            if event in self.seen: continue
            try:
                if (self.output/name).stat().st_size:
                    self.emit(event,"LOG_HAS_BYTES")
                    return
            except OSError: pass

    def run(self):
        # This thread is purely observational. It owns every GitHub API call.
        # At most one queued event per iteration to avoid starvation of
        # actual client/server and pre-cancel stack-file observations.
        while not self.stop.is_set():
            # Main-PID clock stages MUST outrank any slow log file or gh API.
            # Older order observed two file-start receipts then starved every
            # supervisor heartbeat; sender is still never the PID owner.
            try: event=self.events.get_nowait()
            except queue.Empty: event=None
            if event: self.emit(event,"SUPERVISOR_ALIVE")
            self.observe()
            self.stop.wait(.1)
