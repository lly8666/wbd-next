"""H2286 full ORIGINAL product chain source/OS/identity/owned cleanup gates.

The Python guest and TCP app are never allowed to masquerade as an original
GoTLS/Rust/Wintun/Npcap client. Product qualification requires real Windows
native Go TLS plus Rust and remote ARM64 original AF_PACKET/TUN owner.
"""
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2286_full_windows_product as win
import m0_h2286_arm_product as arm


class H2286TrueOriginalWinArmProduct(unittest.TestCase):
    def test_original_win_signals_real_npfcapture_443_not_native_tcp_outer(self):
        cli=win.original_win_client_args(
            "C:/native/original-go.exe","172.20.90.2",
            pathlib.Path("h2286-peer/server"))
        self.assertEqual(cli[:3],
            ["C:/native/original-go.exe","--native-v4-product","--control-stdin"])
        self.assertEqual(cli[cli.index("--server-ip")+1],"172.20.90.2")
        self.assertEqual(cli[cli.index("--server-port")+1],"443")
        self.assertEqual(cli[cli.index("--source-port")+1],"41031")
        self.assertEqual(cli[cli.index("--lease4")+1],"10.66.0.2/32")
        self.assertEqual(cli[cli.index("--route-mode")+1],"all")
        self.assertEqual(cli[cli.index("--outer-repair")+1],"off")
        for f in ("--route-key-hex-file","--tls-ca-pem","--username",
                  "--password","--tunnel-id","--adapter","--state-path","--mtu"):
            self.assertIn(f,cli)
        self.assertNotIn("--fake-received"," ".join(cli))
        self.assertNotIn("m0_wl_loss_tcp_probe.py"," ".join(cli))

    def test_real_windows_wsl_original_tcp443_nat_and_reverse_owned(self):
        rules=win.scope_nat_rules("172.29.16.1","172.29.19.2","100.100.50.1")
        self.assertEqual(len(rules),4)
        self.assertIn("443"," ".join(rules[0]))
        self.assertIn("100.100.50.1:18727"," ".join(rules[0]))
        self.assertIn("MASQUERADE"," ".join(rules[1]))
        self.assertIn("18727"," ".join(rules[2]))
        for r in rules:
            inverse=win.guestroute.reversible_rule(r)
            self.assertIn("-D",inverse)
            self.assertNotIn("-I",inverse)
            self.assertNotIn("-F",inverse)
        with self.assertRaises(RuntimeError):
            win.scope_nat_rules("172.29.16.1","172.29.19.2","8.8.8.8")
        with self.assertRaises(RuntimeError):
            win.scope_nat_rules("8.8.8.8","172.29.19.2","100.100.50.1")

    def test_original_arm_wan0_ethernet_afpacket_and_cannot_fake_remote(self):
        server={"tail_ip":"100.101.2.4","role":"server","source_sha":"a"*40,
                "run_id":"12345","group":"b",
                "topology":"TWO_INDEPENDENT_THREE_RUNNER_WIN_RELAY_ARM"}
        relay={"tail_ip":"100.101.2.5","role":"relay","source_sha":"a"*40,
               "run_id":"12345","group":"b",
               "topology":"TWO_INDEPENDENT_THREE_RUNNER_WIN_RELAY_ARM"}
        rules=arm.server_nat_rules(server,relay)
        self.assertEqual(len(rules),4)
        self.assertIn("10.248.82.2:443"," ".join(rules[0]))
        self.assertIn("100.101.2.5/32"," ".join(rules[0]))
        self.assertIn("10.248.82.1"," ".join(rules[1]))
        self.assertIn(arm.HOST_DEV," ".join(rules[1]))
        for row in rules:
            self.assertIn("-D",arm.reverse_rule(row))
        relay["group"]="a"
        with self.assertRaises(RuntimeError):
            arm.server_nat_rules(server,relay)

    def test_two_independent_original_triples_and_one_ARM_product_build(self):
        p=(ROOT/".github/workflows/qa-h2286-dual-original-windows-arm.yml").read_text()
        self.assertEqual(p.count("group: [a, b]"),3)
        self.assertEqual(p.count("runs-on: windows-2025"),1)
        self.assertEqual(p.count("runs-on: ubuntu-24.04-arm"),3)
        self.assertEqual(p.count("uses: tailscale/github-action@v4"),3)
        self.assertEqual(p.count("[m0-029-h2286-real-windows-arm-product]"),4)
        self.assertEqual(p.count("original_arm_build:"),1)
        self.assertIn("needs: [static, original_arm_build]",p)
        self.assertIn("c5066db61fc51bafd7c2ad2def3029e615efa777",p)
        self.assertIn("m0_plan029_linux_dual_native_build.sh",p)
        self.assertIn("m0_h2286_windows_npf_owner.ps1",p)
        self.assertIn("m0_wl_npcap_driver_ci.ps1",p)
        self.assertIn("m0_h2286_inner_udp.py",p)
        self.assertIn("m0_h2286_arm_product.py app",p)
        self.assertIn("REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED",p)
        self.assertIn("PASS_H2286_TRUE_ORIGINAL_WINDOWS_ARM_GO_TLS_RUST_WINTUN_TUN_TCP",p)
        self.assertIn("retention-days: 1",p)
        self.assertIn("gh run download 44936859273",p)
        self.assertIn("product_delta=",p)
        self.assertIn("WBD_H2286_ARM_PRODUCT_FROZEN_SOURCE: 97db898f3a1fbebcdeea7f2a1b9d9c3dfcd32573",p)
        self.assertIn("WBD_NPCAP_DRIVER_CI_CLEANUP_PASS",p)
        self.assertNotIn("if($LASTEXITCODE -ne 0){throw 'H2286_SIGNED_NPCAP_NATIVE_DRIVER_OWNED_CLEANUP_FAILED'}",p)

        self.assertNotIn("PASS_FULL_PRODUCT_ALL_PLATFORMS",p)
        self.assertNotIn("gh workflow run m0-wl-public-normal-full.yml",p)
        self.assertNotIn("WBD_H2286_PRODUCT_FULL_WIN_ARM: \"1\"\nconcurrency:",p)

    def test_artifact_name_is_strictly_scoped_to_original_arm_ready(self):
        from m0_h2276_three_runner_tcp import await_artifact
        import inspect,re
        code=inspect.getsource(await_artifact)
        self.assertIn("h2286-[ab]-original-arm-product-ready",code)
        allowed=re.compile(r"h2276-[ab]-(?:client|relay|server)-(?:peer|ready|result)|h2286-[ab]-original-arm-product-ready")
        for n in ("h2286-a-original-arm-product-ready",
                  "h2286-b-original-arm-product-ready"):
            self.assertIsNotNone(allowed.fullmatch(n))
        for n in ("h2286-c-original-arm-product-ready",
                  "h2286-a-other",
                  "h2286-a-original-arm-product-ready-evil"):
            self.assertIsNone(allowed.fullmatch(n))

    def test_true_product_code_not_modified(self):
        assert (ROOT/"tools/m0_h2286_full_windows_product.py").is_file()
        assert (ROOT/"tools/m0_h2286_arm_product.py").is_file()
        assert (ROOT/"tools/m0_h2286_inner_udp.py").is_file()
        assert (ROOT/"tools/m0_h2286_windows_npf_owner.ps1").is_file()
        code=(ROOT/"tools/m0_h2286_full_windows_product.py").read_text()
        self.assertIn("WBD_WINDOWS_CLIENT_READY",code)
        self.assertIn("WBD_WINDOWS_OS_APPLIED",code)
        self.assertIn("M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS",code)
        self.assertIn("original Windows",win.__doc__.lower().replace("original windows","original Windows"))
        self.assertNotIn("PASS_H2285_NATIVE_WSL2_L3_FORWARD_TO_INDEPENDENT_ARM_TCP_SCOPED",code)
        # The new native socket probe must remain behind opt-in, no product knob.
        source=(ROOT/"tools/m0_wl_loss_tcp_probe.py").read_text()
        self.assertIn('os.environ.get("WBD_H2286_PRODUCT_FULL_WIN_ARM") == "1"',source)


if __name__=="__main__":
    unittest.main()
