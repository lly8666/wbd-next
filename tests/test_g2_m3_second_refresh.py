"""M3-014 one-time second M0 tool-only refresh, pinned to exact old worker H."""
import unittest
from tools import worker_scope_ci as w
from tools import governance as g

P=w.M3_G2_REFRESH_PATH
PRE=w.M3_G2_SECOND_REFRESH_PARENT
SHA="d"*40
MAIN="c"*40
BLOB=w.M0_M3_SECOND_TOOL_BLOB
ROLE={"id":"M3","allowed_paths":["crates/wbd-codec/","docs/devlog/M3/",
     "docs/evidence/M3/",".governance/workstreams/M3/cursor.json"]}

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
            return {"type":"file","sha":self.mainblob if "ref="+w.M0_M3_SECOND_TOOL_SOURCE in url else self.blob}
        raise AssertionError(url)

def edge(extra=None):
    d={"sha":SHA,"is_main_ancestor":False,"parents":1,"paths":[P],
       "approved_m3_g2_tool_refresh_v2":True,"first_parent":PRE,
       "sync_paths":[P]}
    return dict(d,**(extra or {}))

class SecondM3OneShot(unittest.TestCase):
    def test_exact_parent_path_historic_blob(self):
        result=w.review_m3_g2_second_single_file_refresh(Api(),ROLE,SHA,MAIN)
        self.assertTrue(result["approved_m3_g2_tool_refresh_v2"])
        self.assertEqual(w.verify_worker_commits(ROLE,[edge()]),1)
    def test_parent_changed(self):
        with self.assertRaises(g.ContractError):
            w.review_m3_g2_second_single_file_refresh(Api(parent="f"*40),ROLE,SHA,MAIN)
    def test_extra_root_file(self):
        with self.assertRaises(g.ContractError):
            w.review_m3_g2_second_single_file_refresh(Api(paths=[P,"Cargo.lock"]),ROLE,SHA,MAIN)
    def test_wrong_historic_main_blob(self):
        with self.assertRaises(g.ContractError):
            w.review_m3_g2_second_single_file_refresh(Api(mainblob="f"*40),ROLE,SHA,MAIN)
    def test_anchor_lost(self):
        with self.assertRaises(g.ContractError):
            w.review_m3_g2_second_single_file_refresh(Api(anchor="diverged"),ROLE,SHA,MAIN)
    def test_not_one_parent(self):
        with self.assertRaises(g.ContractError):
            w.review_m3_g2_second_single_file_refresh(Api(parents=2),ROLE,SHA,MAIN)
    def test_wrong_role(self):
        with self.assertRaises(g.ContractError):
            w.review_m3_g2_second_single_file_refresh(Api(),{**ROLE,"id":"M2"},SHA,MAIN)
    def test_fake_result_wrong_first_parent(self):
        with self.assertRaises(g.ContractError):
            w.verify_worker_commits(ROLE,[edge({"first_parent":"f"*40})])
    def test_fake_result_extra_path(self):
        with self.assertRaises(g.ContractError):
            w.verify_worker_commits(ROLE,[edge({"paths":[P,"Cargo.lock"]})])
    def test_unapproved_root_write(self):
        with self.assertRaises(g.ContractError):
            w.verify_worker_commits(ROLE,[{"sha":SHA,"is_main_ancestor":False,
                                         "parents":1,"paths":[P]}])
if __name__=="__main__":unittest.main()
