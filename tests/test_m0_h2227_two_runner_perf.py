"""H2227 fixture safeguards; NEVER a substitute for two real Actions VMs."""
import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
FILE=ROOT/"tools/m0_h2227_dual_runner_perf.py"
SPEC=importlib.util.spec_from_file_location("h2227",FILE)
MOD=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

class TwoRunnerH2227(unittest.TestCase):
    def setUp(self):
        self.local={"source_sha":"a"*40,"run_id":"123456",
                    "tail_ip":"100.92.7.8"}
        self.peer={"schema_version":1,"role":"server","arch":"aarch64",
                   "source_sha":"a"*40,"run_id":"123456",
                   "tail_ip":"100.92.7.9",
                   "underlay_ip":"10.247.27.1",
                   "topology":"TS-VXLAN-L2-NATIVE-AF_PACKET",
                   "control_token":"d"*64}
    def test_truly_distinct_source_locked_peers(self):
        self.assertEqual(MOD.validate_peer(self.peer,"server",self.local),"100.92.7.9")
        for field,value in [("role","client"),("arch","x86_64"),
                            ("source_sha","b"*40),("run_id","999999"),
                            ("tail_ip","100.92.7.8"),
                            ("tail_ip","8.8.8.8"),
                            ("underlay_ip","10.247.27.2"),
                            ("topology","SINGLE-VM"),
                            ("control_token","public-run-id-is-not-a-secret")]:
            bad=dict(self.peer,**{field:value})
            with self.subTest(field=field,value=value):
                with self.assertRaises(RuntimeError):
                    MOD.validate_peer(bad,"server",self.local)
    def test_bbr_token_binds_run(self):
        a=MOD.token_for_run("a"*40,"123456")
        self.assertNotEqual(a,MOD.token_for_run("a"*40,"123457"))
        self.assertNotEqual(a,MOD.token_for_run("b"*40,"123456"))
        self.assertEqual(len(a),64)
    def test_netem_allowlist_never_shapes_management_interface(self):
        invoked=[]
        def fake_native(*cmd,**kwargs):
            invoked.append(cmd)
            return subprocess.CompletedProcess(cmd,0,
                json.dumps([{"kind":"netem","packets":300,"drops":4}]),"")
        with patch.object(MOD,"native",fake_native):
            q=MOD.set_netem(0.1,5)
            self.assertEqual(q["loss_pct"],0.1)
            self.assertEqual(q["only_owned_veth"],"wan0")
            self.assertTrue(q["tailscale_untouched"])
            with self.assertRaises(RuntimeError):MOD.set_netem(80,5)
            with self.assertRaises(RuntimeError):MOD.set_netem(1,900)
        self.assertEqual(len(invoked),2)
        self.assertTrue(all("wan0" in v for v in invoked))
        self.assertTrue(all("tailscale0" not in v for v in invoked))
    def test_unqualified_iperf_must_be_error_not_zero_mbps(self):
        fake=subprocess.CompletedProcess(["iperf3"],1,'{"error":"connection reset"}',"")
        with tempfile.TemporaryDirectory() as d,patch.object(MOD.subprocess,"run",return_value=fake):
            p=pathlib.Path(d)/"case-001.json"
            out=MOD.iperf_case("10.66.0.1",5201,3,1,False,p)
            self.assertEqual(out["status"],"ERROR")
            self.assertIsNone(out["business_mbps"])
            self.assertEqual(out["direction"],"upload")
            self.assertFalse(out["raw_baseline"])
            self.assertTrue(pathlib.Path(str(p)+".iperf.txt").is_file())
    def test_three_second_early_tcp_close_is_not_pass_or_zero(self):
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)/"case-010.json"
            record={"end":{"sum_sent":{"bits_per_second":160_000_000,
                                        "seconds":0.7}},
                    "intervals":[{"sum":{"bits_per_second":20_000_000}}]}
            with patch.object(MOD.subprocess,"run",return_value=subprocess.CompletedProcess(
                    ["iperf3"],0,json.dumps(record),"")):
                got=MOD.iperf_case("10.66.0.1",5201,3,1,False,path)
                self.assertEqual(got["status"],"ERROR")
                self.assertIsNone(got["business_mbps"])
            record["end"]["sum_sent"]["seconds"]=3.0
            with patch.object(MOD.subprocess,"run",return_value=subprocess.CompletedProcess(
                    ["iperf3"],0,json.dumps(record),"")):
                got=MOD.iperf_case("10.66.0.1",5201,3,1,False,path)
                self.assertEqual(got["status"],"PASS_OBSERVED_TCP_APPLICATION")
                self.assertEqual(got["business_mbps"],160.0)
                self.assertEqual(got["interval_mbps"],[20.0])

    def source_locked_examples(self,root,high_direct=False):
        direct,app=MOD.expected_matrix()
        self.assertEqual((len(direct),len(app)),(12,50))
        rows=sorted(direct)+sorted(app)
        for i,suffix in enumerate(rows):
            MOD.write_json(root/("case-%03d-%s.json"%(i,suffix)),{
                "status":"PASS_OBSERVED_TCP_APPLICATION",
                "business_mbps":900.0 if
                    (high_direct and suffix=="raw-0-fq600-upload") else 80.0,
                "raw_baseline":suffix in direct})
        return sorted(root.glob("case-*.json")),direct,app

    def test_exact_source_report_and_full_matrix_required(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            rows,direct,app=self.source_locked_examples(root)
            s=MOD.summary(root)
            self.assertEqual(len(s["baseline_mbps"]),12)
            self.assertEqual(len(s["business_mbps"]),50)
            self.assertEqual(s["classification"],"REAL_TWO_RUNNER_APPPATH_SCOPED")
            self.assertTrue(s["matrix_complete"])
            self.assertEqual(s["capacity_reference"],
                "INFRA_OR_TS_LIMITED_BELOW_800MBPS_DO_NOT_ATTRIBUTE_80MBPS_TO_WBD")
            f=rows[12]
            r=json.loads(f.read_text());r["status"]="ERROR";r["business_mbps"]=None
            MOD.write_json(f,r)
            bad=MOD.summary(root)
            self.assertEqual(bad["classification"],"FAIL_REAL_TWO_RUNNER_APPLICATION_OR_WORKER")
            f.unlink()
            incomplete=MOD.summary(root)
            self.assertEqual(incomplete["classification"],"FAIL_INCOMPLETE_TWO_RUNNER_APP_MATRIX")
            self.assertEqual(len(incomplete["cases"]),61)
            self.assertGreaterEqual(len(incomplete["missing_business_case_suffixes"]),1)
            self.assertTrue(incomplete["fails"])

    def test_derp_and_unqualified_capacity_never_implicate_wbd(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            self.source_locked_examples(root,high_direct=True)
            topo=root/"topology-client.json"
            MOD.write_json(topo,{"tailscale_path":"RELAY_OR_DERP_NOT_PRODUCT_CAPACITY"})
            relay=MOD.summary(root)
            self.assertTrue(relay["capacity_reference"].startswith("INFRA_OR_TS"))
            MOD.write_json(topo,{"tailscale_path":"DIRECT_CANDIDATE_BUT_VERIFY_RUNNER_CAPACITY"})
            direct=MOD.summary(root)
            self.assertEqual(direct["capacity_reference"],"COMPARABLE_800MBPS_BASELINE")

    def test_original_fec_grade_only_after_business_and_native_stop(self):
        shell=(ROOT/"tools/m0_h2227_dual_runner_case.sh").read_text()
        self.assertNotIn("H2227_FEC6_NOT_RUST_APPLIED",shell)
        src=shell.index("for spec in '3 1 upload'")
        stop=shell.index('sudo -n kill -TERM "$(cat "$TMP/client.pid")"')
        proof=shell.index("H2227_REAL_FEC6_POST_STOP_GRADE")
        self.assertLess(src,stop)
        self.assertLess(stop,proof)
        self.assertIn("REAL_FEC6_APPLIED_PROOF_MISSING_AFTER_BUSINESS_AND_STOP",shell)
        self.assertIn("--outer-repair on",shell)

    def test_reusable_main_push_static_only_manual_real_auth(self):
        yaml=(ROOT/".github/workflows/qa-h2227-two-runner-bbr-netem-iperf3.yml").read_text()
        self.assertIn("branches: ['main', 'fix/h2227-two-runner-bbr-netem-iperf3-uptx-fixture']",yaml)
        self.assertIn("workflow_dispatch:",yaml)
        self.assertIn("permissions:\n  contents: read\n",yaml)
        self.assertEqual(yaml.count("if: ${{ github.event_name == 'workflow_dispatch' }}"),2)
        self.assertEqual(yaml.count("permissions: {contents: read, actions: read, id-token: write}"),2)
        self.assertIn("H2227_FIXTURE_STATIC_PASS_NOT_NETWORK_NOT_PRODUCT",yaml)
        self.assertIn("H2227_REAL_TWO_RUNNER_BUSINESS_TCP_NO_3S_CRASH_PASS_NOT_WINDOWS_ISP",yaml)

    def test_arbitrary_targets_denied_before_running_iperf(self):
        for host,port in [("8.8.8.8",5201),("10.247.27.1",5201),
                          ("10.66.0.1",5202)]:
            with self.assertRaises(RuntimeError):
                MOD.iperf_case(host,port,3,1,False,"/dev/null")
if __name__=="__main__":unittest.main()
