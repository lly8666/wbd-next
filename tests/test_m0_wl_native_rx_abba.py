"""Source-locked same-Windows-runner Rust A/B/B/A decision gates (pure, no drivers)."""
import pathlib,sys,tempfile,unittest,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from m0_wl_native_rx_abba import decision,gates,PAIRS

def leg(label,cpu,okay=True,stop=True):
 return {"leg":label,"variant":label[-1],
         "stop_verified":stop,"qualified":okay,
         "cpu":{"cpu_seconds_per_first_delivered_gb":cpu}}
class ABBAHardGates(unittest.TestCase):
 def test_exact_two_hardcoded_immutable_product_sources(self):
  self.assertEqual(PAIRS["A"]["source"],"7fc38591c501ff4a06e1862c7b08d5d3dbc1be95")
  self.assertEqual(PAIRS["B"]["source"],"e6be9358d2272d7e1960a935be7fe772885bb034")
  self.assertNotEqual(PAIRS["A"]["run"],PAIRS["B"]["run"])
 def test_order_and_complete_stops_fail_closed(self):
  ok=[leg("1-A",10),leg("2-B",9),leg("3-B",9),leg("4-A",10)]
  self.assertEqual(decision(ok)["decision"],"KEEP_B")
  self.assertEqual(decision(ok[1:])["decision"],"INCONCLUSIVE")
  self.assertEqual(decision([ok[1],ok[0],ok[2],ok[3]])["decision"],"INCONCLUSIVE")
  ok[1]["stop_verified"]=False
  self.assertEqual(decision(ok)["decision"],"ROLL_BACK_B")
 def test_delivery_failure_in_b_overrides_cpu_gain(self):
  rows=[leg("1-A",10),leg("2-B",3,False),leg("3-B",3),leg("4-A",10)]
  self.assertEqual(decision(rows)["decision"],"ROLL_BACK_B")
 def test_no_benefit_rollback_and_same_host_drift_counterbalance(self):
  rows=[leg("1-A",10),leg("2-B",10),leg("3-B",10),leg("4-A",10)]
  self.assertEqual(decision(rows)["decision"],"ROLL_BACK_B")
  rows=[leg("1-A",9),leg("2-B",8.2),leg("3-B",8.8),leg("4-A",11)]
  got=decision(rows)
  self.assertEqual(got["decision"],"KEEP_B")
  self.assertAlmostEqual(got["relative_b_vs_a"],-0.15)
 def test_missing_cpu_cannot_be_called_zero(self):
  rows=[leg("1-A",10),leg("2-B",None),leg("3-B",8),leg("4-A",11)]
  self.assertEqual(decision(rows)["decision"],"INCONCLUSIVE")
 def test_real_kernel_and_unique_receipt_required(self):
  report={"mode_public":"PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal",
          "stop":"PASS_BOTH_OWNED","WL_V2":{"status":"MEASURED_BOTH_OS_KERNEL",
          "owned_stop":"PASS_BOTH_OWNED",
          "offered_mbps":{"windows":149.9,"linux":149.9},
          "first_delivery_fraction":{"windows":1.,"linux":1.}}}
  linux={"udp_socket_probe_deltas":{
          "linux_socket_udp_drops_delta":0,"linux_raw_socket_deltas":{
            "12":{"drops_delta":0},"13":{"drops_delta":0}}},
          "udp_socket_probe_end":{"linux_raw_socket_owners":{
             "12":{"pid":1},"13":{"pid":1}}}}
  with tempfile.TemporaryDirectory() as temp:
   # gates() reads the actual full native tc qdisc fixture file.
   from m0_wl_native_rx_abba import OUT
   old=OUT
   import m0_wl_native_rx_abba as module
   module.OUT=pathlib.Path(temp)
   try:
    (module.OUT/"wl-n0-netem-after.json").write_text(json.dumps({
       "ifb":[{"kind":"netem","drops":0,"packets":1000}],
       "eth0":[{"kind":"netem","drops":0,"packets":900}]}))
    good=gates(report,{},linux)
    self.assertTrue(all(good[k] is True for k in (
       "native_stop_and_mode","delivery_ge_99_9_both",
       "offer_ge_95pct_150m_both",
       "linux_owned_raw_socket_kernel_drops_zero",
       "linux_fixture_udp_socket_drops_zero","real_tc_drops_zero")))
    linux["udp_socket_probe_deltas"]["linux_raw_socket_deltas"]["12"]["drops_delta"]=1
    self.assertFalse(gates(report,{},linux)["linux_owned_raw_socket_kernel_drops_zero"])
   finally:module.OUT=old
if __name__=="__main__":unittest.main()
