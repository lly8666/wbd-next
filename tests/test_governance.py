"""Recovery drills: run in Actions, with no network or production side effects."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools import governance as g

ROOT = Path(__file__).resolve().parents[1]
A, B = "a" * 40, "b" * 40


def registry():
    return json.loads((ROOT / ".governance/registry.json").read_text(encoding="utf-8"))


def cursor():
    value = json.loads((ROOT / ".governance/workstreams/M0/cursor.json").read_text(encoding="utf-8"))
    value.update(checkpoint_sha=A, sequence=1, progress="in_progress", unverified=True,
                 last_tested_source=None, evidence_refs=[], open_requests=[],
                 partial_summary="Fixture: product has not been tested.")
    return value


def request():
    return {"schema_version": 1, "request_id": "M0-drill-001", "role_id": "M0", "task_id": "GOV-001",
            "source_sha": A, "harness_sha": B, "config_sha256": "c" * 64,
            "kind": "performance", "scenario": "one-predeclared-waveform", "seed": 7,
            "workflow": ".github/workflows/measure.yml", "samples": 1, "measurement_jobs": 1,
            "status": "DISPATCHED", "supersedes_request": None, "assignment_epoch": 1,
            "reservation_revision": 1, "dispatch_ref": "qualification/M0-drill-001"}


def receipt_and_run():
    receipt = dict(request(), result="PASS", run_id=123, run_attempt=1, artifact_verified=True)
    run = {"id": 123, "run_attempt": 1, "head_sha": B, "path": request()["workflow"],
           "status": "completed", "conclusion": "success", "display_title": "M0|M0-drill-001|measure"}
    return receipt, run


class ContinuityDrills(unittest.TestCase):
    def setUp(self):
        self.role = registry()["roles"][0]
        self.cursor = cursor()

    def classify(self, paths=None, **kwargs):
        commits = [] if paths is None else [{"sha": B, "paths": paths, "parents": 1}]
        return g.classify_continuity(self.role, 1, self.cursor, commits, **kwargs)["state"]

    def test_cursor_only_h_is_clean_but_unverified(self):
        self.assertEqual(self.classify([self.role["cursor"]], previous_sequence=0), "CLEAN")
        self.assertTrue(self.cursor["unverified"])

    def test_substantive_work_without_h_needs_recovery(self):
        self.assertEqual(self.classify(["docs/new-decision.md"]), "RECOVERY_REQUIRED")

    def test_bootstrap_not_clean(self):
        self.cursor.update(checkpoint_sha=None, sequence=0)
        self.assertEqual(self.classify(), "RECOVERY_REQUIRED")

    def test_sequence_rewind_blocked(self):
        self.assertEqual(self.classify([self.role["cursor"]], previous_sequence=1), "BLOCKED")

    def test_old_epoch_blocked(self):
        self.role["assignment_epoch"] = 2
        self.assertEqual(self.classify(), "BLOCKED")

    def test_old_reservation_blocked(self):
        self.cursor["reservation_revision"] = 0
        self.assertEqual(self.classify(), "BLOCKED")

    def test_unassigned_role_blocked(self):
        self.role["state"] = "reserved"
        self.assertEqual(self.classify(), "BLOCKED")

    def test_divergent_checkpoint_blocked(self):
        self.assertEqual(self.classify(ancestry=False), "BLOCKED")

    def test_incomplete_query_blocked(self):
        self.assertEqual(self.classify(complete=False), "BLOCKED")

    def test_commit_bound_blocked(self):
        self.assertEqual(self.classify([self.role["cursor"]], max_commits=0), "BLOCKED")

    def test_path_bound_blocked(self):
        self.assertEqual(self.classify(["one", "two"], max_paths=1), "BLOCKED")

    def test_scope_escape_blocked(self):
        self.role["allowed_paths"] = ["modules/runtime/"]
        self.assertEqual(self.classify(["modules/runtime-other/a.rs"]), "BLOCKED")

    def test_merge_needs_explicit_review(self):
        result = g.classify_continuity(self.role, 1, self.cursor,
                                      [{"sha": B, "paths": [self.role["cursor"]], "parents": 2}])
        self.assertEqual(result["state"], "BLOCKED")

    def test_real_git_change_then_revert_is_not_clean(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)

            def git(*args):
                return subprocess.check_output(["git", "-C", folder, *args], text=True, stderr=subprocess.DEVNULL).strip()

            def commit(message):
                git("add", ".")
                git("commit", "-qm", message)
                return git("rev-parse", "HEAD")

            git("init", "-q")
            git("config", "user.name", "Recovery fixture")
            git("config", "user.email", "fixture@example.invalid")
            cp = root / self.role["cursor"]
            cp.parent.mkdir(parents=True)
            cp.write_text("bootstrap", encoding="utf-8")
            (root / "decision.txt").write_text("original", encoding="utf-8")
            substantive = commit("S")
            cp.write_text("H acknowledges S", encoding="utf-8")
            commit("H")
            (root / "decision.txt").write_text("interrupted change", encoding="utf-8")
            commit("interrupted S")
            (root / "decision.txt").write_text("original", encoding="utf-8")
            commit("revert content")
            self.assertEqual(git("diff", "--name-only", substantive, "HEAD"), self.role["cursor"])
            edges = [{"sha": sha, "parents": 1,
                      "paths": git("diff-tree", "--no-commit-id", "--name-only", "-r", sha).splitlines()}
                     for sha in git("rev-list", "--reverse", f"{substantive}..HEAD").splitlines()]
            self.cursor["checkpoint_sha"] = substantive
            result = g.classify_continuity(self.role, 1, self.cursor, edges, previous_sequence=0)
            self.assertEqual(result["state"], "RECOVERY_REQUIRED")
            self.assertEqual(len(result["commits"]), 2)


class EvidenceDrills(unittest.TestCase):
    def test_exact_receipt_accepted(self):
        self.assertTrue(g.verify_receipt(request(), *receipt_and_run()))

    def test_wrong_provenance_rejected(self):
        for key, wrong in (("source_sha", B), ("config_sha256", "d" * 64),
                           ("seed", 8), ("role_id", "M1"), ("request_id", "other")):
            with self.subTest(key=key):
                receipt, run = receipt_and_run()
                receipt[key] = wrong
                with self.assertRaises(g.ContractError):
                    g.verify_receipt(request(), receipt, run)

    def test_wrong_run_identity_rejected(self):
        for key, wrong in (("id", 999), ("run_attempt", 2), ("head_sha", A), ("path", "wrong.yml")):
            with self.subTest(key=key):
                receipt, run = receipt_and_run()
                run[key] = wrong
                with self.assertRaises(g.ContractError):
                    g.verify_receipt(request(), receipt, run)

    def test_green_without_artifact_review_not_pass(self):
        receipt, run = receipt_and_run()
        receipt["artifact_verified"] = False
        with self.assertRaises(g.ContractError):
            g.verify_receipt(request(), receipt, run)

    def test_failed_or_unfinished_not_pass(self):
        for status, conclusion in (("in_progress", None), ("completed", "failure"), ("completed", "cancelled")):
            receipt, run = receipt_and_run()
            run.update(status=status, conclusion=conclusion)
            with self.assertRaises(g.ContractError):
                g.verify_receipt(request(), receipt, run)

    def test_performance_matrix_and_serial_ab_rejected(self):
        for key in ("samples", "measurement_jobs"):
            value = request()
            value[key] = 2
            with self.assertRaises(g.ContractError):
                g.validate_request(value)

    def test_existing_request_found_without_dispatch(self):
        _, run = receipt_and_run()
        self.assertEqual(g.discover_request_runs(request(), [run]), [run])

    def test_duplicate_runs_not_cherry_picked(self):
        _, run = receipt_and_run()
        with self.assertRaises(g.ContractError):
            g.discover_request_runs(request(), [run, dict(run, id=124)])

    def test_unrelated_workflow_does_not_claim_request(self):
        _, run = receipt_and_run()
        run["path"] = ".github/workflows/unrelated.yml"
        self.assertEqual(g.discover_request_runs(request(), [run]), [])

    def test_incomplete_search_never_authorizes_redispatch(self):
        with self.assertRaises(g.ContractError):
            g.discover_request_runs(request(), [], complete=False)


class RepositoryDrills(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".git", "out", "__pycache__"))

    def mutate(self, path, fn):
        target = self.root / path
        value = json.loads(target.read_text(encoding="utf-8"))
        fn(value)
        target.write_text(json.dumps(value), encoding="utf-8")

    def test_current_repository_structure(self):
        self.assertEqual(g.validate_repo(self.root)["product"], "NOT_RUN")

    def test_context_growth_rejected(self):
        with (self.root / "PROJECT_CHARTER.md").open("a", encoding="utf-8") as stream:
            stream.write("X" * 32768)
        with self.assertRaises(g.ContractError):
            g.validate_repo(self.root)

    def test_missing_referenced_history_rejected(self):
        value = json.loads((self.root / ".governance/workstreams/M0/cursor.json").read_text(encoding="utf-8"))
        (self.root / value["context_refs"][0]).unlink()
        with self.assertRaises(g.ContractError):
            g.validate_repo(self.root)

    def test_unassigned_product_code_rejected(self):
        (self.root / "src").mkdir()
        with self.assertRaises(g.ContractError):
            g.validate_repo(self.root)

    def test_verified_claim_without_evidence_rejected(self):
        self.mutate(".governance/workstreams/M0/cursor.json",
                    lambda value: value.update(unverified=False, last_tested_source=A, evidence_refs=[]))
        with self.assertRaises(g.ContractError):
            g.validate_repo(self.root)

    def test_worker_cannot_claim_control_plane(self):
        value = registry()
        value["roles"][1]["allowed_paths"] = [".governance/"]
        with self.assertRaises(g.ContractError):
            g.validate_registry(value)

    def test_overlapping_worker_scopes_rejected(self):
        value = registry()
        for role in value["roles"][1:3]:
            role.update(state="active", branch=f"work/{role['id']}", assignment_epoch=1,
                        allowed_paths=["modules/shared/"], owned_semantics=[role["id"]],
                        cursor=f".governance/workstreams/{role['id']}/cursor.json")
        with self.assertRaises(g.ContractError):
            g.validate_registry(value)

    def test_duplicate_semantic_owner_rejected(self):
        value = registry()
        role = value["roles"][1]
        role.update(state="active", branch="work/M1", assignment_epoch=1,
                    allowed_paths=["modules/runtime/"], owned_semantics=["governance"],
                    cursor=".governance/workstreams/M1/cursor.json")
        with self.assertRaises(g.ContractError):
            g.validate_registry(value)


class PaginationDrills(unittest.TestCase):
    def test_second_page_and_rename_are_audited(self):
        class FakeAPI:
            def get(self, query):
                files = ([{"filename": f"path/{i}"} for i in range(100)] if query.endswith("&page=1") else
                         [{"filename": "allowed/new", "previous_filename": "protected/old"}])
                return {"files": files, "parents": [{}]}
        result = g.commit_delta(FakeAPI(), A, 256)
        self.assertIn("protected/old", result["paths"])
        self.assertEqual(len(result["paths"]), 102)

    def test_excessive_files_fail_closed(self):
        class FakeAPI:
            def get(self, query):
                return {"files": [{"filename": f"path/{i}"} for i in range(100)], "parents": [{}]}
        with self.assertRaises(g.ContractError):
            g.commit_delta(FakeAPI(), A, 256)


if __name__ == "__main__":
    unittest.main()
