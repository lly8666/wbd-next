import copy
import unittest
from tools import governance as g
from tools import scope_audit as s
from tests.test_worker_scope_ci import roles

A, B, C, D = (n * 40 for n in "abcd")


class API:
    def __init__(self):
        self.registry = roles()
        self.final_registry = copy.deepcopy(self.registry)
        self.role = self.registry["roles"][1]
        self.checkpoint = {"source_sha": A, "authority": s.authority(self.registry, self.role),
                           "evidence_ref": "approved-prior-receipt"}
        self.paths = ["crates/wbd-engine/src/runtime/new.rs"]
        self.parents = 1
        self.ids = [B]
        self.total = 1
        self.current = B
        self.final_control = C
        self.source_removed = False
    def head(self, branch):
        return self.final_control if branch == "main" else self.current
    def file(self, path, ref):
        if path.endswith("registry.json"):
            return self.registry if ref == C else self.final_registry
        if path.endswith("policy.json"):
            return {"max_delta_commits": 64, "max_paths_per_commit": 256, "max_total_delta_paths": 1024}
        if path.endswith("scope-checkpoints.json"):
            return {"schema_version": 1, "roles": {"M1": self.checkpoint}}
        if path.endswith("cursor.json"):
            return {"schema_version": 1, "role_id": "M1", "branch": self.role["branch"],
                    "assignment_epoch": 1, "reservation_revision": 2, "sequence": 1000,
                    "checkpoint_sha": A, "progress": "partial", "unverified": True,
                    "current_task": "task", "why_now": "because", "done_when": "done",
                    "next_action": "next", "partial_summary": "partial", "last_tested_source": None,
                    "evidence_refs": [], "context_refs": [], "open_requests": [], "task_id": "test"}
        raise AssertionError(path)
    def get(self, endpoint):
        if endpoint == f"compare/{A}...{B}?per_page=65":
            return {"status": "ahead", "total_commits": self.total,
                    "commits": [{"sha": n} for n in self.ids]}
        if endpoint.startswith("commits/"):
            return {"parents": [{}] * self.parents, "files": [{"filename": p} for p in self.paths]}
        if endpoint.startswith("compare/"):
            before, after = endpoint.split("/")[1].split("?")[0].split("...")
            if self.source_removed and before == B and after == self.current:
                return {"status": "diverged"}
            return {"status": "identical" if before == after else
                    "ahead" if after == self.current else "diverged"}
        raise AssertionError(endpoint)


class IncrementalScope(unittest.TestCase):
    def audit(self, api):
        return s.audit(api, api.role["branch"], B, C)
    def test_lifetime_history_irrelevant_only_new_delta(self):
        result = self.audit(API())
        self.assertEqual(len(result["delta_commits"]), 1)
        self.assertEqual(result["cursor_sequence"], 1000)
        self.assertEqual(result["product"], "NOT_RUN")
    def test_reverted_illegal_commit_still_fails(self):
        api = API(); api.paths = ["Cargo.lock"]; api.ids = [B, D]; api.total = 2
        with self.assertRaises(g.ContractError): self.audit(api)
    def test_stale_checkpoint_or_changed_permission_fails(self):
        for action in (lambda a: a.checkpoint.update(authority={}),
                       lambda a: a.final_registry["roles"][1].update(assignment_epoch=2)):
            api = API(); api.final_control = D; action(api)
            with self.assertRaises(g.ContractError): self.audit(api)
    def test_main_prose_and_worker_progress_do_not_invalidate_source(self):
        api = API(); api.final_control = D; api.current = D
        api.final_registry["roles"][1]["goal"] = "new task prose"
        result = self.audit(api)
        self.assertEqual(result["result"], "ROLE_SCOPE_PASS")
        self.assertFalse(result["is_current_head"])
    def test_removed_source_unreviewed_merge_and_incomplete_page_fail(self):
        for field, value in (("source_removed", True), ("parents", 2), ("total", 2), ("total", 65)):
            api = API(); setattr(api, field, value)
            with self.subTest(field=field), self.assertRaises(g.ContractError): self.audit(api)
    def test_duplicate_and_negative_count_fail(self):
        for response in ({"status": "ahead", "total_commits": 2, "commits": [{"sha": B}] * 2},
                         {"status": "ahead", "total_commits": -1, "commits": []}):
            with self.assertRaises(g.ContractError): s.complete_delta(response, 64)

    def test_coordination_markdown_is_not_dispatch_json(self):
        class Notes:
            def get(self, endpoint):
                self.assert_endpoint = endpoint
                return {"type": "file"}
            def file(self, *args):
                raise AssertionError("Markdown must not be parsed as a JSON dispatch intent")
        notes = Notes()
        s.check_role_metadata(notes, {"id": "M1"}, B,
                              {"evidence_refs": [], "context_refs": [],
                               "open_requests": [".governance/workstreams/M1/requests/dependency.md"]})
        self.assertIn("dependency.md", notes.assert_endpoint)
