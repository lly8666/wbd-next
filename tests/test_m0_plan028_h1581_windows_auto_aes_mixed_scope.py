"""PLAN028 H1581: one genuine native Win auto/AES256 + Linux 3-cipher 150s scene.

Only source/assembly guards. The Windows signed OS and actual UDP/TCP
are qualified exclusively by the H1548 original-GO/TLS/Rust live Action.
"""
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
HARNESS=ROOT/"tools/m0_plan028_h1548_one_windows_four_linux_600.py"
WORKFLOW=ROOT/".github/workflows/m0-wl-public-normal-full.yml"

class Plan028H1581AutoAESNativeSource(unittest.TestCase):
    def test_distinct_one_source_locked_true_mixed_scene(self):
        w=WORKFLOW.read_text()
        h=HARNESS.read_text()
        marker="[plan028-h1581-win-auto-aes-mixed-150s]"
        self.assertIn("win5_scene: ${{ fromJSON(contains(github.event.head_commit.message, '"+marker+"') && '[\"mixed-loss0\"]'",w)
        self.assertIn("WBD_PLAN028_WIN_AUTO_AES_MIXED_150:",w)
        self.assertIn("WBD_WL_PUBLIC_MODES: ${{ github.ref_name == 'main' && contains(github.event.head_commit.message, '"+marker+"') && 'normal'",w)
        self.assertIn("H1581_REAL_WINDOWS_AUTO_AES256_LINUX_THREE_AEAD_150S_UDP_TCP_SIX_OWNER_STOP_PASS_SCOPED",w)
        # Historic Normal two-OS metadata must not veto a genuinely verified
        # 5-client signed/Wintun strict report after all owners Stop.
        self.assertIn("if($env:WBD_PLAN028_WIN_AUTO_AES_MIXED_150 -eq '1'){",w)
        self.assertIn("H1589_SCOPED_H1586_ORIGINAL_FIVE_NATIVE_RESULT_POSTGATE_PASS",w)
        self.assertIn("$result.source_sha -ne $env:GITHUB_SHA",w)
        self.assertIn("$result.status -ne 'PASS_SCOPED_H1581_WIN_AUTO_AES256_LINUX_THREE_CIPHER_TCP_UDP_150S'",w)
        self.assertIn("$result.mode_public -ne 'PASS_MIXED_FIVE_ORIGINAL_150S'",w)
        self.assertIn("selected same-SOURCE native public mode lacks actual two-OS UDP/TCP/Stop proof",w)
        self.assertIn("H1581 signed Windows actual auto lease/AES256 plus Linux three AEAD 150s TCP/UDP/Stop NOT_PROVEN",w)
        self.assertIn('h1581=os.environ.get("WBD_PLAN028_WIN_AUTO_AES_MIXED_150")=="1"',h)
        self.assertIn('l1_150=os.environ.get("WBD_PLAN028_WIN_FIVE_150S_TCPUDP")=="1" or h1581',h)
        self.assertIn('not h1581 or (probe and l1_150',h)
        self.assertIn('"source_sha":source',h)
        self.assertIn('LINUX_BINARY_SRC',h)
        self.assertIn('original_product_binary_sha256',h)
    def test_real_auto_lease_not_manual_fixture_or_cli_default(self):
        h=HARNESS.read_text()
        self.assertIn('if not(h1581 and who=="alice")',h)
        self.assertIn('*([] if h1581 else ["--tunnel-id","102030405060708090a0b0c0d0e0f001"])',h)
        self.assertIn('*(["--record-cipher","aes-256-gcm"] if h1581 else ["--lease4","10.66.0.2/32"])',h)
        self.assertIn('WBD_WINDOWS_AUTHENTICATED_NETWORK_SELECTION mode=',h)
        self.assertIn('auto_lease=true lease=',h)
        self.assertIn('source=original_TLS_Rust_snapshot',h)
        self.assertIn('ipaddress.ip_network("10.66.0.128/25")',h)
        self.assertIn('h1581_windows_rust_cipher_readback',h)
        self.assertIn('H1584_REAL_SERVER_AUTO_IPV4_COLD_UDP_AFTER_TLS_STARTED lease=',h)
        self.assertIn('h1584_actual_linux_kernel_auto_cold_reverse',h)
        self.assertIn('s.sendto(data,(target,45942))',h)
        self.assertIn('target="10.66.0.2"',h)
        self.assertIn('if auto_seed:',h)
        self.assertIn('"1" if (cold_seed or h1581 or h1579) else "0"',h)
        self.assertIn('guest_root+"/h1548-windows-alice.log"',h)
        self.assertIn('h1581_windows_protected_auto_lease',h)
        self.assertIn('windows_ip in json.loads(readback.stdout).get("ip",[])',h)
        self.assertIn('h1581_windows_actual_signed_wintun_os_ip',h)
        app=(ROOT/"tools/m0_plan028_h1548_mixed_os_app.py").read_text()
        self.assertIn('ap.add_argument("--windows-auto-ip",action="store_true"',app)
        self.assertIn('if a.windows_auto_ip:',app)
        self.assertIn('assert a.duration==150 and a.scene=="loss0"',app)
        self.assertIn('assert actual[0]=="10.66.0.2"',app)
        self.assertIn('*(["--windows-auto-ip"] if h1581 else [])',h)
        self.assertIn('auto_os_ips.values() and inner[0]!=windows_ip',h)
    def test_five_real_os_udp_tcp_owners_and_final_cleanup(self):
        h=HARNESS.read_text()
        self.assertIn('"chacha20-poly1305","aes-128-gcm","aes-256-gcm"',h)
        self.assertIn('windows_ip]+[auto_os_ips[n] for n in names[1:]]',h)
        self.assertIn('"PASS_FIVE_OS_KERNEL_APPS_BIDIRECTIONAL"',h)
        self.assertIn('min(sent,recv,downstream,received)>100',h)
        self.assertIn('tcp_client["invalid"]==tcp_server["invalid"]==0',h)
        self.assertIn('max_udp_gap_client_ms',h)
        self.assertIn('"h1565_original_owned_stop"',h)
        self.assertIn('windows_eth0_original_netem_clean',h)
        self.assertIn('original_WSL_bridge_restored',h)
        self.assertIn('Windows_original_WAL_leftover',h)
        self.assertIn('"PASS_SCOPED_H1581_WIN_AUTO_AES256_LINUX_THREE_CIPHER_TCP_UDP_150S"',h)
        self.assertIn('if report["status"].startswith("PASS") and (not probe or l1_150)',h)

if __name__=="__main__":
    unittest.main()
