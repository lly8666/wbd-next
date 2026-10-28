"""Safety and deterministic V2 scenario contract; no driver side effects."""
import json, pathlib, tempfile, unittest
from tools.m0_wl_perf_v2_config import read_scenario,profile
from tools.m0_wl_impairment_profile import get_profile
SCENE=pathlib.Path(__file__).resolve().parents[1]/"scenarios"/"wl-normal-150m-300ms-0loss-60s.json"
class V2Scenarios(unittest.TestCase):
 def test_exact_150m_300ms_0loss_60s(self):
  c=read_scenario(SCENE)
  self.assertEqual(c["duration_s"],60)
  for side in ("windows","linux"):
   p=profile(c,side)
   self.assertEqual((p["offered_mbps"],p["delay_ms"],p["loss_pct"],p["tc_mbit"]),(150,300,0,None))
   self.assertEqual(sum(x["packets_weight"] for x in p["packet_mix"]),100)
  self.assertEqual(read_scenario(SCENE)["scenario_sha256"],c["scenario_sha256"])
 def test_legacy_unchanged(self):
  self.assertEqual(get_profile("n0")["offered_mbps"],10)
  self.assertEqual(get_profile("p200-250m-30p")["loss_pct"],30)
 def test_invalid_mix_refused(self):
  c=json.loads(SCENE.read_text())
  c["windows_to_linux"]["packet_mix"][0]["udp_payload_bytes"]=1500
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/"bad.json"
   p.write_text(json.dumps(c))
   with self.assertRaisesRegex(ValueError,"PACKET_SIZE"):read_scenario(p)
 def test_v2_must_have_exact_path_and_side(self):
  with self.assertRaises(ValueError):get_profile("v2")
  self.assertEqual(get_profile("v2",side="windows",configfile=str(SCENE))["offered_mbps"],150)
 def test_bad_rates_and_loss_refused(self):
  c=json.loads(SCENE.read_text())
  c["linux_to_windows"]["loss_pct"]=101
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/"bad.json"
   p.write_text(json.dumps(c))
   with self.assertRaises(ValueError):read_scenario(p)
if __name__=="__main__":unittest.main()
