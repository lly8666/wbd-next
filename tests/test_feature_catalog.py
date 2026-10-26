"""Actions-only feature governance tests, including bypass/regression cases."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml
from tools import feature_catalog as f


class FeatureCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ("crates/demo.rs", "docs/use.md", "docs/proof.json", "docs/decision.md"):
            self.write(name, "test")
        self.state = {"schema_version": 1, "status": "NOT_INITIALIZED", "scope_branch": "experiment/demo",
                      "baseline_source": "a" * 40, "gaps": ["pending"], "next_action": "inventory"}
        self.write(f.STATE, self.state)
        self.entry = {"schema_version": 1, "id": "demo", "name": "演示", "owner": "M0",
                      "summary": "Test behavior", "stage": "experimental", "development_branch": "experiment/demo",
                      "available_on": ["experiment/demo", "integration/demo"], "defaults": {},
                      "usage": {"cli": "--demo", "config": "not applicable: internal", "gui": "not wired"},
                      "code_refs": ["crates/demo.rs"], "doc_refs": ["docs/use.md"],
                      "verification": [{"platform": "linux/arm64", "scope": "normal", "status": "NOT_RUN",
                                        "source_sha": None, "evidence": None}], "limitations": [], "promotion": None}

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value, encoding="utf-8")
        return path

    def card(self):
        return self.write(f.CATALOG + "demo.json", self.entry)

    def note(self, kind, ids, reason="No user-facing behavior changed"):
        name = "docs/devlog/M0/test.md"
        self.write(name, "```feature-impact\n" + json.dumps({"kind": kind, "ids": ids, "reason": reason}) + "\n```\n")
        return name

    def test_bootstrap_is_explicit_not_empty_product_success(self):
        state, items = f.read_catalog(self.root)
        self.assertFalse(items)
        self.assertIn("尚未初始化", f.render(state, items))
        self.state.update(status="COMPLETE_FOR_SCOPE", gaps=[], review_ref="docs/decision.md")
        self.write(f.STATE, self.state)
        with self.assertRaises(f.CatalogError):
            f.read_catalog(self.root)

    def test_experiment_location_and_usage_required(self):
        f.validate_entry(self.root, self.card())
        self.entry["development_branch"] = "integration/demo"
        with self.assertRaises(f.CatalogError):
            f.validate_entry(self.root, self.card())
        self.entry["legacy_branch_reason"] = "Recovered historical integration feature"
        f.validate_entry(self.root, self.card())
        del self.entry["usage"]["gui"]
        with self.assertRaises(f.CatalogError):
            f.validate_entry(self.root, self.card())

    def test_main_merge_does_not_promote(self):
        self.entry["available_on"].append("main")
        self.assertEqual(f.validate_entry(self.root, self.card())["stage"], "experimental")
        self.entry["stage"] = "formal"
        with self.assertRaises(f.CatalogError):
            f.validate_entry(self.root, self.card())
        self.entry["promotion"] = {"source_sha": "a" * 40, "decision": "docs/decision.md", "evidence": "docs/proof.json"}
        with self.assertRaises(f.CatalogError):
            f.validate_entry(self.root, self.card())
        self.entry["verification"][0].update(status="FUNCTIONAL_PASS", source_sha="a" * 40, evidence="docs/proof.json")
        f.validate_entry(self.root, self.card())

    def test_pass_requires_source_and_existing_evidence(self):
        self.entry["verification"][0]["status"] = "BUILD_PASS"
        with self.assertRaises(f.CatalogError):
            f.validate_entry(self.root, self.card())
        self.entry["verification"][0].update(source_sha="a" * 40, evidence="docs/missing.json")
        with self.assertRaises(f.CatalogError):
            f.validate_entry(self.root, self.card())

    def test_runtime_changes_need_explicit_impact_and_cards(self):
        self.card()
        items = {"demo": self.entry}
        with self.assertRaises(f.CatalogError):
            f.check_change(self.root, ["crates/demo.rs"], items)
        note = self.note("updated", ["demo"])
        with self.assertRaises(f.CatalogError):
            f.check_change(self.root, ["crates/demo.rs", note], items)
        self.assertEqual(f.check_change(self.root, ["crates/demo.rs", note, f.CATALOG + "demo.json"], items), "DECLARED_UPDATED")

    def test_no_impact_is_allowed_but_cannot_cover_changed_card(self):
        note = self.note("none", [])
        self.assertEqual(f.check_change(self.root, ["crates/demo.rs", note], {}), "DECLARED_NO_FEATURE_IMPACT")
        with self.assertRaises(f.CatalogError):
            f.check_change(self.root, [f.CATALOG + "demo.json", note], {})
        self.assertEqual(f.check_change(self.root, ["tests/helper.py"], {}), "NO_PRODUCT_OR_FEATURE_CHANGE")

    def test_renamed_or_deleted_product_paths_still_require_note(self):
        with self.assertRaises(f.CatalogError):
            f.check_change(self.root, ["crates/old.rs", "docs/old.rs"], {})

    def test_schema_rejects_escape_and_duplicate_scope(self):
        self.entry["code_refs"] = ["../secret"]
        with self.assertRaises(f.CatalogError):
            f.validate_entry(self.root, self.card())
        self.entry["code_refs"] = ["crates/demo.rs"]
        self.entry["verification"] *= 2
        with self.assertRaises(f.CatalogError):
            f.validate_entry(self.root, self.card())

    def test_unmerged_card_can_link_source_without_merging_product(self):
        url = "https://github.com/lly8666/wbd-next/blob/" + "a" * 40 + "/crates/new.rs"
        self.entry["code_refs"] = [url]
        f.validate_entry(self.root, self.card())
        self.entry["code_refs"] = [url.replace("a" * 40, "main")]
        with self.assertRaises(f.CatalogError):
            f.validate_entry(self.root, self.card())

    def test_complete_inventory_requires_reviewed_source(self):
        self.card()
        self.state.update(status="COMPLETE_FOR_SCOPE", gaps=[], review_ref="docs/decision.md")
        self.write(f.STATE, self.state)
        with self.assertRaises(f.CatalogError):
            f.read_catalog(self.root)
        self.state["inventory_source"] = "b" * 40
        self.write(f.STATE, self.state)
        f.read_catalog(self.root)

    def test_push_and_branch_bootstrap_select_immutable_base(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        for key, value in (("user.name", "Test"), ("user.email", "test@example.invalid")):
            f.git(self.root, "config", key, value)
        (self.root / f.STATE).unlink()
        f.git(self.root, "add", ".")
        f.git(self.root, "commit", "-qm", "base")
        base = f.git(self.root, "rev-parse", "HEAD")
        # Deliberately keep unrelated baseline metadata: it cannot skip code.
        self.write(f.STATE, self.state)
        f.git(self.root, "add", ".")
        f.git(self.root, "commit", "-qm", "install gate")
        self.assertEqual(f.select_base(self.root, self.state, "0" * 40), base)
        self.write("crates/demo.rs", "changed")
        f.git(self.root, "add", ".")
        f.git(self.root, "commit", "-qm", "work")
        self.assertEqual(f.select_base(self.root, self.state, base), base)

    def test_workflow_has_user_requested_branches_and_keeps_role_audit(self):
        root = Path(__file__).resolve().parents[1]
        workflow = yaml.load((root / ".github/workflows/governance.yml").read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(workflow["on"]["push"]["branches"], ["main", "work/**", "experiment/**"])
        self.assertNotIn("if", workflow["jobs"]["feature-catalog"])
        self.assertIn("startsWith(github.ref_name, 'work/')", workflow["jobs"]["governance"]["if"])
        self.assertNotIn("experiment", workflow["jobs"]["governance"]["if"])


if __name__ == "__main__":
    unittest.main()
