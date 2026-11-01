import contextlib
import io
import pathlib
import tempfile
import unittest

from tools.m0_wl_gamefec_progress import GameFecProgress


class GameFecProgressTests(unittest.TestCase):
    def test_native_worker_fatal_without_due_origin_is_visible_and_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            sent = []
            trace = GameFecProgress(root, env={}, relay=lambda stage, detail: sent.append((stage, detail)), now=lambda: 20)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                trace.snapshot("MODE_STARTED")
                (root/"client.log").write_text(
                    "M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=offer_send_records rc=1 lane=2 secret=DO_NOT_LOG\n"
                )
                trace.poll()
                trace.poll()
                trace.snapshot("MODE_TIMEOUT")
            self.assertEqual(trace.first_error, "offer_send_records")
            self.assertEqual(sent, [
                ("MODE_STARTED", "MODE_STARTED"),
                ("FIRST_ERROR", "offer_send_records"),
                ("MODE_TIMEOUT", "FIRST_FAULT"),
            ])
            self.assertNotIn("DO_NOT_LOG", output.getvalue())

    def test_h740_independent_receiver_accepts_numeric_supervisor_stages(self):
        recv=(pathlib.Path(__file__).resolve().parents[1]/
              ".github/workflows/m0-plan027-gamefec-rescue-record.yml").read_text()
        self.assertIn('[[ "$TRACE_STAGE" =~ ^[A-Z0-9_]{3,30}$ ]]',recv)
        for stage in ("SUPERVISOR_20S_ALIVE","SUPERVISOR_60S_ALIVE"):
            self.assertRegex(stage,r"^[A-Z0-9_]{3,30}$")

    def test_h745_independent_first_fault_receipt_precedes_blocked_console(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            events=[]
            trace=GameFecProgress(root,env={},
                relay=lambda event, detail: events.append((event,detail)),now=lambda:50)
            (root/"client.log").write_text(
                "M0_PLAN026_GAME_NATIVE_FIRST_ERROR role=TX stage=due_send_records "
                "rc=1 lane=2 token=SENSITIVE\\n".replace("\\\\n","\\n"))
            class DeadConsole(io.StringIO):
                def write(self, value):
                    raise OSError("native job stdout unavailable")
            with contextlib.redirect_stdout(DeadConsole()):
                with self.assertRaises(OSError):
                    trace.poll()
            self.assertEqual(events,[("FIRST_ERROR","due_send_records")])
            self.assertEqual(trace.first_error,"due_send_records")

    def test_true_ready_and_due_failure_sends_bounded_independent_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            events = []
            log = io.StringIO()
            trace = GameFecProgress(root, env={}, relay=lambda stage, detail: events.append((stage, detail)), now=lambda: 20)
            with contextlib.redirect_stdout(log):
                trace.snapshot("MODE_STARTED")
                (root/"client.log").write_text(
                    "WBD_WINDOWS_CLIENT_READY\n"
                    "M0_PLAN027_GAME_DUE_FAULT first_failure=1 stage=wire_frame origin=due lane=2 "
                    "cipher_len=1391 path_mtu=1400 rc=1 token=TOPSECRET\n"
                )
                (root/"server.log").write_text("V4_ORIGINAL_GO_GAME_NATIVE_READY\n")
                trace.poll()
                trace.poll()
            self.assertEqual([e[0] for e in events], ["MODE_STARTED", "FIRST_ERROR", "BOTH_READY"])
            self.assertNotIn("TOPSECRET", log.getvalue())
            self.assertIn("cipher_len=1391", log.getvalue())
            self.assertIn("path_mtu=1400", log.getvalue())
            self.assertIn("stage=FIRST_FAULT", log.getvalue())
