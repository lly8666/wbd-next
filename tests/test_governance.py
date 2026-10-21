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
# Governance revision is an assignment property; tests must not freeze epoch1 rev1.
REVISION = json.loads((ROOT / ".governance/registry.json").read_text(encoding="utf-8"))["reservation_revision"]


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
            "reservation_revision": REVISION, "dispatch_ref": "qualification/M0-drill-001"}


def receipt_and_run():
    receipt = dict(request(), result="PASS", run_id=123, run_attempt=1, artifact_verified=True)
    run = {"id": 123, "run_attempt": 1, "head_sha": B, "path": request()["workflow"],
           "status": "completed", "conclusion": "success", "display_title": "M0|M0-drill-001|measure"}
    return receipt, run


class LiveGitHubReadFailureDrills(unittest.TestCase):
    """No external GitHub call. 403 permission must never become PASS."""

    def test_rate_limit_403_retries_exact_authenticated_endpoint(self):
        import io
        import urllib.error
        from unittest import mock
        error = urllib.error.HTTPError(
            "https://api.github.com/repos/example/repo/git/ref/heads/main",
            403, "rate limited",
            {"X-RateLimit-Remaining": "0", "Retry-After": "1"},
            io.BytesIO(b'{"message":"API rate limit exceeded"}'))
        success = io.BytesIO(b'{"object":{"sha":"' + b"a" * 40 + b'"}}')
        with mock.patch("tools.governance.urllib.request.urlopen",
                        side_effect=[error, success]) as open_url, \
             mock.patch("tools.governance.time.sleep") as sleep:
            value = g.GitHub("example/repo").head("main")
        self.assertEqual(value, "a" * 40)
        self.assertEqual(open_url.call_count, 2)
        sleep.assert_called_once_with(1)
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url,
                         "https://api.github.com/repos/example/repo/git/ref/heads/main")

    def test_permission_403_fails_without_retry_or_unauthenticated_fallback(self):
        import io
        import urllib.error
        from unittest import mock
        error = urllib.error.HTTPError(
            "https://api.github.com/repos/example/repo/git/ref/heads/main",
            403, "forbidden", {"X-RateLimit-Remaining": "4999"},
            io.BytesIO(b'{"message":"Resource not accessible by integration"}'))
        with mock.patch("tools.governance.urllib.request.urlopen",
                        side_effect=error) as open_url, \
             mock.patch("tools.governance.time.sleep") as sleep:
            with self.assertRaisesRegex(g.ContractError, "permission_denied"):
                g.GitHub("example/repo").head("main")
        open_url.assert_called_once()
        sleep.assert_not_called()


class ContinuityDrills(unittest.TestCase):
    def setUp(self):
        self.role = registry()["roles"][0]
        self.cursor = cursor()

    def classify(self, paths=None, **kwargs):
        commits = [] if paths is None else [{"sha": B, "paths": paths, "parents": 1}]
        return g.classify_continuity(self.role, REVISION, self.cursor, commits, **kwargs)["state"]

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
        result = g.classify_continuity(self.role, REVISION, self.cursor,
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
            result = g.classify_continuity(self.role, REVISION, self.cursor, edges, previous_sequence=0)
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

    def test_undeclared_multi_sample_and_multi_job_rejected(self):
        for key in ("samples", "measurement_jobs"):
            value = request()
            value[key] = 2
            with self.assertRaises(g.ContractError):
                g.validate_request(value)

    def paired(self, order="AB"):
        value = request()
        source = {"A": B, "B": A}
        value.update(mode="paired_ab", samples=2, legs=[
            {"label": label, "source_sha": source[label], "build_manifest_sha256": label.lower()*64}
            for label in order])
        receipt, run = receipt_and_run()
        receipt.update(mode="paired_ab", samples=2, legs=[
            dict(leg, job_id=321, config_sha256=value["config_sha256"], scenario=value["scenario"],
                 seed=value["seed"], harness_sha=value["harness_sha"], result="PASS",
                 start_monotonic_ns=i*200, end_monotonic_ns=i*200+100)
            for i, leg in enumerate(value["legs"])])
        jobs = [{"id": 321, "run_id": 123, "run_attempt": 1, "status": "completed", "conclusion": "success"}]
        return value, receipt, run, jobs

    def test_declared_ab_and_ba_same_job_accepted(self):
        for order in ("AB", "BA"):
            self.assertTrue(g.verify_receipt(*self.paired(order)))

    def test_four_leg_abba_and_baab_source_locked_and_nonoverlap(self):
        for order in ("ABBA", "BAAB"):
            value,receipt,run,jobs=self.paired()
            legs={leg["label"]:leg for leg in value["legs"]}
            value.update(mode="paired_abba", samples=4,
                         legs=[dict(legs[label]) for label in order])
            receipt.update(mode="paired_abba", samples=4,
                legs=[dict(leg,job_id=321,config_sha256=value["config_sha256"],
                           scenario=value["scenario"],seed=value["seed"],
                           harness_sha=value["harness_sha"],result="PASS",
                           start_monotonic_ns=i*200,end_monotonic_ns=i*200+100)
                      for i,leg in enumerate(value["legs"])])
            self.assertTrue(g.verify_receipt(value,receipt,run,jobs))
            for tamper in ("status","source","config","overlap","job","missing","label"):
                v=dict(value,legs=[dict(x) for x in value["legs"]])
                e=dict(receipt,legs=[dict(x) for x in receipt["legs"]])
                if tamper=="status":e["legs"][3]["result"]="NOT_RUN"
                if tamper=="source":v["legs"][3]["source_sha"]="f"*40
                if tamper=="config":e["legs"][2]["config_sha256"]="f"*64
                if tamper=="overlap":e["legs"][2]["start_monotonic_ns"]=100
                if tamper=="job":e["legs"][3]["job_id"]=999
                if tamper=="missing":e["legs"].pop()
                if tamper=="label":
                    v["legs"][1]["label"]=("B" if v["legs"][1]["label"]=="A" else "A")
                with self.subTest(order=order,tamper=tamper),self.assertRaises(g.ContractError):
                    g.verify_receipt(v,e,run,jobs)
        # Four samples cannot pass as 2-leg paired_ab nor undocumented mode.
        v,_,_,_=self.paired()
        v["samples"]=4
        with self.assertRaises(g.ContractError):g.validate_request(v)

    def test_frozen_public_control_is_distinct_from_worker_harness(self):
        value,receipt,run,jobs=self.paired()
        value["workflow"]=".github/workflows/worker-component-validation.yml"
        value["dispatch_ref"]="qualification/worker-ci-v1"
        run["path"]=value["workflow"]+"@refs/heads/qualification/worker-ci-v1"
        run["head_sha"]="d"*40
        receipt["control_sha"]="d"*40
        receipt["dispatch_ref"]=value["dispatch_ref"]
        self.assertTrue(g.verify_receipt(value,receipt,run,jobs))
        for mutation in (dict(control_sha="f"*40),dict(dispatch_ref="main")):
            with self.assertRaises(g.ContractError):
                g.verify_receipt(value,dict(receipt,**mutation),run,jobs)
        # Native M3 old fixture has genuine ABBA ticks but lacks exact
        # monotonic per-leg windows: INCONCLUSIVE only, never PASS.
        value["mode"]="paired_abba"
        value["samples"]=4
        value["legs"]=[dict(receipt["legs"][0]),
                       dict(receipt["legs"][1]),
                       dict(receipt["legs"][1]),
                       dict(receipt["legs"][0])]
        receipt["mode"]="paired_abba"
        receipt["result"]="INCONCLUSIVE"
        receipt["legs"]=[dict(z,job_id=321,absolute_window="NOT_INSTRUMENTED",
                              result="INCONCLUSIVE",
                              start_monotonic_ns=None,end_monotonic_ns=None)
                         for z in value["legs"]]
        for leg in value["legs"]:
            leg.pop("job_id",None)
            for key in ("config_sha256","scenario","seed","harness_sha","result",
                        "start_monotonic_ns","end_monotonic_ns"):
                leg.pop(key,None)
        self.assertTrue(g.verify_receipt(value,receipt,run,jobs))
        with self.assertRaises(g.ContractError):
            g.verify_receipt(value,dict(receipt,result="PASS"),run,jobs)

    def test_paired_wrong_source_build_config_job_and_overlap_rejected(self):
        for key, wrong in (("source_sha", "e"*40), ("build_manifest_sha256", "e"*64),
                           ("config_sha256", "e"*64), ("job_id", 999), ("start_monotonic_ns", 50),
                           ("result", "NOT_RUN"), ("label", "A")):
            with self.subTest(key=key):
                value, receipt, run, jobs = self.paired()
                receipt["legs"][1][key] = wrong
                with self.assertRaises(g.ContractError):
                    g.verify_receipt(value, receipt, run, jobs)

    def test_paired_requires_actual_job_of_same_attempt(self):
        for jobs in (None, [], [{"id": 321, "run_id": 123, "run_attempt": 2}]):
            value, receipt, run, _ = self.paired()
            with self.assertRaises(g.ContractError):
                g.verify_receipt(value, receipt, run, jobs)

    def test_paired_request_cannot_hide_other_scenarios_or_sources(self):
        value, _, _, _ = self.paired()
        for mutation in (dict(samples=3), dict(measurement_jobs=2), dict(source_sha=B), dict(mode="matrix")):
            with self.assertRaises(g.ContractError):
                g.validate_request(dict(value, **mutation))

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

    def test_main_historical_worker_snapshots_dont_claim_live_rev3_epoch(self):
        # M1/M2/M3 cursors stored on main are archival. Their branch-local
        # cursors must be refreshed before ACTIVE worker commits, rather
        # than M0 silently changing another worker's checkpoint.
        worker = self.root / ".governance/workstreams/M1/cursor.json"
        original = json.loads(worker.read_text(encoding="utf-8"))
        self.assertLessEqual(original["reservation_revision"], REVISION)
        self.assertEqual(g.validate_repo(self.root)["scope"], "governance_structure_only")
        self.mutate(".governance/workstreams/M1/cursor.json",
                    lambda value: value.update(reservation_revision=REVISION+1))
        with self.assertRaisesRegex(g.ContractError, "historical cursor revision"):
            g.validate_repo(self.root)

    def test_live_main_writer_stale_rev_is_always_rejected(self):
        self.mutate(".governance/workstreams/M0/cursor.json",
                    lambda value: value.update(reservation_revision=REVISION-1))
        with self.assertRaisesRegex(g.ContractError, "stale reservation revision"):
            g.validate_repo(self.root)

    def test_historical_worker_role_or_epoch_is_not_relaxed(self):
        self.mutate(".governance/workstreams/M1/cursor.json",
                    lambda value: value.update(assignment_epoch=100))
        with self.assertRaisesRegex(g.ContractError, "stale writer epoch"):
            g.validate_repo(self.root)

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

    def test_product_code_rejected_when_phase_not_started(self):
        # Restore pre-R0 phase in an isolated fixture: the copied Cargo/crates
        # must then be rejected. This prevents the guard from silently weakening
        # when R0 legitimately begins on main.
        self.mutate(".governance/project.json",
                    lambda value: value.update(product_implementation="NOT_STARTED"))
        with self.assertRaisesRegex(g.ContractError, "product development not assigned"):
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
