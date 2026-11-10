"""Mixed one signed Windows + four native Linux clients, hard original-owner gates.

This is an offline deployment/fixture contract; no user traffic/OS PASS until
the two actual Windows 2025 + WSL2 x86 Actions finish and artifacts qualify.
"""
import ast,pathlib,re,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
APP=ROOT/"tools/m0_plan028_h1548_mixed_os_app.py"
SUP=ROOT/"tools/m0_plan028_h1548_one_windows_four_linux_600.py"
YAML=ROOT/".github/workflows/m0-wl-public-normal-full.yml"

class Plan028MixedNativeWinLinux(unittest.TestCase):
    def test_same_real_shared_server_one_wintun_four_linux_namespaces(self):
        text=SUP.read_text()
        for p in (APP,SUP):
            ast.parse(p.read_text(),filename=str(p))
        self.assertIn('NAMES=("alice","bob","carol","dave","erin")',text)
        self.assertIn('NS4=(NS,"wbm1548c","wbm1548d","wbm1548e")',text)
        self.assertIn('CHILD4=(CHILD,"wbc1548c","wbc1548d","wbc1548e")',text)
        self.assertIn('WBDWLMAIN',text)
        self.assertEqual(text.count('"--adapter","WBDWLMAIN"'),1)
        self.assertNotIn("WBDWL5",text)
        self.assertIn(" --mode shared --peer-persona windows11 --outer-repair on",text)
        self.assertIn(" --manual-client-leases-file",text)
        self.assertIn('for i,who in enumerate(names[1:],1):',text)
        self.assertIn('"/32" for i,who in enumerate(names)',text)
        self.assertIn('game2',text)
        self.assertIn('game4',text)
        self.assertIn('fec-fixed',text)
        self.assertIn('"-subj","/CN=wbd-v4.example.test"',text)
        self.assertNotIn('"-subj","/CN/wbd-v4.example.test"',text)
        self.assertIn("V4_PUBLIC_MIXED_MULTI_SERVER_READY",text)
        self.assertIn("V4_PUBLIC_GAME_GROUP_LANE_READY role=server",text)
    def test_real_kernel_duplex_bytes_delay_loss_and_600s_sources(self):
        text=SUP.read_text();app=APP.read_text()
        self.assertIn("BAND=(250,300)",text)
        self.assertIn('"loss0","loss30"',text)
        self.assertIn('"delay","200ms","loss"',text)
        self.assertIn("actual_ingress_windows_to_linux", (ROOT/"tools/m0_plan028_h1506_windows_five_native_600.py").read_text())
        self.assertIn('linux_true_outer',text)
        self.assertIn("original true 250-300 Mbps outer both direction real kernel gate unmet",text)
        self.assertIn('len(steady)>=28',text)
        self.assertIn('"real_10s_windows":len(steady)',text)
        self.assertIn('"all_six_original_owned_Stop"',text)
        self.assertIn('"source_sha":source',text)
        self.assertIn('"--duration",type=int,default=600',app)
        self.assertIn('assert a.duration==600',app)
        self.assertIn('TCP_HEAD.pack(',app)
        self.assertIn('"tcp_real_frames"',app)
        self.assertIn("MAX_SEQ=3600000",app)
        self.assertIn("MAX_SEQ",app)
    def test_foreign_routes_wal_and_guest_l2_are_not_silently_removed(self):
        text=SUP.read_text()
        for clause in (
           'get("WBD_PLAN028_FIVE_REAL_CLIENTS")!="1"',
           'l2_setup(ipv4,prefix,mac,gateway)',
           'original_WSL_bridge_restored',
           'WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1',
           'V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server',
           'netem("clean",loss)',
           'Windows_original_WAL_leftover',
           'original_file(p)',
           'LINUX_BINARY_SRC',
           'original_OS_ready'):
            self.assertIn(clause,text)
        self.assertNotIn('route-mode","all-through"',text)
        self.assertNotIn('0.0.0.0",45910',APP.read_text())
    def test_600s_mixed_owner_deadline_is_not_single_normal_320s(self):
        from tools.m0_wl_native_step_runner import native_batch_deadline
        base={"WBD_PLAN028_MIXED_SCENE":"loss0",
              "WBD_WL_RUNNER_MGMT_PIN":"1",
              "WBD_WL_PUBLIC_MODES":"normal",
              "WBD_PLAN028_FIVE_REAL_CLIENTS":"0",
              "WBD_WL_NATIVE_OUTER_MTU_REQUEST":"default1460"}
        for scene in ("loss0","loss30"):
            self.assertEqual(native_batch_deadline({**base,
                            "WBD_PLAN028_MIXED_SCENE":scene}),940)
        for key,value in (("WBD_WL_RUNNER_MGMT_PIN","0"),
                          ("WBD_WL_PUBLIC_MODES","game4"),
                          ("WBD_PLAN028_FIVE_REAL_CLIENTS","1"),
                          ("WBD_WL_NATIVE_OUTER_MTU_REQUEST","legacy1400"),
                          ("WBD_PLAN028_MIXED_SCENE","unsupported")):
            self.assertEqual(native_batch_deadline({**base,key:value}),320)
        wf=YAML.read_text()
        self.assertIn("$wholeLimit=if($env:WBD_PLAN028_MIXED_SCENE -in @('loss0','loss30')){1180}",wf)
        self.assertIn("m0_wl_native_step_runner.py tools/m0_plan028_h1548_one_windows_four_linux_600.py",wf)
    def test_one_source_two_independent_windows_runner_scenes(self):
        text=YAML.read_text()
        self.assertEqual(text.count("  native-public-two-os:"),1)
        self.assertIn('["mixed-loss0","mixed-loss30"]',text)
        self.assertIn('[plan028-h1548-win1-linux4-600]',text)
        self.assertIn('WBD_PLAN028_MIXED_SCENE:',text)
        self.assertIn('m0_plan028_h1548_one_windows_four_linux_600.py',text)
        self.assertIn('m0_plan028_h1548_mixed_os_app.py',text)
        self.assertIn('h1548-*-strict-native-report.json',text)
        self.assertNotIn('result/wl-public/h1548-private*',text)
        management=(ROOT/"tools/m0_wl_gamefec_management_route.ps1").read_text()
        exact="result/wl-public/h1549-mixed-management-route-lease.json"
        self.assertIn("$mixedWin1Linux4=(",management)
        self.assertIn("$Receipt -eq '"+exact+"'",management)
        self.assertIn("$env:WBD_PLAN028_FIVE_REAL_CLIENTS -eq '0'",management)
        self.assertIn("$env:WBD_WL_NATIVE_OUTER_MTU_REQUEST -eq 'default1460'",management)
        self.assertEqual(text.count(exact),2)
        self.assertIn("MANAGEMENT_ROUTE_SCOPE_REFUSED",management)
        self.assertIn("PREEXISTING_SPECIFIC_HOST_ROUTE",management)
        self.assertIn("FOREIGN_MANAGEMENT_LEASE",management)
        self.assertNotIn("WBD_PLAN028_WIN_LINUX_COCLIENTS -eq '1' -and WBD_PLAN028_MIXED_SCENE",management)
if __name__=="__main__":unittest.main()
