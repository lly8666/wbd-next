"""No worker source, secrets, real dispatch or GitHub API used by unit tests."""
import io
import json
import zipfile
import unittest
from tools import worker_request_dispatch as d
from tools import worker_component_validation as e

MAIN = "f"*40
M1 = "1"*40
M3 = "3"*40
I1 = "a"*40
I3 = "b"*40
OLD = "c"*40
CFG = b"fixture configuration"
def zippy(obj, role):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w") as z:
        z.writestr(f"scope-{role}.json",json.dumps(obj))
    return buf.getvalue()
def fake_receipt(role,branch,source,epoch=1,revision=2):
    return {"result":"ROLE_SCOPE_PASS","role_id":role,"source_sha":source,
            "branch":branch,"scope_standard":"G2_ACTIVATION_COMPLETE_PAGINATED_V1",
            "control_sha":"d"*40,"final_control_sha":"e"*40,
            "is_current_head":True,"run_id":"101" if role=="M1" else "102",
            "run_attempt":"1","authority":{"id":role,"state":"active",
                   "assignment_epoch":epoch,"reservation_revision":revision}}
def roledef(role):
    return {"id":role,"state":"active","global_writer":False,
        "assigned_task":f"{role}-TEST","branch":f"work/{role.lower()}",
        "assignment_epoch":1,
        "allowed_paths":["crates/wbd-engine/tests/"] if role=="M1"
                        else ["crates/wbd-codec/"],
        "prompt":f"docs/prompts/{role}.md",
        "goal":"bounded module work","done_when":"scoped exact-source tests",
        "cursor":f".governance/workstreams/{role}/cursor.json",
        "owned_semantics":[role+"-exclusive"]}
def req(role):
    suite,fixture,*_=e.SUITES[role]
    return {"schema_version":1,"request_id":role+"-PREPARE-001",
        "role_id":role,"task_id":role+"-TEST","assignment_epoch":1,
        "reservation_revision":2,"kind":"functional","status":"PLANNED",
        "source_sha":"9"*40,"baseline_sha":OLD,"harness_sha":"8"*40,
        "config_path":fixture,"config_sha256":e.sha(CFG),
        "scenario":suite,"seed":631,"workflow":d.TARGET_WORKFLOW,
        "dispatch_ref":d.CONTROL_REF,"control_sha":d.CONTROL_SHA,
        "measurement_jobs":1,"samples":1}
class Mock:
    def __init__(self):
        self.reg={"schema_version":1,"reservation_revision":2,
                  "roles":[{"id":"M0","state":"active","global_writer":True,
                            "branch":"main","assignment_epoch":1,
                            "assigned_task":"M0","allowed_paths":["*"],
                            "prompt":"docs/prompts/M0.md",
                            "goal":"bounded integration","done_when":"integration tested",
                            "cursor":".governance/workstreams/M0/cursor.json",
                            "owned_semantics":["m0-exclusive"]},
                           roledef("M1"),roledef("M3")]}
        self.src={"M1":M1,"M3":M3}
        self.requests={"M1":req("M1"),"M3":req("M3")}
        self.scope_valid=True
        self.posts=[]
        self.runs=[]
    def get(self,path):
        if path=="branches/main":return {"commit":{"sha":MAIN}}
        if path=="branches/"+d.CONTROL_REF:
            return {"commit":{"sha":d.CONTROL_SHA}}
        for role,sha in self.src.items():
            if path=="branches/work/"+role.lower():return {"commit":{"sha":sha}}
        if path.startswith("actions/workflows/scope-audit.yml/runs?"):
            if not self.scope_valid:return {"workflow_runs":[]}
            return {"workflow_runs":[{"id":101 if role=="M1" else 102,
                      "display_title":f"scope|work/{role.lower()}|{sha}",
                      "status":"completed","conclusion":"success",
                      "event":"workflow_run","head_branch":"main","run_attempt":1}
                      for role,sha in self.src.items()]}
        if path.startswith("actions/runs/") and path.endswith("/artifacts?per_page=100"):
            rid=int(path.split("/")[2])
            return {"artifacts":[{"name":f"central-scope-{rid}-1",
                                  "id":201 if rid==101 else 202,
                                  "expired":False}]}
        if path.startswith("contents/.governance/workstreams/") and "?ref=" in path:
            role=path.split("/")[3]
            return [{"type":"file","name":self.requests[role]["request_id"]+".json"}]
        if path.startswith("commits?sha="):
            role="M1" if "M1" in path else "M3"
            return [{"sha":I1 if role=="M1" else I3}]
        if path.startswith("commits/") and "?per_page=100" in path:
            role="M1" if I1 in path else "M3"
            return {"parents":[{"sha":OLD}],
                    "files":[{"filename":f".governance/workstreams/{role}/requests/{self.requests[role]['request_id']}.json",
                              "status":"added"}]}
        if path.startswith("compare/"):
            return {"status":"ahead"}
        if path.startswith("actions/workflows/worker-component-validation.yml/runs?"):
            return {"workflow_runs":self.runs}
        raise AssertionError("unexpected GET "+path)
    def blob(self,path,ref):
        if path==".governance/registry.json":return json.dumps(self.reg).encode()
        for role in self.requests:
            if path.endswith("/"+self.requests[role]["request_id"]+".json"):
                return json.dumps(self.requests[role]).encode()
            if path==e.SUITES[role][1]:return CFG
        raise AssertionError("unexpected blob "+path)
    def artifact_zip(self,artifact_id):
        role="M1" if artifact_id==201 else "M3"
        return zippy(fake_receipt(role,"work/"+role.lower(),self.src[role]),role)
    def post(self,path,payload):
        assert path=="actions/workflows/worker-component-validation.yml/dispatches"
        self.posts.append(payload)
        role=payload["inputs"]["role_id"]
        request=self.requests[role]
        self.runs.append({"display_title":f"{role}|{request['request_id']}|prepare|{d.CONTROL_SHA}",
                          "event":"workflow_dispatch","head_sha":d.CONTROL_SHA,"id":1000+len(self.posts)})
        return b""

class DispatchTests(unittest.TestCase):
    def test_dynamic_run_name_triggers_only_exact_scope_workflow(self):
        scope = {"name":"scope|work/m1-r1-runtime|" + M1,
                 "display_title":"scope|work/m1-r1-runtime|" + M1,
                 "workflow_id":d.SCOPE_WORKFLOW_ID,"path":d.SCOPE_PATH,
                 "conclusion":"success","event":"workflow_run",
                 "head_branch":"main",
                 "head_repository":{"full_name":e.REPO}}
        self.assertTrue(d.trusted_scope_trigger(scope))
        self.assertTrue(d.trusted_scope_trigger({**scope,"name":"any dynamic run-name"}))
        for changes in ({"workflow_id":0}, {"path":".github/workflows/unrelated.yml"},
                        {"conclusion":"failure"}, {"event":"push"},
                        {"head_branch":"work/m1-r1-runtime"},
                        {"head_repository":{"full_name":"someone/untrusted"}},
                        {"head_repository":None}):
            with self.subTest(changes=changes):
                self.assertFalse(d.trusted_scope_trigger({**scope,**changes}))
    def test_scope_receipt_accepts_real_main_control_rotation(self):
        r=fake_receipt("M1","work/m1",M1)
        run={"worker_branch":"work/m1","id":101,"run_attempt":1,"epoch":1,"revision":2}
        self.assertEqual(d.scope_receipt(zippy(r,"M1"),"M1",M1,run),r)
        for key,value in (("source_sha","0"*40),("result","FAIL"),
                          ("is_current_head",False),("scope_standard","UNKNOWN"),
                          ("role_id","M3"),("run_attempt","2")):
            with self.subTest(key=key),self.assertRaises(ValueError):
                d.scope_receipt(zippy({**r,key:value},"M1"),"M1",M1,run)
    def test_exact_two_roles_dispatch_once_and_skip_preexisting(self):
        api=Mock()
        ready=d.plan(api,MAIN)
        self.assertEqual([x["result"] for x in ready],["READY","READY"])
        self.assertEqual([x["request_ref"] for x in ready],[I1,I3])
        d.execute(api,ready)
        self.assertEqual(len(api.posts),2)
        self.assertEqual({x["ref"] for x in api.posts},{d.CONTROL_REF})
        self.assertEqual([x["result"] for x in d.plan(api,MAIN)],
                         ["SKIP_ALREADY_DISPATCHED"]*2)
    def test_no_g2_means_no_dispatch(self):
        api=Mock();api.scope_valid=False
        outcomes=d.plan(api,MAIN)
        self.assertEqual([x["result"] for x in outcomes],["SKIP_SCOPE_NOT_READY"]*2)
        d.execute(api,outcomes)
        self.assertEqual(api.posts,[])
    def test_stale_epoch_bad_config_and_wrong_control_fail_closed(self):
        for mutation in ("task","epoch","digest","control","source"):
            api=Mock()
            if mutation=="task":api.requests["M1"]["task_id"]="old"
            if mutation=="epoch":api.requests["M1"]["assignment_epoch"]=55
            if mutation=="digest":api.requests["M1"]["config_sha256"]="0"*64
            if mutation=="control":api.requests["M1"]["control_sha"]="0"*40
            if mutation=="source":api.requests["M1"]["source_sha"]="bad"
            if mutation=="control":
                self.assertEqual(len(d.plan(api,MAIN)),1)
            else:
                with self.subTest(mutation=mutation),self.assertRaises((ValueError,KeyError)):
                    d.plan(api,MAIN)
    def test_role_head_changes_after_auth_rejected_before_write(self):
        api=Mock();out=d.plan(api,MAIN);api.src["M1"]="7"*40
        with self.assertRaises(ValueError):d.execute(api,out)
        self.assertEqual(api.posts,[])
    def test_malformed_zip_refuses_other_paths(self):
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,"w") as f:f.writestr("wrong.json","{}")
        with self.assertRaises(ValueError):
            d.scope_receipt(buf.getvalue(),"M1",M1,
                {"worker_branch":"work/m1","id":101,"run_attempt":1,"epoch":1,"revision":2})
if __name__=="__main__":unittest.main()
