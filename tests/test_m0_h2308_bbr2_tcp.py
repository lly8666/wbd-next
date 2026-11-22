"""H2308 signed Windows kernel BBR2 vs historic ARM Linux BBR: test-only evidence."""
import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class H2308CCRegression(unittest.TestCase):
    def test_exact_bbr2_source_and_original_kernel_cc_restore(self):
        p=(ROOT/"tools/m0_h2308_windows_cc.ps1").read_text()
        for phrase in ("Get-NetTCPSetting","Internet","Datacenter",
                       "congestionprovider=bbr2","windows-cc-before.json",
                       "windows-cc-after.json","windows-cc-restored.json",
                       "H2308_WINDOWS_ORIGINAL_TCP_CC_RESTORED",
                       "H2308_WINDOWS2025_OS_BBR2_REAL_READBACK_APPLIED"):
            self.assertIn(phrase,p)
        for loss in (1,5):
            w=(ROOT/f".github/workflows/qa-h2308-bbr2-loss{loss}.yml").read_text()
            for term in (f'WBD_H2293_WEAK_LOSS_PCT: "{loss}"',
                         'WBD_H2306_TCP_PROGRESS: "1"',
                         'WBD_H2308_WIN_BBR2: "1"',
                         'WBD_H2302_BASE_BYTES: "8388608"',
                         'WBD_H2302_TUNED_BYTES: "2097152"',
                         'WBD_H2302_WINDOW_ABA: "1"',
                         'WBD_H2294_OFF_REPAIR_ABA: "0"',
                         "H2308 verify Windows TCP baseline",
                         "H2308 always restore Windows TCP",
                         "-Action Setup","-Action Restore",
                         "h2308-out/",f'[m0-029-h2308-bbr2-loss{loss}]',
                         "H2302_REAL_ARM_TUN_THREE_FEC_OFF_TCP_STAGES_DONE",
                         "==[8388608,2097152,8388608]",
                         "original_rust_binary_identical_all_legs",
                         "REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED"):
                self.assertIn(term,w)
            self.assertLess(w.index("H2308 verify Windows TCP baseline"),
                            w.index("ORIGINAL true Go TLS/Rust Windows signed Npcap-Wintun"))
            self.assertLess(w.index("H2308 always restore Windows TCP"),
                            w.index("Stop and restore exact WSL"))
    def test_real_active_inner_tcp_profile_not_intended_setting(self):
        p=(ROOT/"tools/m0_wl_loss_tcp_probe.py").read_text()
        w=(ROOT/"tools/m0_h2286_full_windows_product.py").read_text()
        for term in ("Get-NetTCPConnection","-RemotePort 45902",
                     "CLIENT_CC_ACTIVE_PROFILE","AppliedSetting"):
            self.assertIn(term,p)
        self.assertIn("H2308_BBR2_SELECTED_TCP_PROFILE_UNQUALIFIED",w)
if __name__=="__main__":unittest.main()
