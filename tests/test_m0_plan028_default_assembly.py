"""PLAN028: all current source repairs must reach both DEFAULT original Go products.

Pure source-lock/regression checks, not a native OS or performance PASS.
The historical PLAN008 manifest.json remains a separate historical snapshot;
PLAN020 is the active original Windows product source manifest.
"""
import json
import pathlib
import subprocess
import unittest

from tools.m0_install_public_faketcp import ROOT, REPLACE, CREATE, blob, expected_rows

MANIFEST = ROOT / "r0/go_overlay/assembly/manifest-plan020-m0.json"
X86 = ROOT / ".github/workflows/m0-wl-public-normal-full.yml"
ARM = ROOT / "tools/arm64_public_go_rust_bundle.sh"
SERVER = ROOT / "r0/go_overlay/internal/v4productcli/game_linux.go"
TARGET_GO = ROOT / "r0/go_overlay/internal/v4productcli"
TARGET_RF = ROOT / "r0/go_overlay/internal/realityfront"

class Plan028DefaultAssembly(unittest.TestCase):
    def test_all_11_original_go_faketcp_fix_blobs_are_source_locked_and_installed(self):
        rows = expected_rows()
        self.assertEqual(len(rows), 11)
        self.assertEqual(len(REPLACE), 6)
        self.assertEqual(len(CREATE), 5)
        manifest = json.loads(MANIFEST.read_text())
        self.assertEqual(manifest["legacy_source"],
                         "a7a82db31fe736ffedee330795a3234d358f1984")
        all_paths = [e["path"] for e in manifest["operations"]]
        self.assertEqual(len(all_paths), len(set(all_paths)))
        for name, row in rows.items():
            self.assertIn(row, manifest["operations"])
            self.assertEqual(blob((ROOT / row["overlay_path"]).read_bytes()),
                             row["result_blob"], name)
            if name in REPLACE:
                self.assertEqual(row["kind"], "replace")
                self.assertEqual(len(row["original_blob"]), 40)
            else:
                self.assertEqual(row["kind"], "create")
        self.assertTrue({
            "transition.go", "transition_test.go",
            "transition_h1285_test.go", "transition_h1285_association_test.go",
        }.issubset(rows))
    def test_x86_and_arm64_always_assemble_exact_same_current_original_go_files(self):
        x86, arm = X86.read_text(), ARM.read_text()
        install = "python3 tools/m0_install_public_faketcp.py legacy"
        rf = "python3 tools/m0_install_public_realityfront_tests.py legacy"
        all_go = "cp r0/go_overlay/internal/v4productcli/*.go legacy/internal/v4productcli/"
        for description, script in (("x86", x86), ("arm64", arm)):
            with self.subTest(platform=description):
                self.assertIn(install, script)
                self.assertIn(rf, script)
                self.assertIn(all_go, script)
                self.assertIn("for f in r0/go_overlay/internal/realityfront/*.go; do", script)
                self.assertIn("518a18104803baf75c703fd8b038f2126beb8d64", script)
                self.assertIn("raw_detached_data_linux.go", script)
                self.assertIn("raw_detached_data_linux_test.go", script)
                self.assertIn("wbd-v4-client", script)
                self.assertIn("wbd-v4-server", script)
        self.assertIn("m0_v4_embedded_go", x86)
        self.assertIn("native_fec_acceleration", x86)
        self.assertIn("native_fec_acceleration", arm)
        self.assertIn('go test -count=1 ./internal/faketcp', arm)
        self.assertIn('TestPLAN028PreDetach', arm)
        self.assertIn('go test -count=1 -tags wbd_v4_embedded_go,wbd_v4_fec2_product', arm)
        self.assertTrue((TARGET_GO/"game_cold_cohort_linux_test.go").is_file())
        self.assertTrue((TARGET_RF/"bridge_v4_linux_game_product.go").is_file())
    def test_windows_product_assembles_full_canonical_not_stale_baseline(self):
        script = X86.read_text()
        self.assertIn("'r0/go_overlay/assembly/manifest-plan020-m0.json'", script)
        manifest=json.loads(MANIFEST.read_text())
        paths={row["path"] for row in manifest["operations"]}
        self.assertIn("internal/faketcp/transition.go", paths)
        self.assertIn("internal/windowsclient/native_unified_assembly_windows.go", paths)
        self.assertIn("cmd/wbd-client/m0_native_v4_windows.go", paths)
        self.assertIn("cmd/wbd-client/m0_plan028_five_native_slot_windows_test.go", paths)
    def test_game2_game4_cold_cohorts_are_not_grouped_only_by_same_epoch(self):
        script=SERVER.read_text()
        self.assertIn("type originalGameColdFlowKey struct", script)
        self.assertIn("originalGameColdFlowIdentity(key,id,lane.Association().Flow())", script)
        self.assertIn("groups map[originalGameColdFlowKey]*originalGameCohortPending", script)
        self.assertIn("pending:=make(map[originalGameColdFlowKey]*originalGameCohortPending)", script)
        self.assertNotIn("pending[coldKey]!=nil",script)
        self.assertIn("V4_PUBLIC_GAME_SERVER_B_CLIENT_READY", script)
        self.assertIn("PromoteServerGameAfterAuthenticatedClientRx", script)
        self.assertIn("ProtectedFreshGroupRequested()", script)
    def test_arm64_bundle_is_one_valid_shell_not_truncated_duplicated_harness(self):
        completed=subprocess.run(["bash","-n",str(ARM)],
                                 capture_output=True,text=True)
        self.assertEqual(completed.returncode,0,completed.stderr)
        s=ARM.read_text()
        self.assertEqual(s.count("ARM64_PUBLIC_GO_RUST_SOURCE_LOCKED_BUILD_ONLY_PASS"),1)
        self.assertEqual(s.count("go build -trimpath -buildvcs=false"),2)
        self.assertEqual(s.count("cp r0/go_overlay/internal/v4productcli/*.go"),1)
        self.assertIn('test "$(git -C legacy rev-parse HEAD)" = "$GO_SOURCE"',s)
        self.assertIn('test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',s)
        self.assertIn('original_go_faketcp":"11-source-locked-records"',s)
if __name__=="__main__":
    unittest.main()
