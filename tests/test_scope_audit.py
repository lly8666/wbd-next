"""Central scope = main-owned G2 exact history; no second 64-commit rule."""
import copy
import unittest
from unittest.mock import patch
from tools import governance as g
from tools import scope_audit as s
from tools import worker_scope_ci as g2
from tests.test_worker_scope_ci import roles

A,B,C,D = (n*40 for n in "abcd")


class API:
    def __init__(self):
        self.registry=roles()
        self.final_registry=copy.deepcopy(self.registry)
        self.role=self.registry["roles"][1]
        self.current=B
        self.final_control=C
        self.source_removed=False
    def head(self,branch):
        return self.final_control if branch=="main" else self.current
    def file(self,path,ref):
        if path==".governance/registry.json":
            return self.registry if ref==C else self.final_registry
        if path.endswith("/cursor.json"):
            return {"schema_version":1,"role_id":"M1",
                    "branch":self.role["branch"],"assignment_epoch":1,
                    "reservation_revision":2,"sequence":1000,
                    "checkpoint_sha":A,"progress":"partial","unverified":True,
                    "current_task":"task","why_now":"because","done_when":"done",
                    "next_action":"next","partial_summary":"partial",
                    "last_tested_source":None,"evidence_refs":[],
                    "context_refs":[],"open_requests":[],"task_id":"test"}
        raise AssertionError("unexpected obsolete checkpoint/policy lookup: "+path)
    def get(self,endpoint):
        if endpoint.startswith("compare/"):
            before,after=endpoint.split("/")[1].split("?")[0].split("...")
            if self.source_removed and before==B and after==self.current:
                return {"status":"diverged"}
            if before==after:return {"status":"identical"}
            if before==B and after==self.current:return {"status":"ahead"}
            if before==B and after==self.final_control:return {"status":"ahead"}
            return {"status":"diverged"}
        raise AssertionError(endpoint)


class CentralReusesG2(unittest.TestCase):
    def run_scope(self,api,history=None):
        if history is None:
            history={"activation_commits":155,"scope_commits_checked":150,
                     "main_integration_commits_exempt":5}
        with patch.object(s.g2,"audit_worker_history",return_value=history) as scanner:
            receipt=s.audit(api,api.role["branch"],B,C)
            scanner.assert_called_once_with(api,api.role,B,C)
            return receipt

    def test_worker_g2_512_standard_is_only_scope_gate(self):
        result=self.run_scope(API())
        self.assertEqual(result["scope_standard"],"G2_ACTIVATION_COMPLETE_PAGINATED_V1")
        self.assertEqual(result["activation_base_sha"],g2.G2_BASE)
        self.assertEqual(result["activation_max_commits"],512)
        self.assertEqual(result["activation_page_size"],80)
        self.assertEqual(result["activation_commits"],155)
        self.assertEqual(result["scope_commits_checked"],150)
        self.assertEqual(result["product"],"NOT_RUN")
        self.assertNotIn("checkpoint_sha",result)
        self.assertNotIn("delta_commits",result)

    def test_512_full_history_accepted_513_fails_via_one_scanner(self):
        api=API()
        self.assertEqual(self.run_scope(api,{"activation_commits":512,
            "scope_commits_checked":512,"main_integration_commits_exempt":0})[
                "activation_commits"],512)
        with patch.object(s.g2,"audit_worker_history",
                          side_effect=g.ContractError("G2 above 512")):
            with self.assertRaises(g.ContractError):s.audit(api,api.role["branch"],B,C)

    def test_drifted_authority_and_source_removal_fail_closed(self):
        cases=[
            lambda a:a.final_registry["roles"][1].update(assignment_epoch=2),
            lambda a:setattr(a,"source_removed",True),
        ]
        for alter in cases:
            api=API()
            api.final_control=D
            api.current=D
            alter(api)
            with self.subTest(alter=alter),self.assertRaises(g.ContractError):
                self.run_scope(api)

    def test_main_prose_does_not_revoke_worker_write_authority(self):
        api=API();api.final_control=D;api.current=D
        api.final_registry["roles"][1]["goal"]="changed prose only"
        result=self.run_scope(api)
        self.assertEqual(result["result"],"ROLE_SCOPE_PASS")
        self.assertFalse(result["is_current_head"])

    def test_g2_merged_review_and_complete_page_failure_are_not_downgraded(self):
        api=API()
        for msg in ["G2 incomplete paginated commit page",
                    "unreviewed worker merge", "worker write outside authority"]:
            with self.subTest(error=msg):
                with patch.object(s.g2,"audit_worker_history",
                                  side_effect=g.ContractError(msg)):
                    with self.assertRaises(g.ContractError):
                        s.audit(api,api.role["branch"],B,C)

    def test_scoped_component_pass_receipt_not_product_pass(self):
        class Evidence:
            def __init__(self,result,verified):
                self.result=result;self.verified=verified
            def file(self,path,source):
                return {"schema_version":1,"source_sha":B,
                        "result":self.result,"artifact_verified":self.verified}
            def get(self,endpoint):
                return {"type":"file"}
        cursor={"evidence_refs":["docs/evidence/M4/component.json"],
                "context_refs":[],"open_requests":[],
                "last_tested_source":B,"unverified":False}
        for label in ("PASS","PASS_SCOPED_COLD_GO_AND_ISAL_SAFE_WRAPPER_ONLY"):
            s.check_role_metadata(Evidence(label,True),{"id":"M4"},B,cursor)
        for label,verified in (
            ("FAIL",True),("INCONCLUSIVE",True),("PASS_SCOPED_F2",False),
            ("PASS_NOT_RUN",True)):
            with self.subTest(label=label),self.assertRaises(g.ContractError):
                s.check_role_metadata(Evidence(label,verified),{"id":"M4"},B,cursor)

    def test_coordination_markdown_is_not_dispatch_json(self):
        class Notes:
            def get(self,endpoint):
                self.endpoint=endpoint
                return {"type":"file"}
            def file(self,*args):
                raise AssertionError("Markdown must not be parsed as JSON request")
        api=Notes()
        s.check_role_metadata(api,{"id":"M1"},B,{"evidence_refs":[],
                    "context_refs":[],"open_requests":[
                        ".governance/workstreams/M1/requests/dependency.md"]})
        self.assertIn("dependency.md",api.endpoint)


if __name__=="__main__":
    unittest.main()
