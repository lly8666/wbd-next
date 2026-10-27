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
    @classmethod
    def setUpClass(cls):
        cls.workflow = yaml.load((ROOT / ".github/workflows/m0-wl-public-normal-full.yml").read_text(),
                                 Loader=yaml.BaseLoader)

    def test_plain_staging_push_does_not_launch_full_product(self):
        job = self.workflow["jobs"]["linux-source-locked-public"]
        self.assertEqual(job["needs"], ["windows-compile-preflight"])
        self.assertEqual(job["if"], "github.event_name == 'workflow_dispatch' || github.ref_name == 'main' || contains(github.event.head_commit.message, '[wiring-full]')")
        self.assertEqual(self.workflow["jobs"]["native-public-two-os"]["needs"], ["linux-source-locked-public"])

    def test_preflight_has_no_native_runtime_or_driver_effects(self):
        job = self.workflow["jobs"]["windows-compile-preflight"]
        self.assertEqual(job["needs"], ["wiring-contract"])
        self.assertNotIn("if", job)
        scripts = "\n".join(x.get("run", "") for x in job["steps"])
        self.assertIn("go test -c", scripts)
        self.assertIn("./cmd/wbd-client", scripts)
        self.assertIn("./internal/realityfront", scripts)
        self.assertIn("GO_COMPILE_ONLY", scripts)
        self.assertIn("native_product='NOT_RUN'", scripts)
        for forbidden in ("rustup", "cargo ", "wsl.exe", "-Action Install", "m0_wl_public_normal_e2e.py"):
            self.assertNotIn(forbidden, scripts)
        self.assertNotIn("continue-on-error", job)

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
        self.assertEqual(job["env"]["WBD_WL_RUN_N0"],
                         "${{ inputs.run_n0 == true && '1' || '0' }}")
        self.assertIn("inputs.public_mode || 'all'",
                      job["env"]["WBD_WL_PUBLIC_MODES"])
        self.assertIn("PASS_SCOPED_", scripts)
        self.assertIn("selected same-SOURCE native public mode", scripts)

    def test_isolated_n0_push_does_not_change_manual_run_n0_contract(self):
        job = self.workflow["jobs"]["native-public-two-os"]
        self.assertEqual(job["env"]["WBD_WL_RUN_N0"],
                         "${{ inputs.run_n0 == true && '1' || '0' }}")
        scripts = "\\n".join(x.get("run", "") for x in job["steps"])
        self.assertIn("experiment/windows-wiring-n0-normal-parallel-20261028", scripts)
        self.assertIn("[[]wl-n0-normal-only[]]", scripts)
        self.assertIn("WL_N0_ISOLATED_PUSH_SELECTED_ONE_NORMAL_PERFORMANCE_SCENARIO", scripts)
        self.assertIn("$env:WBD_WL_PUBLIC_MODES='normal'", scripts)
        self.assertIn("$env:WBD_WL_RUN_N0='1'", scripts)
        checks = "\\n".join(x.get("run", "") for x in
                           self.workflow["jobs"]["wiring-contract"]["steps"])
        self.assertIn("select_source_locked_modes", checks)
        self.assertIn("RUN_N0", checks)

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
