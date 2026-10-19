"""PLAN-009 pure fail-closed worker request/ABBA tests (no network)."""
import unittest
from tools import worker_component_validation as w
from tools import governance as g
A,B,H,CONTROL=("a"*40,"b"*40,"c"*40,"d"*40)
CFG=b"owned-fixture"
def reg(role):
    return {"reservation_revision":2,"roles":[{"id":role,"state":"active",
       "branch":"work/m1-r1-runtime" if role=="M1" else "work/m3-r1-codec",
       "assigned_task":"M1-TASK" if role=="M1" else "M3-TASK",
       "assignment_epoch":1,"allowed_paths":["crates/wbd-engine/tests/"] if role=="M1"
                                                 else ["crates/wbd-codec/"]}]}
def request(role="M1",stage="prepare"):
    suite,fixture,*_=w.SUITES[role]
    d={"request_id":"WR-001","role_id":role,
       "task_id":reg(role)["roles"][0]["assigned_task"],"assignment_epoch":1,
       "reservation_revision":2,"kind":"functional" if stage=="prepare" else "performance",
       "source_sha":B,"harness_sha":H,"baseline_sha":A,"control_sha":CONTROL,
       "config_path":fixture,"config_sha256":w.sha(CFG),
       "scenario":suite,"seed":631,"workflow":w.CONTROL_WORKFLOW,
       "dispatch_ref":"qualification/worker-ci-v3","measurement_jobs":1,
       "samples":1 if stage=="prepare" else 2 if role=="M1" else 4,
       "status":"PLANNED","_request_path":".governance/workstreams/"+role+"/requests/WR-001.json"}
    if stage=="paired":
        d.update(mode="paired_ab" if role=="M1" else "paired_abba",
                 prepare_run_id=10,prepare_run_attempt=1,prepare_artifact_id=20,
                 prepare_manifest_sha256="f"*64,
                 legs=[{"label":x,"source_sha":A if x=="A" else B,
                        "build_manifest_sha256":"f"*64}
                       for x in ("AB" if role=="M1" else "ABBA")])
    return d
def check(d,stage,cfg=CFG):
    return w.validate_context(d,d["role_id"],stage,"qualification/worker-ci-v3",
             CONTROL,reg(d["role_id"]),"e"*40,"f"*40,cfg)
class ValidationTests(unittest.TestCase):
    def test_valid_both_stages(self):
        for role in ("M1","M3"):
            self.assertTrue(check(request(role),"prepare"))
            self.assertTrue(check(request(role,"paired"),"paired"))
    def test_scope_epoch_task_and_config_fail_closed(self):
        for key,bad in [("task_id","INVALID"),("assignment_epoch",2),
                        ("reservation_revision",3),("source_sha","HEAD"),
                        ("harness_sha","HEAD"),("baseline_sha",B),
                        ("config_path","tools/worker_scope_ci.py"),
                        ("config_sha256","f"*64),
                        ("dispatch_ref","main"),
                        ("workflow",".github/workflows/governance.yml"),
                        ("scenario","arbitrary-shell"),("control_sha",A)]:
            d=request();d[key]=bad
            with self.subTest(key=key),self.assertRaises((ValueError,g.ContractError)):
                check(d,"prepare")
        with self.assertRaises((ValueError,g.ContractError)):
            check(request(),"prepare",b"tampered")
    def test_paired_artifact_identity_and_shape(self):
        for role in ("M1","M3"):
            for what in ("missing","wrong-source","wrong-build","wrong-mode","two-jobs"):
                d=request(role,"paired");d["legs"]=[dict(x) for x in d["legs"]]
                if what=="missing":d["legs"].pop()
                if what=="wrong-source":d["legs"][-1]["source_sha"]="e"*40
                if what=="wrong-build":d["legs"][-1]["build_manifest_sha256"]="e"*64
                if what=="wrong-mode":d["mode"]="single"
                if what=="two-jobs":d["measurement_jobs"]=2
                with self.subTest(role=role,what=what),self.assertRaises((ValueError,g.ContractError)):
                    check(d,"paired")
    def test_native_four_leg_abba_parser_and_quantization(self):
        lines=["M3_018_ABBA leg=%d version=%s backend=NativeIsaL k=16 r=16 e=4 recoveries=2000000 checksum=83 wall_ns=1100000000 cpu_ticks=150"%(i,x)
               for i,x in enumerate("ABBA")]
        self.assertEqual(len(w.check_abba_lines(lines,100)),4)
        # Rust libtest --nocapture can print the test-name prefix before
        # the FIRST fixture marker, which must not silently drop leg 0.
        streamed="test worker_fixture ... "+lines[0]+"\n"+"\n".join(lines[1:])
        import re
        found=re.findall(r"M3_018_ABBA leg=[^\n]*",streamed)
        self.assertEqual(len(w.check_abba_lines(found,100)),4)
        for what in ("scalar","order","checksum","work","cpu","missing"):
            v=lines[:]
            if what=="scalar":v[1]=v[1].replace("NativeIsaL","Scalar")
            if what=="order":v[3]=v[3].replace("version=A","version=B")
            if what=="checksum":v[1]=v[1].replace("checksum=83","checksum=2")
            if what=="work":v[1]=v[1].replace("recoveries=2000000","recoveries=2")
            if what=="cpu":v[2]=v[2].replace("cpu_ticks=150","cpu_ticks=10")
            if what=="missing":v.pop()
            with self.subTest(what=what),self.assertRaises(ValueError):
                w.check_abba_lines(v,100)
    def test_prepare_does_not_pass_zero_or_missing_functional_tests(self):
        for role in ("M1","M3"):
            header=("test fec_v2_tests::r1_f2_native_decode_tables_and_workspace_reused_dirty_tail_exact ... ok\n"
                    if role=="M3" else "test game_shared_tests::first_delivery ... ok\n")
            good=header+"test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 20 filtered out\n"
            self.assertEqual(w.verify_functional_log(good,role),1)
            for bad in ("test result: ok. 0 passed; 0 failed; 0 ignored; 100 filtered out",
                        "test result: FAILED. 1 passed; 1 failed; 0 ignored",
                        "compiling... cargo returned 0 without running tests",
                        "test result: ok. 1 passed; 0 failed; 0 ignored; 0 filtered out"):
                # For M3 a success without the named native test is also invalid.
                if role=="M1" and bad.startswith("test result: ok. 1 passed"):
                    continue
                with self.subTest(role=role,bad=bad),self.assertRaises(ValueError):
                    w.verify_functional_log(bad,role)
    def test_manifest_rejects_platform_scalar_old_source_or_missing_binary(self):
        d=request("M3")
        manifest={"schema_version":1,"stage":"prepare","role_id":"M3",
          "scenario":d["scenario"],"seed":d["seed"],"config_sha256":d["config_sha256"],
          "source_sha":B,"harness_sha":H,"baseline_sha":A,"control_sha":CONTROL,
          "platform":"linux-x86_64","native_backend":"official-isal",
          "feature":"native-isal","functional_result":"PASS",
          "binaries_sha256":{"m3-abba":"e"*64}}
        self.assertTrue(w.validate_manifest(manifest,"M3",d,CONTROL))
        for key,value in (("native_backend","scalar"),("platform","windows"),
                          ("feature","default"),("source_sha",A),
                          ("control_sha",A),("functional_result","FAIL"),
                          ("binaries_sha256",{})):
            with self.subTest(key=key),self.assertRaises(ValueError):
                w.validate_manifest(dict(manifest,**{key:value}),"M3",d,CONTROL)
if __name__=="__main__":unittest.main()
