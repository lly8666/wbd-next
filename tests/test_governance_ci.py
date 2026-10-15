"""Actions-only checks for reduced CI without weakening identity/structure gates."""
import fnmatch
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml
from tools import governance as g

ROOT = Path(__file__).resolve().parents[1]


class GovernanceCiTests(unittest.TestCase):
    def outcomes(self, event):
        return dict(role="success", identity="success", structure="success",
                    drills="success" if event == "workflow_dispatch" else "skipped",
                    model="success" if event == "workflow_dispatch" else "skipped")

    def test_push_does_not_claim_selftests_and_never_skips_mandatory_gates(self):
        good = self.outcomes("push")
        self.assertEqual(g.summarize_checks("push", good)["selftests"], "NOT_RUN")
        self.assertEqual(g.summarize_checks("push", good)["result"], "PASS")
        for key in ("role", "identity", "structure"):
            for outcome in ("failure", "skipped", "cancelled"):
                with self.subTest(key=key, outcome=outcome):
                    self.assertEqual(g.summarize_checks("push", dict(good, **{key: outcome}))["result"], "FAIL")

    def test_manual_selftest_cannot_pass_with_missing_or_failed_drills(self):
        good = self.outcomes("workflow_dispatch")
        self.assertEqual(g.summarize_checks("workflow_dispatch", good)["result"], "PASS")
        for key in ("drills", "model"):
            for outcome in ("failure", "skipped", "cancelled"):
                self.assertEqual(g.summarize_checks("workflow_dispatch", dict(good, **{key: outcome}))["result"], "FAIL")

    def test_incomplete_unknown_event_or_outcome_rejected(self):
        with self.assertRaises(g.ContractError):
            g.summarize_checks("pull_request", self.outcomes("push"))
        with self.assertRaises(g.ContractError):
            g.summarize_checks("push", {})
        with self.assertRaises(g.ContractError):
            g.summarize_checks("push", dict(self.outcomes("push"), role="unknown"))

    def test_receipt_preserves_scope_and_rejects_fabricated_pass(self):
        for event in ("push", "workflow_dispatch"):
            with self.subTest(event=event), tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
                "GITHUB_ACTIONS": "true", "GITHUB_SHA": "a" * 40, "GITHUB_RUN_ID": "1",
                "GITHUB_RUN_ATTEMPT": "2", "GITHUB_EVENT_NAME": event, "WBD_ROLE_ID": "M0",
                "WBD_REQUEST_ID": "", "WBD_REQUEST_REF": "",
            }):
                path = Path(tmp) / "checks.json"
                summary = g.summarize_checks(event, self.outcomes(event))
                path.write_text(json.dumps(summary))
                receipt = g.make_receipt("PASS", tmp)
                self.assertEqual(receipt["scope"], summary["scope"])
                self.assertEqual(receipt["checks"], summary)
                self.assertEqual(receipt["scenario"], "governance-selftest" if event == "workflow_dispatch" else "governance-push-checks")
                summary = g.summarize_checks(event, dict(self.outcomes(event), structure="failure"))
                path.write_text(json.dumps(summary))
                with self.assertRaises(g.ContractError):
                    g.make_receipt("PASS", tmp)
                self.assertEqual(g.make_receipt("FAIL", tmp)["result"], "FAIL")

    def test_push_workflow_keeps_required_gates_and_manual_full_checks(self):
        workflow = yaml.load((ROOT / ".github/workflows/governance.yml").read_text(), Loader=yaml.BaseLoader)
        steps = {step["id"]: step for step in workflow["jobs"]["governance"]["steps"] if "id" in step}
        for key in ("role", "identity", "structure"):
            self.assertNotIn("if", steps[key])
            self.assertNotIn("continue-on-error", steps[key])
        for key in ("drills", "model"):
            self.assertEqual(steps[key]["if"], "github.event_name == 'workflow_dispatch'")
        self.assertEqual(steps["observed"]["if"], "always()")
        self.assertIn("work/**", workflow["on"]["push"]["branches"])

    def test_maintenance_covers_rule_changes_not_ordinary_progress(self):
        workflow = yaml.load((ROOT / ".github/workflows/governance-maintenance.yml").read_text(), Loader=yaml.BaseLoader)
        patterns = workflow["on"]["push"]["paths"]
        for path in ("tools/governance.py", "tests/test_governance_ci.py", ".governance/policy.json",
                     ".governance/native-suites.json", ".governance/scope-checkpoints.json",
                     ".github/workflows/governance.yml", "docs/GOVERNANCE.md", "docs/prompts/M0.md",
                     "docs/architecture/model-inputs.json"):
            self.assertTrue(any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns), path)
        for path in (".governance/project.json", ".governance/registry.json",
                     ".governance/workstreams/M0/cursor.json", ".governance/workstreams/M2/requests/r.json",
                     "docs/evidence/M0/new.json", "docs/devlog/M0/new.md"):
            self.assertFalse(any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns), path)
        scripts = "\n".join(step.get("run", "") for step in workflow["jobs"]["regression"]["steps"])
        for required in ("unittest discover", "tools/check_workflows.py", "tools/cost_model.py", "tools/design_models.py"):
            self.assertIn(required, scripts)
