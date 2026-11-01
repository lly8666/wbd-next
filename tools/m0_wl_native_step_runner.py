#!/usr/bin/env python3
"""Windows original Go/Rust native E2E runner without PowerShell PIPE lifetime.

The former '& python ... 2>&1 | Tee-Object direct-full.log' waits for EOF
from *every inherited writer*, including orphan WSL/Go subprocess handles.
An exited E2E test can therefore appear permanently running. Capture the
test child directly to an actual file HANDLE, tail by byte offset while the
one owning PID is alive, and stop tailing on that PID's exit. Product, driver,
credential, test selection, and pass/fail exit code are unchanged.
"""
import faulthandler
import os
import pathlib
import queue
import re
import signal
import subprocess
import sys
import threading
import time
if __package__:
    from .m0_wl_gamefec_progress import GameFecProgress
    from .m0_wl_gamefec_relay import GameFecRelay
else:
    from m0_wl_gamefec_progress import GameFecProgress
    from m0_wl_gamefec_relay import GameFecRelay

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
    if (env.get("WBD_WL_PUBLIC_MODES")=="game2-fec" and
            env.get("WBD_WL_V2_SCENARIO")=="scenarios/plan027-b-game2-fec6-cold-minimum-1m-25ms-loss0-10s.json"):
        # One 10s real first-fault reproduction: nested 185s mode, one
        # bounded Windows child tree cleanup, no repeated 600s test.
        return 250
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

def _diagnostic_tail(output, stop, game):
    # All file reads, text parsing, stdout and GitHub CLI are isolated from
    # the only PID deadline. A blocked stdout PIPE or filesystem cannot hold
    # the process owner. No second watchdog or product worker is introduced.
    # Local stdout/log side cannot own outbound evidence. A separate relay
    # thread consumes the main PID events and scans the same on-disk files.
    quiet_env=os.environ.copy()
    quiet_env["WBD_WL_GAME_FEC_RESCUE"]="0"
    trace = GameFecProgress(output.parent, env=quiet_env) if game else None
    state = {"stage":"UNKNOWN","first_error":"UNKNOWN","fragment":"",
             "lane":"UNKNOWN","cipher_len":"UNKNOWN","path_mtu":"UNKNOWN",
             "tx":"UNKNOWN","rx":"UNKNOWN","wal":"UNKNOWN"}
    offset = 0
    last_trace = 0.0
    while True:
        now = time.monotonic()
        if trace and now - last_trace >= 2:
            trace.poll()
            last_trace = now
        try:
            with output.open("rb") as reader:
                reader.seek(offset)
                data = reader.read(64 * 1024)
        except OSError:
            data = b""
        offset += len(data)
        if data:
            _inspect(state, data)
            if game:
                for line in data.decode("utf-8","replace").splitlines():
                    if line.startswith(("WL_PUBLIC_REAL_MODE_RESULT",
                                       "WL_PUBLIC_REAL_MODE_TIMEOUT",
                                       "WL_PUBLIC_REAL_MODE_PROCESS_EXIT",
                                       "WL_GAME_DUE_DIAGNOSTIC_FINAL")):
                        print("WL_GAME_BOUNDED_NATIVE_RESULT "+line[:420], flush=True)
            else:
                sys.stdout.write(data.decode("utf-8","replace"))
                sys.stdout.flush()
        if stop.is_set():
            # One final bounded file read is enough; on normal success the
            # immutable full log remains on disk for postmortem inspection.
            return
        stop.wait(.1)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: m0_wl_native_step_runner.py <source-test.py> <real-log>")
    script = pathlib.Path(sys.argv[1]).resolve()
    output = pathlib.Path(sys.argv[2])
    if not script.is_file() or script.suffix != ".py":
        raise SystemExit("real test script not found")
    output.parent.mkdir(parents=True, exist_ok=True)
    game = os.environ.get("WBD_WL_PUBLIC_MODES","").endswith("-fec")
    limit = native_batch_deadline(os.environ)
    stop = threading.Event()
    events = queue.SimpleQueue()
    stack_handle = None
    # At 12s before the owning PID deadline, independently record *all*
    # Python thread program counters, including blocked diagnostics. This
    # low-level faulthandler path does not use stdout, GitHub, or trace.poll.
    if game:
        stack_path = output.parent / "gamefec-supervisor-stack.txt"
        stack_handle = stack_path.open("w")
        faulthandler.dump_traceback_later(
            max(.5, float(limit)-12), repeat=False, file=stack_handle,
            exit=False)
    try:
        # Give the product a regular output file, never an inherited PIPE.
        with output.open("wb") as writer:
            child = subprocess.Popen([sys.executable, "-u", str(script)],
                                     stdout=writer, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, env=os.environ.copy(),
                                     start_new_session=(os.name != "nt"))
            # Two optional, non-supervisory observers: stdout/file tailer
            # may block forever, but the independent GH stage relay never
            # prints to stdout and never shares its queue consumer.
            if game:
                reporter=threading.Thread(
                    target=GameFecRelay(output.parent,events,stop).run,
                    name="game-fec-independent-stages",daemon=True)
                reporter.start()
            diagnostic = threading.Thread(
                target=_diagnostic_tail, args=(output,stop,game),
                name="game-fec-diagnostics" if game else "native-diagnostics",
                daemon=True)
            diagnostic.start()
            if game:
                (output.parent/"gamefec-stop-request.flag").unlink(missing_ok=True)
                events.put("MODE_STARTED")
                events.put("SUPERVISOR_LOOP_ENTER")
            else:
                # Even regular stdout is owned by the optional log worker.
                events.put("MODE_STARTED")
            first_polled = False
            started = time.monotonic()
            last_heartbeat = started
            near_deadline_sent=False
            while True:
                # Deliberately only PID, monotonic time and process-tree
                # termination. Never read files, format logs or call GitHub.
                rc = child.poll()
                now = time.monotonic()
                if game and not first_polled:
                    events.put("SUPERVISOR_POLL_OK")
                    first_polled = True
                if rc is not None:
                    if game:
                        events.put("MODE_EXIT")
                    stop.set()
                    diagnostic.join(timeout=.15)
                    return rc
                if now - started >= limit:
                    break

                if game and not near_deadline_sent and now-started >= max(1,limit-35):
                    events.put("SUPERVISOR_NEAR_DEADLINE")
                    near_deadline_sent=True
                if game and now - last_heartbeat >= 20:
                    if now - started < 65:
                        events.put("SUPERVISOR_20S_ALIVE" if now-started < 40
                                   else "SUPERVISOR_60S_ALIVE")
                    last_heartbeat = now
                time.sleep(.2)
            # The sole monotonic PID loop has ENDED. Do not close a live
            # original Windows Game WAL owner without offering native Stop.
            if game:
                events.put("SUPERVISOR_LOCAL_TIMEOUT")
                (output.parent/"gamefec-supervisor-timeout.txt").write_text(
                    "result=TIMEOUT\nsource="+os.environ.get("GITHUB_SHA","UNKNOWN")+
                    "\nchild_pid="+str(child.pid)+"\n")
                (output.parent/"gamefec-stop-request.flag").write_text(
                    "ORIGINAL_OWNER_STOP_REQUESTED\n")
                try:child.wait(timeout=12 if limit>10 else .2)
                except subprocess.TimeoutExpired:pass
            if child.poll() is None:
                kill_native_child_tree(child)
            if game:
                # Never claim that N4NativeRecoverState restored routes:
                # its PreRoute-only path rejects *.routes sidecars.
                wal=output.parent/"owned-wal.json.n4-owned-wal"
                side=output.parent/"owned-wal.json.n4-owned-wal.routes"
                client=output.parent/"client.log"
                owner_stopped=False
                if client.is_file():
                    with client.open("rb") as f:
                        f.seek(max(0,client.stat().st_size-32768))
                        data=f.read(32768)
                    owner_stopped=(b"WBD_WINDOWS_GAME_NATIVE_DISCONNECTED" in data
                        and b"M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS" in data)
                verdict=("PRODUCT_STOP_LOG_ONLY_OS_READBACK_NOT_INDEPENDENT"
                    if owner_stopped and not wal.exists() and not side.exists()
                    else "NETWORK_RECOVERY_UNVERIFIED_KEEP_WAL")
                with (output.parent/"gamefec-supervisor-timeout.txt").open("a") as f:
                    f.write("child_exit="+str(child.poll())+
                        "\nwal_present="+str(wal.exists()).lower()+
                        "\nroute_sidecar_present="+str(side.exists()).lower()+
                        "\nnetwork_recovery="+verdict+"\n")
                events.put("MODE_TIMEOUT")
            stop.set()
            diagnostic.join(timeout=.15)
            return 124
    finally:
        if stack_handle is not None:
            faulthandler.cancel_dump_traceback_later()
            stack_handle.close()


if __name__ == "__main__":
    code = main()
    if code == 124 and os.environ.get("WBD_WL_PUBLIC_MODES","").endswith("-fec"):
        # Optional daemon stdout/Actions diagnostic may be indefinitely stuck
        # on an inherited pipe. The real child tree has ALREADY been killed,
        # stack file is preserved, and interpreter shutdown must not wait for
        # an optional diagnostic thread's global stdout lock.
        os._exit(124)
    sys.exit(code)
