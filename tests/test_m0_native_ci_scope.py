import unittest

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
            "crates/wbd-engine/src/v4_owner_crypto.rs",
            "r0/go_overlay/cmd/wbd-client/m0_native_v4_windows.go",
            "r0/go_overlay/internal/windowsclient/native_unified_network_transaction.go",
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
        for marker in ("[wiring-full]", "[plan028-h1602-near-mtu-five-native]", "[m0-native-smoke]"):
            self.assertTrue(requires_native_smoke("push", ["docs/readme.md"], marker))

    def test_unknown_diff_fails_open_to_native(self):
        self.assertTrue(requires_native_smoke("push", []))
        self.assertTrue(requires_native_smoke("unknown", ["docs/README.md"]))


if __name__ == "__main__":
    unittest.main()
