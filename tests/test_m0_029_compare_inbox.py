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
        start=1000000000+idx*30000000000
        end=start+20000000000
        echo={k:{"requests_sent":160,"unique_replies":150,"missing":10,
                 "latency_ms":{"p99":300.0}} for k in ("udp","tcp")}
        row={"name":name,"server_inbox_slots":slots,
             "status":"PASS_SCOPED_REAL_SOURCE_MEASURED_NOT_PRODUCT_GAIN",
             "owned_stop":{"server":{"generation":20+idx},"client":{"generation":30+idx}},
             "measure":{"original_product_tcp":{
                 "tcp_streams":4,"receiver_bps":bps[idx]*1e6,
                 "start_monotonic_ns":start,"end_monotonic_ns":end},
                 "cpu_and_rss":{"server":{"cpu_seconds_per_rx_gib":cpu[idx]},
                                "client":{"cpu_seconds_per_rx_gib":cpu[idx]}},
                 "smallflow":{"status":"PASS_SCOPED_REAL_INNER_UDP_TCP_ECHO",
                              "probe_start_monotonic_ns":start+2000000000,
                              "probe_end_monotonic_ns":start+14000000000,**echo},
                 "router_kernel_skb":{dev:{"netem_skb_emitted_delta":1000,
                                           "netem_skb_drop_delta":10}
                                      for dev in ("rcli0","rsrv0")}}}
        rows.append(row)
    return {"source_sha":SOURCE,"run_id":"5","architecture":"aarch64",
            "scenario":"ZERO_LOSS_0MS_NATIVE_ARM64_HIGH_SUPPLY_4_TCP_PLUS_SMALL",
            "netem_ge_stationary_parameters":{"profile":"ZERO_ARTIFICIAL_LOSS","target_loss_pct":0.0},
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
    def test_client_only_phases_must_have_actual_both_cold_readbacks(self):
        data=fixture()
        data["scenario"]="ZERO_LOSS_0MS_NATIVE_ARM64_CLIENT_ONLY_INBOX_ABA"
        for idx,row in enumerate(data["phases"]):
            row["client_inbox_slots"]=row.pop("server_inbox_slots")
            row["server_inbox_slots"]=64
            row["client_generation"]=10+idx
            row["server_generation"]=20+idx
            row["native_cold_readback_verified"]=True
        result=mod.readout(data,SOURCE,"5")
        self.assertEqual(result["changed_inbox_side"],"client")
        self.assertNotEqual(result["status"],"PRODUCT_PASS")
        data["phases"][1]["server_inbox_slots"]=256
        with self.assertRaises(ValueError):mod.readout(data,SOURCE,"5")
        data["phases"][1]["server_inbox_slots"]=64
        del data["phases"][1]["native_cold_readback_verified"]
        with self.assertRaises(ValueError):mod.readout(data,SOURCE,"5")
    def test_overlapping_original_candidate_legs_must_fail(self):
        data=fixture()
        candidate=data["phases"][1]["measure"]
        candidate["original_product_tcp"]["start_monotonic_ns"]=10000000000
        candidate["original_product_tcp"]["end_monotonic_ns"]=30000000000
        candidate["smallflow"]["probe_start_monotonic_ns"]=12000000000
        candidate["smallflow"]["probe_end_monotonic_ns"]=24000000000
        with self.assertRaises(ValueError):mod.readout(data,SOURCE,"5")
    def test_ge1_wrong_stationary_probability_rejected(self):
        x=fixture()
        x["scenario"]="GE1% stationary two L3 router qdiscs; +200ms each direction"
        x["netem_ge_stationary_parameters"]={
            "target_loss_pct":1.0,"good_to_bad_pct":0.252809,
            "bad_to_good_pct":25.0,"bad_loss_pct":90.0,
            "good_loss_pct":0.1}
        self.assertEqual(mod.readout(x,SOURCE,"5")["trial_shape"],"A64_B256_A64")
        x["netem_ge_stationary_parameters"]["good_to_bad_pct"]=0.16
        with self.assertRaises(ValueError):mod.readout(x,SOURCE,"5")
    def test_client_lower_memory_128_cold_source(self):
        x=fixture()
        x["scenario"]="ZERO_LOSS_0MS_NATIVE_ARM64_CLIENT_ONLY_INBOX_128_ABA"
        for idx,row in enumerate(x["phases"]):
            old=row.pop("server_inbox_slots")
            row["frozen_stage_slots"]=old
            row["server_inbox_slots"]=64
            row["client_inbox_slots"]=(64,128,64)[idx]
            row["native_cold_readback_verified"]=True
            row["client_generation"]=10+idx
            row["server_generation"]=20+idx
            if idx==1:row["name"]="inbox128_candidate"
        out=mod.readout(x,SOURCE,"5")
        self.assertEqual(out["trial_shape"],"A64_B128_A64")
        self.assertEqual(out["changed_inbox_side"],"client")
        x["phases"][1]["frozen_stage_slots"]=128
        with self.assertRaises(ValueError):mod.readout(x,SOURCE,"5")
    def test_reverse_order_client_actual_phases_not_mislabeled(self):
        x=fixture(bps=(330,300,340))
        x["scenario"]="ZERO_LOSS_0MS_NATIVE_ARM64_CLIENT_ONLY_INBOX_REVERSED_BAB"
        for idx,row in enumerate(x["phases"]):
            stage=row.pop("server_inbox_slots")
            row["frozen_stage_slots"]=stage
            row["name"]=("candidate_before","original_middle","candidate_after")[idx]
            row["server_inbox_slots"]=64
            row["client_inbox_slots"]=(256,64,256)[idx]
            row["native_cold_readback_verified"]=True
            row["client_generation"]=10+idx
            row["server_generation"]=20+idx
        out=mod.readout(x,SOURCE,"5")
        self.assertEqual(out["screen_decision"],"REVERSE_BAB_MEASURED_NOT_PRODUCT_PASS")
        self.assertGreater(out["receiver_goodput_mbps"]["candidate_gain_vs_baseline_pct"],0)
        self.assertEqual(out["trial_shape"],"B256_A64_B256")
        x["phases"][2]["client_inbox_slots"]=64
        with self.assertRaises(ValueError):mod.readout(x,SOURCE,"5")
    def test_ge1_128_actual_arch_and_impact(self):
        x=fixture()
        x["scenario"]="GE1_BURST_200MS_EACH_WAY_NATIVE_ARM64_CLIENT_ONLY_INBOX_128_ABA"
        x["netem_ge_stationary_parameters"]={
            "analytical_mean_loss_pct":1.0,"good_to_bad_pct":0.252809,
            "bad_to_good_pct":25.0,"bad_loss_pct":90.0,"good_loss_pct":0.1}
        for idx,row in enumerate(x["phases"]):
            stage=row.pop("server_inbox_slots")
            row.update({"frozen_stage_slots":stage,
                        "server_inbox_slots":64,
                        "client_inbox_slots":(64,128,64)[idx],
                        "native_cold_readback_verified":True,
                        "client_generation":11+idx,
                        "server_generation":21+idx})
            if idx==1:row["name"]="inbox128_candidate"
        x["only_changed_setting"]="authenticated client Rust M1 inbox 64→128→64; server fixed64"
        out=mod.readout(x,SOURCE,"5")
        self.assertEqual(out["trial_shape"],"A64_B128_A64")
        self.assertEqual(out["native_architecture"],"aarch64")
        self.assertNotIn("metadata_warning",out)
        x["only_changed_setting"]="authenticated client Rust M1 inbox 64→256→64; server fixed64"
        out=mod.readout(x,SOURCE,"5")
        self.assertEqual(out["metadata_warning"],
             "STALE_256_TOPLEVEL_LABEL_CONFLICTS_WITH_AUTHENTIC_COLD_128_PHASE_RECEIPTS")
        x["netem_ge_stationary_parameters"]["good_to_bad_pct"]=0.16
        with self.assertRaises(ValueError):mod.readout(x,SOURCE,"5")
    def test_x86_native_client_128_and_wrong_arch_denied(self):
        x=fixture()
        x["scenario"]="ZERO_LOSS_0MS_NATIVE_X86_64_CLIENT_ONLY_INBOX_128_ABA"
        x["architecture"]="x86_64"
        for idx,row in enumerate(x["phases"]):
            stage=row.pop("server_inbox_slots")
            row.update({"frozen_stage_slots":stage,
                        "server_inbox_slots":64,"client_inbox_slots":(64,128,64)[idx],
                        "native_cold_readback_verified":True,
                        "client_generation":10+idx,"server_generation":20+idx})
            if idx==1:row["name"]="inbox128_candidate"
        out=mod.readout(x,SOURCE,"5")
        self.assertEqual(out["native_architecture"],"x86_64")
        self.assertEqual(out["trial_shape"],"A64_B128_A64")
        x["architecture"]="aarch64"
        with self.assertRaises(ValueError):mod.readout(x,SOURCE,"5")
    def test_scalar_baseline_drift_is_explicit(self):
        r=mod.compare_scalar(100,130,120)
        self.assertEqual(r["candidate_vs_baselines"],"ABOVE_BOTH")
        self.assertGreater(r["baseline_drift_pct"],0)
        with self.assertRaises(ValueError):mod.compare_scalar(1,0,1)

if __name__=="__main__":unittest.main()
