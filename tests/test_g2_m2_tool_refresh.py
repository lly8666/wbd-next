"""One-time M2 M0-owned checker mirror after worker ancestry limit; fail-closed."""
import unittest
from tools import worker_scope_ci as w
from tools import governance as g

P=w.M2_G2_REFRESH_PATH
PRE=w.M2_G2_REFRESH_PARENT
SHA="d"*40
MAIN="c"*40
BLOB=w.M0_M2_HISTORICAL_TOOL_BLOB
role={"id":"M2","allowed_paths":["crates/wbd-recovery/","docs/devlog/M2/","docs/evidence/M2/",
      ".governance/workstreams/M2/cursor.json",".governance/workstreams/M2/requests/"]}

class API:
    def __init__(self,files=None,parent=PRE,blob=BLOB,mainblob=BLOB,anchor="ahead",parents=1):
        self.files=[P] if files is None else files
        self.parent=parent;self.blob=blob;self.mainblob=mainblob
        self.anchor=anchor;self.parents=parents
    def get(self,path):
        if path.startswith("commits/"):
            return {"parents":[{"sha":self.parent}]*self.parents,
                    "files":[{"filename":p} for p in self.files]}
        if path.startswith("compare/"):
            return {"status":self.anchor}
        if path.startswith("contents/"):
            return {"type":"file","sha":self.mainblob if f"ref={w.M0_M2_HISTORICAL_TOOL_SOURCE}" in path else self.blob}
        raise AssertionError(path)

def edge(extra=None):
    out={"sha":SHA,"is_main_ancestor":False,"parents":1,"paths":[P],
         "approved_m2_g2_tool_refresh":True,"first_parent":PRE,"sync_paths":[P]}
    if extra:out.update(extra)
    return out

class OneTimeM2CheckerRefresh(unittest.TestCase):
    def test_accept_exact_parent_only_main_blob(self):
        r=w.review_m2_g2_single_file_refresh(API(),role,SHA,MAIN)
        self.assertTrue(r["approved_m2_g2_tool_refresh"])
        self.assertEqual(w.verify_worker_commits(role,[edge()]),1)
    def test_reject_pre_unreviewed_tool_edit(self):
        with self.assertRaises(g.ContractError):
            w.verify_worker_commits(role,[edge({"approved_m2_g2_tool_refresh":False})])
    def test_reject_parent_mismatch(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_single_file_refresh(API(parent="a"*40),role,SHA,MAIN)
    def test_reject_extra_tool_or_cargo_path(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_single_file_refresh(API(files=[P,"Cargo.lock"]),role,SHA,MAIN)
    def test_reject_diverged_m0_control(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_single_file_refresh(API(anchor="diverged"),role,SHA,MAIN)
    def test_reject_fake_historic_main_blob(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_single_file_refresh(API(mainblob="a"*40),role,SHA,MAIN)
    def test_historic_approval_survives_current_main_tool_upgrade(self):
        self.assertTrue(w.review_m2_g2_single_file_refresh(
            API(),role,SHA,MAIN)["approved_m2_g2_tool_refresh"])
    def test_reject_modified_worker_tool(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_single_file_refresh(API(blob="f"*40),role,SHA,MAIN)
    def test_reject_merge_instead_of_one_parent(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_single_file_refresh(API(parents=2),role,SHA,MAIN)
    def test_reject_wrong_role(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_single_file_refresh(API(),{**role,"id":"M1"},SHA,MAIN)
    def test_reject_forged_flag_wrong_paths(self):
        with self.assertRaises(g.ContractError):
            w.verify_worker_commits(role,[edge({"paths":["Cargo.lock"]})])
    def test_reject_forged_flag_wrong_parent(self):
        with self.assertRaises(g.ContractError):
            w.verify_worker_commits(role,[edge({"first_parent":"a"*40})])
    def test_reject_any_later_second_unapproved_root_edit(self):
        with self.assertRaises(g.ContractError):
            w.verify_worker_commits(role,[{"sha":"e"*40,"is_main_ancestor":False,
                                           "parents":1,"paths":[P]}])
if __name__=="__main__": unittest.main()
