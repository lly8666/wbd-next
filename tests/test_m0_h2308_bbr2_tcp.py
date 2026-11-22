"""H2308: FEC OFF 400ms Windows BBR2 test-only paired replay, exact kernel profile receipt."""
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class H2308OriginalWinKernelCC(unittest.TestCase):
    def test_both_loss_tiers_keep_original_fec_off_and_native_product(self):
        for loss in (1,5):
            s=(ROOT/f".github/workflows/qa-h2308-bbr2-loss{loss}.yml").read_text()
            for mark in (f'WBD_H2293_WEAK_LOSS_PCT: "{loss}"',
                         'WBD_H2306_TCP_PROGRESS: "1"',
                         'WBD_H2308_WIN_BBR2: "1"',
                         'WBD_H2302_WINDOW_ABA: "1"',
                         'WBD_H2294_OFF_REPAIR_ABA: "0"',
                         'WBD_H2302_BASE_BYTES: "8388608"',
                         'WBD_H2302_TUNED_BYTES: "2097152"',
                         "==[8388608,2097152,8388608]",
                         f'[m0-029-h2308-bbr2-loss{loss}]',
                         "ORIGINAL true Go TLS/Rust Windows signed Npcap-Wintun",
                         "H2308_WINDOWS2025_OS_TCP_INTERNET_DATACENTER_BBR2_APPLIED",
                         "H2308_WINDOWS_ORIGINAL_TCP_CC_RESTORED",
                         "windows-cc-before.json",
                         "windows-cc-after.json",
                         "windows-cc-restored.json",
                         'congestionprovider=bbr2',
                         "REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED",
                         "original_rust_binary_identical_all_legs",
                         "H2302_REAL_ARM_TUN_THREE_FEC_OFF_TCP_STAGES_DONE"):
                self.assertIn(mark,s)
            self.assertLess(s.index("H2308 verify and apply BBR2"),
                            s.index("ORIGINAL true Go TLS/Rust Windows signed Npcap-Wintun"))
            self.assertLess(s.index("H2308 always restore original Windows TCP"),
                            s.index("Stop and restore exact WSL"))
    def test_os_active_connection_readback_and_fail_closed(self):
        p=(ROOT/"tools/m0_wl_loss_tcp_probe.py").read_text()
        w=(ROOT/"tools/m0_h2286_full_windows_product.py").read_text()
        for mark in ("CLIENT_CC_ACTIVE_PROFILE","Get-NetTCPConnection",
                     "-RemotePort 45902","AppliedSetting","WBD_H2308_WIN_BBR2"):
            self.assertIn(mark,p)
        for mark in ("H2308_BBR2_SELECTED_TCP_PROFILE_UNQUALIFIED",
                     "h2308_actual_os_tcp_connection_profiles",
                     "h2308_tcp_applied_profile_failure"):
            self.assertIn(mark,w)
if __name__=="__main__":
    unittest.main()
