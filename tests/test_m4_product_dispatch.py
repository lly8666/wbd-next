"""M0 negative-only M4 live original Go Windows product manual request gate."""
import base64
import hashlib
import json
import unittest
from tools import m4_product_source as m

C="c"*40
S="a"*40
I="b"*40
HEAD="d"*40
RID="M4-016-WIN-NATIVE-001"
RUN=7819234
REQ_PATH=f".governance/workstreams/M4/requests/{RID}.json"
CFG=b'{"legacy_source":"a7a82db", "operations":[]}'
REG={"schema_version":1,"reservation_revision":2,"roles":[{
    "id":"M4","branch":m.BRANCH,"state":"active","assignment_epoch":1,
    "global_writer":False,"prompt":"docs/prompts/M4.md",
    "cursor":".governance/workstreams/M4/cursor.json",
    "owned_semantics":["platform"],"allowed_paths":["r0/go_overlay/internal/windowsclient/"],
    "assigned_task":"R5-M4-NATIVE-WINDOWS-NETWORK-016","goal":"native","done_when":"native"}]}
REQ={"schema_version":1,"request_id":RID,"role_id":"M4","task_id":REG["roles"][0]["assigned_task"],
    "assignment_epoch":1,"reservation_revision":2,"kind":"functional","status":"PLANNED",
    "workflow":".github/workflows/m0-m4-product-assembly.yml","dispatch_ref":m.M4_CONTROL_REF,
    "control_sha":C,"source_sha":S,"harness_sha":S,"baseline_sha":m.LEGACY_SOURCE,
    "config_sha256":hashlib.sha256(CFG).hexdigest(),
    "config_path":"r0/go_overlay/assembly/manifest.json",
    "scenario":"windows-native-product-runtime-016","seed":1,
    "samples":1,"measurement_jobs":1,"target":"windows-amd64"}
def git_file(raw):
    return {"type":"file","encoding":"base64","content":base64.b64encode(raw).decode()}
class API:
    def __init__(self):
        self.req=dict(REQ)
        self.commit={"sha":I,"parents":[{"sha":S}],"files":[{"filename":REQ_PATH,"status":"added"}]}
        self.current=HEAD
        self.config=CFG
        self.runs={"total_count":1,"workflow_runs":[{
            "id":RUN,"event":"workflow_dispatch",
            "display_title":f"M4|{RID}|windows-amd64|{C}",
            "head_sha":C}]}
    def get(self,path):
        if path=="commits/"+I:return self.commit
        if path=="contents/"+REQ_PATH+"?ref="+I:return git_file(json.dumps(self.req).encode())
        if path=="contents/"+REQ_PATH+"?ref="+HEAD:return git_file(json.dumps(self.req).encode())
        if path=="contents/r0/go_overlay/assembly/manifest.json?ref="+S:return git_file(self.config)
        if path.startswith("compare/"):return {"status":"ahead"}
        if path=="branches/"+m.BRANCH:return {"commit":{"sha":self.current}}
        if path=="actions/workflows/m0-m4-product-assembly.yml/runs?event=workflow_dispatch&branch=qualification%2Fm4-product-windows-v1&per_page=100":
            return self.runs
        raise AssertionError(path)
class Tests(unittest.TestCase):
    def validate(self,a):
        return m.verify_manual_request(a,{"source_sha":HEAD},REG,C,RID,I,S,RUN)
    def test_valid_exact_source_current_scope_and_one_manual_run(self):
        got=self.validate(API())
        self.assertEqual((got["source_sha"],got["request_id"],got["attested_worker_sha"]),
                         (S,RID,HEAD))
        self.assertEqual(got["product"],"NOT_RUN_UNTIL_WINDOWS_JOB")
    def test_reject_cross_role_task_source_manifest_or_duplicate(self):
        cases=["role_id","task_id","control_sha","source_sha","harness_sha","config_sha256",
               "target","workflow","reservation_revision","request_ref","duplicate",
               "wrong_head","extra_file","not_added","no_ancestor","wrong_run","not_current"]
        for case in cases:
            a=API()
            if case in a.req:a.req[case]="x" if case not in ("reservation_revision",) else 3
            if case=="request_ref":a.commit["sha"]="a"*40
            if case=="duplicate":a.runs["workflow_runs"].append(dict(a.runs["workflow_runs"][0],id=RUN+1))
            if case=="wrong_head":a.current="e"*40
            if case=="extra_file":a.commit["files"].append({"filename":"crates/forbidden","status":"added"})
            if case=="not_added":a.commit["files"][0]["status"]="modified"
            if case=="no_ancestor":
                original=a.get
                a.get=lambda path:{"status":"diverged"} if path.startswith("compare/") else original(path)
            if case=="wrong_run":a.runs["workflow_runs"][0]["id"]=RUN+5
            if case=="not_current":a.runs["workflow_runs"][0]["head_sha"]="f"*40
            with self.subTest(case=case),self.assertRaises((ValueError,KeyError)):
                self.validate(a)
if __name__=="__main__":
    unittest.main()
