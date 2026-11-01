"""Regression: native descendants keeping stdio open must not trap a passed/failed test."""
import contextlib
import io
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

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

    def test_h708_first_fault_then_stuck_process_is_logged_before_kill(self):
        # One deliberately hung child, no product or OS driver. No artifact
        # service or final child flush is needed to see the first fault.
        from tools import m0_wl_native_step_runner as native
        with tempfile.TemporaryDirectory() as d:
            code=pathlib.Path(d)/"original-e2e-fixture.py"
            log=pathlib.Path(d)/"direct-full.log"
            code.write_text(
                "import time\n"
                "print('M0_PLAN027_GAME_DUE_FAULT stage=due_send_records "
                "first_error=INVALID lane=2 cipher_len=1391 path_mtu=1400',flush=True)\n"
                "time.sleep(30)\n"
            )
            captured=io.StringIO()
            with (mock.patch.object(native,"native_batch_deadline",return_value=1),
                  mock.patch.object(sys,"argv",[str(RUNNER),str(code),str(log)]),
                  mock.patch.dict("os.environ",{
                      "GITHUB_RUN_ID":"123456789",
                      "GITHUB_SHA":"653744efca9e6878c456595b508a2968d7ad83ff",
                      "WBD_WL_PUBLIC_MODES":"game2-fec",
                      "WBD_WL_V2_SCENARIO":"scenarios/original-game2-fec.json"
                  }),
                  contextlib.redirect_stdout(captured),
                  contextlib.redirect_stderr(captured)):
                rc=native.main()
            self.assertEqual(rc,124,captured.getvalue())
            self.assertIn("WL_DIAG_FIRST_ERROR marker=INVALID",captured.getvalue())
            self.assertIn("first_error=INVALID",captured.getvalue())
            self.assertIn("stage=due_send_records",captured.getvalue())
            self.assertIn("tx=UNKNOWN rx=UNKNOWN wal=UNKNOWN",captured.getvalue())
            self.assertIn("result=TIMEOUT_FAIL_NATIVE",captured.getvalue())
            self.assertIn("M0_PLAN027_GAME_DUE_FAULT",log.read_text())


    def test_h738_blocked_game_log_read_cannot_block_owning_pid_deadline(self):
        from tools import m0_wl_native_step_runner as native
        with tempfile.TemporaryDirectory() as d:
            code=pathlib.Path(d)/"stuck-game.py"
            log=pathlib.Path(d)/"direct-full.log"
            code.write_text("import time\nprint('GAME_CHILD_RUNNING',flush=True)\ntime.sleep(15)\n")
            trace_started=__import__("threading").Event()
            def blocked_read(_self):
                trace_started.set()
                time.sleep(4)
            captured=io.StringIO()
            with (mock.patch.object(native,"native_batch_deadline",return_value=1),
                  mock.patch.object(native.GameFecProgress,"poll",blocked_read),
                  mock.patch.object(sys,"argv",[str(RUNNER),str(code),str(log)]),
                  mock.patch.dict("os.environ",{
                      "WBD_WL_PUBLIC_MODES":"game2-fec",
                      "WBD_WL_GAME_FEC_RESCUE":"0"
                  }),
                  contextlib.redirect_stdout(captured),
                  contextlib.redirect_stderr(captured)):
                start=time.monotonic()
                rc=native.main()
                elapsed=time.monotonic()-start
            self.assertTrue(trace_started.is_set())
            self.assertEqual(rc,124,captured.getvalue())
            self.assertLess(elapsed,3.0,captured.getvalue())
            self.assertIn("WL_ORIGINAL_NATIVE_E2E_BATCH_TIMEOUT",captured.getvalue())

    def test_h741_raw_game_stdout_block_cannot_hold_supervisor_timeout(self):
        from tools import m0_wl_native_step_runner as native
        with tempfile.TemporaryDirectory() as d:
            code=pathlib.Path(d)/"game-stdout-stuck.py"
            log=pathlib.Path(d)/"direct-full.log"
            code.write_text(
                "import time\nprint('H741_RAW_LOG_WILL_BLOCK',flush=True)\ntime.sleep(15)\n")
            started=__import__("threading").Event()
            class BlockingLog(io.StringIO):
                def write(self, s):
                    if "H741_RAW_LOG_WILL_BLOCK" in s:
                        started.set()
                        time.sleep(4)
                    return super().write(s)
            captured=BlockingLog()
            with (mock.patch.object(native,"native_batch_deadline",return_value=1),
                  mock.patch.object(sys,"argv",[str(RUNNER),str(code),str(log)]),
                  mock.patch.dict("os.environ",{
                      "WBD_WL_PUBLIC_MODES":"game2-fec",
                      "WBD_WL_GAME_FEC_RESCUE":"0"
                  }),
                  contextlib.redirect_stdout(captured),
                  contextlib.redirect_stderr(captured)):
                start=time.monotonic()
                rc=native.main()
                elapsed=time.monotonic()-start
            self.assertTrue(started.is_set())
            self.assertEqual(rc,124)
            self.assertLess(elapsed,3.0)
            self.assertIn("WL_ORIGINAL_NATIVE_E2E_BATCH_TIMEOUT",captured.getvalue())

    def test_h711_real_native_stop_markers_not_guessed(self):
        from tools import m0_wl_native_step_runner as native
        state={"stage":"UNKNOWN","first_error":"UNKNOWN","fragment":"",
               "lane":"UNKNOWN","cipher_len":"UNKNOWN","path_mtu":"UNKNOWN",
               "tx":"UNKNOWN","rx":"UNKNOWN","wal":"UNKNOWN"}
        native._inspect(state,b"M0_PLAN027_GAME_NATIVE_STOP_NOT_DRAINED group=7 rc=3 tx_finished=true rx_finished=false worker_rc=3 retained_loans=1\n")
        self.assertEqual(state["tx"],"FINISHED_UNJOINED")
        self.assertEqual(state["rx"],"NOT_EXITED")
        self.assertEqual(state["wal"],"UNKNOWN")
        native._inspect(state,b"M0_PLAN027_GAME_NATIVE_STOP_JOIN group=7 tx_finished=true rx_finished=true tx_rc=0 rx_rc=0\n")
        native._inspect(state,b"M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS\n")
        self.assertEqual((state["tx"],state["rx"],state["wal"]),
                         ("EXITED","EXITED","RESTORED"))

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
        self.assertIn("$gameSingle",flow)
        self.assertIn("$wholeLimit=if($gameSingle){600}else{1020}",flow)

    def test_gamefec_actual_log_observer_is_owned_by_one_pid_supervisor(self):
        mode=(ROOT/"tools/m0_wl_public_modes_e2e.py").read_text()
        runner=(ROOT/"tools/m0_wl_native_step_runner.py").read_text()
        rescue=(ROOT/"tools/m0_wl_gamefec_progress.py").read_text()
        self.assertIn("GameFecProgress(output.parent,env=os.environ)",runner)
        self.assertIn('trace.snapshot("MODE_TIMEOUT")',runner)
        self.assertIn('trace.snapshot("MODE_EXIT")',runner)
        self.assertNotIn("GameFecProgress",mode)
        self.assertNotIn("capture_output=True,timeout=20",mode)
        self.assertIn("stderr=subprocess.DEVNULL, timeout=8",rescue)
        self.assertNotIn("capture_output=True",rescue)

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
        self.assertIn('185 if minimal_game_fec else',mode)
        self.assertIn('240 if (slow and mode.startswith("game")) else 690 if slow else 165',mode)

    def test_game_v2_nested_deadlines_finish_before_external_windows_watchdog(self):
        from tools.m0_wl_native_step_runner import native_batch_deadline
        game={"WBD_WL_PUBLIC_MODES":"game4-fec",
              "WBD_WL_V2_SCENARIO":"scenarios/plan027-c-game4-fec-10m-250ms-loss0-60s.json"}
        normal={"WBD_WL_PUBLIC_MODES":"normal",
                "WBD_WL_V2_SCENARIO":"scenarios/plan027-c-normal-50m-25ms-loss0-60s.json"}
        self.assertEqual(native_batch_deadline(game),310)
        minimal={"WBD_WL_PUBLIC_MODES":"game2-fec",
                 "WBD_WL_V2_SCENARIO":"scenarios/plan027-b-game2-fec6-cold-minimum-1m-25ms-loss0-10s.json"}
        self.assertEqual(native_batch_deadline(minimal),250)
        self.assertLess(185,250)
        self.assertEqual(native_batch_deadline(normal),760)
        self.assertLess(240,310)
        self.assertLess(310+160+90,600)
        self.assertLess(690,760)
        self.assertLess(760+160+90,1020)
        self.assertEqual(native_batch_deadline({"WBD_WL_PUBLIC_MODES":"game2"}),320)

    def test_real_workflow_regular_batch_does_not_use_tee_pipeline(self):
        content=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn(
          "& python -u tools/m0_wl_native_step_runner.py tools/m0_wl_public_modes_e2e.py",
          content)
        self.assertNotIn(
          "& python tools/m0_wl_public_modes_e2e.py 2>&1 |",content)

if __name__=="__main__":unittest.main()
