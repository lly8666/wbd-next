"""Actions-only tests for batch delivery without weakening native qualification."""
import copy
from pathlib import Path
import tempfile
import unittest

import yaml
from tools import prepare_windows_wiring as p
from tools import governance as g

ROOT = Path(__file__).resolve().parents[1]


class DeliveryCiTests(unittest.TestCase):
    def test_retired_a5_has_no_public_native_dispatch(self):
        workflow=(ROOT / ".github/workflows/m0-wl-public-normal-full.yml").read_text()
        self.assertNotIn("perf_ab",self.workflow["on"]["workflow_dispatch"]["inputs"])
        self.assertNotIn("m0_wl_perf_v2_ab.py",workflow)
        self.assertNotIn("WBD_WL_PERF_AB",workflow)
        self.assertIn("WL_V2_REUSED_WINDOWS_NATIVE_EXACT_BINARY_SHA_PASS",workflow)

    @classmethod
    def setUpClass(cls):
        cls.workflow = yaml.load((ROOT / ".github/workflows/m0-wl-public-normal-full.yml").read_text(),
                                 Loader=yaml.BaseLoader)

    def test_plain_staging_push_does_not_launch_full_product(self):
        job = self.workflow["jobs"]["linux-source-locked-public"]
        self.assertEqual(job["needs"], ["windows-compile-preflight"])
        # Normal staging still cannot run full product; only an explicit,
        # source-verified Rust-only reuse bypasses separate compiler jobs.
        for guard in ("github.event_name == 'workflow_dispatch'", "github.ref_name == 'main'",
                      "contains(github.event.head_commit.message, '[wiring-full]')",
                      "inputs.perf_reuse_run_id == ''", "[plan026-rust-reuse-150]", "[plan026-rust-reuse-100]"):
            self.assertIn(guard, job["if"])
        native=self.workflow["jobs"]["native-public-two-os"]
        self.assertIn("[plan026-coding]", job["if"])
        self.assertIn("[plan026-coding]", native["if"])
        self.assertEqual(native["needs"], ["wiring-contract","linux-source-locked-public"])
        for guard in ("always()", "needs.wiring-contract.result == 'success'",
                      "needs.linux-source-locked-public.result == 'success'",
                      "inputs.perf_reuse_run_id != ''", "[plan026-rust-reuse-150]", "[plan026-rust-reuse-100]"):
            self.assertIn(guard,native["if"])

    def test_preflight_has_no_native_runtime_or_driver_effects(self):
        job = self.workflow["jobs"]["windows-compile-preflight"]
        self.assertEqual(job["needs"], ["wiring-contract"])
        self.assertEqual(job.get("if"),
            "inputs.perf_reuse_run_id == '' && !contains(github.event.head_commit.message, '[plan026-coding]') && !(contains(github.event.head_commit.message, '[plan026-rust-reuse-150]') || contains(github.event.head_commit.message, '[plan026-rust-reuse-100]') || contains(github.event.head_commit.message, '[plan026-rust-rxbuf-reuse-150]') || contains(github.event.head_commit.message, '[plan026-rust-cpu-reuse-150]') || contains(github.event.head_commit.message, '[plan026-win-npf-abba-150]'))")
        scripts = "\n".join(x.get("run", "") for x in job["steps"])
        self.assertIn("go test -c", scripts)
        self.assertIn("./cmd/wbd-client", scripts)
        self.assertIn("./internal/realityfront", scripts)
        self.assertIn("GO_COMPILE_ONLY", scripts)
        self.assertIn("native_product='NOT_RUN'", scripts)
        for forbidden in ("rustup", "cargo ", "wsl.exe", "-Action Install", "m0_wl_public_normal_e2e.py"):
            self.assertNotIn(forbidden, scripts)
        self.assertNotIn("continue-on-error", job)

    def test_reused_rust_product_requires_source_and_binary_sha_and_real_driver(self):
        native=self.workflow["jobs"]["native-public-two-os"]
        step=next(x for x in native["steps"] if x.get("name","").startswith("Restore exact prebuilt"))
        self.assertEqual(step["if"],"env.WBD_WL_REUSE_RUN_ID != '' && env.WBD_WL_ABBA_NATIVE != '1'")
        for required in ("gh api", "head_sha", "git diff --name-only",
                         "Cargo.lock", "m0-wl-windows-product-binaries-", "sha256",
                         "wbd_engine.dll", "wbd-client-embedded.exe", "m['features']"):
            self.assertIn(required,step["run"])
        install=next(x for x in native["steps"] if x.get("name","").startswith("Full public-run signed"))
        self.assertIn("-Action Install",install["run"])
        linux=next(x for x in native["steps"] if x.get("name","").startswith("Restore SAME-RUN"))
        self.assertIn("$env:WBD_WL_REUSE_RUN_ID",linux["run"])
        self.assertIn('m["source_sha"]==os.environ["LINUX_BINARY_SRC"]',linux["run"])
        self.assertIn("WBD_WL_REUSE_RUN_ID", native["env"])
        self.assertIn("WBD_WL_BINARY_SOURCE",native["env"])

    def test_rust_only_100mbps_scene_preserves_original_parameters(self):
        import json
        scene100=json.loads((ROOT/"scenarios/wl-normal-100m-300ms-0loss-60s.json").read_text())
        scene150=json.loads((ROOT/"scenarios/wl-normal-150m-300ms-0loss-60s.json").read_text())
        self.assertEqual(scene100["scenario_id"],"wl-normal-100m-300ms-0loss-60s")
        for field in ("schema_version","duration_s","warmup_s","drain_s","tun_mtu","seed"):
            self.assertEqual(scene100[field],scene150[field])
        for direction in ("windows_to_linux","linux_to_windows"):
            a=scene100[direction];b=scene150[direction]
            self.assertEqual(a["offered_mbps"],100)
            self.assertEqual(b["offered_mbps"],150)
            for field in ("delay_ms","loss_pct","tc_rate_mbps","packet_mix"):
                self.assertEqual(a[field],b[field])
        flow=self.workflow["jobs"]["wiring-contract"]["steps"]
        preflight=next(x for x in flow if x.get("name","").startswith("Enforce functional"))
        native=self.workflow["jobs"]["native-public-two-os"]
        for key in ("WL_V2_SCENARIO","WL_V2_REUSE_RUN","WL_V2_BINARY_SHA"):
            self.assertIn("[plan026-rust-reuse-100]",preflight["env"][key])
        self.assertIn("wl-normal-100m-300ms-0loss-60s.json",preflight["env"]["WL_V2_SCENARIO"])
        self.assertIn("wl-normal-100m-300ms-0loss-60s.json",native["env"]["WBD_WL_V2_SCENARIO"])
        self.assertIn("[plan026-rust-reuse-100]",native["env"]["WBD_WL_REUSE_RUN_ID"])
        self.assertIn("0543b805ca25d804ccd131be6686b0b99f61f80f",native["env"]["WBD_WL_BINARY_SOURCE"])

    def test_linux_raw_rxbuf_100_rebuilds_new_product_and_never_reuses_old_binary(self):
        flow=self.workflow["jobs"]["wiring-contract"]["steps"]
        first=next(x for x in flow if x.get("name","").startswith("Enforce functional"))
        native=self.workflow["jobs"]["native-public-two-os"]
        marker="[plan026-rust-rxbuf-100]"
        for expression in (first["env"]["PUBLIC_MODE"],first["env"]["WL_V2_SCENARIO"],
                           native["env"]["WBD_WL_PUBLIC_MODES"],native["env"]["WBD_WL_V2_SCENARIO"]):
            self.assertIn(marker,expression)
        self.assertIn("wl-normal-100m-300ms-0loss-60s.json",native["env"]["WBD_WL_V2_SCENARIO"])
        # The product ABI changed under crates/; this tag MUST NOT be a
        # prebuilt-mode selector or turn on Go steady-state A/B.
        self.assertNotIn(marker,native["env"]["WBD_WL_REUSE_RUN_ID"])
        self.assertNotIn(marker,first["env"]["WL_V2_REUSE_RUN"])
        self.assertNotIn(marker,native["env"]["WBD_WL_BINARY_SOURCE"])
        self.assertNotIn(marker,first["env"]["WL_V2_BINARY_SHA"])
        self.assertNotIn("WBD_WL_PERF_AB",native["env"])
        self.assertNotIn(marker,self.workflow["jobs"]["linux-source-locked-public"]["if"])
        for step_name in ("Prepare exact original Go", "Build actual original Windows Rust"):
            step=next(x for x in native["steps"] if x.get("name","").startswith(step_name))
            self.assertEqual(step["if"],"env.WBD_WL_REUSE_RUN_ID == ''")

    def test_linux_raw_rxbuf_new_source_150_reuse_is_hash_and_product_guarded(self):
        native=self.workflow["jobs"]["native-public-two-os"]
        preflight=self.workflow["jobs"]["wiring-contract"]["steps"]
        guard=next(x for x in preflight if x.get("name","").startswith("Enforce functional"))
        linux=self.workflow["jobs"]["linux-source-locked-public"]
        tag="[plan026-rust-rxbuf-reuse-150]"
        for line in (native["env"]["WBD_WL_PUBLIC_MODES"],native["env"]["WBD_WL_V2_SCENARIO"],
                     guard["env"]["PUBLIC_MODE"],guard["env"]["WL_V2_SCENARIO"]):
            self.assertIn(tag,line)
        for key in ("WBD_WL_BINARY_SOURCE","LINUX_BINARY_SRC","WBD_WL_REUSE_RUN_ID"):
            self.assertIn(tag,native["env"][key])
        self.assertIn("40681039919",native["env"]["WBD_WL_REUSE_RUN_ID"])
        self.assertIn("0abd1b04ee7a39d8aa426963564a079523c1036a",native["env"]["WBD_WL_BINARY_SOURCE"])
        self.assertIn("0abd1b04ee7a39d8aa426963564a079523c1036a",native["env"]["LINUX_BINARY_SRC"])
        self.assertIn("40681039919",guard["env"]["WL_V2_REUSE_RUN"])
        self.assertIn("0abd1b04ee7a39d8aa426963564a079523c1036a",guard["env"]["WL_V2_BINARY_SHA"])
        self.assertIn("150m-300ms-0loss-60s.json",native["env"]["WBD_WL_V2_SCENARIO"])
        # New product already validated source0abd; only now is a further
        # harness-only source allowed to skip rebuild with exact SHA checks.
        self.assertIn(tag,linux["if"])
        self.assertIn(tag,native["if"])
        self.assertIn(tag,self.workflow["jobs"]["windows-compile-preflight"]["if"])
        self.assertNotIn("WBD_WL_PERF_AB",native["env"])
        verify=next(x for x in native["steps"] if x.get("name","").startswith("Restore exact prebuilt"))
        for needle in ("git diff --name-only", "Cargo.lock", "sha256", "head_sha"):
            self.assertIn(needle,verify["run"])

    def test_rust_150_windows_cpu_audit_uses_same_compiled_source_and_real_os(self):
        native=self.workflow["jobs"]["native-public-two-os"]
        preflight=next(x for x in self.workflow["jobs"]["wiring-contract"]["steps"]
                       if x.get("name","").startswith("Enforce functional"))
        tag="[plan026-rust-cpu-reuse-150]"
        for env in (preflight["env"],native["env"]):
            self.assertIn(tag,env["WL_V2_SCENARIO"] if "WL_V2_SCENARIO" in env
                          else env["WBD_WL_V2_SCENARIO"])
        self.assertIn("150m-300ms-0loss-60s.json",native["env"]["WBD_WL_V2_SCENARIO"])
        self.assertIn(tag,native["env"]["WBD_WL_V2_CPU_AUDIT"])
        self.assertIn("40681039919",native["env"]["WBD_WL_REUSE_RUN_ID"])
        self.assertIn("0abd1b04ee7a39d8aa426963564a079523c1036a",
                      native["env"]["WBD_WL_BINARY_SOURCE"])
        self.assertIn(tag,self.workflow["jobs"]["linux-source-locked-public"]["if"])
        self.assertIn(tag,native["if"])
        self.assertNotIn("WBD_WL_PERF_AB",native["env"])
        self.assertIn("tests.test_m0_wl_windows_cpu_audit",
                      " ".join(x.get("run","") for x in
                          self.workflow["jobs"]["wiring-contract"]["steps"]))

    def test_win_rx_wake_batch_source_build_and_true_150_cpu_audit(self):
        tag="[plan026-win-wake-150]"
        preflight=next(x for x in self.workflow["jobs"]["wiring-contract"]["steps"]
            if x.get("name","").startswith("Enforce functional"))
        native=self.workflow["jobs"]["native-public-two-os"]
        for expr in (preflight["env"]["PUBLIC_MODE"],
                     preflight["env"]["WL_V2_SCENARIO"],
                     native["env"]["WBD_WL_PUBLIC_MODES"],
                     native["env"]["WBD_WL_V2_SCENARIO"],
                     native["env"]["WBD_WL_V2_CPU_AUDIT"]):
            self.assertIn(tag,expr)
        self.assertIn("150m-300ms-0loss-60s.json",
                      native["env"]["WBD_WL_V2_SCENARIO"])
        # Changed Rust owner requires SAME new-SOURCE Windows+Linux native
        # builds. Old 0abd products must never be reused for this experiment.
        for expr in (preflight["env"]["WL_V2_REUSE_RUN"],
                     preflight["env"]["WL_V2_BINARY_SHA"],
                     native["env"]["WBD_WL_REUSE_RUN_ID"],
                     native["env"]["WBD_WL_BINARY_SOURCE"],
                     native["env"]["LINUX_BINARY_SRC"]):
            self.assertNotIn(tag,expr)
        self.assertNotIn(tag,self.workflow["jobs"]["linux-source-locked-public"]["if"])
        self.assertNotIn(tag,self.workflow["jobs"]["windows-compile-preflight"]["if"])
        self.assertNotIn(tag,self.workflow["jobs"]["windows-rust-contract-preflight"]["if"])
        self.assertIn("env.WBD_WL_REUSE_RUN_ID == ''",
                      next(x for x in native["steps"]
                           if x.get("name","").startswith("Build actual original Windows Rust"))["if"])

    def test_windows_npf_borrowed_rx_rebuilds_source_and_keeps_full_150_gate(self):
        tag="[plan026-win-npf-borrow-150]"
        jobs=self.workflow["jobs"]
        native=jobs["native-public-two-os"]
        preflight=next(x for x in jobs["wiring-contract"]["steps"]
            if x.get("name","").startswith("Enforce functional"))
        for val in (preflight["env"]["PUBLIC_MODE"],
                    preflight["env"]["WL_V2_SCENARIO"],
                    native["env"]["WBD_WL_PUBLIC_MODES"],
                    native["env"]["WBD_WL_V2_SCENARIO"],
                    native["env"]["WBD_WL_V2_CPU_AUDIT"]):
            self.assertIn(tag,val)
        self.assertIn("wl-normal-150m-300ms-0loss-60s.json",
                      native["env"]["WBD_WL_V2_SCENARIO"])
        # An ABI-compatible Rust platform/engine source change still changes
        # the Windows and Linux product: old binary reuse is prohibited.
        for val in (preflight["env"]["WL_V2_REUSE_RUN"],
                    preflight["env"]["WL_V2_BINARY_SHA"],
                    native["env"]["WBD_WL_REUSE_RUN_ID"],
                    native["env"]["WBD_WL_BINARY_SOURCE"],
                    native["env"]["LINUX_BINARY_SRC"]):
            self.assertNotIn(tag,val)
        self.assertNotIn(tag,jobs["linux-source-locked-public"]["if"])
        self.assertNotIn(tag,jobs["windows-compile-preflight"]["if"])
        self.assertNotIn(tag,jobs["windows-rust-contract-preflight"]["if"])
        self.assertIn("env.WBD_WL_REUSE_RUN_ID == ''",
            next(x for x in native["steps"]
                if x.get("name","").startswith("Build actual original Windows Rust"))["if"])

    def test_same_windows_runner_rust_native_abba_is_exact_source_only(self):
        tag="[plan026-win-npf-abba-150]"
        jobs=self.workflow["jobs"]
        native=jobs["native-public-two-os"]
        for line in (native["if"],native["env"]["WBD_WL_PUBLIC_MODES"],
                     native["env"]["WBD_WL_V2_SCENARIO"],
                     native["env"]["WBD_WL_ABBA_NATIVE"]):
            self.assertIn(tag,line)
        self.assertIn("40693430836",native["env"]["WBD_WL_REUSE_RUN_ID"])
        self.assertIn("7fc38591c501ff4a06e1862c7b08d5d3dbc1be95",
                      native["env"]["WBD_WL_BINARY_SOURCE"])
        self.assertNotIn("WBD_WL_PERF_AB",native["env"])
        self.assertIn(tag,jobs["linux-source-locked-public"]["if"])
        self.assertIn(tag,jobs["windows-compile-preflight"]["if"])
        self.assertIn(tag,jobs["windows-rust-contract-preflight"]["if"])
        prepare=next(x for x in native["steps"]
                if x.get("name","").startswith("Prepare source-locked A/B"))
        self.assertEqual(prepare["if"],"env.WBD_WL_ABBA_NATIVE == '1'")
        self.assertIn("m0_wl_native_abba_prepare.py",prepare["run"])
        self.assertIn("git diff --name-only",prepare["run"])
        execution=next(x for x in native["steps"]
                if x.get("name","").startswith("Launch actual WSL2"))
        self.assertIn("m0_wl_native_rx_abba.py",execution["run"])
        self.assertIn("WL_REAL_SAME_WINDOWS_RUNNER_ABBA_DECISION",execution["run"])
        self.assertIn("result/wl-public/wl-native-abba/",
                next(x for x in native["steps"]
                  if x.get("uses","").startswith("actions/upload-artifact")
                     and x.get("if")=="always()")["with"]["path"])
        preflight="\n".join(x.get("run","") for x in jobs["wiring-contract"]["steps"])
        self.assertIn("tests.test_m0_wl_native_rx_abba",preflight)

    def test_native_success_and_cleanup_contracts_retained(self):
        job = self.workflow["jobs"]["native-public-two-os"]
        scripts = "\n".join(x.get("run", "") for x in job["steps"])
        for required in ("cargo +1.85.1 test", "TestM0WindowsGameFecProtectedExtensionBounds",
                         "TestM0PLAN", "-Action Install", "PASS_ACTUAL_WINDOWS_LINUX_NATIVE",
                         "LINUX_BINARY_SRC", "--test-threads=1"):
            self.assertIn(required, scripts)
        cleanups = [x for x in job["steps"] if x.get("name", "").startswith(
            ("Restore Linux raw", "Remove exact owned", "Delete only exact owned", "Restore Npcap owned"))]
        self.assertEqual(len(cleanups), 4)
        self.assertTrue(all(x.get("if") == "always()" for x in cleanups))
        self.assertNotIn("continue-on-error", job)
        # N0 is a performance scenario, not an implicit main seven-mode
        # startup requirement. Keep strong delivery checks and require
        # explicit one-mode selection/true on-wire N0 PASS before promotion.
        # Existing manual N0 selection is unchanged; a narrowly tagged main
        # source may select ONLY Normal N0 240s, never a hidden seven-mode
        # performance matrix or an unrelated staging/PR event.
        run_n0=job["env"]["WBD_WL_RUN_N0"]
        mode=job["env"]["WBD_WL_PUBLIC_MODES"]
        seconds=job["env"]["WBD_WL_N0_SECONDS"]
        for guard in ("github.ref_name == 'main'", "[plan025-n0-240s]",
                      "inputs.run_n0 == true && '1' || '0'"):
            self.assertIn(guard, run_n0)
        for guard in ("github.ref_name == 'main'", "[plan025-n0-240s]",
                      "&& 'normal'", "inputs.public_mode || 'all'"):
            self.assertIn(guard, mode)
        self.assertIn("&& '240' || '60'", seconds)
        preflight=self.workflow["jobs"]["wiring-contract"]["steps"]
        entry=next(x for x in preflight if x.get("name","").startswith("Enforce functional"))
        self.assertIn("[plan025-n0-240s]",entry["env"]["RUN_N0"])
        self.assertIn("&& 'normal'",entry["env"]["PUBLIC_MODE"])
        self.assertIn("PASS_SCOPED_", scripts)
        self.assertIn("selected same-SOURCE native public mode", scripts)

    def test_performance_one_scenario_rejected_before_any_native_build(self):
        inputs = self.workflow["on"]["workflow_dispatch"]["inputs"]
        self.assertEqual(inputs["public_mode"]["default"], "all")
        self.assertEqual(inputs["run_n0"]["default"], "false")
        self.assertEqual(inputs["run_n0"]["type"], "boolean")
        self.assertIn("normal", inputs["public_mode"]["options"])
        self.assertIn("game4-fec", inputs["public_mode"]["options"])
        checks = "\n".join(x.get("run", "") for x in
                           self.workflow["jobs"]["wiring-contract"]["steps"])
        self.assertIn("select_source_locked_modes", checks)
        self.assertIn("RUN_N0", checks)

    def test_new_windows_original_m2_and_m3_regressions_are_compiled_not_zero_tests(self):
        # A go test -run exact name silently exits 0 when the test file was
        # not copied into pinned original-Go. Require both source files in
        # the exact shared original-Go assembly, not just workflow path triggers.
        self.assertIn("bridge_v4_windows_m2_batch_preflight_test.go",
                      p.EXTRA_BRIDGES["realityfront"])
        self.assertIn("bridge_v4_windows_open_validated_test.go",
                      p.EXTRA_BRIDGES["realityfront"])
        scripts = "\n".join(x.get("run", "") for x in
                            self.workflow["jobs"]["windows-compile-preflight"]["steps"])
        self.assertIn("TestM0PLAN025WindowsOriginalM2BatchPreflightClassifiesFirstRefusal", scripts)
        self.assertIn("TestM0PLAN025WindowsNativeNormalOpenFirstFaultIsBoundedAndSafe", scripts)

    def test_both_paths_use_same_assembly_and_pinned_original(self):
        for name in ("windows-compile-preflight", "native-public-two-os"):
            steps = self.workflow["jobs"][name]["steps"]
            self.assertTrue(any(x.get("run") == "python tools/prepare_windows_wiring.py" for x in steps))
            donor = next(x for x in steps if x.get("with", {}).get("repository") == "lly8666/wobuzhidao")
            self.assertEqual(donor["with"]["ref"], p.ORIGINAL)

    def test_manifest_mismatch_is_not_silently_repaired(self):
        data = b"package example\n"
        spec = {"legacy_source": p.ORIGINAL, "operations": [{"overlay_path": "demo.go", "result_blob": p.blob(data)}]}
        p.check_spec(spec, lambda path: data)
        with self.assertRaisesRegex(ValueError, "blob mismatch"):
            p.check_spec(spec, lambda path: data + b"changed")
        bad = copy.deepcopy(spec)
        bad["legacy_source"] = "a" * 40
        with self.assertRaisesRegex(ValueError, "SOURCE changed"):
            p.check_spec(bad, lambda path: data)

    def test_bad_evidence_reports_exact_path_instead_of_anonymous_json_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "wrong-kind.md").write_text("# Not a JSON receipt", encoding="utf-8")
            with self.assertRaisesRegex(g.ContractError, "invalid JSON in wrong-kind.md"):
                g.read_json(root, "wrong-kind.md")


if __name__ == "__main__":
    unittest.main()
