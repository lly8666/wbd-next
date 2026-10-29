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
            time.sleep(.2)


if __name__ == "__main__":
    sys.exit(main())
