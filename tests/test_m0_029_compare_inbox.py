"""Bounded negative/positive tests for no-false-PASS PLAN029 A/B/A readout."""
import importlib.util
import pathlib
import unittest

PATH=pathlib.Path(__file__).resolve().parents[1]/"tools/m0_029_compare_inbox.py"
spec=importlib.util.spec_from_file_location("m029_comparator",PATH)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SOURCE="a"*40

def fixture(bps=(300,330,290),cpu=(10,9,10)):
    rows=[]
    for idx,(name,slots) in enumerate(mod.ORDER):
        echo={k:{"requests_sent":160,"unique_replies":150,"missing":10,
                 "latency_ms":{"p99":300.0}} for k in ("udp","tcp")}
        row={"name":name,"server_inbox_slots":slots,
             "status":"PASS_SCOPED_REAL_SOURCE_MEASURED_NOT_PRODUCT_GAIN",
             "owned_stop":{"server":{"generation":20+idx},"client":{"generation":30+idx}},
             "measure":{"original_product_tcp":{
                 "tcp_streams":4,"receiver_bps":bps[idx]*1e6,
                 "start_monotonic_ns":1000,"end_monotonic_ns":200000000000},
                 "cpu_and_rss":{"server":{"cpu_seconds_per_rx_gib":cpu[idx]},
                                "client":{"cpu_seconds_per_rx_gib":cpu[idx]}},
                 "smallflow":{"status":"PASS_SCOPED_REAL_INNER_UDP_TCP_ECHO",
                              "probe_start_monotonic_ns":1000000000,
                              "probe_end_monotonic_ns":12000000000,**echo},
                 "router_kernel_skb":{dev:{"netem_skb_emitted_delta":1000,
                                           "netem_skb_drop_delta":10}
                                      for dev in ("rcli0","rsrv0")}}}
        rows.append(row)
    return {"source_sha":SOURCE,"run_id":"5","architecture":"aarch64",
            "status":"PASS_SCOPED_REAL_ABA_MEASURED_NOT_PRODUCT_GAIN",
            "old_and_new_same_build_manifest":{
                 "libwbd_engine.so":"hash","wbd-v4-client":"hash",
                 "wbd-v4-server":"hash"},"phases":rows}

class TestCompare(unittest.TestCase):
    def test_abca_no_product_pass_and_missing_preserved(self):
        result=mod.readout(fixture(),SOURCE,"5")
        self.assertEqual(result["screen_decision"],
                         "BETTER_GOODPUT_OUTSIDE_BASELINE_BUT_NOT_ACCEPTED")
        self.assertEqual(result["smallflow"]["udp"]["missing"],[10,10,10])
        self.assertEqual(result["smallflow"]["tcp"]["missing"],[10,10,10])
        self.assertEqual(result["status"],"SAME_RUN_SCOPED_SCREEN_NOT_PRODUCT_PASS")
    def test_cost_tradeoff_does_not_claim_full_gain(self):
        result=mod.readout(fixture((300,301,310),(10,9,10)),SOURCE,"5")
        self.assertEqual(result["screen_decision"],"INCONCLUSIVE_OR_COST_TRADEOFF")
    def test_worse_goodput_is_a_negative_screen(self):
        result=mod.readout(fixture((300,250,295)),SOURCE,"5")
        self.assertEqual(result["screen_decision"],"WORSE_GOODPUT_OUTSIDE_BASELINE")
    def test_no_promotion_when_run_or_source_wrong(self):
        with self.assertRaises(ValueError):mod.readout(fixture(),"b"*40,"5")
        with self.assertRaises(ValueError):mod.readout(fixture(),SOURCE,"6")
    def test_missing_response_not_allowed_as_fast_p99(self):
        x=fixture()
        x["phases"][1]["measure"]["smallflow"]["udp"]["missing"]=0
        with self.assertRaises(ValueError):mod.readout(x,SOURCE,"5")
    def test_missing_owned_stop_and_nonconcurrent_rejected(self):
        x=fixture();del x["phases"][2]["owned_stop"]["server"]["generation"]
        with self.assertRaises(ValueError):mod.readout(x,SOURCE,"5")
        y=fixture()
        y["phases"][1]["measure"]["smallflow"]["probe_end_monotonic_ns"]=1000000000000
        with self.assertRaises(ValueError):mod.readout(y,SOURCE,"5")
    def test_scalar_baseline_drift_is_explicit(self):
        r=mod.compare_scalar(100,130,120)
        self.assertEqual(r["candidate_vs_baselines"],"ABOVE_BOTH")
        self.assertGreater(r["baseline_drift_pct"],0)
        with self.assertRaises(ValueError):mod.compare_scalar(1,0,1)

if __name__=="__main__":unittest.main()
