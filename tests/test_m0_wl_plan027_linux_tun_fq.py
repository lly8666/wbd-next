"""FQ queue drops require real beginning and ending TC counters."""
import unittest
from tools.m0_wl_plan027_linux_tun_fq import fq_delta
class LinuxFqTests(unittest.TestCase):
    def test_actual_kernel_fq_delta(self):
        a=[{"kind":"fq","root":True,"stats":{"drops":100,"packets":200,"bytes":300,"overlimits":0}}]
        b=[{"kind":"fq","root":True,"stats":{"drops":1867,"packets":2200,"bytes":3000,"overlimits":5}}]
        d=fq_delta(a,b)
        self.assertEqual(d["status"],"MEASURED_ORIGINAL_LINUX_TUN_FQ_KERNEL")
        self.assertEqual(d["drops_delta"],1767)
        self.assertEqual(d["packets_delta"],2000)
    def test_actual_linux_tc_root_top_level_stats(self):
        a=[{"kind":"fq","root":True,"handle":"8001:","options":{"flow_limit":256},
            "bytes":6484,"packets":106,"drops":0,"overlimits":0}]
        b=[{"kind":"fq","root":True,"handle":"8001:","options":{"flow_limit":256},
            "bytes":767560182,"packets":626250,"drops":0,"overlimits":0}]
        r=fq_delta(a,b)
        self.assertEqual(r["status"],"MEASURED_ORIGINAL_LINUX_TUN_FQ_KERNEL")
        self.assertEqual(r["drops_delta"],0)
        self.assertEqual(r["packets_delta"],626144)
    def test_absent_kernel_stats_unknown_not_zero(self):
        self.assertEqual(fq_delta([],[])["status"],"NOT_MEASURED_LINUX_TUN_FQ_ROOT_COUNTERS")
        self.assertEqual(fq_delta([{"kind":"fq","root":True}],[])["status"],"NOT_MEASURED_LINUX_TUN_FQ_ROOT_COUNTERS")
    def test_reset_fail_closed(self):
        a=[{"kind":"fq","root":True,"stats":{"drops":9,"packets":20,"bytes":50,"overlimits":0}}]
        b=[{"kind":"fq","root":True,"stats":{"drops":1,"packets":40,"bytes":75,"overlimits":0}}]
        self.assertEqual(fq_delta(a,b)["status"],"INCONCLUSIVE_KERNEL_QDISC_COUNTER_RESET_OR_RECREATED")
