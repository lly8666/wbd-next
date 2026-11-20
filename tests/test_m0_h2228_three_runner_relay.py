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

    def test_bbr_must_be_set_inside_new_linux_namespace(self):
        invocations=[]
        def root(*args,**kwargs):
            invocations.append(("root",args))
            return subprocess.CompletedProcess(args,0,"","")
        def ns(name,*args,**kwargs):
            invocations.append((name,args))
            value="bbr\n" if args==("sysctl","-n","net.ipv4.tcp_congestion_control") else (
                "4096 87380 67108864\n")
            return subprocess.CompletedProcess(args,0,value,"")
        with patch.object(H,"root",root),patch.object(H,"ns",ns):
            actual=H.bbr(H.NODE)
        self.assertEqual(actual["tcp_cc"],"bbr")
        self.assertIn((H.NODE,("sysctl","-q","-w",
                      "net.ipv4.tcp_congestion_control=bbr")),invocations)
        self.assertIn(("root",("sysctl","-q","-w",
                      "net.ipv4.tcp_congestion_control=bbr")),invocations)
        self.assertGreater(len([n for n,args in invocations if n==H.NODE]),6)

    def test_tailnet_control_reuses_proven_tcp18727_and_waits_for_bind(self):
        self.assertEqual(H.CONTROL_PORT,18727)
        shell=(ROOT/"tools/m0_h2228_three_runner_case.sh").read_text()
        self.assertIn("H2228_RELAY_CONTROL_BIND_FAILED tcp18727",shell)
        self.assertIn("H2228_RELAY_CONTROL_NOT_REACHABLE_REAL_NOT_RUN",shell)
        self.assertIn("relay_http_ready=0",shell)

    def test_first_derp_then_direct_is_not_mislabeled_a_permanent_relay(self):
        ping=("pong from h228-peer (100.99.1.8) via DERP(dfw) in 101ms\n"
              "pong from h228-peer (100.99.1.8) via 20.221.60.81:14344 in 8ms\n")
        self.assertEqual(H.classify_final_tail_ping(ping,0),"DIRECT_CANDIDATE")
        self.assertEqual(H.classify_final_tail_ping(ping.splitlines()[0],0),
                         "DERP_OR_RELAY_INFRA_LIMIT")
        self.assertEqual(H.classify_final_tail_ping(ping,1),"UNKNOWN_NOT_QUALIFIED")

    def test_cold_ready_wait_must_check_real_root_worker_pid_not_sudo_parent(self):
        shell=(ROOT/"tools/m0_h2228_three_runner_case.sh").read_text()
        self.assertIn('sudo -n kill -0 "$owned_pid"',shell)
        self.assertNotIn('if ! kill -0 "$parent" 2>/dev/null;then break',shell)
        self.assertIn('rm -f "$pidfile"',shell)
        self.assertIn('H2228_NATIVE_WORKER_EXIT_BEFORE_COLD_READY',shell)

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

    def test_ack10ms_h2229_is_current_source_not_stale_pre_ack(self):
        ack=ROOT/'crates/wbd-engine/src/v4_presentation_ack.rs'
        self.assertTrue(ack.exists(),'H2229 common presentation ACK missing: stale product branch')
        src=ack.read_text()
        self.assertIn('ACK_ONLY_MIN_INTERVAL_NS:u64=10_000_000',src)
        self.assertIn('STEADY_TCP_WINDOW:u16=65_535',src)
        self.assertIn('real_out_of_order',src)
        wf=(ROOT/'.github/workflows/qa-h2228-three-runner-arm-relay-ge200.yml').read_text()
        self.assertIn('tests.test_m0_h2229_native_ack_unified -v',wf)

    def test_relay_snapshots_cannot_masquerade_as_iperf_cases(self):
        shell=(ROOT/"tools/m0_h2228_three_runner_case.sh").read_text()
        self.assertIn('if [[ "$label" == case-* ]];then label="relay-receipt-$label";fi',shell)
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)
            self.fill_cases(path,"burst")
            H.save(path/"relay-receipt-case-000-clear-zero-direct-12s-8p-upload-relay.json",{
                "qdisc":{"kind":"netem"},"not_iperf":True})
            result=H.result_summary("normal","burst",path)
            self.assertEqual(result["status"],"PASS_REAL_THREE_RUNNER_TCP_MATRIX")
            self.assertEqual(result["observed_qualified_cases"],27)

    def test_iperf_tcp_failure_not_same_as_native_client_process_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            p=root/"real-root-owner.pid"
            p.write_text("42424\n")
            fail=subprocess.CompletedProcess(["iperf3"],1,
                '{"error":"control socket has closed unexpectedly"}', "")
            running=subprocess.CompletedProcess(["sudo","-n","ps"],0,"S wbd-v4-client\n","")
            with patch.object(H.subprocess,"run",side_effect=[fail,running]) as proc:
                result=H.iperf("wbd",3,1,"upload",root/"case-001.json",str(p))
            self.assertEqual(result["status"],"ERROR_TCP_CRASH_ABORT_OR_UNREACHABLE")
            self.assertTrue(result["native_worker_alive_after_iperf"])
            self.assertEqual(result["tcp_failure_cause"],
                "INNER_TCP_CONTROL_OR_RESULT_ERROR_NATIVE_WORKER_ALIVE")
            self.assertEqual(len(proc.call_args_list),2)
            self.assertEqual(proc.call_args_list[-1].args[0][-1],"42424")
            # TCP can report real bits while the original native owner
            # has exited: keep numeric observation but do NOT say PASS.
            passed=subprocess.CompletedProcess(["iperf3"],0,
                '{"end":{"sum_sent":{"bits_per_second":120000000,"seconds":3.0}}}',"")
            gone=subprocess.CompletedProcess(["sudo","-n","ps"],1,"","")
            with patch.object(H.subprocess,"run",side_effect=[passed,gone]):
                observed=H.iperf("wbd",3,1,"upload",root/"case-002.json",str(p))
            self.assertEqual(observed["mbps"],120.0)
            self.assertEqual(observed["status"],"ERROR_TCP_CRASH_ABORT_OR_UNREACHABLE")
            self.assertFalse(observed["native_worker_alive_after_iperf"])
            self.assertEqual(observed["tcp_failure_cause"],
                "NATIVE_WORKER_EXITED_AFTER_REPORTED_TCP_BITS")
            with self.assertRaises(RuntimeError):
                H.iperf("direct",12,8,"upload",root/"bad.json",str(p))
            shell=(ROOT/"tools/m0_h2228_three_runner_case.sh").read_text()
            self.assertIn('owner_check=(--pidfile "$TMP/client.pid")',shell)
            self.assertIn('"${owner_check[@]}"',shell)

    def test_kernel_qdisc_phase_drop_is_real_not_target_assumption(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)
            prefix="delay200-loss1-burst"
            def snap(emitted,dropped):
                return {role:{"qdisc":[{"kind":"netem",
                    "handle":"8001:" if role=="client" else "8002:",
                    "options":{"loss-gemodel":{"p":0.003,"r":0.25}},
                    "packets":emitted,"drops":dropped}]}
                    for role in ("client","server")}
            H.save(root/f"{prefix}-before-relay.json",snap(0,0))
            H.save(root/f"{prefix}-final-relay.json",snap(990,10))
            result=H.observed_relay_phase_loss(root,prefix)
            self.assertEqual(result["status"],"REAL_KERNEL_NETEM_PHASE_COUNTER_DIFFERENCE")
            self.assertEqual(result["server_to_client"]["drop_pct_approx"],1.0)
            self.assertEqual(result["client_to_server"]["drop_pct_approx"],1.0)
            self.assertEqual(result["client_to_server"]["dropped_packets"],10)
            H.save(root/f"{prefix}-final-relay.json",snap(700,0))
            changed=H.observed_relay_phase_loss(root,prefix)
            self.assertEqual(changed["client_to_server"]["drop_pct_approx"],0.0)
            H.save(root/f"{prefix}-before-relay.json",snap(900,50))
            invalid=H.observed_relay_phase_loss(root,prefix)
            self.assertEqual(invalid["status"],"UNKNOWN_INCONSISTENT_NETEM_SNAPSHOTS")

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
