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
import subprocess
import sys
import time

def kill_native_child_tree(child):
    # A deadline kills exactly the one original E2E child tree.
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill.exe","/PID",str(child.pid),"/T","/F"],
                           stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,timeout=15,check=False)
        except (OSError,subprocess.TimeoutExpired):
            pass
    if child.poll() is None:child.kill()
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:pass

def native_batch_deadline(env):
    # One functional mode has <=165s, historical four modes <=4*165s.
    # These extra guards end earlier than the 1020s whole-step watchdog.
    if (env.get("WBD_WL_RUN_N0")=="1" or env.get("WBD_WL_RUN_P200")=="1"
        or env.get("WBD_WL_V2_SCENARIO")):return 970
    selected=env.get("WBD_WL_PUBLIC_MODES","all")
    return 800 if selected=="through-game2" else 970 if selected=="all" else 320


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
                                 stdin=subprocess.DEVNULL, env=os.environ.copy())
        print("WL_ORIGINAL_NATIVE_E2E_CHILD_STARTED pid=" + str(child.pid) +
              " script=" + script.name, flush=True)
        offset = 0
        started=time.monotonic()
        last_heartbeat=started
        limit=native_batch_deadline(os.environ)
        print('WL_ORIGINAL_NATIVE_E2E_BATCH_DEADLINE seconds='+str(limit),flush=True)
        while True:
            with output.open("rb") as reader:
                reader.seek(offset)
                data = reader.read(64 * 1024)
                offset += len(data)
            if data:
                sys.stdout.write(data.decode("utf-8", "replace"))
                sys.stdout.flush()
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
                print("WL_ORIGINAL_NATIVE_E2E_CHILD_EXIT pid=" + str(child.pid) +
                      " rc=" + str(rc), flush=True)
                return rc
            now=time.monotonic()
            if now-started>=limit:
                print("WL_ORIGINAL_NATIVE_E2E_BATCH_TIMEOUT seconds="+str(limit)+
                      " owner_pid="+str(child.pid)+" mode="+os.environ.get("WBD_WL_PUBLIC_MODES","all"),
                      file=sys.stderr,flush=True)
                kill_native_child_tree(child)
                return 124
            if now-last_heartbeat>=20:
                print("WL_ORIGINAL_NATIVE_E2E_BATCH_HEARTBEAT elapsed_seconds="+
                      str(int(now-started))+" owner_pid="+str(child.pid),flush=True)
                last_heartbeat=now
            time.sleep(.2)


if __name__ == "__main__":
    sys.exit(main())
