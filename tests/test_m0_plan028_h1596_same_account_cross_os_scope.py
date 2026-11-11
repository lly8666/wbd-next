"""H1596 source guard only: one signed Windows Wintun and Linux independent same-login client."""
import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
H=ROOT/"tools/m0_plan028_h1548_one_windows_four_linux_600.py"
W=ROOT/".github/workflows/m0-wl-public-normal-full.yml"
class CrossOSOriginalGoSameAccount(unittest.TestCase):
    def test_scoped_single_wintun_150s_and_test_only_pace(self):
        h=H.read_text();w=W.read_text()
        self.assertIn("[plan028-h1596-same-account-win-linux-150s]",w)
        self.assertIn("WBD_PLAN028_WIN_LINUX_SAME_ACCOUNT_150:",w)
        self.assertIn("&& '0.6'",w)
        self.assertIn('h1596=os.environ.get("WBD_PLAN028_WIN_LINUX_SAME_ACCOUNT_150")=="1"',h)
        self.assertIn("(.59<=offered_scale<=.61) if h1596",h)
        self.assertIn("no GUI singleton bypass: this case has exactly ONE Windows Wintun",h)
    def test_protected_credential_independent_installation_and_native_lease(self):
        h=H.read_text()
        for key in ('"--username",("alice" if h1596 and who=="bob" else who)',
            '"--password",(users["alice"] if h1596 and who=="bob" else users[who])',
            '"--auto-ip","--installation-id-file"',
            '"--installation-id","445566778899aabbccddeeff00112233"',
            'windows_ip!=auto_os_ips["bob"]',
            'h1596_distinct_same_account_auto_OS_IPs',
            '"Linux_Bob_kernel_TUN":auto_os_ips["bob"]+"/32"',
            'h1596_actual_all_six_OS_apps_scale',
            'h1575_bob_post_Alice_stop_on_real_live_echo',
            'h1596_same_account_native_stop_pass'):
            self.assertIn(key,h)
    def test_real_strict_and_generic_report_gated_in_original_action(self):
        w=W.read_text()
        for key in ("if($env:WBD_PLAN028_WIN_LINUX_SAME_ACCOUNT_150 -eq '1'){",
            "$twins.Windows_signed_Wintun -eq $twins.Linux_Bob_kernel_TUN",
            "$mixed.h1596_same_account_150s_and_sibling_stop",
            "$result.h1596_same_account_native_stop_pass -ne $true",
            "H1596_REAL_ONE_WIN_ONE_LINUX_SAME_ACCOUNT_TWO_AUTO_OS_IPS_150S_ALL_STOP_PASS_SCOPED"):
            self.assertIn(key,w)
if __name__=="__main__":unittest.main()
