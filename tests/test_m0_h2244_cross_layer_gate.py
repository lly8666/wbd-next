"""H2244 fail-closed full-chain oracle using actual H2241-H2243 receipt values.

The numbers are frozen source-specific reference fixtures, not fresh network
results from this test. An Action PASS here is STATIC only, never native Mbps.
"""
import unittest
from tools import m0_h2244_cross_layer_gate as G

SRC_2243="30d7fff41be89aeeea240586e75e78947917f8f3"
SRC_2241="db4a5877308b75692c1aec3f756e9225ced95419"
SRC_2242="b6a64a19e4984b9ac3da701672063a4cb4d0b458"

def stage(source=SRC_2243, run=44853457069, kind="original", **overrides):
    d=dict(source_sha=source,run_id=run,duration_s=20,
        receiver_goodput_mbps=276.596,sharedtun_queue_full=74931,
        tun_link_tx_dropped=0,root_qdisc_drops=0,child_qdisc_drops=0,
        m4_copied_per_batch=14.57,tx_cpu_s_per_received_gib=16.9781,
        inner_tcp_retrans=80452,owned_stop=True,kind=kind)
    d.update(overrides)
    return d

def h2243(arch):
    if arch=="x86_64":
        a=stage()
        b=stage(kind="candidate",receiver_goodput_mbps=281.917,
                sharedtun_queue_full=17192,m4_copied_per_batch=15.15,
                tx_cpu_s_per_received_gib=19.503,inner_tcp_retrans=20874)
        ap=stage(receiver_goodput_mbps=240.086,
                 sharedtun_queue_full=89674,m4_copied_per_batch=14.61,
                 tx_cpu_s_per_received_gib=17.2837,inner_tcp_retrans=98421)
        return a,b,ap
    a=stage(receiver_goodput_mbps=314.284,sharedtun_queue_full=46911,
            m4_copied_per_batch=16.68,tx_cpu_s_per_received_gib=10.8602,
            inner_tcp_retrans=42229)
    b=stage(kind="candidate",receiver_goodput_mbps=315.227,
            sharedtun_queue_full=255,root_qdisc_drops=9,child_qdisc_drops=9,
            m4_copied_per_batch=10.13,tx_cpu_s_per_received_gib=10.767,
            inner_tcp_retrans=8509)
    ap=stage(receiver_goodput_mbps=294.678,sharedtun_queue_full=17039,
             m4_copied_per_batch=13.0,tx_cpu_s_per_received_gib=10.7061,
             inner_tcp_retrans=23946)
    return a,b,ap

class WholeChainNativeEvidenceGate(unittest.TestCase):
    def test_h2241_reader_gate_is_relocated_ring_loss_not_a_fix(self):
        a=stage(SRC_2241,44847350573,receiver_goodput_mbps=267.8,
                sharedtun_queue_full=25940,m4_copied_per_batch=14.0,
                tx_cpu_s_per_received_gib=10.22)
        b=stage(SRC_2241,44847350573,"candidate",
                receiver_goodput_mbps=319.7,sharedtun_queue_full=2185,
                tun_link_tx_dropped=38670,m4_copied_per_batch=14.0,
                tx_cpu_s_per_received_gib=11.64)
        ans=G.assess(a,b)
        self.assertEqual(ans["verdict"],"REJECT_AS_PRODUCT_DEFAULT")
        self.assertIn("TOTAL_LOCAL_LOSS_RELOCATED_OR_AMPLIFIED",ans["blockers"])
        self.assertIn("NEW_TUN_DRIVER_DROPS_REQUIRE_CAUSAL_REVIEW",ans["open_gates"])
        self.assertGreater(ans["candidate"]["local_drop_lower_per_received_gib"],
                           ans["original"]["local_drop_upper_per_received_gib"])

    def test_h2242_cake_fair_only_rejected_due_to_cpu_and_batch(self):
        a=stage(SRC_2242,44852383940,receiver_goodput_mbps=278.533,
                sharedtun_queue_full=81076,m4_copied_per_batch=14.37,
                tx_cpu_s_per_received_gib=12.3866)
        b=stage(SRC_2242,44852383940,"candidate",
                receiver_goodput_mbps=242.346,sharedtun_queue_full=29090,
                root_qdisc_drops=4,child_qdisc_drops=4,
                m4_copied_per_batch=2.89,tx_cpu_s_per_received_gib=21.1283)
        ans=G.assess(a,b)
        self.assertIn("ORIGINAL_M4_SENDMMSG_BATCH_COLLAPSE",ans["blockers"])
        self.assertIn("NATIVE_CPU_PER_RECEIVED_GIB_REGRESSION",ans["blockers"])
        self.assertIn("RECEIVER_GOODPUT_REGRESSION",ans["blockers"])
        self.assertLess(ans["candidate"]["local_drop_upper_per_received_gib"],
                        ans["original"]["local_drop_lower_per_received_gib"])

    def test_h2243_x86_burst48_reduces_local_drop_but_cpu_regresses(self):
        a,b,ap=h2243("x86_64")
        ans=G.assess(a,b,original_restored=ap)
        self.assertEqual(ans["verdict"],"REJECT_AS_PRODUCT_DEFAULT")
        self.assertEqual(ans["blockers"],["NATIVE_CPU_PER_RECEIVED_GIB_REGRESSION"])
        self.assertLess(ans["candidate"]["local_drop_upper_per_received_gib"],
                        ans["original"]["local_drop_lower_per_received_gib"])
        self.assertIn("CONCURRENT_SMALL_TCP_UDP_TAIL_NOT_RUN",ans["open_gates"])

    def test_h2243_arm_burst48_mechanism_only_due_to_missing_p99_and_0pct(self):
        a,b,ap=h2243("aarch64")
        ans=G.assess(a,b,original_restored=ap)
        self.assertEqual(ans["verdict"],"MECHANISM_ONLY_FURTHER_QUALIFICATION_REQUIRED")
        self.assertFalse(ans["blockers"])
        self.assertIn("NO_FIXED_450MBPS_PRODUCT_CAP_ALLOWED",ans["open_gates"])
        self.assertIn("ZERO_LOSS_HIGH_CAPACITY_NOT_QUALIFIED_BY_THIS_COMPARISON",
                      ans["open_gates"])
        # Both qdisc layers report SAME nine drops. Do not count nine as
        # eighteen independently proven drops or claim exact overlap.
        lo=ans["candidate"]["local_drop_lower_per_received_gib"]
        hi=ans["candidate"]["local_drop_upper_per_received_gib"]
        self.assertGreater(hi,lo)

    def test_cross_source_and_run_not_comparable_even_when_metrics_match(self):
        a,b,ap=h2243("aarch64")
        with self.assertRaisesRegex(ValueError,"CROSS_SOURCE_OR_RUN"):
            G.assess(a,{**b,"source_sha":SRC_2241},original_restored=ap)
        with self.assertRaisesRegex(ValueError,"CROSS_SOURCE_OR_RUN"):
            G.assess(a,{**b,"run_id":44852383940},original_restored=ap)

    def test_unknown_missing_and_false_stops_fail_closed(self):
        a,b,ap=h2243("aarch64")
        for key in ("receiver_goodput_mbps","tun_link_tx_dropped",
                    "root_qdisc_drops","tx_cpu_s_per_received_gib"):
            bad=b.copy();bad.pop(key)
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"MISSING"):
                G.assess(a,bad,original_restored=ap)
        for replacement in (None,False,-1,float("nan"),float("inf")):
            bad=b.copy();bad["tun_link_tx_dropped"]=replacement
            with self.subTest(value=replacement),self.assertRaises(ValueError):
                G.assess(a,bad,original_restored=ap)
        with self.assertRaisesRegex(ValueError,"OWNED_STOP"):
            G.assess(a,{**b,"owned_stop":False},original_restored=ap)

    def test_receiver_denominator_and_overlapping_parent_child_are_bounded(self):
        a=stage(sharedtun_queue_full=100,root_qdisc_drops=25,child_qdisc_drops=25,
                receiver_goodput_mbps=100)
        d=G.loss_bounds(a)
        gib=100*1e6*20/(8*2**30)
        self.assertAlmostEqual(d["local_drop_lower_per_received_gib"],125/gib)
        self.assertAlmostEqual(d["local_drop_upper_per_received_gib"],150/gib)

    def test_small_udp_tcp_p99_lost_replies_not_turned_into_zero(self):
        a,b,ap=h2243("aarch64")
        tail=dict(udp_replies=100,udp_requests=120,udp_p99_ms=42,
                  udp_baseline_p99_ms=40,tcp_samples=100,tcp_p99_ms=35,
                  tcp_baseline_p99_ms=35,
                  real_concurrent_with_bulk=True,same_source_same_vm=True)
        ans=G.assess(a,b,original_restored=ap,tail=tail)
        self.assertIn("UDP_LOSS_MUST_BE_REPORTED_NOT_HIDDEN",ans["open_gates"])
        self.assertIn("P99_PRODUCT_SAMPLE_SIZE_NOT_MET",ans["open_gates"])
        self.assertNotIn("CONCURRENT_SMALL_TCP_UDP_TAIL_NOT_RUN",ans["open_gates"])
        with self.assertRaisesRegex(ValueError,"NOT_REAL_SAME_SOURCE"):
            G.assess(a,b,original_restored=ap,tail={**tail,"same_source_same_vm":False})
        with self.assertRaisesRegex(ValueError,"MORE_THAN_SENT"):
            G.assess(a,b,original_restored=ap,tail={**tail,"udp_replies":121})

    def test_evidence_import_fails_if_mutated_or_missing_child(self):
        a,b,ap=h2243("aarch64")
        def row(name,st):
            return dict(name=name,receiver_goodput_mbps=st["receiver_goodput_mbps"],
                sharedtun_queue_full=st["sharedtun_queue_full"],
                real_tun_link_tx_dropped=st["tun_link_tx_dropped"],
                kernel_root_qdisc_drops=st["root_qdisc_drops"],
                kernel_fq_codel_child_qdisc_drops=st["child_qdisc_drops"],
                m4_copied_per_batch=st["m4_copied_per_batch"],
                m4_tx_cpu_s_per_delivered_GiB=st["tx_cpu_s_per_received_gib"],
                inner_TCP_retrans=st["inner_tcp_retrans"])
        x=dict(checkpoint="H2243_TRUE_TUN_GLOBAL_TBF_BURST_FAIR_FQCODEL_NATIVE_TWO_ISA",
               product_defaults_unchanged=True,source_sha=SRC_2243,
               run_id=44853457069,cases={"iperf_duration_s":20},
               aarch64={"real_app_and_stops":"PASS_TRUE_ORIGINAL","stages":[
                   row("original_A",a),row("TBF16K_fq_codel",b),
                   row("TBF48K_fq_codel",b),row("original_A_prime",ap)]})
        self.assertEqual(G.from_h2243(x,arch="aarch64")["source_sha"],SRC_2243)
        x["aarch64"]["stages"][2].pop("kernel_fq_codel_child_qdisc_drops")
        with self.assertRaisesRegex(ValueError,"MISSING_CHILD"):
            G.from_h2243(x,arch="aarch64")
        x["product_defaults_unchanged"]=False
        with self.assertRaisesRegex(ValueError,"PRODUCT_SOURCE_ALREADY_MUTATED"):
            G.from_h2243(x,arch="aarch64")

if __name__=="__main__":
    unittest.main()
