"""Fail-fast WSL2 guard regression; pure offline tests, no Windows kernel."""
import pathlib
import subprocess
import sys
import time
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools"/"m0_wl_windows_bounded_cmd.py"

class NativeWslDeadlineTests(unittest.TestCase):
    def test_bounded_command_passes_real_child_result(self):
        p=subprocess.run([sys.executable,str(SCRIPT),"5",sys.executable,
            "-c","print('BOUNDED_WSL_OS_REAL_CHILD_OK')"],capture_output=True,text=True,timeout=9)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("BOUNDED_WSL_OS_REAL_CHILD_OK",p.stdout)

    def test_hung_child_fails_not_pass_after_deadline(self):
        start=time.monotonic()
        p=subprocess.run([sys.executable,str(SCRIPT),"1",sys.executable,
            "-c","import time;time.sleep(30)"],capture_output=True,text=True,timeout=12)
        self.assertEqual(p.returncode,124,p.stderr)
        self.assertLess(time.monotonic()-start,10)
        self.assertIn("WL_WSL2_COMMAND_TIMEOUT seconds=1",p.stderr)

    def test_owned_linux_pid_script_expands_shell_pid(self):
        # A literal "$" leaves an invalid two-byte PID file after real UDP.
        script=(ROOT/"tools/m0_wl_public_normal_e2e.py").read_text()
        self.assertIn("echo $$ > ",script)
        self.assertNotIn("echo $ > ",script)

    def test_hard_guard_is_whole_step_not_only_mode(self):
        y=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn("WL_WSL2_OUTER_WATCHDOG_ARMED",y)
        self.assertIn("m0_wl_windows_bounded_cmd.py 180 wsl.exe --import",y)
        self.assertIn("timeout-minutes: 24",y)
        # The original Windows 2025 runner can freeze *above* PowerShell,
        # defeating its on-host watchdog and the step timeout entirely.
        # A different Ubuntu Actions worker must cancel the stuck exact run.
        # A watcher inside the tested Action cancels itself with Windows.
        # The native deadline must run in a distinct Linux workflow_run.
        self.assertNotIn("native-wsl-external-deadline:",y)
        independent=(ROOT/".github/workflows/m0-plan027-independent-native-deadline.yml").read_text()
        self.assertIn("workflow_dispatch:",independent)
        self.assertIn("target_run_id:",independent)
        self.assertIn("M0_SEPARATE_NATIVE_DEADLINE_ARMED",y)
        self.assertIn("M0_EXTERNAL_NATIVE_TIMEOUT",independent)
        self.assertIn("/force-cancel",independent)
        self.assertIn("actions: write",independent)
        self.assertIn('1200',independent)
        self.assertIn('target_job_limit:',independent)
        self.assertIn('720',independent)
        self.assertIn('launch_at:',independent)
        self.assertNotIn("recover-h601-stuck:",independent)
        self.assertIn('WL_GAME_NATIVE_FILE_BACKED_STREAMING_DEADLINE seconds=310',y)
        self.assertNotIn('m0_wl_windows_bounded_cmd.py 510 python -u tools/m0_wl_native_step_runner.py',y)
        self.assertIn('& python -u tools/m0_wl_native_step_runner.py',y)
        # Retired old Go A5 has no runner or Tee path; live Rust/Game
        # still uses the file-backed bounded native process guard.
        self.assertNotIn("m0_wl_perf_v2_ab.py",y)
        self.assertIn("m0_wl_native_step_runner.py tools/m0_wl_public_modes_e2e.py",y)
        child=(ROOT/"tools/m0_wl_public_normal_e2e.py").read_text()
        self.assertIn("WL_REAL_LINUX_OWNED_STOP_REQUEST_TIMEOUT",child)
        self.assertIn("WBD_WINDOWS_ORIGINAL_GO_TLS_REAUTHORIZE generation=",child)
        self.assertIn('win_log.count("WBD_WINDOWS_CLIENT_READY")<2',child)
        batch=(ROOT/"tools/m0_wl_public_modes_e2e.py").read_text()
        self.assertIn("WL_PUBLIC_REAL_MODE_ABORT_ON_TIMEOUT",batch)

if __name__=="__main__":
    unittest.main()
