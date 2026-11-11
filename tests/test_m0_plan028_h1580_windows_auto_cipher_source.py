"""PLAN028 H1580 source+assembly contract, never a Windows OS PASS.

Real auto/manual lease, ChaCha/AES128/AES256 and mixed Win/Linux
must be qualified by signed-Npcap/Wintun Actions at the exact SOURCE.
"""
import hashlib
import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
OVERLAY=ROOT/"r0/go_overlay"
MANIFEST=OVERLAY/"assembly/manifest-plan020-m0.json"

def git_blob(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

class WindowsNativeAutoCipherSource(unittest.TestCase):
    def test_cli_native_default_and_verified_selection_from_config_to_os(self):
        manifest=json.loads(MANIFEST.read_text())
        main=next(x for x in manifest["operations"] if x["path"]=="cmd/wbd-client/main_windows.go")
        text="\n".join(x["replace"] for x in main["patches"])
        self.assertIn('flag.Bool("native-v4-product", true,',text)
        self.assertIn('AutoLease:autoLease,RecordCipher:suite',text)
        self.assertNotIn('requires explicit lease and authenticated ChaCha',text)
        self.assertIn('if *nativeV4Product {',text)
        self.assertIn('return runM0NativeV4Windows(',text)
        self.assertIn('native V4 requires 32B pre-shared route key',text)

        dispatch=(OVERLAY/"cmd/wbd-client/m0_native_v4_dispatch_windows.go").read_text()
        normal=(OVERLAY/"cmd/wbd-client/m0_native_v4_windows.go").read_text()
        game=(OVERLAY/"cmd/wbd-client/m0_native_v4_game_windows.go").read_text()
        grouped=(OVERLAY/"internal/realityfront/bridge_v4_windows_game_group.go").read_text()
        self.assertIn('AutoLease bool',dispatch)
        self.assertIn('RecordCipher uint8',dispatch)
        self.assertIn('AutoLease:o.AutoLease,DesiredLanes:1',normal)
        self.assertIn('AutoLease:o.AutoLease,DesiredLanes:uint8(count)',game)
        self.assertIn('1,"off",0,4,20,o.RecordCipher',normal)
        self.assertIn('1,"fixed",4,4,20,o.RecordCipher',normal)
        self.assertIn('1,"auto",0,4,20,o.RecordCipher',normal)
        self.assertIn('count,"fixed",4,4,20,o.RecordCipher',game)
        self.assertIn('snapshot.Cipher()!=o.RecordCipher',normal)
        self.assertIn('assigned,parseErr:=netip.ParsePrefix(trustedLease)',normal)
        self.assertIn('assigned,parseErr:=netip.ParsePrefix(trustedLease)',game)
        self.assertIn('Lease4:o.Lease4',normal)
        self.assertIn('plan,err:=makePlan(o.Lease4)',game)
        self.assertIn('planForGame:=func(verifiedLease netip.Prefix)',normal)
        self.assertIn('Lease4:verifiedLease,Server4:o.ServerIP',normal)
        self.assertIn('AuthenticatedNetworkSelection()',grouped)
        self.assertIn('lease!=g.authenticatedLease||snap.Cipher()!=g.authenticatedCipher',grouped)
        self.assertIn('WBD_WINDOWS_INNER_OS_MTU_APPLIED_V1',normal)
        self.assertIn('WBD_WINDOWS_INNER_OS_MTU_APPLIED_V1',game)

    def test_exact_assembled_source_and_extra_group_not_forgotten(self):
        manifest=json.loads(MANIFEST.read_text())
        pins={x["path"]:x for x in manifest["operations"] if x.get("overlay_path")}
        for name in (
            "cmd/wbd-client/m0_native_v4_dispatch_windows.go",
            "cmd/wbd-client/m0_native_v4_windows.go",
            "cmd/wbd-client/m0_native_v4_game_windows.go",
        ):
            self.assertEqual(git_blob(OVERLAY/name),pins[name]["result_blob"],name)
        # The Windows assembly has a separately source-pinned bridge list,
        # not a blank manifest assumption. Verify the actual install path.
        prepare=(ROOT/"tools/prepare_windows_wiring.py").read_text()
        self.assertIn('"bridge_v4_windows_game_group.go"',prepare)
        self.assertIn('data = git(root, "show", source + ":" + relative)',prepare)
        self.assertIn('target.write_bytes(data)',prepare)
        self.assertIn('check_spec(spec,',prepare)

if __name__=="__main__":
    unittest.main()
