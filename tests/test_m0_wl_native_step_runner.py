"""Regression: native descendants keeping stdio open must not trap a passed/failed test."""
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNNER=ROOT/"tools/m0_wl_native_step_runner.py"

class NativeChildStdoutLifetimeTests(unittest.TestCase):
    def test_old_pipe_collection_waits_for_unrelated_inherited_writer(self):
        with tempfile.TemporaryDirectory() as d:
            code=pathlib.Path(d)/"child.py"
            code.write_text(
                "import subprocess,sys\n"
                "subprocess.Popen([sys.executable,'-c','import time;time.sleep(3)'],"
                " stdout=sys.stdout,stderr=sys.stderr)\n"
                "print('PARENT_ALREADY_FINISHED',flush=True)\n")
            # Direct subprocess PIPE-collect waits for EOF from the child of
            # the already-exited parent. The old PowerShell Tee pipe has
            # the same lifetime dependence.
            with self.assertRaises(subprocess.TimeoutExpired):
                subprocess.run([sys.executable,str(code)],capture_output=True,
                               text=True,timeout=.8)

    def test_file_handle_tailer_reports_first_process_exit_not_descendants(self):
        with tempfile.TemporaryDirectory() as d:
            code=pathlib.Path(d)/"child.py"
            log=pathlib.Path(d)/"real.log"
            code.write_text(
                "import subprocess,sys\n"
                "subprocess.Popen([sys.executable,'-c','import time;time.sleep(3)'],"
                " stdout=sys.stdout,stderr=sys.stderr)\n"
                "print('GENUINE_NATIVE_FAILURE_STAGE',flush=True)\n"
                "sys.exit(3)\n")
            start=time.monotonic()
            p=subprocess.run([sys.executable,str(RUNNER),str(code),str(log)],
                             capture_output=True,text=True,timeout=2.5)
            self.assertEqual(p.returncode,3,p.stdout+p.stderr)
            self.assertLess(time.monotonic()-start,2.4)
            self.assertIn("GENUINE_NATIVE_FAILURE_STAGE",p.stdout)
            self.assertIn("WL_ORIGINAL_NATIVE_E2E_CHILD_EXIT",p.stdout)
            self.assertIn("GENUINE_NATIVE_FAILURE_STAGE",log.read_text())

    def test_inner_wsl_control_does_not_capture_a_raw_wsl_pipe(self):
        content=(ROOT/"tools/m0_wl_public_normal_e2e.py").read_text()
        self.assertIn('str(root/"tools"/"m0_wl_windows_bounded_cmd.py")',content)
        self.assertNotIn("subprocess.run(a,capture_output=True",content)

    def test_file_backed_inner_control_preserves_parent_exit_with_inherited_writer(self):
        with tempfile.TemporaryDirectory() as d:
            code=pathlib.Path(d)/"wsl-like-parent.py"
            code.write_text(
                "import subprocess,sys\n"
                "subprocess.Popen([sys.executable,'-c','import time;time.sleep(4)'],"
                " stdout=sys.stdout,stderr=sys.stderr)\n"
                "print('GENUINE_INNER_WSL_PARENT_EXIT',flush=True)\n"
                "sys.exit(7)\n")
            start=time.monotonic()
            p=subprocess.run([sys.executable,
                              str(ROOT/"tools/m0_wl_windows_bounded_cmd.py"),
                              "5",sys.executable,str(code)],
                             capture_output=True,text=True,timeout=3.5)
            self.assertEqual(p.returncode,7,p.stdout+p.stderr)
            self.assertIn("GENUINE_INNER_WSL_PARENT_EXIT",p.stdout)
            self.assertLess(time.monotonic()-start,3.2)

    def test_genuine_wsl_guest_probe_uses_file_backed_deadline(self):
        probe=(ROOT/"tools/m0_wl_real_wsl2_guest_probe.py").read_text()
        self.assertIn('with_name("m0_wl_windows_bounded_cmd.py")',probe)
        self.assertNotIn("subprocess.run(args, capture_output=True",probe)
        self.assertIn('"90",*args',probe)

    def test_native_step_has_no_raw_wsl_pipe_and_own_progress(self):
        flow=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertNotIn("& wsl.exe -d Ubuntu -u root -- ip -j -4 addr",flow)
        self.assertIn("m0_wl_windows_bounded_cmd.py 25 wsl.exe",flow)
        self.assertIn("Invoke-WebRequest -UseBasicParsing -TimeoutSec 180",flow)
        mode=(ROOT/"tools/m0_wl_public_modes_e2e.py").read_text()
        runner=(ROOT/"tools/m0_wl_native_step_runner.py").read_text()
        self.assertIn("WL_PUBLIC_REAL_MODE_HEARTBEAT",mode)
        self.assertIn("WL_ORIGINAL_NATIVE_E2E_BATCH_TIMEOUT",runner)
        self.assertIn("WL_ORIGINAL_NATIVE_E2E_BATCH_HEARTBEAT",runner)

    def test_wsl_real_boot_is_own_action_step_before_native_game(self):
        flow=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        stage="Real WSL2 Ubuntu kernel boot and TUN prerequisite (independent bounded stage)"
        native="Launch actual WSL2 Linux and direct full public two-OS product"
        self.assertLess(flow.index(stage),flow.index(native))
        self.assertEqual(flow.count("WL_WSL2_BOOT_STAGE_COMPLETE_REAL_KERNEL"),1)
        self.assertEqual(flow.count("WL_REAL_PINNED_UBUNTU_24045_WSL2_IMPORTED"),1)
        self.assertIn("m0-wl-real-guest-boot-",flow)

    def test_game_process_group_rolls_back_first_hanging_a8_launcher_flag(self):
        mode=(ROOT/"tools/m0_wl_public_modes_e2e.py").read_text()
        self.assertIn("creationflags=0)",mode)
        self.assertNotIn("creationflags=getattr(subprocess",mode)
        self.assertIn('mode_seconds=360 if (slow and mode.startswith("game")) else 1200 if slow else 165',mode)

    def test_game_v2_nested_deadlines_finish_before_external_windows_watchdog(self):
        from tools.m0_wl_native_step_runner import native_batch_deadline
        game={"WBD_WL_PUBLIC_MODES":"game4-fec",
              "WBD_WL_V2_SCENARIO":"scenarios/plan027-c-game4-fec-10m-250ms-loss0-60s.json"}
        normal={"WBD_WL_PUBLIC_MODES":"normal",
                "WBD_WL_V2_SCENARIO":"scenarios/plan027-c-normal-50m-25ms-loss0-60s.json"}
        self.assertEqual(native_batch_deadline(game),440)
        self.assertEqual(native_batch_deadline(normal),970)
        self.assertLess(360,440)
        self.assertLess(440,1200)
        self.assertEqual(native_batch_deadline({"WBD_WL_PUBLIC_MODES":"game2"}),320)

    def test_real_workflow_regular_batch_does_not_use_tee_pipeline(self):
        content=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn(
          "& python -u tools/m0_wl_native_step_runner.py tools/m0_wl_public_modes_e2e.py",
          content)
        self.assertNotIn(
          "& python tools/m0_wl_public_modes_e2e.py 2>&1 |",content)

if __name__=="__main__":unittest.main()
