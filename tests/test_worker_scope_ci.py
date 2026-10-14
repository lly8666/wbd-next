"""R0/G2 identity tests: Green M0 tests never attest to M1 scope."""
import unittest
from tools import worker_scope_ci as w
from tools import governance as g

def roles():
    return {"schema_version":1,"reservation_revision":2,"roles":[
       {"id":"M0","state":"active","branch":"main","global_writer":True,
        "assignment_epoch":1,"allowed_paths":["*"],"owned_semantics":["integration"],
        "cursor":".governance/workstreams/M0/cursor.json",
        "prompt":"docs/prompts/M0.md","goal":"integrate","done_when":"done"},
       {"id":"M1","state":"active","branch":"work/m1-r1-runtime","global_writer":False,
        "assignment_epoch":1,
        "allowed_paths":["crates/wbd-engine/src/runtime/",".governance/workstreams/M1/cursor.json"],
        "owned_semantics":["runtime_owner"],
        "cursor":".governance/workstreams/M1/cursor.json",
        "prompt":"docs/prompts/M1.md","goal":"runtime","done_when":"done"}]}
class WorkerRoleTests(unittest.TestCase):
    def test_worker_ref_never_aliases_m0(self):
        self.assertEqual(w.resolve_role(roles(),"work/m1-r1-runtime")["id"],"M1")
        self.assertEqual(w.resolve_role(roles(),"main")["id"],"M0")
    def test_wrong_declared_role_ref_rejected(self):
        for ref,declared in [
            ("work/m1-r1-runtime","M0"),("main","M1"),
            ("work/attacker","M1"),("refs/pull/1/merge","M0")]:
            with self.assertRaises(g.ContractError):
                w.resolve_role(roles(),ref,declared)
    def test_worker_substantive_scope_and_individual_commits(self):
        role=w.resolve_role(roles(),"work/m1-r1-runtime")
        self.assertEqual(w.verify_worker_commits(role,[{
            "parents":1,"is_main_ancestor":True,"paths":[".github/workflows/governance.yml"]},
            {"parents":1,"is_main_ancestor":False,"paths":["crates/wbd-engine/src/runtime/owner.rs"]},
            {"parents":1,"is_main_ancestor":False,
             "paths":[".governance/workstreams/M1/cursor.json"]}
        ]),2)
    def test_worker_cannot_modify_root_other_worker_or_ci(self):
        role=w.resolve_role(roles(),"work/m1-r1-runtime")
        for bad in ["Cargo.toml","crates/wbd-codec/src/lib.rs",
                    ".governance/workstreams/M2/cursor.json",
                    ".github/workflows/governance.yml","tools/governance.py"]:
            with self.assertRaises(g.ContractError):
                w.verify_worker_commits(role,[{"parents":1,"is_main_ancestor":False,"paths":[bad]}])
    def test_merge_and_indeterminate_origin_fail_closed(self):
        role=w.resolve_role(roles(),"work/m1-r1-runtime")
        for edge in [
            {"parents":2,"is_main_ancestor":False,"paths":["crates/wbd-engine/src/runtime/a.rs"]},
            {"parents":1,"paths":["crates/wbd-engine/src/runtime/a.rs"]}]:
            with self.assertRaises(g.ContractError):
                w.verify_worker_commits(role,[edge])

    def test_one_m0_reviewed_m3_main_sync_preserves_worker_scope(self):
        role=dict(roles()["roles"][1])
        role["id"]="M3"
        role["allowed_paths"]=["crates/wbd-codec/", "docs/evidence/M3/",
                                ".governance/workstreams/M3/cursor.json"]
        merge={"parents":2,"is_main_ancestor":False,
               "first_parent":w.M3_APPROVED_PRE_SYNC_HEAD,
               "approved_main_sync":True,
               "paths":["Cargo.lock"], # Conventional merge first-parent delta is NOT authority.
               "sync_paths":["crates/wbd-codec/src/path_budget.rs",
                             ".governance/workstreams/M3/cursor.json"]}
        self.assertEqual(w.verify_worker_commits(role,[merge]),1)
        for mutation in [
            {"approved_main_sync":False},
            {"first_parent":"f"*40},
            {"sync_paths":["Cargo.lock"]},
            {"sync_paths":["crates/wbd-codec/Cargo.toml"]},
            {"sync_paths":["crates/wbd-engine/src/lib.rs"]},
            {"sync_paths":[]},
        ]:
            with self.subTest(mutation=mutation), self.assertRaises(g.ContractError):
                w.verify_worker_commits(role,[dict(merge,**mutation)])
        with self.assertRaises(g.ContractError):
            w.verify_worker_commits(roles()["roles"][1],[merge])

if __name__=="__main__": unittest.main()
