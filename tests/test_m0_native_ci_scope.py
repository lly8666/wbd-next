import unittest
from pathlib import Path

from tools.m0_native_ci_scope import is_native_path, requires_native_smoke


class NativeSmokeScopeTests(unittest.TestCase):
    def test_cold_dns_and_gui_do_not_start_real_os_native(self):
        self.assertFalse(requires_native_smoke("push", [
            "r0/go_overlay/internal/windowsclient/native_bootstrap_dns_windows.go",
            "r0/go_overlay/cmd/wbd-client/m0_plan029_single_dns_windows.go",
            "r0/go_overlay/assembly/manifest-plan020-m0.json",
            "docs/architecture/CLIENT_SPLIT_DNS_CONTRACT.md",
        ]))

    def test_pure_rust_policy_does_not_run_real_os(self):
        self.assertFalse(requires_native_smoke("push", [
            "crates/wbd-engine/src/v4_client_split.rs",
        ]))

    def test_windows_and_rust_network_paths_start_native(self):
        for path in (
            "crates/wbd-engine/src/v4_windows_native_runtime.rs",
            "crates/wbd-engine/src/v4_windows_game_native_runtime.rs",
            "crates/wbd-platform/src/windows_native_io.rs",
            "crates/wbd-platform/src/windows_direct_socket.rs",
            "crates/wbd-engine/src/v4_direct_egress.rs",
            "r0/go_overlay/cmd/wbd-client/m0_native_v4_direct_windows.go",
            "crates/wbd-engine/src/v4_owner_crypto.rs",
            "r0/go_overlay/cmd/wbd-client/m0_native_v4_windows.go",
            "r0/go_overlay/internal/windowsclient/native_unified_network_transaction.go",
            "r0/go_overlay/internal/windowsclient/native_plan029_no_wfp_routes_windows.go",
            "r0/go_overlay/internal/windowsclient/native_plan029_no_wfp_dns_windows.go",
            "r0/go_overlay/internal/windowsclient/native_product_activation_windows.go",
            "r0/go_overlay/internal/windowsclient/native_real_product_service_windows.go",
            "r0/go_overlay/internal/windowsclient/native_qualified_guard_intent_recovery_windows.go",
            "r0/go_overlay/internal/windowsclient/native_owned_transaction.go",
            "r0/go_overlay/internal/windowsclient/native_dns_write_windows.go",
            "r0/go_overlay/internal/windowsclient/native_lease_windows.go",
            "r0/go_overlay/internal/windowsclient/native_route_windows.go",
            "r0/go_overlay/internal/windowsclient/native_mtu_write_windows.go",
            "r0/go_overlay/internal/windowsclient/direct_udp_windows.go",
            "r0/go_overlay/internal/windowsclient/userspace_tcp_direct_windows.go",
            "r0/go_overlay/internal/windowsclient/network_plan.go",
            "r0/go_overlay/internal/windowsclient/native_rust_wintun_loan_windows.go",
            "r0/go_overlay/internal/realityfront/bridge_v4_windows_native_io.go",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_native_path(path))
                self.assertTrue(requires_native_smoke("push", [path]))

    def test_go_test_only_is_not_native(self):
        self.assertFalse(requires_native_smoke("push", [
            "r0/go_overlay/internal/windowsclient/native_unified_network_transaction_test.go",
        ]))

    def test_mixed_commit_starts_native(self):
        self.assertTrue(requires_native_smoke("push", [
            "r0/go_overlay/internal/windowsclient/native_bootstrap_dns_windows.go",
            "crates/wbd-engine/src/v4_windows_owner.rs",
        ]))

    def test_manual_and_explicit_full_requests_are_preserved(self):
        self.assertTrue(requires_native_smoke("workflow_dispatch", ["README.md"]))
        for marker in ("[wiring-full]", "[plan028-h1602-near-mtu-five-native]", "[m0-native-smoke]", "[plan029-v3-real-tunnel]", "[plan029-v3-real-direct-udp]", "[plan029-v3-real-p1-tunnel-ab]", "[plan029-v3-real-p2-bulk]", "[plan029-real-product-cn]"):
            self.assertTrue(requires_native_smoke("push", ["docs/readme.md"], marker))

    def test_workflow_gates_expensive_jobs_but_keeps_fast_push_checks(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/m0-wl-public-normal-full.yml").read_text(encoding="utf-8")
        self.assertIn("native_smoke: ${{ steps.native_scope.outputs.native_smoke }}", workflow)
        # GitHub 'needs' context only exposes DIRECT job dependencies.
        self.assertIn("needs: [wiring-contract, windows-compile-preflight]", workflow)
        self.assertIn("if: needs.wiring-contract.outputs.native_smoke == 'true'", workflow)
        self.assertIn("if: always() && needs.wiring-contract.outputs.native_smoke == 'true'", workflow)
        self.assertIn("python -m unittest tests.test_m0_native_ci_scope -v", workflow)
        self.assertIn("- r0/go_overlay/assembly/manifest-plan020-m0.json", workflow)
        self.assertIn("- .github/workflows/m0-wl-public-normal-full.yml", workflow)
        # Workflow-only edits trigger cheap source check; explicit marker
        # determines whether the same push admits a signed native scene.
        self.assertFalse(requires_native_smoke("push", [
            ".github/workflows/m0-wl-public-normal-full.yml"], "test-only workflow cleanup"))
        self.assertTrue(requires_native_smoke("push", [
            ".github/workflows/m0-wl-public-normal-full.yml"],
            "[plan029-v3-real-direct-udp]"))

    def test_h1859_p1_and_p2_bulk_both_build_exact_v3_before_native(self):
        source=(Path(__file__).resolve().parents[1] /
                ".github/workflows/m0-wl-public-normal-full.yml").read_text()
        trial=next(x for x in source.splitlines()
                   if x.strip().startswith("WBD_PLAN029_NATIVE_V3_TRIAL:"))
        for marker in ("[plan029-v3-real-p1-tunnel-ab]",
                       "[plan029-v3-real-p2-bulk]"):
            self.assertIn(marker,trial)
        for field in ("WBD_PLAN029_V3_DIRECT_SCENE:",
                      "WBD_WL_NATIVE_OUTER_MTU_REQUEST:",
                      "WBD_WL_TUN_MTU:"):
            row=next(x for x in source.splitlines() if x.strip().startswith(field))
            self.assertIn("[plan029-v3-real-p2-bulk]",row)
        self.assertIn('getattr(d,"wbd_m0_win_native_v3_start")',source)

    def test_plan029_real_gui_config_source_does_not_borrow_old_rust_dll(self):
        gui = (Path(__file__).resolve().parents[1] /
               ".github/workflows/m0-plan029-h1663-gui-domain-mtu-vm.yml").read_text()
        self.assertIn("tools/m0_plan029_gui_address_mtu_harness.cs", gui)
        self.assertIn("m0_plan029_*.go", gui)
        self.assertIn("workflow_dispatch:", gui)
        self.assertIn("python tools/prepare_windows_wiring.py", gui)
        self.assertIn("current-plan029-native.exe", gui)
        self.assertIn("cargo +1.85.1 build --locked --release -p wbd-engine", gui)
        self.assertIn("Copy-Item -LiteralPath $rustDLL -Destination result/gui/wbd_engine.dll", gui)
        self.assertIn("rust_source_sha=$env:GITHUB_SHA", gui)
        self.assertIn('rust_abi_scope="CURRENT_SOURCE_CONFIG_CHECK_ONLY"', gui)
        self.assertNotIn("PINNED_RUST_PRODUCT", gui)
        self.assertNotIn("actions/download-artifact@", gui)
        self.assertNotIn("pinned-rust/wbd_engine.dll", gui)
        # Whole manifest changes no longer cause a stale Rust product check.
        self.assertNotIn('      - "r0/go_overlay/assembly/manifest-plan020-m0.json"', gui)

    def test_plan029_nonci_product_split_has_one_outer_mtu_source_contract(self):
        # A source-only native build can be green while the actual signed
        # runner aborts before OS Apply if these two selectors diverge.
        # This is the first failure of H1840, not a Linux/Wintun bug.
        flow = (Path(__file__).resolve().parents[1] /
                ".github/workflows/m0-wl-public-normal-full.yml").read_text()
        outer = next(x for x in flow.splitlines()
                     if x.strip().startswith("WBD_WL_NATIVE_OUTER_MTU_REQUEST:"))
        requested = next(x for x in flow.splitlines()
                         if x.strip().startswith("WBD_WL_TUN_MTU:"))
        marker = "[plan029-real-product-cn]"
        self.assertIn(marker, outer)
        self.assertIn("'default1460'", outer.split(marker, 1)[1].split("||", 1)[0])
        self.assertIn(marker, requested)
        self.assertIn("'1460'", requested.split(marker, 1)[1].split("||", 1)[0])

    def test_h1843_real_product_v3_abi_built_and_checked_before_driver(self):
        workflow=(Path(__file__).resolve().parents[1] /
                  ".github/workflows/m0-wl-public-normal-full.yml").read_text()
        # Signed product build and runtime selection are different knobs.
        # The CI-only trial stays off in the original Go child, but that
        # cannot imply shipping a DLL without the V3 entrypoint.
        feature_section=workflow.split("$features='m0_v4_embedded_go,fec2_product_record,native_fec_acceleration'",1)[1]
        feature_section=feature_section.split("& cargo +1.85.1 build --locked --release",1)[0]
        self.assertIn("$env:WBD_PLAN029_PRODUCT_SPLIT_SCENE -eq '1'",feature_section)
        self.assertIn("$features+=',m0_v4_probe'",feature_section)
        self.assertIn("WBD_PLAN029_NATIVE_V3_TRIAL -eq '1'",feature_section)
        abi_section=workflow.split("Copy-Item target/release/wbd_engine.dll result/wl-public/wbd_engine.dll",1)[1]
        abi_section=abi_section.split("windows-binary-manifest.json",1)[0]
        self.assertIn("$env:WBD_PLAN029_PRODUCT_SPLIT_SCENE -eq '1'",abi_section)
        self.assertIn("getattr(d,\"wbd_m0_win_native_v3_start\")",abi_section)
        self.assertIn("if (os.environ.get('WBD_PLAN029_NATIVE_V3_TRIAL')=='1' or",workflow)
        self.assertIn("os.environ.get('WBD_PLAN029_PRODUCT_SPLIT_SCENE')=='1' or",workflow)

    def test_unknown_diff_fails_open_to_native(self):
        self.assertTrue(requires_native_smoke("push", []))
        self.assertTrue(requires_native_smoke("unknown", ["docs/README.md"]))


if __name__ == "__main__":
    unittest.main()
