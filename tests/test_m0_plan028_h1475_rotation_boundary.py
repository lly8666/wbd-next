import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"tools/m0_plan028_h1475_rotation_boundary_replay.py"
FLOW=ROOT/".github/workflows/m0-plan028-h1475-rotation-10ms-original-offline.yml"

class OriginalRotationBoundary(unittest.TestCase):
    def test_correct_10ms_persistent_deficit_not_transient_inflight(self):
        spec=importlib.util.spec_from_file_location("h1475_unit",SCRIPT)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        tx=[2,2,2,2]+[0]*18997
        rx=[1,3,1,1]+[1,0]+[0]*18995
        # transients must not invent final loss. A genuinely missing
        # packet persists even if new receive catches up in later bins.
        events,n=mod.persistent_deficits(tx,rx)
        self.assertEqual(n,1)
        self.assertEqual(sum(x["new_permanent_deficit"] for x in events),1)
    def test_synthetic_unlost_sent_received_no_permanent_events(self):
        spec=importlib.util.spec_from_file_location("h1475_unit2",SCRIPT)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sent=[1]*19001;recv=sent.copy()
        recv[100]=0;recv[101]=2
        events,n=mod.persistent_deficits(sent,recv)
        self.assertEqual(n,0)
        self.assertEqual(events,[])
    def test_exact_original_artifact_and_sources_not_derived_product(self):
        s=SCRIPT.read_text()
        self.assertIn('SOURCE="66fb6b4454b1ce4297ab04efa20c7f931ff12383"',s)
        self.assertIn("ACTION=42595013191",s)
        self.assertIn("ARTIFACT=13663646307",s)
        self.assertIn("manifest",s)
        self.assertIn('SOURCE',s)
        self.assertIn("STOP",s)
        self.assertIn("M2_first_wire_rotated_vs_static_pct",s)
        self.assertIn("no_new_native_test",s)
    def test_workflow_original_only_and_no_invocation(self):
        s=FLOW.read_text()
        self.assertIn("run-id: 42595013191",s)
        self.assertIn("plan028-h1473-source66fb-reverse-generation-42595013191",s)
        self.assertNotIn("sudo ",s)
        self.assertNotIn("cargo build",s)
        self.assertNotIn("rustup",s)
        self.assertNotIn("wbd-v4-client",s)
        self.assertNotIn("runs-on: windows",s)

if __name__=="__main__":
    unittest.main()
