"""H2291 source-locked Windows native Rust TX service candidate, never a product PASS.

A ready-only 16-record stage and native 64KiB/16-frame NPF queue are opt-in.
The original default 8-record/16KiB queue is unchanged for every other build.
"""
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]


class WindowsNPFTXService(unittest.TestCase):
    def test_only_explicit_source_feature_changes_original_native_tx(self):
        platform=(ROOT/"crates/wbd-platform/src/windows_native_io.rs").read_text()
        runtime=(ROOT/"crates/wbd-engine/src/v4_windows_native_runtime.rs").read_text()
        engine=(ROOT/"crates/wbd-engine/Cargo.toml").read_text()
        oscrate=(ROOT/"crates/wbd-platform/Cargo.toml").read_text()
        self.assertIn('h2291_windows_tx_service = ["wbd-platform/h2291_windows_tx_service"]',engine)
        self.assertIn('h2291_windows_tx_service = []',oscrate)
        self.assertIn('const BATCH:usize=if cfg!(any(feature="h2291_windows_tx_service",',runtime)
        self.assertIn('feature="h2311_windows_tx16_only")){16}else{8};',runtime)
        self.assertIn('h2311_windows_tx16_only = ["wbd-platform/h2311_windows_npf_trace"]',engine)
        self.assertIn('h2311_windows_npf64_only = ["wbd-platform/h2311_windows_npf64_only", "wbd-platform/h2311_windows_npf_trace"]',engine)
        self.assertIn('h2311_windows_npf64_only = []',oscrate)
        self.assertIn('h2311_windows_npf_trace = []',oscrate)
        self.assertIn('feature="h2311_windows_npf64_only"',platform)
        self.assertIn('PLAN029_H2311_NPF_STOP_PROFILE',platform)
        self.assertIn('queue_bytes_copied',platform)
        self.assertIn('h2311_trace_counts_real_driver_queue_prefix_and_direct_calls',platform)
        self.assertIn('for _ in 0..(RX_WAKE_BATCH/BATCH)',runtime)
        self.assertIn('const RX_WAKE_BATCH:usize=32;',runtime)
        self.assertIn('const POST_INGRESS_RETURN_QUANTUM:usize=8;',runtime)
        self.assertIn('64 * 1024',platform)
        self.assertIn('16 * 1024',platform)
        self.assertIn('NPF_QUEUE_PACKETS: usize = if cfg!(any(feature="h2291_windows_tx_service", feature="h2311_windows_npf64_only"))',platform)
        self.assertIn('fn h2291_ready_sixteen_frames_use_one_queue_only_when_explicitly_enabled()',platform)
        self.assertIn('queue_bytes={} max_frames={} ready_only=1',platform)
        self.assertIn('let result=npf.send_batch(&ready[..count]);',runtime)
        self.assertIn('m2_kernel_firstsend_entry(',runtime)

    def test_only_after_same_source_real_windows_rust_build_and_immutable_original_go(self):
        w=(ROOT/".github/workflows/qa-h2291-dual-original-win-tx-batch.yml").read_text()
        self.assertEqual(w.count("group: [a, b]"),3)
        self.assertEqual(w.count("runs-on: windows-2025"),2)
        self.assertEqual(w.count("runs-on: ubuntu-24.04-arm"),3)
        self.assertIn("win_candidate_build:",w)
        self.assertIn("cargo +1.85.1 test --locked -p wbd-platform --features h2291_windows_tx_service",w)
        self.assertIn("cargo +1.85.1 build --locked --release -p wbd-engine --features $features",w)
        self.assertIn("h2291-win-rust-candidate-",w)
        self.assertIn("H2291_NATIVE_WINDOWS_CANDIDATE_SHA_MATCH",w)
        self.assertIn("PASS_H2286_TRUE_ORIGINAL_WINDOWS_ARM_GO_TLS_RUST_WINTUN_TUN_TCP",w)
        self.assertIn("H2291_TRUE_ORIGINAL_GO_TLS_EXE_CANDIDATE_RUST_DLL_READY",w)
        self.assertEqual(w.count("[m0-029-h2291-windows-tx-service]"),5)
        self.assertIn("original ARM64 GoTLS Rust",w)
        self.assertNotIn("PASS_H2291_THROUGHPUT_IMPROVED",w)
        self.assertNotIn("GO_RUST_PRODUCT_DEFAULT_PROMOTED",w)

    def test_original_client_is_same_authenticated_go_exe_and_real_driver(self):
        p=(ROOT/"tools/m0_h2286_full_windows_product.py").read_text()
        self.assertIn('WBD_H2291_WINDOWS_TX_CANDIDATE',p)
        self.assertIn('H2291_EXACT_RUST_SOURCE_AND_ORIGINAL_GO_ABI_MANIFEST',p)
        self.assertIn('FROZEN_WIN_BINARY_SOURCE_MANIFEST',p)
        self.assertIn('H2291_RUST_CANDIDATE_QUEUE_NOT_ACTUALLY_USED',p)
        self.assertIn('PASS_REAL_ORIGINAL_GO_RUST_WAL_STOP',p)
        self.assertIn('Wintun',p)
        self.assertIn('original_win_client_args(',p)
        self.assertIn('tcp.client(APP_IP,APP_PEER,own["source_sha"])',p)


if __name__=="__main__":
    unittest.main()
