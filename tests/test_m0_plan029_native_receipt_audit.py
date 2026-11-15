"""Offline PLAN029 artifact audit: no OS/network/runtime prerequisites."""
import json
import pathlib
import tempfile
import unittest
import zipfile
import sys

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
import m0_plan029_native_receipt_audit as a

SHA="a"*40
SHA_OTHER="b"*40
FOUR=4*1024**2
ONE=2*1024**3
DUP=1536*1024**2


def sample(long=False,failed=False):
    p={
        "source_sha":SHA,"binary_source_sha":SHA,
        "physical_baseline":{"echo_bytes":FOUR,"half_close":True,
           "throughput_scope":"UNPACED_4M_BULK","payload_sha256":"1"*64,"elapsed_ms":40.},
        "direct_windows":{"echo_bytes":FOUR,"half_close":True,
           "throughput_scope":"UNPACED_4M_BULK","payload_sha256":"1"*64,"elapsed_ms":120.},
        "physical_guest":{"received_bytes":[FOUR,FOUR]},
        "overlap":True,"covered_whole_direct_tcp":True,"stop":"PASS_BOTH_OWNED",
        "highrate_direct_tcp":None}
    if long:
        stages={};physical={};delta={};udp={}
        for key,target,mbps in [(a.STAGES[0],ONE,500.),(a.STAGES[1],DUP,700.)]:
            base={"local_sent_bytes":target,
                  "local_received_bytes":DUP,
                  "actual_aggregate_mbps":mbps,
                  "original_process_cpu":{"original_process_total_cpu_s_per_gib":0.4},
                  "target_reached":True}
            direct={**base,"actual_aggregate_mbps":mbps-0.006,
                    "original_process_cpu":{"original_process_total_cpu_s_per_gib":12.4},
                    "target_reached":False}
            physical[key]=base;stages[key]=direct
            delta[key]={"added_process_total_cpu_s_per_gib":12.}
            for prefix in ("physical_",""):
                udp[prefix+key]={"unique_delivered":200,"rtt_p99_ms":1.5}
        sessions=[{"path":key,"half_close":True,
                   "oneway_received_bytes":ONE,
                   "duplex":{"local_received_bytes":DUP,"local_sent_bytes":DUP}}
                  for key in ("physical","direct")]
        p["highrate_direct_tcp"]={
            "source_sha":SHA,"status":a.RATE_PASS,
            "windows":{"source_sha":SHA,"stages":stages},
            "physical_control":{"source_sha":SHA,"stages":physical},
            "linux":{"source_sha":SHA,"sessions":sessions,
                     "oneway_received_bytes":ONE,
                     "duplex":{"local_received_bytes":DUP}},
            "tunnel_udp_per_stage":udp,"owner_stop":"PASS_BOTH_OWNED",
            "tunnel_udp_covers_rate":True,
            "same_vm_original_process_cpu_increment":delta}
    report={"source":SHA,
            "mode_public":("FAIL_TRUE_PUBLIC_EXECUTION" if failed else
                           "PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal"),
            "stop":"PASS_BOTH_OWNED","plan029_p2_mixed_real":p}
    return report


class NativeReceiptTests(unittest.TestCase):
    def audit(self,report,conclusion="success",manifest=True):
        with tempfile.TemporaryDirectory() as tmp:
            path=pathlib.Path(tmp)/"native.zip"
            with zipfile.ZipFile(path,"w") as z:
                z.writestr("report.json",json.dumps(report))
                if manifest:
                    z.writestr("mode-results/normal/artifact-manifest.json",
                               json.dumps({"source":SHA,"mode":"normal",
                                           "exit_code":0,"product_pass":True}))
            return a.analyse(path,SHA,conclusion)

    def test_real_4m_scoped_pass_but_never_claims_all_d1_d5(self):
        got=self.audit(sample())
        self.assertEqual(got["verdict"],"PASS_SCOPED_4M")
        self.assertEqual(got["metrics"]["4m"]["bytes_each"],FOUR)
        self.assertIn("NOT_FULL_PLAN029",got["limitations"])

    def test_10gib_actual_bytes_and_499_994_is_not_fake_ci_failure(self):
        got=self.audit(sample(long=True))
        self.assertEqual(got["verdict"],"PASS_SIGNED_LONG")
        stage=got["metrics"]["long_10gib"]["phases"][a.STAGES[0]]
        self.assertEqual(stage["direct_mbps"],499.994)
        self.assertIs(stage["target_reached_reported"],False)
        self.assertEqual(stage["added_original_process_cpu_s_per_gib"],12.)

    def test_true_native_failure_never_exempted(self):
        got=self.audit(sample(long=True,failed=True))
        self.assertEqual(got["verdict"],"TRUE_NATIVE_PRODUCT_FAILURE")

    def test_action_red_cannot_automatically_be_called_false_red(self):
        got=self.audit(sample(long=True),"failure")
        self.assertEqual(got["verdict"],"ACTION_FAILURE_REVIEW_REQUIRED")

    def test_missing_action_conclusion_never_promoted(self):
        got=self.audit(sample(long=True),"unknown")
        self.assertEqual(got["verdict"],"ACTION_CONCLUSION_NOT_ATTESTED")

    def test_wrong_source_is_fail_closed_before_cpu_or_rate(self):
        report=sample(long=True);report["source"]=SHA_OTHER
        got=self.audit(report)
        self.assertEqual(got["verdict"],"SOURCE_MISMATCH")

    def test_sha_or_fin_incomplete_is_not_scoped_pass(self):
        report=sample();report["plan029_p2_mixed_real"]["direct_windows"]["half_close"]=False
        self.assertEqual(self.audit(report)["verdict"],"INCOMPLETE_OR_INCONSISTENT_P2")
        report=sample();report["plan029_p2_mixed_real"]["direct_windows"]["payload_sha256"]="2"*64
        self.assertEqual(self.audit(report)["verdict"],"INCOMPLETE_OR_INCONSISTENT_P2")

    def test_missing_10gib_one_direction_fails_closed(self):
        report=sample(long=True)
        report["plan029_p2_mixed_real"]["highrate_direct_tcp"]["linux"]["sessions"][1][
             "duplex"]["local_received_bytes"]-=1
        self.assertEqual(self.audit(report)["verdict"],"INCOMPLETE_OR_INCONSISTENT_LONG")


if __name__=="__main__":
    unittest.main()
