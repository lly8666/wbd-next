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

    def test_real_workflow_regular_batch_does_not_use_tee_pipeline(self):
        content=(ROOT/".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertIn(
          "& python -u tools/m0_wl_native_step_runner.py tools/m0_wl_public_modes_e2e.py",
          content)
        self.assertNotIn(
          "& python tools/m0_wl_public_modes_e2e.py 2>&1 |",content)

if __name__=="__main__":unittest.main()
