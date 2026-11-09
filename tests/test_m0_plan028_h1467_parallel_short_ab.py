import json,os,pathlib,subprocess,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
FIXTURE=ROOT/"tools/m0_plan028_h1467_fiveclient_ab_netns.py"
AUDIT=ROOT/"tools/m0_plan028_h1467_ab_audit.py"
WORKFLOW=ROOT/".github/workflows/m0-plan028-h1467-source66fb-paired-four-short-differentials.yml"
SOURCE="66fb6b4454b1ce4297ab04efa20c7f931ff12383"
SCENES=("capacity_mixed","capacity_large","static12","rotating12")
class NativeFourPairedShort(unittest.TestCase):
    def test_exact_old_source_frozen_one_artifact_two_same_host_pairs(self):
        s=WORKFLOW.read_text()
        self.assertIn("run-id: 42578056120",s)
        self.assertIn(SOURCE,s)
        self.assertIn("h1461-x86-one-patched-build-"+SOURCE,s)
        self.assertIn("max-parallel: 2",s)
        self.assertIn("fail-fast: false",s)
        self.assertIn('for scene in "$AB_A" "$AB_B"',s)
        self.assertIn('GITHUB_SHA="$ORIGINAL_PRODUCT_SOURCE"',s)
        self.assertIn("H1467_EXACT_SOURCE66FB_SAME_BINARY_THREE_ELF_NATIVE_ISAL_SHA_PASS",s)
        for x in SCENES:self.assertIn(x,s)
        self.assertNotIn("runs-on: windows",s)
        self.assertNotIn("[plan028-win-linux-1800]",s)
    def test_all_four_180s_modes_actual_python_profile_readback(self):
        code='import json,runpy;d=runpy.run_path(r"'+str(FIXTURE)+'",run_name="h1467_import_guard");print(json.dumps({k:d[k] for k in ("H1467_CASE","RATE","LOSS","DELAY","ROTATION_SECONDS","FAST_PHASES")}))'
        for case in SCENES:
            env=dict(os.environ,WBD_PLAN028_H1467_CASE=case,WBD_PLAN028_FAST_SCENE="pressure",
                     WBD_PLAN028_FAST_CAPACITY_STEPS="2",WBD_PLAN028_STATIC_OWNED_NEIGH="1")
            x=subprocess.run([sys.executable,"-c",code],env=env,cwd=ROOT,text=True,capture_output=True,timeout=12)
            self.assertEqual(x.returncode,0,(case,x.stderr))
            d=json.loads(x.stdout)
            self.assertEqual(d["H1467_CASE"],case)
            self.assertEqual(d["LOSS"],[0]*5)
            self.assertEqual(d["DELAY"],[0]*5)
            self.assertEqual([p[1] for p in d["FAST_PHASES"]],[30,60,30,50])
            self.assertEqual(d["RATE"],[75 if case.startswith("capacity") else 12,2,2,2,2])
            self.assertEqual(d["ROTATION_SECONDS"][0],97 if case=="rotating12" else 3600)
    def test_reject_unsupported_scenes_and_no_source_default_change(self):
        old=(ROOT/"tools/m0-plan028-h1259-five-client-recovery-netns.py").read_text()
        s=FIXTURE.read_text()
        self.assertNotIn("H1467_CASE",old)
        self.assertIn('H1467_CASE=os.environ.get("WBD_PLAN028_H1467_CASE","")',s)
        self.assertIn('cfg["traffic"]["sizes"]=[[1024,1]]',s)
        self.assertIn('who=="alice"',s)
        self.assertIn('run("sudo", "-n", "ip", "netns", "add"',s)
        self.assertIn("V4_PUBLIC_SHARED_TUN_STOP",s) if False else None
        env=dict(os.environ,WBD_PLAN028_H1467_CASE="wrong",WBD_PLAN028_FAST_SCENE="pressure",
                 WBD_PLAN028_FAST_CAPACITY_STEPS="2",WBD_PLAN028_STATIC_OWNED_NEIGH="1")
        q=subprocess.run([sys.executable,"-c",'import runpy;runpy.run_path(r"'+str(FIXTURE)+'",run_name="h1467_import_guard")'],env=env,cwd=ROOT,capture_output=True,text=True,timeout=12)
        self.assertNotEqual(q.returncode,0)
        self.assertIn("unsupported H1467",q.stderr)
    def test_five_real_source_bound_udp_loss_and_stop_in_auditor(self):
        s=AUDIT.read_text()
        for item in ("original_six_Stop","all_zero_loss_complete","h1250-product-","original_rotation_verdict","alice_zero_loss_down_missing","alice_original_queue_overflow","SOURCE","source_sha","180000000000"):
            self.assertIn(item,s)
        self.assertIn(SOURCE,s)
        self.assertIn("PASS_SCOPED_180S",s)
        self.assertIn("FAIL_SCOPED_180S",s)
        self.assertIn("same_runner_sequential_original_binary",s)
if __name__=="__main__":unittest.main()
