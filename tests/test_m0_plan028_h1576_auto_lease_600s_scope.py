"""PLAN028 H1576: offline guard for real 600s automatic IPv4 sockets.

A passing source inspection here is NOT an original Go/Rust native 600s PASS.
Original strict 250-300Mbps scenario and thresholds remain unchanged.
"""
import ast
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
HARNESS=ROOT/"tools/m0_plan028_h1548_one_windows_four_linux_600.py"
APP=ROOT/"tools/m0_plan028_h1548_mixed_os_app.py"
WF=ROOT/".github/workflows/m0-wl-public-normal-full.yml"


class SourceLocked600sActualAutoLeases(unittest.TestCase):
    def test_all_five_os_actual_original_addresses_not_stale_manual_fixtures(self):
        h=HARNESS.read_text()
        a=APP.read_text()
        ast.parse(h,filename=str(HARNESS))
        ast.parse(a,filename=str(APP))
        self.assertNotIn('need(IPS[i] in inner',h)
        self.assertIn('auto_os_ips[who]=inner[0]',h)
        self.assertIn('inner[0] not in auto_os_ips.values()',h)
        self.assertIn('ipaddress.ip_network("10.66.0.128/25")',h)
        self.assertIn('csv_ips=",".join([IPS[0]]+[auto_os_ips[n] for n in names[1:]])',h)
        self.assertGreaterEqual(h.count('"--inner-ips",csv_ips'),5)
        self.assertIn('assert a.inner_ips and (a.duration!=150 or a.scene=="loss0")',a)
        self.assertIn('assert len(actual)==5 and actual[0]=="10.66.0.2" and len(set(actual))==5',a)
        self.assertIn('IPS=tuple(actual)',a)
        self.assertIn('s.bind((ip,port))',a)
        self.assertIn('tcp_exchange(',a)

    def test_legacy_full_600s_strict_source_unchanged(self):
        h=HARNESS.read_text()
        a=APP.read_text()
        w=WF.read_text()
        for token in (
            'while time.monotonic()-t0<602:',
            'need(capacity<30,',
            'inband>=.70*len(steady)',
            '250<=actual<=300',
            'need(r["client_max_first_delivery_gap_ms"]<3000',
            'BASES={0:(8,14,11,6,9),30:(10,22,18,10,14)}',
            'assert a.duration in (150,600)',
            'if loss==0:',
            'up==up_rx and down==down_rx',
            "WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1",
            "V4_PUBLIC_SHARED_TUN_STOP generation=",
        ):
            self.assertIn(token,h+"\n"+a)
        self.assertIn('[plan028-h1548-win1-linux4-600]',w)
        self.assertIn('["mixed-loss0","mixed-loss30"]',w)


if __name__=="__main__":
    unittest.main()
