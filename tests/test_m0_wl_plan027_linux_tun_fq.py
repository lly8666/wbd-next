"""Original Linux root fq drops require true kernel tc readbacks, never a default zero."""
import unittest
from tools.m0_wl_plan027_linux_tun_fq import fq_delta
class LinuxFqTests(unittest.TestCase):
    def test_root_top_level_actual_tc_output(self):
        a=[{"kind":"fq","root":True,"handle":"8001:","options":{"flow_limit":256},
            "bytes":6484,"packets":106,"drops":0,"overlimits":0}]
        b=[{"kind":"fq","root":True,"handle":"8001:","options":{"flow_limit":256},
            "bytes":767560182,"packets":626250,"drops":0,"overlimits":0}]
        r=fq_delta(a,b)
        self.assertEqual(r["status"],"MEASURED_ORIGINAL_LINUX_TUN_FQ_KERNEL")
        self.assertEqual(r["drops_delta"],0)
        self.assertEqual(r["packets_delta"],626144)
    def test_nested_variant_supported(self):
        a=[{"kind":"fq","root":True,"stats":{"drops":100,"packets":200,"bytes":300,"overlimits":0}}]
        b=[{"kind":"fq","root":True,"stats":{"drops":200,"packets":300,"bytes":500,"overlimits":1}}]
        self.assertEqual(fq_delta(a,b)["drops_delta"],100)
    def test_missing_does_not_claim_zero(self):
        self.assertEqual(fq_delta([],[])["status"],"NOT_MEASURED_LINUX_TUN_FQ_ROOT_COUNTERS")
    def test_reset_is_not_negative_drop(self):
        a=[{"kind":"fq","root":True,"drops":9,"packets":20,"bytes":50,"overlimits":0}]
        b=[{"kind":"fq","root":True,"drops":1,"packets":40,"bytes":75,"overlimits":0}]
        self.assertEqual(fq_delta(a,b)["status"],"INCONCLUSIVE_KERNEL_QDISC_COUNTER_RESET_OR_RECREATED")
