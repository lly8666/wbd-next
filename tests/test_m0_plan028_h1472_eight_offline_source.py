"""No original native execution: validate eight artifact-source forensic contract."""
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/"tools/m0_plan028_h1472_eight_short_original_offline.py"
YAML=ROOT/".github/workflows/m0-plan028-h1472-eight-immutable-180s-offline-rejudge.yml"

class EightOriginalSourceOffline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location("h1472_case_original",SRC)
        cls.mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    def test_all_original_exact_artifact_ids_source_manifests_and_cases(self):
        m=self.mod
        self.assertEqual(len(m.FILES),8)
        self.assertEqual(len({(a,b) for a,b,_,_ in m.FILES}),8)
        self.assertEqual({r["id"] for r in m.ART.values()},
                         {13661277093,13660868907,13661168078,13660943781})
        self.assertNotEqual(m.OLD,m.NEW)
        self.assertEqual(len(m.NEW),len(m.OLD))
        self.assertEqual(set(m.BIN),{m.NEW,m.OLD})
        self.assertEqual(len(m.BIN[m.NEW]),3)
        self.assertEqual(len(m.BIN[m.OLD]),3)
        self.assertEqual(len(set(m.BIN[m.OLD].values())&set(m.BIN[m.NEW].values())),0)

    def test_native_owner_queue_receipt_parses_real_sized_bounded_lease(self):
        m=self.mod
        example="M0_SHARED_TUN_LEASE_QUEUE_DIAG ip=10.66.0.240 offered=1424741 direct_delivered=1424688 downstream_full=93 pending_overflow=32 pending_byte_limit=0 pending_peak_packets=8 pending_peak_bytes=7872"
        got=m.QUEUE_RE.findall(example)
        self.assertEqual(len(got),1)
        self.assertEqual(got[0][0],"10.66.0.240")
        self.assertEqual(int(got[0][4]),32)
        self.assertEqual(int(got[0][6]),8)
        self.assertEqual(int(got[0][7]),7872)

    def test_real_old_reversal_failure_not_hidden_by_new_zero_udp(self):
        s=SRC.read_text()
        self.assertIn('new_jitter["strict_zero_loss"]=="FAIL_SCOPED"',s)
        self.assertIn('new_jitter["original_alice_server_queue_overflow"])==(0,32)',s)
        self.assertIn('oldbad["original_alice_server_queue_overflow"])==(57,16,78)',s)
        self.assertIn('rotating["all_five_server_lease_queue_overflow"])==(16,25,0)',s)
        self.assertIn('original_H1286_raw_alerts',s)
        self.assertIn('rotation_qualifier',s)
        self.assertIn('NOT_REQUESTED_NOT_FAIL',s)
        self.assertIn('FAIL_SCOPED',s)

    def test_true_180s_five_users_all_six_stops_and_zero_loss_counts(self):
        s=SRC.read_text()
        for marker in ('"h1250-c-"','"h1250-s-"',
                       '==180_000_000_000','V4_PUBLIC_SHARED_TUN_STOP generation=',
                       'M0_SHARED_TUN_LEASE_QUEUE_DIAG',
                       '"h1286-rapid-report.json"',
                       'plan["source_sha"]==source',
                       'original_six_owned_final_Stops',
                       'original_total_unique_UDP_missing'):
            self.assertIn(marker,s)
        self.assertIn('assert len(q)==5',s)
        self.assertIn("NO_ORIGINAL_TLS_SERVER_PORT_READY",s)
        self.assertNotIn('assert "V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443" in original_logs["server"]',s)
        self.assertIn('alloverflow',s)
        self.assertIn('assert sum(x[1] for x in phase_plan)==180',s)

    def test_offline_workflow_cannot_accidentally_start_original_network(self):
        y=YAML.read_text()
        self.assertEqual(y.count("run-id: 42590018240"),2)
        self.assertEqual(y.count("run-id: 42590601995"),2)
        self.assertEqual(y.count("actions/download-artifact@"),4)
        self.assertIn('m0_plan028_h1472_eight_short_original_offline.py',y)
        self.assertIn('H1472_NO_NEW_NETWORK_EIGHT_ORIGINAL_NATIVE_SOURCE_SCOPED_VERIFIED',y)
        self.assertNotIn("ip netns",y)
        self.assertNotIn("sudo ",y)
        self.assertNotIn("runs-on: windows",y)
        self.assertNotIn("cargo build",y)
        self.assertNotIn("[plan028-win-linux-1800]",y)

if __name__=="__main__":
    unittest.main()
