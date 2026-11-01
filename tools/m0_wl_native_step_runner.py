#!/usr/bin/env python3
"""Windows original Go/Rust native E2E runner without PowerShell PIPE lifetime.

The former '& python ... 2>&1 | Tee-Object direct-full.log' waits for EOF
from *every inherited writer*, including orphan WSL/Go subprocess handles.
An exited E2E test can therefore appear permanently running. Capture the
test child directly to an actual file HANDLE, tail by byte offset while the
one owning PID is alive, and stop tailing on that PID's exit. Product, driver,
credential, test selection, and pass/fail exit code are unchanged.
"""
import os
import pathlib
import re
import signal
import subprocess
import sys
import time
if __package__:
    from .m0_wl_gamefec_progress import GameFecProgress
else:
    from m0_wl_gamefec_progress import GameFecProgress

def kill_native_child_tree(child):
    # A deadline kills exactly the one original E2E child tree.
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill.exe","/PID",str(child.pid),"/T","/F"],
                           stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,timeout=15,check=False)
        except (OSError,subprocess.TimeoutExpired):
            pass
    if child.poll() is None:
        if os.name != "nt":
            # Test child starts a separate session; kill its process group,
            # not only the owning PID, when a fixture is permanently stuck.
            try: os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError: pass
        else: child.kill()
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:pass

def native_batch_deadline(env):
    # One functional mode has <=165s, historical four modes <=4*165s.
    # Leave substantial OS setup/owned cleanup time before the whole-step 600/1020s guard.
    if env.get("WBD_WL_V2_SCENARIO") and env.get("WBD_WL_PUBLIC_MODES","").startswith("game"):
        # Nested 240s mode + bounded tree cleanup; native Windows guard
        # includes its own WSL/Firewall preflight and finally within 600s.
        return 310
    if (env.get("WBD_WL_RUN_N0")=="1" or env.get("WBD_WL_RUN_P200")=="1"
        or env.get("WBD_WL_V2_SCENARIO")):return 760
    selected=env.get("WBD_WL_PUBLIC_MODES","all")
    return 800 if selected=="through-game2" else 970 if selected=="all" else 320


# Only bounded, de-identified diagnostic tokens are synthesized. Original
# source log bytes are already streamed verbatim by the existing file tailer.
FIRST_FAULT = re.compile(
    r"M0_PLAN027_GAME_DUE_FAULT|M0_PLAN026_GAME_NATIVE_FIRST_ERROR"
    r"|WL_GAME_ORIGINAL_STOP_FAILURE|WL_GAME_FATAL_|WBD_WL_TRUE_PUBLIC_MODE_FAIL"
    r"|WL_ORIGINAL_NATIVE_E2E_BATCH_TIMEOUT|WL_PUBLIC_REAL_MODE_TIMEOUT"
)
STAGE = re.compile(r"due_send_records|m4_receipt|on_firstsend|wal_disconnect|"
                   r"game2-fec|game4-fec|native_stop|stop", re.I)

def _safe(value, max_len=100):
    return re.sub(r"[^a-zA-Z0-9_./:-]", "_", str(value or "UNKNOWN"))[:max_len]

def _diagnostic(state, rc, verdict):
    fields = {
        "run": _safe(os.environ.get("GITHUB_RUN_ID")),
        "source": _safe(os.environ.get("WBD_WL_BINARY_SOURCE") or os.environ.get("GITHUB_SHA")),
        "scene": _safe(os.environ.get("WBD_WL_V2_SCENARIO"), 140),
        "mode": _safe(os.environ.get("WBD_WL_PUBLIC_MODES")),
        "stage": _safe(state["stage"]),
        "first_error": _safe(state["first_error"]),
        "lane": _safe(state["lane"]),
        "cipher_len": _safe(state["cipher_len"]),
        "path_mtu": _safe(state["path_mtu"]),
        "tx": state["tx"],
        "rx": state["rx"],
        "wal": state["wal"],
        "child_rc": rc if rc is not None else "UNKNOWN",
        "result": verdict,
    }
    print("WL_DIAG " + " ".join(f"{k}={v}" for k,v in fields.items()), flush=True)

def _inspect(state, data):
    # Handle log lines split across 64KiB reads. Never retain whole output,
    # packets, identities, credentials, or arbitrary unbounded text.
    chunks = (state["fragment"] + data.decode("utf-8", "replace")).split("\n")
    state["fragment"] = chunks.pop()[-2048:]
    for line in chunks:
        line = line[:2048]
        stage = STAGE.search(line)
        if stage: state["stage"] = stage.group(0).lower()
        for field in ("lane", "cipher_len", "path_mtu"):
            match = re.search(r"\b" + field + r"=(\d{1,7})\b", line)
            if match: state[field] = match.group(1)
        # Read the actual H700 Rust/Go owned Stop printouts, not imagined
        # helper markers. A finished worker is not yet an owned Join/Stop.
        if "M0_PLAN027_GAME_NATIVE_STOP_NOT_DRAINED" in line:
            for kind in ("tx", "rx"):
                match = re.search(kind + r"_finished=(true|false)", line)
                if match:
                    state[kind] = ("FINISHED_UNJOINED" if match.group(1)=="true"
                                   else "NOT_EXITED")
        if "M0_PLAN027_GAME_NATIVE_STOP_JOIN" in line:
            state["tx"] = state["rx"] = "EXITED"
        if "M0_PLAN027_NATIVE_STOP_RESULT" in line:
            if "stage=wal_kernel_crypto result=PASS" in line:
                state["wal"] = "RESTORED"
            elif "stage=wal_disconnect result=FAIL" in line:
                state["wal"] = "NOT_RESTORED"
        if FIRST_FAULT.search(line) and state["first_error"] == "UNKNOWN":
            match = re.search(r"\b(?:first_error|reason|rc|result)=([A-Za-z0-9_-]{1,40})", line)
            state["first_error"] = (match.group(1) if match else
                                    FIRST_FAULT.search(line).group(0))
            print("WL_DIAG_FIRST_ERROR marker=" + _safe(state["first_error"]) +
                  " stage=" + _safe(state["stage"]), flush=True)

def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: m0_wl_native_step_runner.py <source-test.py> <real-log>")
    script = pathlib.Path(sys.argv[1]).resolve()
    output = pathlib.Path(sys.argv[2])
    if not script.is_file() or script.suffix != ".py":
        raise SystemExit("real test script not found")
    output.parent.mkdir(parents=True, exist_ok=True)
    # A *regular file*, never a PowerShell stdout pipe: a detached Windows
    # native or WSL process cannot hold the pipeline's EOF open.
    with output.open("wb") as writer:
        child = subprocess.Popen([sys.executable, "-u", str(script)],
                                 stdout=writer, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, env=os.environ.copy(),
                                 start_new_session=(os.name != "nt"))
        print("WL_ORIGINAL_NATIVE_E2E_CHILD_STARTED pid=" + str(child.pid) +
              " script=" + script.name, flush=True)
        # One owning supervisor also samples the ACTUAL original Go/Rust
        # native client/server/app files, not the possibly hung test child.
        # This replaces the nested test child's GameFEC observer; no new
        # watcher, subprocess, protocol RTT or product hot path.
        trace = (GameFecProgress(output.parent,env=os.environ)
                 if os.environ.get("WBD_WL_PUBLIC_MODES","").endswith("-fec") else None)
        if trace: trace.snapshot("MODE_STARTED")
        last_trace = time.monotonic()
        offset = 0
        state={"stage":"UNKNOWN","first_error":"UNKNOWN","fragment":"",
               "lane":"UNKNOWN","cipher_len":"UNKNOWN","path_mtu":"UNKNOWN",
               "tx":"UNKNOWN","rx":"UNKNOWN","wal":"UNKNOWN"}
        started=time.monotonic()
        last_heartbeat=started
        limit=native_batch_deadline(os.environ)
        print('WL_ORIGINAL_NATIVE_E2E_BATCH_DEADLINE seconds='+str(limit),flush=True)
        while True:
            now = time.monotonic()
            if trace and now-last_trace>=2:
                trace.poll()
                last_trace=now
            with output.open("rb") as reader:
                reader.seek(offset)
                data = reader.read(64 * 1024)
                offset += len(data)
            if data:
                sys.stdout.write(data.decode("utf-8", "replace"))
                sys.stdout.flush()
                _inspect(state,data)
            rc = child.poll()
            if rc is not None:
                # Drain bytes already committed by the owning test, but DO
                # NOT wait for inherited handles or arbitrary native peers.
                with output.open("rb") as reader:
                    reader.seek(offset)
                    rest = reader.read(256 * 1024)
                if rest:
                    sys.stdout.write(rest.decode("utf-8", "replace"))
                    sys.stdout.flush()
                    _inspect(state,rest)
                if trace:
                    trace.poll()
                    trace.snapshot("MODE_EXIT")
                _diagnostic(state,rc,"EXITED_NOT_AUTOMATIC_PASS" if rc==0 else "FAIL_NATIVE")
                print("WL_ORIGINAL_NATIVE_E2E_CHILD_EXIT pid=" + str(child.pid) +
                      " rc=" + str(rc), flush=True)
                return rc
            now=time.monotonic()
            if now-started>=limit:
                print("WL_ORIGINAL_NATIVE_E2E_BATCH_TIMEOUT seconds="+str(limit)+
                      " owner_pid="+str(child.pid)+" mode="+os.environ.get("WBD_WL_PUBLIC_MODES","all"),
                      file=sys.stderr,flush=True)
                if trace:
                    trace.poll()
                    trace.snapshot("MODE_TIMEOUT")
                _diagnostic(state,None,"TIMEOUT_FAIL_NATIVE")
                kill_native_child_tree(child)
                return 124
            if now-last_heartbeat>=20:
                print("WL_ORIGINAL_NATIVE_E2E_BATCH_HEARTBEAT elapsed_seconds="+
                      str(int(now-started))+" owner_pid="+str(child.pid),flush=True)
                last_heartbeat=now
            time.sleep(.2)


if __name__ == "__main__":
    sys.exit(main())
