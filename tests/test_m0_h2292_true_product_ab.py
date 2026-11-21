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
        self.assertEqual(trial.CANDIDATE_BUILD_SHA,trial.os.environ.get("WBD_H2292_COMPILED_SOURCE_SHA",trial.os.environ.get("GITHUB_SHA","NO_GITHUB_SHA")))
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
        self.assertIn("shutil.copy2(MANIFEST,ACTIVE_MANIFEST)",source)
        self.assertIn("ACTIVE_MANIFEST.unlink(missing_ok=True)",source)
        self.assertIn("ACTIVE_MANIFEST.exists()==tuned",source)
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
        self.assertIn('WBD_H2292_COMPILED_SOURCE_SHA: "dc2da4b98ecc419a67e3e2ee6530f944b78d88ef"',workflow)
        self.assertIn('gh run download 44949570906',workflow)
        self.assertIn('git diff --name-only $compiled $env:GITHUB_SHA -- crates r0/go_overlay Cargo.toml Cargo.lock',workflow)
        self.assertIn('H2292_REAL_WINDOWS_PRODUCT_COMPILED_SOURCE_CHANGED',workflow)
        self.assertIn('H2292_EXACT_PRIOR_REAL_RUST_DLL_PAIR_REUSED_ZERO_PRODUCT_DIFF',workflow)
        self.assertIn("H2292_TWO_ACTUAL_DLLS_DIFFER_ONLY_BY_ONE_RUST_FEATURE",workflow)
        self.assertIn("H2292_REAL_ARM_TUN_THREE_ORIGINAL_TCP_STAGES_DONE",workflow)
        self.assertIn("H2292_REAL_ARM_STAGE_READY", (ROOT/"tools/m0_h2276_three_runner_tcp.py").read_text())
        self.assertIn("tools/m0_h2292_true_product_ab.py client $env:GROUP",workflow)
        self.assertIn("tools/m0_h2292_true_product_ab.py arm",workflow)
        self.assertIn("h2292-out/",workflow)
        self.assertNotIn("PASS_H2292_THROUGHPUT_IMPROVED",workflow)

    def test_windows_peer_identity_published_before_slow_wsl_and_driver_install(self):
        # H2292 run44949570906 group B finished all 3 true sessions,
        # group A waited in WSL boot and ARM/relay timed out because the
        # Windows Tailscale peer artifact was published AFTER slow bootstrap.
        workflow=(ROOT/".github/workflows/qa-h2292-true-windows-rust-aba.yml").read_text()
        peer=workflow.index("      - name: Publish real Windows VM identity and validate Python probe")
        upload=workflow.index("          name: h2276-${{ matrix.group }}-client-peer")
        wsl=workflow.index("      - name: Boot real Windows-owned Ubuntu WSL2 kernel")
        drv=workflow.index("      - name: Real signed Npcap 1.88")
        self.assertLess(peer,upload)
        self.assertLess(upload,wsl)
        self.assertLess(wsl,drv)
        self.assertIn("curl.exe --fail --location",workflow)
        self.assertIn("--max-time 180 --retry 1 --retry-delay 2",workflow)
        self.assertIn("m0_wl_windows_bounded_cmd.py 150 wsl.exe -d Ubuntu",workflow)
        self.assertIn("m0_wl_windows_bounded_cmd.py 30 wsl.exe -d Ubuntu",workflow)

    def test_no_faux_win_or_arm_tun_and_true_owned_stop(self):
        wrapper=(ROOT/"tools/m0_h2292_true_product_ab.py").read_text()
        self.assertIn("CANDIDATE_BUILD_SHA=os.environ.get",wrapper)
        self.assertIn("EXACT_ORIGINAL_WINDOWS_GO_TLS_EXE",wrapper)
        self.assertEqual(str(trial.ACTIVE_MANIFEST),
                         "result/wl-public/h2291-windows-dll-manifest.json")
        validator=(ROOT/"tools/m0_h2286_full_windows_product.py").read_text()
        self.assertIn('(p/"h2291-windows-dll-manifest.json").read_text()',validator)
        self.assertIn("DEFAULT_AND_CANDIDATE_SAME_COMPILED_RUST_FEATURE_BASE",wrapper)
        self.assertIn("CANDIDATE_BUILD_SHA=os.environ.get(\"WBD_H2292_COMPILED_SOURCE_SHA\"",wrapper)
        self.assertIn('compiled_source=os.environ.get("WBD_H2292_COMPILED_SOURCE_SHA"',validator)
        self.assertIn("PASS_H2286_TRUE_ORIGINAL_WINDOWS_ARM_GO_TLS_RUST_WINTUN_TUN_TCP",wrapper)
        self.assertIn("arm.ROOT/(\"server-\"+tag+\".json\")",wrapper)
        self.assertIn("h2292_same_vm_original_product_abaprime",wrapper)
        self.assertIn("wait_arm_stage(relay_ready,tag)",wrapper)
        self.assertIn("h2292_arm_stage_ready",wrapper)


if __name__=="__main__":
    unittest.main()
