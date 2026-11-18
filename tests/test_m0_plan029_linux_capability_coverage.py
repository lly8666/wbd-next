"""PLAN029 H2181 cross-platform capability test scope, fail closed by default.

Cheap static regression; the real x86_64/aarch64 original Go TLS/Rust M4
AF_PACKET/TUN/TCP/UDP evidence comes only from completed native Actions.
"""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def read(path):
    return (ROOT/path).read_text(encoding="utf-8")

class LinuxNonWindowsCapabilities(unittest.TestCase):
    def test_padding_is_explicit_authenticated_game_only_and_default_off(self):
        cli=read("r0/go_overlay/internal/v4productcli/linux.go")
        rust=read("crates/wbd-engine/src/v4_embedded_go.rs")
        crate_root=read("crates/wbd-engine/src/lib.rs")
        self.assertIn('#[cfg(any(target_os="windows",target_os="linux",test))]\nmod v4_client_startup_padding;',crate_root)
        self.assertIn('#[cfg(any(target_os="windows",target_os="linux",test))]\nmod v4_client_split;',crate_root)
        game=read("crates/wbd-engine/src/v4_game_lane.rs")
        go=read("r0/go_overlay/internal/realityfront/bridge_v4_linux_game_product.go")
        self.assertIn('flags.String("startup-padding","off"',cli)
        self.assertIn("Linux startup-padding tls/flows is currently wired only",cli)
        self.assertIn('case "off":c.startupPaddingMode=0',cli)
        self.assertIn('case "tls":c.startupPaddingMode=1',cli)
        self.assertIn('case "flows":c.startupPaddingMode=2',cli)
        self.assertIn("wbd_m0_embedded_go_game_group_startup_padding_set",rust)
        self.assertIn("e.original_identity.logical_epoch",rust)
        self.assertIn("e.drivers.is_some()",rust)
        self.assertIn("set_native_startup_padding",game)
        self.assertIn('#[cfg(any(target_os="windows",target_os="linux",test))]',game)
        self.assertIn("drain_for_linux_native",game)
        self.assertIn("if body.first().copied()!=Some(2){return None}",game)
        self.assertIn("configureStartupPadding(p.cfg.StartupPaddingMode,effective)",go)

    def test_original_raw_kernel_copy_statistics_only_after_send_success(self):
        native=read("crates/wbd-engine/src/v4_game_public_kernel.rs")
        self.assertIn("game.drain_for_linux_native",native)
        self.assertIn("let ok=sent.is_ok();",native)
        self.assertIn("if pad>0",native)
        self.assertIn("tx_pad_records.fetch_add(1,Ordering::Relaxed)",native)
        self.assertIn("tx_pad_bytes.fetch_add(pad as u64,Ordering::Relaxed)",native)
        self.assertIn("padding_copied_counters",native)
        netns=read("tools/arm64_linux_netns_smoke.sh")
        self.assertIn("PLAN029_LINUX_ORIGINAL_GAME_PADDING_ACTUAL_RAW_COPY_PASS",netns)
        self.assertIn("padded_records=",netns)
        self.assertIn("bytes_<=500*records",netns)
        self.assertIn("WBD_PLAN029_LINUX_COVERAGE",netns)

    def test_small_complementary_scope_not_original_matrix_or_windows_claim(self):
        script=read("tools/m0_plan029_linux_crossplatform_coverage.py")
        workflow=read(".github/workflows/m0-plan029-linux-crossplatform-capabilities.yml")
        self.assertIn("game2-tls",script)
        self.assertIn("game2-flows-outer-off",script)
        self.assertIn("game2-fec6-flows",script)
        self.assertIn("game4-off-immediate-flows",script)
        self.assertIn('("normal-aes128","normal","off","",1460,"aes-128-gcm","on","",False,False)',script)
        self.assertIn("Live 1500-to-1280 route reauthentication in manual-IP mode not supported",script)
        self.assertIn("normal-aes256-x25519-mtu1280",script)
        self.assertIn("NORMAL_FEC_PADDING_UNWIRED_FAIL_CLOSED_PASS",script)
        self.assertIn("arch: [x86_64, aarch64]",workflow)
        self.assertIn("ubuntu-24.04-arm",workflow)
        self.assertIn("[plan029-linux-capabilities]",workflow)
        self.assertIn("WBD_PLAN029_LINUX_DUAL_ISA",workflow)
        self.assertNotIn("qemu-aarch64-static",workflow)

if __name__=="__main__":
    unittest.main()
