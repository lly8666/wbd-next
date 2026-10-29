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
 def test_v2_udp_fixture_socket_headroom_is_extra_but_scoped(self):
  path=pathlib.Path(__file__).resolve().parents[1]/"tools"/"m0_wl_public_rate_app.py"
  app=path.read_text()
  self.assertIn('sys.argv[7]=="v2" else 2)*1024*1024',app)
  self.assertIn('sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, receiver_rcvbuf_request)',app)
  self.assertIn('"requested_socket_rcvbuf_bytes":receiver_rcvbuf_request',app)
  self.assertIn('socket_start=udp_socket_probe(sock) if profile_name=="v2" else None',app)
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
 def test_mode_aware_w168_fixed_game_matrix_reuses_v2_observation(self):
  root=SCENE.parents[0]
  for name,mode,loss in (
   ("wl-fec-fixed6-10m-75ms-loss5-20s","fixed",5),
   ("wl-game2-fixed6-10m-75ms-loss15-20s","game2-fec",15),
   ("wl-game4-fixed6-10m-75ms-loss30-20s","game4-fec",30)):
   s=read_scenario(root/(name+".json"))
   self.assertEqual(s["public_mode"],mode)
   self.assertEqual(s["duration_s"],20)
   for side in ("windows","linux"):
    p=profile(s,side)
    self.assertEqual((p["offered_mbps"],p["delay_ms"],p["loss_pct"]),(10,75,loss))
  legacy=read_scenario(SCENE)
  self.assertEqual(legacy.get("public_mode","normal"),"normal")
 def test_mode_rejects_implicit_game_auto_and_unknown(self):
  original=json.loads(SCENE.read_text())
  with tempfile.TemporaryDirectory() as directory:
   path=pathlib.Path(directory)/"scene.json"
   for mode in ("game-auto","game4-auto","invented"):
    original["public_mode"]=mode
    path.write_text(json.dumps(original))
    with self.assertRaisesRegex(ValueError,"UNSUPPORTED_PUBLIC_MODE"):
     read_scenario(path)
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
class V2ABFailureWitness(unittest.TestCase):
 def test_rust_first_preserves_evidence_if_go_exits(self):
  script=(pathlib.Path(__file__).resolve().parents[1]/"tools"/"m0_wl_perf_v2_ab.py").read_text()
  self.assertIn('for label in ("B","A"):',script)
  self.assertIn('"order":["B","A"]',script)
  self.assertIn('if row["stop"]!="PASS_BOTH_OWNED":break',script)
 def test_native_exit_has_hash_only_allowlisted_signatures(self):
  script=(pathlib.Path(__file__).resolve().parents[1]/"tools"/"m0_wl_public_normal_e2e.py").read_text()
  self.assertIn("WL_V2_FIRST_NATIVE_EXIT",script)
  self.assertIn('"observed_marker_signatures":diagnostic',script)
  self.assertIn('hashlib.sha256(raw.encode("utf-8")).hexdigest()',script)

if __name__=="__main__":unittest.main()
