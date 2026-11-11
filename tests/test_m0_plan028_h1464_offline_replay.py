"""H1464 offline only: source-locked rejudge must not erase negative original data."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
REPORT=ROOT/"tools/m0-plan028-h1274-30min-report.py"
VERDICT=ROOT/"tools/m0_plan028_h1461_five_client_soak_verdict.py"
REPLAY=ROOT/"tools/m0_plan028_h1464_offline_replay.py"
WORKFLOW=ROOT/".github/workflows/m0-plan028-h1464-two-original-soaks-offline-replay.yml"

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class OriginalTwoSoakReplay(unittest.TestCase):
    def test_reporter_iterates_phase_specs_not_its_empty_output_list(self):
        s=REPORT.read_text()
        self.assertIn("phase_specs=(H1520_OUTER_PHASES if h1520 else MID600_PHASES) if midsix else PHASES",s)
        self.assertIn("for i,(name,phase_seconds,rate_scale) in enumerate(phase_specs):",s)
        self.assertIn('assert len(phases)==len(phase_specs)',s)
        self.assertNotIn("for i,(name,phase_seconds,rate_scale) in enumerate(phases):",s)
        self.assertIn("assert sum(p[1] for p in phase_specs)==duration",s)

    def test_reviewed_product_source_not_relabelled_as_new_harness(self):
        s=REPLAY.read_text()
        self.assertIn('SOURCE="66fb6b4454b1ce4297ab04efa20c7f931ff12383"',s)
        self.assertIn("ACTION=42578056120",s)
        self.assertIn('"artifact_id":13656024788',s)
        self.assertIn('"artifact_id":13657785615',s)
        self.assertIn("reviewer_sha!=SOURCE",s)
        self.assertIn('manifest["source_sha"]==SOURCE',s)
        self.assertIn("original_manifest_sha256",s)
        self.assertIn("original_product_sha256",s)
        self.assertIn("H1464_IMMUTABLE_ORIGINAL_NATIVE_600_AND_1800_NEGATIVE_REPLAY_PASS",s)

    def test_zero_loss_original_600_32_missing_45_overflow_and_1800_351(self):
        s=REPLAY.read_text()
        self.assertIn('verdict["total_true_queue_overflow"]==45',s)
        self.assertIn('alice_down==32',s)
        self.assertIn('==[0,0,0,32,0]',s)
        self.assertIn('verdict["total_true_queue_overflow"]==0',s)
        self.assertIn('alice_down==351',s)
        self.assertIn('"_ZERO_LOSS_MISSING_"',VERDICT.read_text())
        self.assertIn('"_NO_CONFIGURED_LOSS_UDP_MISSING_"',VERDICT.read_text())

    def test_original_durations_six_Stops_and_phase_time_checked(self):
        s=REPLAY.read_text()
        self.assertIn('raw["end_ns"]-raw["start_ns"]==duration*1_000_000_000',s)
        self.assertIn('STOP="V4_PUBLIC_SHARED_TUN_STOP generation="',s)
        self.assertIn("assert all(stop.values())",s)
        self.assertIn('["phases"])==5',s)
        self.assertIn('sum(x["seconds"]',s)
        self.assertIn('["rotation_verdict"]=="PASS_ALL_FIVE_SCOPED"',s)
        self.assertIn("original_1800_authentic_rotation_verdict",s)

    def test_udp_replay_distinguishes_real_sender_vs_real_receiver(self):
        mod=load_module("m0_h1464_replay_unit",REPLAY)
        with tempfile.TemporaryDirectory() as t:
            root=pathlib.Path(t)
            sample=lambda role, n:{"role":role,"stats":{"udp":[{"tx_packets":n[0],"rx_packets":n[1]}]}}
            (root/"h1250-c-alice.json").write_text(json.dumps(sample("client",(100,95))))
            (root/"h1250-s-alice.json").write_text(json.dumps(sample("server",(98,99))))
            up=mod.phase_totals(root,"alice","uplink")
            down=mod.phase_totals(root,"alice","downlink")
            self.assertEqual(up[0]["missing"],1)
            self.assertEqual(down[0]["missing"],3)

    def test_only_existing_archive_downloads_no_new_sudo_or_binary_runner(self):
        s=WORKFLOW.read_text()
        self.assertIn("run-id: 42578056120",s)
        self.assertEqual(s.count("run-id: 42578056120"),2)
        self.assertIn("plan028-h1461-real-fiveclient-600s-capacity75-42578056120",s)
        self.assertIn("plan028-h1461-real-fiveclient-1800s-heterogeneous-42578056120",s)
        self.assertIn("tools/m0_plan028_h1464_offline_replay.py",s)
        self.assertNotIn("sudo ",s)
        self.assertNotIn("fixed-build/wbd-v4-client",s)
        self.assertNotIn("fixed-build/wbd-v4-server",s)
        self.assertNotIn("cargo build",s)
        self.assertNotIn("runs-on: windows",s)

if __name__=="__main__":
    unittest.main()
