"""Fail-fast WSL2 guard regression; pure offline tests, no Windows kernel."""
import os
import pathlib
import subprocess
import sys
import tempfile
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

    def test_1800s_watchdog_opt_in_is_live_and_bounded(self):
        # The watchdog checks its max *before* the done flag. A pre-existing
        # sentinel exercises the actual argument parser without a 2600s wait,
        # network mutation, or a process kill.
        script=ROOT/"tools"/"m0_wl_windows_step_watchdog.py"
        with tempfile.TemporaryDirectory() as tmp:
            done=pathlib.Path(tmp)/"finished.flag"
            done.write_text("DONE")
            base=[sys.executable,str(script),"54321"]
            env=os.environ.copy()
            env.pop("WBD_PLAN028_WIN_LINUX_L3",None)
            def run(sec,scope):
                cfg=env.copy()
                if scope:cfg["WBD_PLAN028_WIN_LINUX_L3"]="1"
                return subprocess.run(base+[str(sec),str(done)],
                    env=cfg,text=True,capture_output=True,timeout=5)
            self.assertEqual(run(1020,False).returncode,0)
            self.assertNotEqual(run(2600,False).returncode,0)
            self.assertEqual(run(2600,True).returncode,0)
            self.assertNotEqual(run(2601,True).returncode,0)
        flow=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn("$guard.Refresh()",flow)
        self.assertIn("if($guard.HasExited)",flow)
        self.assertIn("WL_WSL2_OUTER_WATCHDOG_ARMED",flow)

    def test_crossos_1800_runner_management_lease_is_exact_and_owned(self):
        flow=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        lease=(ROOT/"tools/m0_wl_gamefec_management_route.ps1").read_text()
        self.assertIn("contains(github.event.head_commit.message, '[plan028-win-linux-1800]') && '1'",flow)
        self.assertIn("WBD_PLAN028_WIN_LINUX_COCLIENTS -eq '1'",lease)
        self.assertIn("WBD_PLAN028_WIN_LINUX_L3 -eq '1'",lease)
        self.assertIn("WBD_WL_PUBLIC_MODES -eq 'normal'",lease)
        self.assertIn("$Receipt -eq 'result/wl-public/crossos1800-management-route-lease.json'",lease)
        self.assertEqual(flow.count("'result/wl-public/crossos1800-management-route-lease.json'"),2)
        self.assertIn("PLAN028_CROSSOS1800_RUNNER_UNDERLAY_PINNED",flow)
        self.assertIn("PLAN028_CROSSOS1800_RUNNER_EXACT_RESTORED",flow)
        self.assertIn("[ValidateSet('Arm','Refresh','Restore')]",lease)
        self.assertIn("if($Action -eq 'Refresh')",lease)
        self.assertIn("if(-not $crossOsL3){throw 'MANAGEMENT_REFRESH_L3_ONLY'}",lease)
        self.assertIn("$_.State -in @('Established','SynSent')",lease)
        self.assertIn("OWNED_MANAGEMENT_ROUTE_LOST",lease)
        self.assertIn("MANAGEMENT_HOST_ROUTE_READBACK_FAIL",lease)
        self.assertIn("MANAGEMENT_L3_MAX_OWNED_ROUTES",lease)
        self.assertIn("OWNED_MANAGEMENT_ROUTE_LOST_FOREIGN_OR_AMBIGUOUS",lease)
        self.assertIn("ORIGINAL_MANAGEMENT_UNDERLAY_CHANGED",lease)
        self.assertIn("MANAGEMENT_REARM_READBACK_FAIL",lease)
        self.assertIn("if($ours.Count -eq 0){",lease)
        self.assertIn("repaired='+$repaired",lease)
        native=(ROOT/"tools/m0_plan028_h1430_windows_linux_l3.py").read_text()
        self.assertIn("refresh_runner_management()",native)
        self.assertIn('next_mgmt=time.monotonic()+10',native)
        self.assertIn('"runner_new_peer_routes":added_peers',native)
        self.assertIn('"runner_repaired_owned_routes":repaired_routes',native)
        self.assertIn('len(management)>=60',native)
        self.assertIn("if($env:WBD_WL_RUNNER_MGMT_PIN -eq '1'){",flow)
        self.assertLess(flow.index("PLAN028_CROSSOS1800_RUNNER_UNDERLAY_PINNED"),
                        flow.index("tools/m0_plan028_h1415_windows_linux_independent_clients.py result/wl-public/direct-full.log"))

    def test_owned_linux_pid_script_expands_shell_pid(self):
        # A literal "$" leaves an invalid two-byte PID file after real UDP.
        script=(ROOT/"tools/m0_wl_public_normal_e2e.py").read_text()
        self.assertIn("echo $$ > ",script)
        self.assertNotIn("echo $ > ",script)
        # Windows defaults to CRLF in text-mode writes; native WSL /bin/sh
        # requires an LF-only script. A stopped capture is NOT TLS evidence.
        self.assertIn("capture_script.write_bytes(",script)
        self.assertNotIn("capture_script.write_text(",script)
        self.assertIn('reason=(out/"tls-capture-stderr.log").read_text',script)

    def test_hard_guard_is_whole_step_not_only_mode(self):
        y=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn("WL_WSL2_OUTER_WATCHDOG_ARMED",y)
        self.assertIn("m0_wl_windows_bounded_cmd.py 180 wsl.exe --import",y)
        # Legacy scoped native step remains 24min; only real Windows+Linux
        # 1800s L3 opts into 52min. Do not lengthen all Windows workflows.
        self.assertIn("timeout-minutes: ${{ contains(github.event.head_commit.message, '[plan028-win-linux-1800]') && 52 || 24 }}",y)
        self.assertIn("WBD_PLAN028_WIN_LINUX_L3 -eq '1'",y)
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
        self.assertIn('480',independent)
        self.assertIn('M0_EXTERNAL_NATIVE_CANCEL_FIRST',independent)
        self.assertLess(independent.index('M0_EXTERNAL_NATIVE_CANCEL_FIRST'),
                        independent.index('recover_logs "after_immediate_timeout_cancel"'))
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
