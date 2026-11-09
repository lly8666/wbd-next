import os
import pathlib
import subprocess
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE="548a47cc708d82d45e1722540b6677342f3c8c5b"
HISTORIC="6c5fd909b9f42d1af89c698cdaabc79bbb72e589"
BASES=("h1332-x86-normal-zero-loss","h1360-x86-normal75-zero-loss",
       "h1349-x86-game4-fixed6-20mbps")

class StressSourceLockContract(unittest.TestCase):
    def test_parallel_one_source_true_product_and_original_stop(self):
        f=(ROOT/".github/workflows/m0-plan028-h1458-four-native-x86-stress.yml").read_text()
        self.assertIn("max-parallel: 4",f)
        for scenario in ("normal50","normal75","game4fec20","weaknet30"):
            self.assertIn("scene: "+scenario,f)
        for item in ("run-id: 42555320138","name: m0-plan024-linux-product",
                     "H1458_SOURCE548_NATIVE_X86_GO_TLS_RUST_ISAL_MANIFEST_SHA_PASS",
                     "WBD_PLAN028_H1458_PRODUCT_SOURCE","WBD_PLAN028_STATIC_OWNED_NEIGH=1",
                     "if-no-files-found: warn","V4_PUBLIC_SHARED_TUN_STOP generation="):
            self.assertIn(item,f)
        self.assertNotIn("runs-on: windows",f)
        self.assertNotIn("[plan028-win-linux-1800]",f)
        self.assertIn("actions/upload-artifact@",f)

    def test_historic_source_default_unchanged_and_new_source_whitelisted(self):
        for name in BASES:
            for suffix in ("-fixture.py","-audit.py"):
                f=ROOT/"tools"/("m0-plan028-"+name+suffix)
                content=f.read_text()
                self.assertIn('os.environ.get("WBD_PLAN028_H1458_PRODUCT_SOURCE","'+HISTORIC+'")',content)
                self.assertIn(SOURCE,content)
                self.assertIn("unsupported source pin for H1458 opt-in",content)

    def test_specialized_three_capacity_preflights_and_reject_unknown_source(self):
        env=dict(os.environ,WBD_PLAN028_H1458_PRODUCT_SOURCE=SOURCE,
                 WBD_PLAN028_FAST_SCENE="pressure",WBD_PLAN028_FAST_CAPACITY_STEPS="2",
                 WBD_PLAN028_QDISC_CLOCK_DIAG="1",WBD_H1349_WRAPPER_SOURCE="a"*40,
                 WBD_H1360_WRAPPER_SOURCE="a"*40)
        for name in BASES:
            fixture=ROOT/"tools"/("m0-plan028-"+name+"-fixture.py")
            p=subprocess.run([sys.executable,str(fixture),"--preflight"],env=env,
                             cwd=ROOT,capture_output=True,text=True,timeout=15)
            self.assertEqual(p.returncode,0,(name,p.stderr))
        env["WBD_PLAN028_H1458_PRODUCT_SOURCE"]="f"*40
        fixture=ROOT/"tools"/("m0-plan028-"+BASES[0]+"-fixture.py")
        p=subprocess.run([sys.executable,str(fixture),"--preflight"],env=env,
                         cwd=ROOT,capture_output=True,text=True,timeout=10)
        self.assertNotEqual(p.returncode,0)
        self.assertIn("unsupported source pin",p.stderr)

    def test_auditor_never_promotes_capacity_or_loss_to_full_l3(self):
        s=(ROOT/"tools/m0_plan028_h1458_stress_verdict.py").read_text()
        self.assertIn("actual_sent_udp_packets",s)
        self.assertIn("actual_received_udp_packets",s)
        self.assertIn("real_original_TLS443_and_Rust_TUN",s)
        self.assertIn("INCONCLUSIVE_WEAKNET_ALERTS_PRESENT",s)
        self.assertIn("FAIL_REAL_BUSINESS_OR_OWNED_STOP",s)
        self.assertIn("Windows Wintun 1800s",s)
        self.assertIn("STOP",s)

if __name__=="__main__":
    unittest.main()
