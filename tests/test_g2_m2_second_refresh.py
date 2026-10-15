"""Second one-time M2 sole-root-file checker sync, exact frozen worker parent."""
import unittest
from tools import worker_scope_ci as w
from tools import governance as g

P=w.M2_G2_REFRESH_PATH
PRE=w.M2_G2_SECOND_REFRESH_PARENT
SHA="d"*40
MAIN="c"*40
BLOB=w.M0_M2_SECOND_TOOL_BLOB
ROLE={"id":"M2","allowed_paths":["crates/wbd-recovery/","docs/evidence/M2/",
                                "docs/devlog/M2/",".governance/workstreams/M2/cursor.json"]}

class Api:
    def __init__(self,parent=PRE,paths=None,blob=BLOB,mainblob=BLOB,anchor="ahead",parents=1):
        self.parent=parent;self.paths=[P] if paths is None else paths
        self.blob=blob;self.mainblob=mainblob;self.anchor=anchor;self.parents=parents
    def get(self,url):
        if url.startswith("commits/"):
            return {"parents":[{"sha":self.parent}]*self.parents,
                    "files":[{"filename":p} for p in self.paths]}
        if url.startswith("compare/"):
            return {"status":self.anchor}
        if url.startswith("contents/"):
            return {"type":"file","sha":self.mainblob if "ref="+w.M0_M2_SECOND_TOOL_SOURCE in url else self.blob}
        raise AssertionError(url)

def edge(extra=None):
    e={"sha":SHA,"is_main_ancestor":False,"parents":1,"paths":[P],
       "approved_m2_g2_tool_refresh_v2":True,"first_parent":PRE,"sync_paths":[P]}
    return dict(e,**(extra or {}))

class SecondM2OneShot(unittest.TestCase):
    def test_reviewed_parent_and_blob(self):
        self.assertTrue(w.review_m2_g2_second_single_file_refresh(
            Api(),ROLE,SHA,MAIN)["approved_m2_g2_tool_refresh_v2"])
        self.assertEqual(w.verify_worker_commits(ROLE,[edge()]),1)
    def test_wrong_role(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_second_single_file_refresh(Api(),{**ROLE,"id":"M3"},SHA,MAIN)
    def test_wrong_parent(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_second_single_file_refresh(Api(parent="f"*40),ROLE,SHA,MAIN)
    def test_extra_path(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_second_single_file_refresh(Api(paths=[P,"Cargo.lock"]),ROLE,SHA,MAIN)
    def test_wrong_historical_approved_main_blob(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_second_single_file_refresh(Api(mainblob="f"*40),ROLE,SHA,MAIN)
    def test_historical_approval_survives_current_main_checker_upgrade(self):
        self.assertTrue(w.review_m2_g2_second_single_file_refresh(
            Api(),ROLE,SHA,MAIN)["approved_m2_g2_tool_refresh_v2"])
    def test_control_anchor_lost(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_second_single_file_refresh(Api(anchor="diverged"),ROLE,SHA,MAIN)
    def test_merge_forbidden(self):
        with self.assertRaises(g.ContractError):
            w.review_m2_g2_second_single_file_refresh(Api(parents=2),ROLE,SHA,MAIN)
    def test_forged_edge_parent(self):
        with self.assertRaises(g.ContractError):
            w.verify_worker_commits(ROLE,[edge({"first_parent":"f"*40})])
    def test_forged_edge_path(self):
        with self.assertRaises(g.ContractError):
            w.verify_worker_commits(ROLE,[edge({"paths":[P,"Cargo.lock"]})])
    def test_unapproved_later_root_edit(self):
        with self.assertRaises(g.ContractError):
            w.verify_worker_commits(ROLE,[{"sha":"f"*40,"is_main_ancestor":False,
                                        "parents":1,"paths":[P]}])

if __name__=="__main__":unittest.main()
