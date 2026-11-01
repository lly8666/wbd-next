"""No raw original Go TLS logs survive a failed source-frozen blackhole run."""
import unittest
from tools.network_harness.runner import startup_diagnostic

class SafeOriginalReauthDiagnosticTest(unittest.TestCase):
    def test_counts_only_fixed_markers_no_keys_addresses_or_raw_logs(self):
        raw = ("sensitive-key=SECRETS\\n"
               "2026 V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client\\n"
               "2026 V4_PUBLIC_NATIVE_DEAD_RECONNECT_ARMED role=client generation=1 old_owner_drained=1\\n"
               "2026 V4_PUBLIC_NATIVE_RECONNECT_TRIGGER role=client source=real_kernel_tun_ready generation=2\\n"
               "2026 V4_PUBLIC_ORIGINAL_GO_TLS_REAUTHORIZE role=client generation=2\\n"
               "error: connection refused\\n")
        d=startup_diagnostic(raw)
        self.assertEqual(d["native_reauthorization_stage_counts"]["cold_tls_reauthorize"],1)
        self.assertEqual(d["native_reauthorization_stage_counts"]["dead_reconnect_armed"],1)
        self.assertEqual(d["native_reauthorization_stage_counts"]["real_tun_reconnect_trigger"],1)
        self.assertEqual(d["last_native_reauthorization_marker"],"cold_tls_reauthorize")
        self.assertIn("NETWORK_CONNECT_REFUSED",d["safe_failure_classes"])
        self.assertNotIn("SECRETS",str(d))
        self.assertNotIn("role=client",str(d))
        self.assertNotIn("generation=2",str(d))
    def test_no_stage_no_observed(self):
        d=startup_diagnostic("product exited")
        self.assertEqual(d["last_native_reauthorization_marker"],"NOT_OBSERVED")
        self.assertTrue(all(v==0 for v in d["native_reauthorization_stage_counts"].values()))

if __name__=="__main__":unittest.main()
