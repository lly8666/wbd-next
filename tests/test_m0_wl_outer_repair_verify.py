import pathlib,sys,unittest,copy
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from m0_wl_outer_repair_verify import verify
class OuterRepairQualification(unittest.TestCase):
 def setUp(self):
  self.scene={"scenario_id":"wl-outer-repair-50m-300ms-loss30-60s","scenario_sha256":"abc","duration_s":60,"windows_to_linux":{"offered_mbps":50,"loss_pct":30}}
  self.report={"source":"a"*40,"mode":"normal","stop":"PASS_BOTH_OWNED","WL_V2":{"scenario_sha256":"abc","status":"MEASURED_BOTH_OS_KERNEL","owned_stop":"PASS_BOTH_OWNED","offered_mbps":{"windows":50,"linux":49},"first_delivery_fraction":{"windows":.75,"linux":.74}}}
  self.tc={"eth0":[{"kind":"netem","drops":100}],"ifb":[{"kind":"netem","drops":100}]}
 def line(self,r=28_000_000,u=0,f=350_000_000,k=100_000):
  return f"WBD_WINDOWS_NATIVE_OUTER_REPAIR source_wire_bytes={f} repair_accepted_wire_bytes={r} repair_uncertain_wire_bytes={u} control_wire_bytes={k} repair_packets=3000 r_to_f_ppm={(r+u)*1_000_000//f} r_to_total_ppm={(r+u)*1_000_000//(f+r+u+k)} joined=true"
 def test_valid_high_loss_does_not_require_999_delivery(self):
  self.assertEqual(verify(self.scene,self.report,self.line(),self.tc)["status"],"PASS_SCOPED_WINDOWS_OUTER_REPAIR")
 def test_uncertain_charged_to_cap(self):
  with self.assertRaisesRegex(ValueError,"TEN_PERCENT"):verify(self.scene,self.report,self.line(r=40_000_000,u=3_000_000),self.tc)
 def test_zero_high_loss_repair_fails(self):
  with self.assertRaisesRegex(ValueError,"BELOW_6"):verify(self.scene,self.report,self.line(r=0),self.tc)
 def test_no_fake_run_or_stop_or_drop(self):
  with self.assertRaisesRegex(ValueError,"UNVERIFIED"):verify(self.scene,{**self.report,"stop":"NOT_RUN"},self.line(),self.tc)
  with self.assertRaisesRegex(ValueError,"KERNEL_TC"):verify(self.scene,self.report,self.line(),{"eth0":[],"ifb":[]})
  with self.assertRaisesRegex(ValueError,"UNIQUE"):verify(self.scene,self.report,self.line()+"\n"+self.line(),self.tc)
if __name__=="__main__":unittest.main()
