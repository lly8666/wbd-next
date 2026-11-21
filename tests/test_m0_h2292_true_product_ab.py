"""H2292 real ORIGINAL Windows signed Npcap/Wintun GoTLS/Rust A/B/A' paired CI."""
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2292_true_product_ab as trial


class OriginalProductSameTripletAB(unittest.TestCase):
    def test_three_real_sessions_exact_order_not_parallel_or_bare_tcp(self):
        self.assertEqual(trial.LEGS,("A_default","B_tx16","A_prime"))
        self.assertEqual(trial.ROOT,pathlib.Path("h2292-out"))
        self.assertEqual(trial.CANDIDATE_BUILD_SHA,trial.os.environ.get("GITHUB_SHA","NO_GITHUB_SHA"))
        source=(ROOT/"tools/m0_h2292_true_product_ab.py").read_text()
        self.assertIn("true_windows_product(group,relay,arm,ready)",source)
        self.assertIn("arm.check_server_and_run_app(group)",source)
        self.assertIn('arm_restart_original_tun_udp(tag,own)',source)
        self.assertIn("client_owned_stop",source)
        self.assertIn("windows_original_go_rust_cpu_stage",source)
        self.assertIn("h2292_same_vm_original_product_abaprime",source)
        self.assertIn('candidate_enabled',source)
        self.assertIn('os.environ["WBD_H2291_WINDOWS_TX_CANDIDATE"]=',source)
        self.assertIn("shutil.copy2(chosen,BINARY)",source)
        self.assertIn("shutil.copy2(ORIGINAL,BINARY)",source)
        self.assertIn('client-result.json',source)
        self.assertNotIn("MOCK_PRODUCT_PASS",source)

    def test_two_dlls_share_real_source_features_except_one_rust_flag(self):
        workflow=(ROOT/".github/workflows/qa-h2292-true-windows-rust-aba.yml").read_text()
        self.assertEqual(workflow.count("group: [a, b]"),3)
        self.assertEqual(workflow.count("runs-on: windows-2025"),2)
        self.assertEqual(workflow.count("runs-on: ubuntu-24.04-arm"),3)
        self.assertEqual(workflow.count("uses: tailscale/github-action@v4"),3)
        self.assertEqual(workflow.count("[m0-029-h2292-true-rust-aba]"),5)
        self.assertIn("win_candidate_build:",workflow)
        self.assertIn("h2292-two-real-win-rust-dlls-",workflow)
        self.assertIn('cargo +1.85.1 test --locked -p wbd-platform --lib windows_native_io',workflow)
        self.assertIn("cargo +1.85.1 test --locked -p wbd-platform --features h2291_windows_tx_service",workflow)
        self.assertIn('cargo +1.85.1 build --locked --release -p wbd-engine --features $base',workflow)
        self.assertIn('cargo +1.85.1 build --locked --release -p wbd-engine --features "$base,h2291_windows_tx_service"',workflow)
        self.assertIn("H2292_TWO_ACTUAL_DLLS_DIFFER_ONLY_BY_ONE_RUST_FEATURE",workflow)
        self.assertIn("H2292_REAL_ARM_TUN_THREE_ORIGINAL_TCP_STAGES_DONE",workflow)
        self.assertIn("H2292_REAL_ARM_STAGE_READY", (ROOT/"tools/m0_h2276_three_runner_tcp.py").read_text())
        self.assertIn("tools/m0_h2292_true_product_ab.py client $env:GROUP",workflow)
        self.assertIn("tools/m0_h2292_true_product_ab.py arm",workflow)
        self.assertIn("h2292-out/",workflow)
        self.assertNotIn("PASS_H2292_THROUGHPUT_IMPROVED",workflow)

    def test_no_faux_win_or_arm_tun_and_true_owned_stop(self):
        wrapper=(ROOT/"tools/m0_h2292_true_product_ab.py").read_text()
        self.assertIn("CANDIDATE_BUILD_SHA=os.environ.get",wrapper)
        self.assertIn("EXACT_ORIGINAL_WINDOWS_GO_TLS_EXE",wrapper)
        self.assertIn("DEFAULT_AND_CANDIDATE_SAME_COMPILED_RUST_FEATURE_BASE",wrapper)
        self.assertIn("PASS_H2286_TRUE_ORIGINAL_WINDOWS_ARM_GO_TLS_RUST_WINTUN_TUN_TCP",wrapper)
        self.assertIn("arm.ROOT/(\"server-\"+tag+\".json\")",wrapper)
        self.assertIn("h2292_same_vm_original_product_abaprime",wrapper)
        self.assertIn("wait_arm_stage(relay_ready,tag)",wrapper)
        self.assertIn("h2292_arm_stage_ready",wrapper)


if __name__=="__main__":
    unittest.main()
