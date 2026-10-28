import tempfile
import unittest
from pathlib import Path
from tools.m0_wl_n0_drop_delta import latest_counter, measured_delta

class TestN0NpcapDelta(unittest.TestCase):
    def test_real_telemetry_last_snapshot_not_startup_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"client.log"
            p.write_text("noise\nWBD_WINDOWS_NATIVE_PACKET_TELEMETRY {\"npcap_ingress_local_drops\":17}\n"
                         "WBD_WINDOWS_NATIVE_PACKET_TELEMETRY {\"npcap_ingress_local_drops\":19}\n")
            self.assertEqual(latest_counter(p), 19)
            self.assertEqual(measured_delta(17, latest_counter(p)), 2)
            self.assertEqual(measured_delta(19,19), 0)
    def test_missing_reset_or_wrong_type_is_unknown_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"client.log"
            self.assertIsNone(latest_counter(p))
            p.write_text("WBD_WINDOWS_NATIVE_PACKET_TELEMETRY {\"npcap_ingress_local_drops\":\"unknown\"}\n")
            self.assertIsNone(latest_counter(p))
        self.assertIsNone(measured_delta(None, 7))
        self.assertIsNone(measured_delta(50, 7))

if __name__ == "__main__":
    unittest.main()
