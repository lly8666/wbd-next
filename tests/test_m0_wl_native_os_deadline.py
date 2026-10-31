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
        self.assertIn("types: [requested]",independent)
        self.assertIn("github.event.workflow_run.event == 'workflow_dispatch'",independent)
        self.assertIn("M0_EXTERNAL_NATIVE_TIMEOUT",independent)
        self.assertIn("/force-cancel",independent)
        self.assertIn("actions: write",independent)
        self.assertIn('1200',independent)
        # An A5 old-Go process must not hold a PowerShell Tee pipe open.
        self.assertIn("m0_wl_native_step_runner.py tools/m0_wl_perf_v2_ab.py",y)
        self.assertNotIn("& python tools/m0_wl_perf_v2_ab.py 2>&1 |",y)
        child=(ROOT/"tools/m0_wl_public_normal_e2e.py").read_text()
        self.assertIn("WL_REAL_LINUX_OWNED_STOP_REQUEST_TIMEOUT",child)
        batch=(ROOT/"tools/m0_wl_public_modes_e2e.py").read_text()
        self.assertIn("WL_PUBLIC_REAL_MODE_ABORT_ON_TIMEOUT",batch)

if __name__=="__main__":
    unittest.main()
