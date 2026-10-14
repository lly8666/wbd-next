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

    def test_m3_main_sync_remote_tree_and_root_pins(self):
        main_parent = "b" * 40
        control = "c" * 40
        proposed = "d" * 40
        class Api:
            def __init__(self):
                self.path="crates/wbd-codec/src/path_budget.rs"
                self.lock_status="ahead"
                self.first_parent=w.M3_APPROVED_PRE_SYNC_HEAD
                self.total=8
            def get(self, endpoint):
                if endpoint.startswith("commits/"):
                    return {"parents":[{"sha":self.first_parent},{"sha":main_parent}]}
                if endpoint.startswith("compare/"):
                    query=endpoint.partition("?")[0]
                    if query=="compare/"+main_parent+"..."+control:
                        return {"status":"ahead"}
                    if query=="compare/"+w.M0_CRYPTO_LOCK_SOURCE+"..."+main_parent:
                        return {"status":self.lock_status}
                    if query=="compare/"+main_parent+"..."+proposed:
                        return {"status":"ahead","total_commits":self.total,
                                "commits":[{} for _ in range(self.total)],
                                "files":[{"filename":self.path}]}
                raise AssertionError("unexpected "+endpoint)
        role=dict(roles()["roles"][1])
        role["id"]="M3"
        role["allowed_paths"]=["crates/wbd-codec/"]
        self.assertEqual(w.review_m3_main_sync(Api(),role,proposed,control),
                         ["crates/wbd-codec/src/path_budget.rs"])
        for field, value in [
            ("path","Cargo.lock"),
            ("path","crates/wbd-codec/Cargo.toml"),
            ("path",".github/workflows/governance.yml"),
            ("lock_status","diverged"),
            ("first_parent","e"*40),
            ("total",13)
        ]:
            api=Api()
            setattr(api,field,value)
            with self.subTest(field=field), self.assertRaises(g.ContractError):
                w.review_m3_main_sync(api,role,proposed,control)

    def test_one_m0_reviewed_m2_merge_scope_and_role_rejects(self):
        role=dict(roles()["roles"][1])
        role["id"]="M2"
        role["allowed_paths"]=[
            "crates/wbd-recovery/","docs/devlog/M2/","docs/evidence/M2/",
            ".governance/workstreams/M2/cursor.json",
        ]
        merge={"parents":2,"is_main_ancestor":False,
               "first_parent":w.M2_APPROVED_PRE_SYNC_HEAD,
               "approved_main_sync":True,
               "paths":["Cargo.toml"], # first-parent merge diff is not authority
               "sync_paths":["docs/evidence/M2/R2-M2-RECEIPT-001.json",
                             ".governance/workstreams/M2/cursor.json"]}
        self.assertEqual(w.verify_worker_commits(role,[merge]),1)
        for mutation in [
            {"approved_main_sync":False},
            {"first_parent":"f"*40},
            {"sync_paths":[]},
            {"sync_paths":["Cargo.lock"]},
            {"sync_paths":["Cargo.toml"]},
            {"sync_paths":["crates/wbd-recovery/Cargo.toml"]},
            {"sync_paths":["crates/wbd-codec/src/record_crypto.rs"]},
            {"sync_paths":[".governance/workstreams/M1/cursor.json"]},
            {"sync_paths":["docs/evidence/M2/"+str(i) for i in range(17)]},
        ]:
            with self.subTest(mutation=mutation), self.assertRaises(g.ContractError):
                w.verify_worker_commits(role,[dict(merge,**mutation)])
        with self.assertRaises(g.ContractError):
            w.verify_worker_commits(roles()["roles"][1],[merge])

    def test_m2_main_sync_remote_ancestry_and_changed_tree(self):
        main_parent = "b"*40
        control = "c"*40
        proposal = "d"*40
        class Api:
            def __init__(self):
                self.file="docs/evidence/M2/R2-M2-RECEIPT-001.json"
                self.expected_first=w.M2_APPROVED_PRE_SYNC_HEAD
                self.ingress_status="ahead"
                self.main_status="ahead"
                self.commits=5
                self.old_path=None
            def get(self, endpoint):
                if endpoint.startswith("commits/"):
                    return {"parents":[{"sha":self.expected_first},
                                       {"sha":main_parent}]}
                if endpoint.startswith("compare/"):
                    query=endpoint.partition("?")[0]
                    if query=="compare/"+main_parent+"..."+control:
                        return {"status":self.main_status}
                    if query=="compare/"+w.M0_M2_INGRESS_SOURCE+"..."+main_parent:
                        return {"status":self.ingress_status}
                    if query=="compare/"+main_parent+"..."+proposal:
                        return {"status":"ahead","total_commits":self.commits,
                                "commits":[{} for _ in range(self.commits)],
                                "files":[{"filename":self.file,
                                          "previous_filename":self.old_path}]}
                raise AssertionError("unexpected endpoint "+endpoint)
        role=dict(roles()["roles"][1])
        role["id"]="M2"
        role["allowed_paths"]=["docs/evidence/M2/"]
        self.assertEqual(w.review_m2_main_sync(Api(),role,proposal,control),
                         ["docs/evidence/M2/R2-M2-RECEIPT-001.json"])
        for field,value in [
            ("expected_first","e"*40),
            ("ingress_status","diverged"),
            ("main_status","behind"),
            ("commits",13),
            ("file","Cargo.lock"),
            ("file","crates/wbd-recovery/Cargo.toml"),
            ("file","tools/worker_scope_ci.py"),
            ("old_path","crates/wbd-engine/src/lib.rs"),
        ]:
            api=Api()
            setattr(api,field,value)
            with self.subTest(field=field),self.assertRaises(g.ContractError):
                w.review_m2_main_sync(api,role,proposal,control)

if __name__=="__main__": unittest.main()
