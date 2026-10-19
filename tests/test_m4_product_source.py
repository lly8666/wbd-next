"""M0 shared original-Go M4 exact SOURCE gate; no network in unit tests."""
import io
import json
import unittest
import zipfile
from tools import m4_product_source as m

SOURCE="a"*40
CONTROL="b"*40
HEAD="c"*40
RUN=m.BOOTSTRAP_SCOPE_RUN
role={"id":"M4","branch":m.BRANCH,"state":"active","assignment_epoch":1,
      "allowed_paths":["r0/go_overlay/assembly/"],"owned_semantics":["product"],
      "cursor":".governance/workstreams/M4/cursor.json",
      "global_writer":False,"prompt":"docs/prompts/M4.md",
      "goal":"original-Go product assembly","done_when":"native smoke verified"}
registry={"schema_version":1,"reservation_revision":2,"roles":[
    dict(role, id="M0",branch="main",state="active",global_writer=True,
         owned_semantics=["governance"],cursor=".governance/workstreams/M0/cursor.json"),
    role]}
def run():
    return {"id":RUN,"workflow_id":m.SCOPE_WORKFLOW_ID,
            "path":m.SCOPE_PATH,"head_branch":"main","head_sha":CONTROL,
            "event":"workflow_run","status":"completed","conclusion":"success",
            "head_repository":{"full_name":m.REPO},"run_attempt":1,
            "display_title":"scope|"+m.BRANCH+"|"+SOURCE}
def receipt():
    return {"source_sha":SOURCE,"role_id":"M4","branch":m.BRANCH,
            "result":"ROLE_SCOPE_PASS","scope_standard":"G2_ACTIVATION_COMPLETE_PAGINATED_V1",
            "is_current_head":True,"run_id":str(RUN),"run_attempt":"1",
            "control_sha":CONTROL,"final_control_sha":CONTROL,
            "authority":dict(role,reservation_revision=2)}
def zipped(obj):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w") as z:z.writestr("scope-M4.json",json.dumps(obj))
    return stream.getvalue()
class API:
    def __init__(self):self.r=run();self.receipt=receipt();self.head=SOURCE
    def get(self,path):
        if path=="actions/runs/"+str(RUN):return self.r
        if path.endswith("/artifacts?per_page=100"):
            return {"artifacts":[{"name":f"central-scope-{RUN}-1",
                                 "id":123,"expired":False}]}
        if path.startswith("compare/"):return {"status":"ahead"}
        if path=="branches/"+m.BRANCH:return {"commit":{"sha":self.head}}
        raise AssertionError("unrecognized API endpoint "+path)
    def artifact_zip(self,artifact_id):
        if artifact_id!=123:raise AssertionError("wrong artifact")
        return zipped(self.receipt)
def event():
    return {"event_type":"workflow_run","workflow_run":run()}
class Tests(unittest.TestCase):
    def test_precise_g2_produces_only_scoped_source(self):
        a=API()
        self.assertEqual(m.perform(a,RUN,event(),HEAD,registry)["source_sha"],SOURCE)
        self.assertEqual(m.perform(a,RUN,{"event_type":"push"},HEAD,registry)["product"],"NOT_RUN")
    def test_reject_wrong_workflow_role_run_receipt_or_authority(self):
        for case in ("workflow_id","path","conclusion","role","source","auth",
                     "attempt","not_current","moved","bad_zip","main_diverged"):
            a=API();ctx=event();reg=registry;h=HEAD
            if case=="workflow_id":a.r["workflow_id"]=1
            if case=="path":a.r["path"]=".github/workflows/wrong.yml"
            if case=="conclusion":a.r["conclusion"]="failure"
            if case=="role":a.receipt["role_id"]="M1"
            if case=="source":a.receipt["source_sha"]="untrusted"
            if case=="auth":reg=dict(registry,reservation_revision=3)
            if case=="attempt":a.receipt["run_attempt"]="2"
            if case=="not_current":a.receipt["is_current_head"]=False
            if case=="moved":a.get_orig=a.get
            if case=="bad_zip":a.artifact_zip=lambda _ : zipped({"result":"ROLE_SCOPE_PASS"})
            if case=="main_diverged":h="not-a-sha"
            if case=="moved":
                oldget=a.get
                a.get=lambda path: ({"status":"diverged"} if path.startswith("compare/")
                                     else oldget(path))
            with self.subTest(case=case),self.assertRaises((ValueError,KeyError)):
                m.perform(a,RUN,ctx,h,reg)
    def test_queued_event_requires_same_run_and_identity(self):
        a=API()
        for key,value in (("workflow_id",1),("path","unrelated"),
                          ("conclusion","failure"),("head_branch","work/m4"),
                          ("head_repository",{"full_name":"untrusted/repo"})):
            event_doc=event()
            event_doc["workflow_run"][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                m.perform(a,RUN,event_doc,HEAD,registry)
        with self.assertRaises(ValueError):
            m.perform(a,RUN,{"event_type":"push","workflow_run":run()},HEAD,
                      dict(registry,reservation_revision=5))
    def test_no_promotional_payload_from_missing_artifact(self):
        a=API();a.artifact_zip=lambda _:zipped({"result":"ROLE_SCOPE_PASS"})
        with self.assertRaises((ValueError,KeyError)):
            m.perform(a,RUN,event(),HEAD,registry)

if __name__=="__main__":unittest.main()
