"""Safety and deterministic V2 scenario contract; no driver side effects."""
import json, pathlib, tempfile, unittest
from tools.m0_wl_perf_v2_config import read_scenario,profile
from tools.m0_wl_impairment_profile import get_profile
SCENE=pathlib.Path(__file__).resolve().parents[1]/"scenarios"/"wl-normal-150m-300ms-0loss-60s.json"
class V2Scenarios(unittest.TestCase):
 def test_plan027_a4_validated_240s_kernel_phase_source_schema(self):
  scene=SCENE.parent/"plan027-a4-auto-10m-staged-240s.json"
  case=read_scenario(scene)
  self.assertEqual((case["public_mode"],case["duration_s"]),("auto",240))
  stages=case["impairment_stages"]
  self.assertEqual([r["start_s"] for r in stages],[0,20,40,65,95])
  self.assertEqual([r["windows_to_linux"]["loss_pct"] for r in stages],[0,5,15,30,0])
  self.assertEqual([r["linux_to_windows"]["loss_pct"] for r in stages],[0,0,5,15,0])
  self.assertGreaterEqual(case["duration_s"]-stages[-1]["start_s"],120)
  self.assertEqual(case["scenario_sha256"],read_scenario(scene)["scenario_sha256"])
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp)/"bad.json"
   bad=json.loads(scene.read_text());bad["impairment_stages"][2]["start_s"]=20
   p.write_text(json.dumps(bad))
   with self.assertRaisesRegex(ValueError,"BAD_AUTO_STAGE_CLOCK"):read_scenario(p)
   bad=json.loads(scene.read_text());bad["impairment_stages"][-1]["start_s"]=125
   p.write_text(json.dumps(bad))
   with self.assertRaisesRegex(ValueError,"NO_120S_FINAL_OBSERVATION"):read_scenario(p)
   bad=json.loads(scene.read_text());bad["public_mode"]="fixed"
   p.write_text(json.dumps(bad))
   with self.assertRaisesRegex(ValueError,"BAD_AUTO_STAGE_SCOPE"):read_scenario(p)
 def test_plan027_a4_runtime_owned_qdisc_stage_and_live_scheduler_implemented(self):
  root=SCENE.parents[0]
  netem=(root/"tools/m0_wl_netem.py").read_text()
  e2e=(root/"tools/m0_wl_public_normal_e2e.py").read_text()
  for guard in ('elif action == "stage":','WL_V2_STAGE_FOREIGN_KERNEL_OWNER',
                'index!=state.get("stage_index",0)+1','"qdisc","change"',
                'WL_V2_OWNED_KERNEL_STAGE_APPLIED','wl-v2-kernel-stage-'):
   self.assertIn(guard,netem)
  for guard in ('phase_schedule=scenario.get("impairment_stages")',
                'netem("stage",phase_next_index)',
                'WL_V2_AUTO_KERNEL_PHASE_NOT_APPLIED',
                '"kernel_phases_applied"','"a4_auto_mature_grade"'):
   self.assertIn(guard,e2e)
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
 def test_plan027_a2_a3_real_bidirectional_scenes_are_separate_and_bounded(self):
  for name,mode,loss in (
   ("plan027-a2-normal-10m-250ms-0loss-60s","normal",0),
   ("wl-outer-repair-10m-250ms-loss30-60s","normal",30),
   ("wl-outer-repair-fixed-10m-250ms-loss30-60s","fixed",30)):
   path=SCENE.parent/(name+".json")
   c=read_scenario(path)
   self.assertEqual((c["scenario_id"],c["public_mode"],c["duration_s"],c["tun_mtu"],c["seed"]),
    (name,mode,60,1400,20261030))
   self.assertEqual(c["warmup_s"],5)
   for side in ("windows","linux"):
    p=profile(c,side)
    self.assertEqual((p["offered_mbps"],p["delay_ms"],p["loss_pct"]),(10,250,loss))
    self.assertEqual(sum(row["packets_weight"] for row in p["packet_mix"]),100)
 def test_plan027_capacity_gradient_and_300s_long_are_source_locked(self):
  names=(("plan027-c-normal-10m-25ms-loss0-60s",10,60),
         ("plan027-c-normal-50m-25ms-loss0-60s",50,60),
         ("plan027-c-normal-100m-25ms-loss0-60s",100,60),
         ("plan027-c-normal-200m-25ms-loss0-60s",200,60),
         ("plan027-c-normal-10m-25ms-loss0-300s",10,300))
  for name,mb,duration in names:
   p=SCENE.parent/(name+".json")
   case=read_scenario(p)
   self.assertEqual((case["scenario_id"],case["duration_s"],case["public_mode"]),(name,duration,"normal"))
   for side in ("windows","linux"):
    prof=profile(case,side)
    self.assertEqual((prof["offered_mbps"],prof["delay_ms"],prof["loss_pct"]),(mb,25,0))
   if duration==300:
    changed=json.loads(p.read_text());changed["duration_s"]=301
    with tempfile.TemporaryDirectory() as d:
     bad=pathlib.Path(d)/"bad.json";bad.write_text(json.dumps(changed))
     with self.assertRaisesRegex(ValueError,"WL_V2_BAD_duration_s"):read_scenario(bad)
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
