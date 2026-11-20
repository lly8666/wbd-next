"""H2228: fail-closed three distinct runner topology / realistic loss fixture unit tests.

These tests NEVER imply real WAN, Linux BBR or kernel netem packet receipt.
"""
import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location(
  "h2228",ROOT/"tools/m0_h2228_three_runner_relay.py")
H=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)

class H2228ThreeGenuineMachines(unittest.TestCase):
    def setUp(self):
        self.local={"schema":1,"role":"client","arch":"x86_64",
            "source_sha":"a"*40,"run_id":"123456","tail_ip":"100.65.1.1",
            "network":"H2228-THREE-PHYSICAL-GHA-VM-L3-RELAY"}
        self.relay={**self.local,"role":"relay","arch":"aarch64",
            "tail_ip":"100.65.1.2","control_token":"9"*64}
        self.server={**self.local,"role":"server","arch":"x86_64",
            "tail_ip":"100.65.1.3"}

    def test_three_independent_roles_and_source_pinning(self):
        self.assertEqual(H.ROLES,{"client":"x86_64","server":"x86_64","relay":"aarch64"})
        self.assertEqual(H.validate_pair(self.local,self.relay,"relay"),"100.65.1.2")
        self.assertEqual(H.validate_pair(self.local,self.server,"server"),"100.65.1.3")
        for field,value in (
            ("arch","x86_64"),("source_sha","b"*40),("run_id","00000"),
            ("tail_ip","100.65.1.1"),("tail_ip","8.8.8.8"),
            ("control_token","not a random control token"),
            ("network","SAME_VM_NETNS")):
            with self.subTest(field=field,value=value):
                with self.assertRaises(RuntimeError):
                    H.validate_pair(self.local,{**self.relay,field:value},"relay")

    def test_stationary_mean_and_ge_real_burst_sensitivity(self):
        for loss in (1.0,5.0,10.0,20.0):
            ge=H.ge_params(loss)
            P=ge["transition_good_bad_pct"]/100
            R=ge["transition_bad_good_pct"]/100
            stationary_bad=P/(P+R)
            mean=stationary_bad*ge["bad_loss_pct"]+\
                (1-stationary_bad)*ge["good_loss_pct"]
            self.assertAlmostEqual(mean,loss,delta=0.000005)
            self.assertEqual(ge["mean_bad_burst_packets"],4)
        for bad in (0,0.1,1.5,8,25):
            with self.assertRaises(RuntimeError):H.ge_params(float(bad))

    def test_impair_only_arm_router_egress_both_directions(self):
        commands=[]
        def fake_ns(name,*cmd,**kwargs):
            commands.append((name,cmd))
            if cmd[:2]==("tc","-s"):
                return subprocess.CompletedProcess(cmd,0,json.dumps([{"kind":"netem"}]),"")
            return subprocess.CompletedProcess(cmd,0,"","")
        with patch.object(H,"ns",fake_ns):
            x=H.impair(10,200,"burst")
            self.assertEqual(x["gilbert"]["analytical_mean_loss_pct"],10)
            self.assertEqual(x["apply_to"],
                "RELAY_ROUTER_ONLY_EGRESS_BOTH_DIRECTIONS")
            self.assertEqual(x["bandwidth_rate_cap"],"NONE")
            self.assertEqual(set(x["qdiscs"]),{"rcli0","rsrv0"})
            self.assertEqual(sum(c[1][:3]==("tc","qdisc","replace") for c in commands),2)
            self.assertTrue(all(name==H.ROUTER for name,_ in commands))
            applied=[cmd for _,cmd in commands if cmd[:3]==("tc","qdisc","replace")]
            self.assertTrue(all("200ms" in cmd and "15ms" in cmd
                                and "gemodel" in cmd for cmd in applied))
            self.assertTrue(all("tailscale0" not in cmd and "rate" not in cmd
                                for cmd in applied))
            iid=H.impair(5,200,"iid")
            self.assertIsNone(iid["gilbert"])
            for params in [(30,200,"burst"),(10,300,"burst"),(10,200,"bad-model")]:
                with self.assertRaises(RuntimeError):H.impair(*params)

    def fill_cases(self,path,model):
        names=sorted(H.expected_cases(model))
        self.assertEqual(len(names),27)
        for i,case in enumerate(names):
            H.save(path/f"case-{i:03d}-{case}.json",{
                "status":"PASS_REAL_KERNEL_IPERF3_TCP","mbps":900.0,
                "kind":"direct" if "-direct-" in case else "wbd"})
        for role in ("client","server"):
            pass
        H.save(path/"clear-before-relay.json",{
            "tail_to_client":{"tail_path":"DIRECT_CANDIDATE"},
            "tail_to_server":{"tail_path":"DIRECT_CANDIDATE"}})
        return names

    def test_source_complete_and_incomplete_never_fake_green(self):
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)
            names=self.fill_cases(path,"burst")
            with patch.dict("os.environ",{"GITHUB_SHA":"a"*40,"GITHUB_RUN_ID":"123456"}):
                good=H.result_summary("normal","burst",path)
            self.assertEqual(good["status"],"PASS_REAL_THREE_RUNNER_TCP_MATRIX")
            self.assertEqual(good["expected_direct_cases"],12)
            self.assertEqual(good["expected_business_cases"],15)
            self.assertEqual(good["relay_capacity_qualification"],
                ">=800Mbps_BOTH_DIRECTIONS_DIRECT_TAILSCALE")
            wbd=next(path.glob("case-*-delay200-loss20-burst-wbd-20s-4p-upload.json"))
            wbd.unlink()
            incomplete=H.result_summary("normal","burst",path)
            self.assertEqual(incomplete["status"],"FAIL_INCOMPLETE_THREE_RUNNER_TCP_MATRIX")
            self.assertEqual(len(incomplete["missing_case_names"]),1)
            self.assertEqual(len(incomplete["raw_cases"]),26)

    def test_derp_fails_line_rate_attribution_even_for_fast_dummy_samples(self):
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)
            self.fill_cases(path,"iid")
            H.save(path/"clear-before-relay.json",{
                "tail_to_client":{"tail_path":"DERP_OR_RELAY_INFRA_LIMIT"},
                "tail_to_server":{"tail_path":"DIRECT_CANDIDATE"}})
            result=H.result_summary("normal","iid",path)
            self.assertTrue(result["relay_capacity_qualification"].startswith("INFRA_"))
            self.assertEqual(result["status"],"PASS_REAL_THREE_RUNNER_TCP_MATRIX")

    def test_exact_model_modes_and_role_specific_m0_contract(self):
        shell=(ROOT/"tools/m0_h2228_three_runner_case.sh").read_text()
        for line in ('--outer-repair on','for loss in 0 1 5 10 20',
                     'measure clear-zero direct 12 8 upload',
                     'measure "$label" direct 20 4 upload',
                     'measure "$label" wbd 20 4 download',
                     'H2228_IN_PROCESS_REAUTH'):
            self.assertIn(line,shell)
        workflow=(ROOT/".github/workflows/qa-h2228-three-runner-arm-relay-ge200.yml").read_text()
        self.assertIn("runs-on: ubuntu-24.04-arm",workflow)
        self.assertEqual(workflow.count("uses: tailscale/github-action@v4"),3)
        self.assertIn("workflow_dispatch:",workflow)
        self.assertIn("branches: ['main', 'test/h2228-three-runner-arm-relay-bbr-ge200']",workflow)
        self.assertIn("H2228_THREE_RUNNER_FIXTURE_STATIC_PASS_NOT_PRODUCT_PASS",workflow)

if __name__=="__main__":
    unittest.main()
