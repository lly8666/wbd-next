"""Regression guards for PLAN029 true native Linux x86_64/aarch64 dual endpoint."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class Plan029LinuxDualIsaTest(unittest.TestCase):
    def test_real_two_native_architectures_and_one_bundle_per_isa(self):
        wf=(ROOT/".github/workflows/m0-plan029-linux-dual-isa-native.yml").read_text()
        builder=(ROOT/"tools/m0_plan029_linux_dual_native_build.sh").read_text()
        self.assertIn("arch: [x86_64, aarch64]",wf)
        self.assertIn("'ubuntu-24.04-arm'",wf)
        self.assertIn("'ubuntu-24.04'",wf)
        self.assertIn("Single exact-SOURCE original Go TLS / Rust / ISA-L native build",wf)
        self.assertIn("WBD_PLAN029_LINUX_DUAL_ISA: \"1\"",wf)
        self.assertIn("[plan029-linux-dual-native]",wf)
        self.assertIn("test \"${WBD_PLAN029_LINUX_EXPECTED_ARCH:?}\" = \"$(uname -m)\"",builder)
        self.assertNotIn("qemu-aarch64-static",wf+builder)

    def test_exact_five_short_modes_and_real_linux_kernel_app(self):
        suite=(ROOT/"tools/m0_plan029_linux_dual_isa_suite.py").read_text()
        netns=(ROOT/"tools/arm64_linux_netns_smoke.sh").read_text()
        self.assertIn('("normal","normal",None,True)',suite)
        self.assertIn('("fixed","fec-fixed",None,False)',suite)
        self.assertIn('("auto","fec-auto",None,False)',suite)
        self.assertIn('("game2","game2",None,False)',suite)
        self.assertIn('("game4-fixed6","game4","6",False)',suite)
        # A non-Game-FEC original Linux run emits empty selector rather
        # than string "off"; keep mode equality exact, never bypass FEC6.
        self.assertIn('proof.get("game_fec_profile")!=(fec or "")',suite)
        self.assertIn('WBD_PLAN029_LINUX_DUAL_ISA',netns)
        self.assertIn('PLAN029_LINUX_APP_TRUE_KERNEL_PASS',netns)
        self.assertIn('disable_ipv6',netns)
        self.assertIn('owned_stop',suite)
        self.assertNotIn('WINDOWS_GAME_PADDING',netns)

    def test_h2171_first_fixture_fail_false_negative_is_not_restored(self):
        app=(ROOT/"tools/m0_plan029_linux_native_app.py").read_text()
        netns=(ROOT/"tools/arm64_linux_netns_smoke.sh").read_text()
        self.assertIn('if tcp.getpeername()[0] != remote:',app)
        self.assertNotIn('if bytes(data) != reply or tcp.getpeername()',app)
        self.assertNotIn('if ! kill -0 "$listener_pid" 2>/dev/null;then break;fi',netns)
        self.assertIn('PLAN029_LINUX_APP_SOCKET_READY',netns)
        # No fake socket/UDP bypass or simulated record crypto in application.
        self.assertIn('socket.socket(socket.AF_INET, socket.SOCK_STREAM)',app)
        self.assertIn('socket.socket(socket.AF_INET, socket.SOCK_DGRAM)',app)

if __name__=="__main__":
    unittest.main()
