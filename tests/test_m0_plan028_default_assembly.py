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
from tools.prepare_windows_wiring import EXTRA_BRIDGES, EXTRA_CLI_TESTS

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
    def test_all_current_windows_product_and_guard_test_overlays_compiled_by_default(self):
        spec=json.loads(MANIFEST.read_text())
        paths={r["path"] for r in spec["operations"]}
        for part,names in EXTRA_BRIDGES.items():
            for name in names:
                paths.add("internal/"+part+"/"+name)
        for name in EXTRA_CLI_TESTS:
            paths.add("cmd/wbd-client/"+name)
        expected=set()
        for part in ("cmd/wbd-client","internal/windowsclient","internal/windowsownerlease"):
            expected.update(x.relative_to(ROOT/"r0/go_overlay").as_posix()
                            for x in (ROOT/"r0/go_overlay"/part).glob("*.go"))
        expected.update(x.relative_to(ROOT/"r0/go_overlay").as_posix()
                        for x in (ROOT/"r0/go_overlay/internal/realityfront").glob("bridge_v4_windows_*.go"))
        # Intentionally EXCLUDED, not a missing product repair:
        # unsafe test-only init() forces global 1420 MSS on entire process.
        excluded={"internal/windowsownerlease/plan020_local_mss_windows_test.go"}
        self.assertFalse(excluded & paths)
        self.assertFalse(expected-paths-excluded,
                         "Uncompiled current Windows Go overlay(s): "+repr(expected-paths-excluded))
        script=(ROOT/"tools/prepare_windows_wiring.py").read_text()
        self.assertIn("for name in EXTRA_CLI_TESTS:",script)
        self.assertIn('need(not target.exists() and not target.is_symlink()',script)
        self.assertIn("original_go_tls_join_windows_test.go",EXTRA_BRIDGES["windowsownerlease"])
        self.assertIn("native_two_wintun_isolation_windows_test.go",EXTRA_BRIDGES["windowsclient"])
        workflow=X86.read_text()
        for phrase in ("windowsownerlease.test.exe","windowsclient.test.exe",
                       "TestPLAN028H1381RealWindowsTwoOriginalNativeDeviceSlots",
                       "TestPLAN028H1515FiveOriginalWindowsNativeDeviceSlots"):
            self.assertIn(phrase,workflow)
        self.assertNotIn("plan020_local_mss_windows_test.go",str(EXTRA_BRIDGES))
    def test_arm64_current_main_native_build_checks_latest_not_frozen_binary(self):
        path=ROOT/".github/workflows/m0-plan028-h1546-arm64-current-default-bundle.yml"
        text=path.read_text()
        self.assertIn("runs-on: ubuntu-24.04-arm",text)
        self.assertIn("bash tools/arm64_public_go_rust_bundle.sh",text)
        self.assertIn('assert m["source_sha"]==os.environ["GITHUB_SHA"]',text)
        self.assertIn("H1546_CURRENT_ARM64_REAL_ORIGINAL_GO_X2_AND_RUST_NATIVE_ISAL_BUILD_PASS_NO_IO",text)
        self.assertIn('"r0/go_overlay/internal/v4productcli/*.go"',text)
        self.assertIn('"crates/wbd-engine/src/*.rs"',text)
        self.assertNotIn("WBD_ARM64_FROZEN_SOURCE",text)
        # Old ARM64 workflow intentionally remains a historical source140a
        # exercise, NEVER a current Go binary accepted by this test.
    def test_one_exact_h1541_native_workflow_has_executable_go_test_and_real_file_trigger(self):
        w=(ROOT/".github/workflows/m0-plan028-h1541-linux30-game2-cold-cohort.yml").read_text()
        self.assertIn("- .github/workflows/m0-plan028-h1541-linux30-game2-cold-cohort.yml",w)
        self.assertIn("go test -count=1 -v -tags wbd_v4_embedded_go,wbd_v4_fec2_product ./internal/v4productcli",w)
        self.assertIn("TestPLAN028Game2ColdRetryCannotMixStaleProtectedEpochLanes",w)
        self.assertIn("TestPLAN028OriginalGame4ColdPortCohortAndForeignScope",w)
        self.assertIn("--strict-band",w)
        self.assertIn("H1531_NATIVE_LINUX_FIVE_CLIENT_REAL_600S_OUTER_300_350_COMPLETE",w)
        self.assertIn("h1541-original-Go-v4productcli.log",w)
        # Do not accidentally execute a filename: H1541's first Action
        # failed in 10s with shell127 after source Go FakeTCP had passed.
        self.assertNotIn("\\n            h1541-original-Go-v4productcli.log\\n          grep",w)
        self.assertEqual(w.count("  one-original-linux-loss30:"),1)
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
