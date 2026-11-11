"""H1587: only source-level qualification of two real Windows manual /32
per-client AES128/ChaCha over one original Go TLS443/Rust Linux server.

Actual product PASS requires signed Npcap/Wintun genuine Win32 UDP+TCP,
live OS /32, and A owned Stop leaving B live in ONE native Action.
"""
import ast
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCENE=ROOT/"tools/m0_plan028_h1382_windows_two_original_tls_product.py"
WF=ROOT/".github/workflows/m0-wl-public-normal-full.yml"

class TwoNativeWindowsDifferentCipher(unittest.TestCase):
    def test_server_and_clients_real_per_device_cipher_after_tls(self):
        s=SCENE.read_text()
        ast.parse(s,filename=str(SCENE))
        self.assertIn('h1587=os.environ.get("WBD_PLAN028_WIN_MANUAL_AES128_CHA")=="1"',s)
        self.assertIn('"aes-128-gcm" if label=="A" else "chacha20-poly1305"',s)
        self.assertIn('"--record-cipher"',s)
        self.assertIn('"--lease4",a["lease"]',s)
        self.assertIn('source=original_TLS_Rust_snapshot',s)
        self.assertIn('h1587_client_native_cipher_readback',s)
        self.assertIn('cid=2 if label=="A" else 1',s)
        self.assertIn('V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=off profile=0 cipher=',s)
        self.assertIn('h1587_server_per_client_cipher_ids',s)
        self.assertIn('H1587_REAL_LINUX_SERVER_PER_CLIENT_CHACHA_AES128_RUST_M4_PASS',s)
    def test_single_existing_signed_real_scene_and_owned_stops(self):
        s=SCENE.read_text()
        w=WF.read_text()
        self.assertIn('[plan028-win-dual-original]',w)
        self.assertIn('[plan028-h1587-win-dual-manual-aes128]',w)
        self.assertIn('WBD_PLAN028_WIN_MANUAL_AES128_CHA:',w)
        self.assertIn("H1587_WINDOWS_A_AES128_B_CHACHA_MANUAL_NATIVE_UDP_TCP_A_STOP_B_ALIVE_PASS_SCOPED",w)
        self.assertIn('tests.test_m0_plan028_h1587_two_windows_manual_cipher_scope',w)
        self.assertIn('H1587_WINDOWS_DUAL_NATIVE_SOURCE_ONLY_NOT_PRODUCT',w)
        for literal in (
            '"alias":"WBDWLCLIENTA"','"alias":"WBDWLCLIENTB"',
            '"lease":"10.66.0.2/32"','"lease":"10.66.0.3/32"',
            'real_kernel_reverse_udp_sent','WBD_H1382_REAL_UDP_REVERSE',
            'WBD_WINDOWS_CLIENT_READY',
            'tcp_echo(config["B"]["ip"],"10.66.0.1","B-AFTER-A-STOP")',
            'need(after-before>=5',
            'WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1',
            'V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server',
            'original_WAL_remaining_',
            'PASS_SCOPED_WINDOWS_TWO_REAL_SIGNED_WINTUN_ORIGINAL_TLS443_RUST_M4',
            'H1587_WINDOWS_A_AES128_B_CHACHA_MANUAL_TWO_SIGNED_WINTUN_UDP_TCP_STOP_PASS_SCOPED',
        ):
            self.assertIn(literal,s)
if __name__=="__main__":
    unittest.main()
