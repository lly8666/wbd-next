"""No driver, network, GH, or OS-wide watchdog: independent GameFEC stages."""
import pathlib
import queue
import tempfile
import threading
import time
import unittest
from unittest import mock
from tools.m0_wl_gamefec_relay import GameFecRelay, stack_stage

class GameFecRescueRelayTests(unittest.TestCase):
    def test_external_receipts_from_real_log_files_and_pre_cancel_stacks(self):
        with tempfile.TemporaryDirectory() as d:
            out=pathlib.Path(d)
            events=[]
            relay=GameFecRelay(out,queue.SimpleQueue(),threading.Event(),
                               env={},send=lambda ev,detail:events.append((ev,detail)))
            relay.emit("SUPERVISOR_POLL_OK","SUPERVISOR_ALIVE")
            (out/"server.log").write_text("V4_ORIGINAL_GO_GAME_NATIVE_READY\n")
            (out/"client.log").write_text(
              "WBD_WINDOWS_CLIENT_READY\n"
              "M0_PLAN026_GAME_NATIVE_FIRST_ERROR origin=due reason=INVALID secret=DO_NOT_PRINT\n")
            (out/"windows-app.log").write_text('{"phase": "udp_1hz","sent":50,"received":0}\n')
            (out/"gamefec-e2e-stack.txt").write_text(
              'Timeout (0:01:45)!\nThread 0x13\n  File "m0_wl_public_normal_e2e.py", line 90 in ready\n')
            for _ in range(20):
                relay.observe()
            names=[x[0] for x in events]
            for expected in ("CLIENT_READY","SERVER_READY","GAME_FIRST_ERROR",
                             "STACK_E2E","WINDOWS_UDP_ALIVE",
                             "SUPERVISOR_POLL_OK"):
                self.assertEqual(names.count(expected),1,expected)
            self.assertEqual(dict(events)["STACK_E2E"],"READY_WAIT")
            self.assertNotIn("DO_NOT_PRINT",str(events))

    def test_blocked_stdout_does_not_affect_relay_sender(self):
        events=[]
        with tempfile.TemporaryDirectory() as d:
            out=pathlib.Path(d)
            q=queue.SimpleQueue()
            stopped=threading.Event()
            relay=GameFecRelay(out,q,stopped,env={},send=lambda a,b:events.append((a,b)))
            q.put("SUPERVISOR_LOOP_ENTER")
            q.put("SUPERVISOR_20S_ALIVE")
            thread=threading.Thread(target=relay.run,daemon=True)
            thread.start()
            for i in range(30):
                if len(events)>=2:break
                stopped.wait(.08)
            stopped.set()
            thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertIn(("SUPERVISOR_LOOP_ENTER","SUPERVISOR_ALIVE"),events)
            self.assertIn(("SUPERVISOR_ALIVE_FIRST","SUPERVISOR_ALIVE"),events)

    def test_priority_supervisor_receipts_before_expensive_log_observation(self):
        with tempfile.TemporaryDirectory() as d:
            out=pathlib.Path(d)
            events=[]
            q=queue.SimpleQueue()
            stopped=threading.Event()
            relay=GameFecRelay(out,q,stopped,env={},
                               send=lambda stage,detail:events.append((stage,detail)))
            q.put("SUPERVISOR_20S_ALIVE")
            (out/"client.log").write_text(
                "WBD_WINDOWS_GAME_COLD_TLS_JOINED lanes=2 fec=7\\n"
                "WBD_WINDOWS_GAME_NATIVE_APPLIED lanes=2 fec=7 tls=1\\n"
                "WBD_WINDOWS_OS_APPLIED\\n")
            thread=threading.Thread(target=relay.run,daemon=True)
            thread.start()
            for _ in range(70):
                if any(a=="OS_APPLIED" for a,b in events): break
                stopped.wait(.06)
            stopped.set();thread.join(2)
            names=[a for a,b in events]
            self.assertFalse(thread.is_alive())
            self.assertEqual(names[0],"SUPERVISOR_ALIVE_FIRST",
                             "PID heartbeat outranks client marker API calls")
            self.assertIn("CLIENT_TLS_JOINED",names)
            self.assertIn("CLIENT_OS_APPLIED",names)
            self.assertIn("OS_APPLIED",names)
            self.assertEqual(names.count("SUPERVISOR_ALIVE_FIRST"),1)

    def test_h760_stalled_gh_api_cannot_starve_observer(self):
        # A real GH call may take eight seconds, but the diagnostics-only
        # publisher must still accept successive unique marker events.
        with tempfile.TemporaryDirectory() as d:
            gate=threading.Event()
            started=threading.Event()
            def stalled_gh(*args,**kwargs):
                started.set()
                gate.wait(1.0)
            with mock.patch("tools.m0_wl_gamefec_relay.subprocess.run",side_effect=stalled_gh):
                relay=GameFecRelay(pathlib.Path(d),queue.SimpleQueue(),threading.Event(),
                    env={"WBD_WL_GAME_FEC_RESCUE":"1",
                         "GITHUB_RUN_ID":"41291160670",
                         "GITHUB_SHA":"0264c2cfc91e05c7c4b8d518fa0efc6707a2ff6b"})
                t=time.monotonic()
                for name in ("SUPERVISOR_20S_ALIVE","COLD_READY_WAIT","GAME_FIRST_ERROR"):
                    relay.emit(name,"TEST_ONLY")
                self.assertLess(time.monotonic()-t,.7)
                self.assertTrue(started.wait(.8))
                gate.set()

    def test_h760_append_only_cold_stages_and_no_secret_echo(self):
        with tempfile.TemporaryDirectory() as d:
            out=pathlib.Path(d); events=[]
            relay=GameFecRelay(out,queue.SimpleQueue(),threading.Event(),
                env={},send=lambda a,b:events.append((a,b)))
            (out/"gamefec-cold-stage.txt").write_text(
                "COLD_E2E_STARTED\nCOLD_WSL_IP_READY\n"
                "COLD_TLS_CERT_READY\nCOLD_CLIENT_SPAWNED\n"
                "COLD_READY_WAIT\nsecret=DO_NOT_LEAK\n")
            for _ in range(8): relay.observe()
            names={a for a,b in events}
            self.assertTrue({"COLD_E2E_STARTED","COLD_WSL_IP_READY",
                "COLD_TLS_CERT_READY","COLD_CLIENT_SPAWNED",
                "COLD_READY_WAIT"}<=names)
            self.assertNotIn("DO_NOT_LEAK",str(events))

    def test_h762_real_go_native_handoff_stages_have_independent_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            out=pathlib.Path(d)
            sent=[]
            relay=GameFecRelay(out,queue.SimpleQueue(),threading.Event(),
                env={},send=lambda stage,detail:sent.append((stage,detail)))
            (out/"client.log").write_text(
                "M0_GAME_COLD_STAGE WINTUN_OPEN_ENTER\n"
                "M0_GAME_COLD_STAGE WINTUN_OPEN_DONE\n"
                "M0_GAME_COLD_STAGE PRODUCT_PREPARE_ENTER\n"
                "M0_GAME_COLD_STAGE BIND_RING_ENTER\n"
                "M0_GAME_COLD_STAGE NPF_READER_JOIN_ENTER\n"
                "M0_GAME_COLD_STAGE NPF_READER_JOIN_DONE\n"
                "M0_GAME_COLD_STAGE RUST_GAME_START_ENTER\n"
                "M0_GAME_COLD_STAGE RUST_GAME_START_DONE\n"
                "M0_GAME_COLD_STAGE OS_APPLY_ENTER\n"
                "M0_GAME_COLD_STAGE OS_APPLY_DONE\n")
            for _ in range(34): relay.observe()
            expected=("WINTUN_OPEN_ENTER","WINTUN_OPEN_DONE",
                "PRODUCT_PREPARE_ENTER","BIND_RING_ENTER",
                "NPF_READER_JOIN_ENTER","NPF_READER_JOIN_DONE",
                "RUST_GAME_START_ENTER","RUST_GAME_START_DONE",
                "OS_APPLY_ENTER","OS_APPLY_DONE")
            for stage in expected:
                self.assertEqual([s for s,_ in sent].count(stage),1)
            self.assertNotIn("PASSWORD",str(sent))

    def test_stage_classifier_never_carries_python_locals(self):
        self.assertEqual(stack_stage("Thread 0xa\nFile ... in stop_linux token=secret"),"STOP_LINUX")
        self.assertEqual(stack_stage("Current thread ... subprocess.py:120\nuser=private"),"PROCESS_WAIT")
