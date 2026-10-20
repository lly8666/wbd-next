"""M0 main-only M4 request auto-dispatch mock: no credential or real Actions."""
import unittest
from unittest.mock import patch
from tools import worker_request_dispatch as d

SHA="a"*40
M4HEAD="b"*40
REQUEST="M4-016-WIN-NATIVE-001"
I="c"*40
CONFIG=b'{"legacy_source":"a7a82"}'
class API:
    def __init__(self):
        self.branch=M4HEAD
        self.control=d.M4_CONTROL_SHA
        self.posts=[]
        self.runs=[]
        self.reg={"schema_version":1,"reservation_revision":2,"roles":[{
            "id":"M4","state":"active","global_writer":False,
            "branch":d.m4.BRANCH,"assigned_task":"R5-M4-NATIVE-WINDOWS-NETWORK-016",
            "assignment_epoch":1,"allowed_paths":["r0/go_overlay/internal/windowsclient/"],
            "prompt":"docs/prompts/M4.md","goal":"native","done_when":"native",
            "cursor":".governance/workstreams/M4/cursor.json",
            "owned_semantics":["m4-product"]}]}
        self.request={
            "role_id":"M4","status":"PLANNED",
            "dispatch_ref":d.M4_CONTROL_REF,"control_sha":d.M4_CONTROL_SHA,
            "source_sha":SHA,"request_id":REQUEST}
    def get(self,path):
        if path=="branches/main":return {"commit":{"sha":d.M4_CONTROL_SHA}}
        if path=="branches/"+d.M4_CONTROL_REF:return {"commit":{"sha":self.control}}
        if path=="branches/"+d.m4.BRANCH:return {"commit":{"sha":self.branch}}
        if path.startswith("contents/.governance/workstreams/M4/requests?"):
            return [{"name":REQUEST+".json","type":"file"}]
        if path.startswith("commits?sha="):return [{"sha":I}]
        if path.startswith("commits/"):return {"parents":[{"sha":SHA}],"files":[{
            "filename":f".governance/workstreams/M4/requests/{REQUEST}.json","status":"added"}]}
        if path.startswith("actions/workflows/"+d.M4_TARGET_WORKFLOW+"/runs?"):
            return {"workflow_runs":self.runs}
        raise AssertionError(path)
    def blob(self,path,ref):
        if path==".governance/registry.json":
            import json
            return json.dumps(self.reg).encode()
        if path.endswith(REQUEST+".json"):
            import json
            return json.dumps(self.request).encode()
        raise AssertionError(path)
    def post(self,path,payload):
        assert path=="actions/workflows/"+d.M4_TARGET_WORKFLOW+"/dispatches"
        self.posts.append(payload)
        self.runs.append({"id":345,"display_title":f"M4|{REQUEST}|windows-amd64|{d.M4_CONTROL_SHA}",
                          "event":"workflow_dispatch","head_sha":d.M4_CONTROL_SHA})
class Tests(unittest.TestCase):
    def mock_scope(self):
        return {"scope_run_id":123,"scope_artifact_id":456}
    def mock_manual(self,api,attest,registry,control,rid,ref,source,runid):
        self.assertIsNone(runid)
        if ref!=I or source!=SHA or control!=d.M4_CONTROL_SHA:raise ValueError("wrong I")
        return {"request_ref":ref,"source_sha":source}
    def plan(self,api):
        with patch.object(d,"latest_scope",return_value=self.mock_scope()),\
             patch.object(d.m4,"perform",return_value={"source_sha":M4HEAD}),\
             patch.object(d.m4,"verify_manual_request",side_effect=self.mock_manual):
            return d.plan_m4(api,d.M4_CONTROL_SHA)
    def test_once_no_extra_workflow_and_replay_is_duplicate(self):
        api=API()
        ready=self.plan(api)
        self.assertEqual([r["result"] for r in ready],["READY"])
        d.execute_m4(api,ready)
        self.assertEqual(len(api.posts),1)
        self.assertEqual(api.posts[0]["ref"],d.M4_CONTROL_REF)
        self.assertEqual(api.posts[0]["inputs"]["request_ref"],I)
        self.assertEqual(api.posts[0]["inputs"]["worker_source_sha"],SHA)
        self.assertEqual(self.plan(api)[0]["result"],"SKIP_ALREADY_DISPATCHED")
    def test_missing_request_or_changed_scope_or_control_fail_closed(self):
        api=API();api.request["dispatch_ref"]="other"
        self.assertEqual(self.plan(api),[])
        api=API();api.control="0"*40
        with self.assertRaises(ValueError):self.plan(api)
        api=API();api.reg["roles"][0]["assigned_task"]="M4-OLD"
        with self.assertRaises(ValueError):self.plan(api)
        api=API();out=self.plan(api);api.branch="f"*40
        with self.assertRaises(ValueError):d.execute_m4(api,out)
        self.assertEqual(api.posts,[])
    def test_main_linux017_skips_historical_windows_i_without_dispatch(self):
        api=API()
        api.reg["roles"][0]["assigned_task"]="R5-M4-PLAN012-LINUX-REAL-NETWORK-STOP-017"
        api.control="0"*40
        planned=d.plan_m4(api,d.M4_CONTROL_SHA)
        self.assertEqual([x["result"] for x in planned],
                         ["SKIP_SUPERSEDED_WINDOWS_TASK"])
        d.execute_m4(api,planned)
        self.assertEqual(api.posts,[])
        self.assertEqual(api.request["status"],"PLANNED")
    def test_no_g2_does_not_launch_windows(self):
        api=API()
        with patch.object(d,"latest_scope",return_value=None):
            decisions=d.plan_m4(api,d.M4_CONTROL_SHA)
        self.assertEqual(decisions[0]["result"],"SKIP_SCOPE_NOT_READY")
        d.execute_m4(api,decisions)
        self.assertEqual(api.posts,[])
if __name__=="__main__":unittest.main()
