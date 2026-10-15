"""M2-008 M0-owned immutable-source third mirror: no general root write."""
import unittest
from tools import worker_scope_ci as w
from tools import governance as g

P=w.M2_G2_REFRESH_PATH
PARENT=w.M2_G2_THIRD_REFRESH_PARENT
SRC="a"*40
BLOB="b"*40
SHA="d"*40
MAIN="c"*40
ROLE={"id":"M2","allowed_paths":["crates/wbd-codec/","docs/devlog/M2/",
 "docs/evidence/M2/",".governance/workstreams/M2/cursor.json"]}

class API:
    def __init__(self,parent=PARENT,paths=None,blob=BLOB,approved=BLOB,origin=SRC,
                 decision=None,status="ahead",parents=1):
        self.parent=parent;self.paths=[P] if paths is None else paths
        self.blob=blob;self.approved=approved;self.origin=origin
        self.status=status;self.parents=parents
        self.decision=decision or {"schema_version":1,"role_id":"M2",
            "parent_sha":PARENT,"path":P,"status":"APPROVED_ONCE",
            "m0_reviewed_source_sha":origin,"approved_git_blob_sha":approved}
    def file(self,path,ref):
        if path!=w.M2_G2_THIRD_DECISION or ref!=MAIN:raise AssertionError((path,ref))
        return self.decision
    def get(self,path):
        if path.startswith("commits/"):
            return {"parents":[{"sha":self.parent}]*self.parents,
                    "files":[{"filename":p} for p in self.paths]}
        if path.startswith("compare/"):return {"status":self.status}
        if path.startswith("contents/"):
            return {"type":"file","sha":self.approved if "ref="+self.origin in path else self.blob}
        raise AssertionError(path)

def edge(change=None):
    d={"sha":SHA,"is_main_ancestor":False,"parents":1,"paths":[P],
       "approved_m2_g2_tool_refresh_v3":True,"first_parent":PARENT,"sync_paths":[P]}
    return dict(d,**(change or {}))

class ThirdM2OneShot(unittest.TestCase):
    def test_exact_reviewed_main_blob_single_parent(self):
        self.assertTrue(w.review_m2_g2_third_single_file_refresh(
            API(),ROLE,SHA,MAIN)["approved_m2_g2_tool_refresh_v3"])
        self.assertEqual(w.verify_worker_commits(ROLE,[edge()]),1)
    def test_wrong_parent(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_third_single_file_refresh(API(parent="f"*40),ROLE,SHA,MAIN)
    def test_extra_root_path(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_third_single_file_refresh(API(paths=[P,"Cargo.lock"]),ROLE,SHA,MAIN)
    def test_wrong_checker_blob(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_third_single_file_refresh(API(blob="f"*40),ROLE,SHA,MAIN)
    def test_absent_invalid_main_decision(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_third_single_file_refresh(API(decision={"schema_version":1}),ROLE,SHA,MAIN)
    def test_forbidden_main_control_divergence(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_third_single_file_refresh(API(status="diverged"),ROLE,SHA,MAIN)
    def test_multi_parent_forbidden(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_third_single_file_refresh(API(parents=2),ROLE,SHA,MAIN)
    def test_forged_role_forbidden(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_third_single_file_refresh(API(),{**ROLE,"id":"M1"},SHA,MAIN)
    def test_forged_scope_edge_rejected(self):
        with self.assertRaises(g.ContractError):
            w.verify_worker_commits(ROLE,[edge({"paths":["tools/worker_scope_ci.py","Cargo.lock"]})])
    def test_unapproved_later_root_edit_rejected(self):
        with self.assertRaises(g.ContractError):
            w.verify_worker_commits(ROLE,[{"sha":"f"*40,"is_main_ancestor":False,
                                          "parents":1,"paths":[P]}])
if __name__=="__main__":unittest.main()
