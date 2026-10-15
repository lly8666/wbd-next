"""One-shot M3 control-tool mirror: unauthorized tool writes remain rejected."""
import unittest
from tools import worker_scope_ci as w
from tools import governance as g

P=w.M3_G2_REFRESH_PATH
PRE=w.M3_G2_REFRESH_PARENT
SHA="d"*40
MAIN="c"*40
BLOB=w.M0_M3_HISTORICAL_TOOL_BLOB
role={"id":"M3","allowed_paths":["crates/wbd-codec/","docs/devlog/M3/","docs/evidence/M3/",
          ".governance/workstreams/M3/cursor.json",".governance/workstreams/M3/requests/"]}

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
            return {"type":"file","sha":self.mainblob if f"ref={w.M0_M3_HISTORICAL_TOOL_SOURCE}" in path else self.blob}
        raise AssertionError(path)

def edge(extra=None):
    x={"sha":SHA,"is_main_ancestor":False,"parents":1,"paths":[P],
       "approved_g2_tool_refresh":True,"first_parent":PRE,"sync_paths":[P]}
    if extra:x.update(extra)
    return x

class OneShotControlTransfer(unittest.TestCase):
    def test_accepted_exact_worker_parent_and_main_blob(self):
        x=w.review_m3_g2_single_file_refresh(API(),role,SHA,MAIN)
        self.assertTrue(x["approved_g2_tool_refresh"])
        self.assertEqual(w.verify_worker_commits(role,[edge()]),1)
    def test_old_worker_root_write_without_review_rejected(self):
        x=edge({"approved_g2_tool_refresh":False})
        with self.assertRaises(g.ContractError):w.verify_worker_commits(role,[x])
    def test_disallow_wrong_first_parent(self):
        with self.assertRaises(g.ContractError):w.review_m3_g2_single_file_refresh(API(parent="a"*40),role,SHA,MAIN)
    def test_disallow_extra_root_path(self):
        with self.assertRaises(g.ContractError):w.review_m3_g2_single_file_refresh(API(files=[P,"Cargo.lock"]),role,SHA,MAIN)
    def test_disallow_modified_historical_main_blob(self):
        with self.assertRaises(g.ContractError):
            w.review_m3_g2_single_file_refresh(API(mainblob="f"*40),role,SHA,MAIN)
    def test_disallow_modified_blob(self):
        with self.assertRaises(g.ContractError):w.review_m3_g2_single_file_refresh(API(blob="f"*40),role,SHA,MAIN)
    def test_disallow_non_main_approved_ancestry(self):
        with self.assertRaises(g.ContractError):w.review_m3_g2_single_file_refresh(API(anchor="diverged"),role,SHA,MAIN)
    def test_disallow_two_parent_sync_under_one_shot(self):
        with self.assertRaises(g.ContractError):w.review_m3_g2_single_file_refresh(API(parents=2),role,SHA,MAIN)
    def test_disallow_unauthorized_role(self):
        with self.assertRaises(g.ContractError):w.review_m3_g2_single_file_refresh(API(),{**role,"id":"M2"},SHA,MAIN)
    def test_disallow_fake_approved_flag_bad_paths(self):
        with self.assertRaises(g.ContractError):w.verify_worker_commits(role,[edge({"paths":["Cargo.lock"]})])
    def test_disallow_fake_approved_flag_bad_parent(self):
        with self.assertRaises(g.ContractError):w.verify_worker_commits(role,[edge({"first_parent":"a"*40})])
    def test_disallow_arbitrary_subsequent_root_edit(self):
        with self.assertRaises(g.ContractError):w.verify_worker_commits(role,[{"sha":"e"*40,"is_main_ancestor":False,"parents":1,"paths":[P]}])
if __name__=="__main__":unittest.main()
