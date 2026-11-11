"""H1602 real signed Windows one-Wintun + Linux4 source guard; Action proves OS effects."""
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
WF=ROOT/".github/workflows/m0-wl-public-normal-full.yml"
H=ROOT/"tools/m0_plan028_h1548_one_windows_four_linux_600.py"
class H1602ActualOSInnerMTUScope(unittest.TestCase):
    def test_one_short_native_scene_not_five_windows_or_150s_replay(self):
        w=WF.read_text()
        h=H.read_text()
        for token in ("[plan028-h1602-near-mtu-five-native]","WBD_PLAN028_WIN_NEAR_MTU_SMOKE:",
            "H1602_ONE_SIGNED_WINTUN_FOUR_LINUX_20_REAL_OS_NEAR_MTU_ECHO_AND_ALL_STOP_PASS_SCOPED",
            "$mixed.h1602_real_OS_near_inner_MTU.status",
            "WBD_PLAN028_WIN_FIRST_REVERSE_PROBE:",
            "WBD_WL_PUBLIC_MODES:"):
            self.assertIn(token,w)
        for token in ('h1602=os.environ.get("WBD_PLAN028_WIN_NEAR_MTU_SMOKE")=="1"',
            'not h1602 or (probe and not h1581 and not h1596 and not l1_150',
            '"NOT_RUN_H1602_NEAR_MTU_SHORT_NATIVE" if h1602 else',
            'h1602_real_signed_Win1_Linux4_near_inner_mtu_probe',
            'h1602_real_near_inner_MTU_and_all_Stop',
            'no GUI singleton bypass: this case has exactly ONE Windows Wintun'):
            self.assertIn(token,h)
    def test_h1605_unchanged_verified_isa_l_binaries_and_default1460(self):
        w=WF.read_text()
        for token in ("FROZEN_SOURCE: 8a31375e36bb6a93860c5579e64b4a39d0b6e346","FROZEN_RUN_ID: \"43027983611\"",
           'git diff --name-only "$FROZEN_SOURCE" "$GITHUB_SHA" -- crates r0/go_overlay Cargo.lock Cargo.toml tools/prepare_windows_wiring.py',
           "H1605_LINUX_SOURCE_QUALIFIED_SAME_BINARY_ISAL_SHA256_PASS",
           "WBD_WL_NATIVE_ACCEL_REUSE:",
           "WBD_WL_NATIVE_OUTER_MTU_REQUEST:",
           "WBD_WL_TUN_MTU:",
           "H1602-Win1Linux4-RealOS-InnerMTU"):
            self.assertIn(token,w)
    def test_requires_real_OS_mtu_and_true_byte_identical_udp_with_full_Stop(self):
        h=H.read_text()
        for token in ('Get-NetAdapter -IncludeHidden -Name \'WBDWLMAIN\'',
            "Get-NetIPInterface -InterfaceIndex $a.ifIndex -AddressFamily IPv4",
            'ip("-j","link","show","dev","wbdwl48")',
            'ip("-n",NS4[i],"-j","link","show","dev",tun)',
            'min(server_mtu,perOS[who])',
            'for ipv4_total in (mtu-1,mtu):',
            'length=ipv4_total-28',
            'reply==data',
            's.sendto(data,peer)',
            'df1="OS_ACCEPTED_MTU_PLUS_ONE_NO_DELIVERY_CLAIM"',
            'H1602_REAL_NEAR_MTU_ECHO_OK',
            'PASS_FIVE_ORIGINAL_REAL_OS_NEAR_INNER_MTU_20_ECHOES',
            'h1565_bob_after_win_owned_stop_real_udp',
            'require_real_original_server_owner_stop(serverproc)',
            'Windows_original_WAL_leftover','original_WSL_bridge_restored'):
            self.assertIn(token,h)
if __name__=="__main__":unittest.main()
