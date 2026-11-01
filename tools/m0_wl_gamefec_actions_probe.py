#!/usr/bin/env python3
"""Single bounded Windows Actions test of the real GameFEC PID runner and local evidence.

Synthetic abnormal child ONLY: proves runner exit, first-fault file, then workflow
GitHub API and artifact transport. It does not run TLS/NPF/Wintun/Rust/FEC or WAL.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: m0_wl_gamefec_actions_probe.py <output-directory>")
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    fixture = out / "h780-synthetic-abnormal-child.py"
    fixture.write_text(
        "import os,time\n"
        "print('M0_PLAN027_GAME_DUE_FAULT fixture=H780_NOT_PRODUCT "
        "first_failure=1 reason=INJECTED_TEST_MARKER',flush=True)\n"
        "time.sleep(.6)\n"
        "os._exit(37)\n", encoding="utf-8")
    direct = out / "h780-original-direct-full.log"
    stdout = out / "h780-native-runner-stdout.txt"
    receipt = {
        "schema": "wbd-h780-windows-native-actions-path/v1",
        "workflow_head": os.environ.get("GITHUB_SHA", "UNKNOWN"),
        "product_source": "NOT_BUILT",
        "driver": "NOT_RUN",
        "tls": "NOT_RUN",
        "game_fec_delivery": "NOT_RUN",
        "owned_stop_and_full_wal": "NOT_RUN",
        "fixture_child": "INJECTED_ABNORMAL_EXIT_37",
        "runner_exit": "UNKNOWN",
        "first_fault_file": "UNKNOWN",
        "actions_artifact": "CHECK_SEPARATELY_AFTER_UPLOAD",
    }
    env = os.environ.copy()
    env.update({
        "WBD_WL_PUBLIC_MODES": "game2-fec",
        "WBD_WL_GAME_FEC_RESCUE": "0",
        "WBD_WL_V2_SCENARIO": "scenarios/plan027-b-game2-fec6-cold-minimum-1m-25ms-loss0-10s.json",
    })
    runner = Path(__file__).with_name("m0_wl_native_step_runner.py")
    error = None
    try:
        with stdout.open("wb") as sink:
            p = subprocess.run([sys.executable, "-u", str(runner),
                                str(fixture), str(direct)],
                               stdout=sink, stderr=subprocess.STDOUT,
                               stdin=subprocess.DEVNULL, timeout=35, env=env,
                               check=False)
        log = direct.read_text(encoding="utf-8", errors="replace")
        observation = stdout.read_text(encoding="utf-8", errors="replace")
        if p.returncode != 37:
            raise RuntimeError("native runner exit not propagated: " + str(p.returncode))
        if "fixture=H780_NOT_PRODUCT" not in log:
            raise RuntimeError("native direct file missing original first-fault fixture")
        if "WL_DIAG_FIRST_ERROR" not in observation:
            raise RuntimeError("native diagnostic thread did not report first fault")
        receipt["runner_exit"] = "PASS_PARENT_EXIT_37_NO_EXTERNAL_CANCEL"
        receipt["first_fault_file"] = "PASS_ORIGINAL_WINDOWS_DISK_AND_DIAGNOSTIC"
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        error = type(exc).__name__ + ": " + str(exc)[:180]
        receipt["runner_exit"] = "FAIL"
        receipt["error"] = error
    finally:
        (out / "h780-actions-probe.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if error:
        print("H780_ACTIONS_NATIVE_PATH_FAIL " + error, flush=True)
        return 1
    print("H780_WINDOWS_NATIVE_RUNNER_EXIT_AND_LOCAL_FAULT_PASS_NOT_PRODUCT", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
