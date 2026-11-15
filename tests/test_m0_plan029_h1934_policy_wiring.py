"""Source-wiring checks of four real original V3 Rust policy ABBA legs."""
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
def read(p):return (ROOT/p).read_text(encoding="utf-8")
class P1OriginalWiring(unittest.TestCase):
 def test_original_rust_v3_four_legs(self):
  s=read("tools/m0_plan029_h1814_p1_tunnel_ab.py")
  self.assertIn('zip(ORDER,MODES)',s)
  self.assertIn('for name,v3,requested_mode in arms:',s)
  self.assertIn('WBD_PLAN029_NATIVE_V3_TRIAL=v3',s)
  self.assertIn('WBD_PLAN029_P1_POLICY_CN_ARM="1" if POLICY_ABBA',s)
  self.assertIn('score(result["legs"],SOURCE)',s)
  self.assertIn('worker_ids(cold)',s)
  self.assertIn('rust_thread_cpu=thread',s)
 def test_same_real_tunnel_alias_and_rule_scale(self):
  s=read("tools/m0_wl_public_normal_e2e.py")
  self.assertIn('if p029_direct or p029_p1_policy:',s)
  self.assertIn('if p029_direct or p029_p1_cn:',s)
  self.assertIn('range(4096)',s)
  self.assertIn('"11.42."+str(i//128)',s)
  self.assertNotIn('"100.64."+str(i//128)',s)
  self.assertIn('range(8192)',s)
  self.assertIn('p1_rate_tunnel_ip=p029_tunnel_alias if p029_p1_policy',s)
  self.assertIn('rate,p1_rate_tunnel_ip,"10.66.0.2"',s)
  self.assertIn('"10.66.0.2",p1_rate_tunnel_ip,"windows"',s)
  self.assertIn('linux_app4=p029_tunnel_alias if p029_direct or p029_p1_policy',s)
 def test_h1946_independent_cold_china_ip_file(self):
  d=read("r0/go_overlay/cmd/wbd-client/m0_native_v4_dispatch_windows.go")
  c=read("r0/go_overlay/cmd/wbd-client/m0_plan029_cold_split_windows.go")
  t=read("r0/go_overlay/cmd/wbd-client/m0_plan029_cold_split_windows_test.go")
  a=read("r0/go_overlay/assembly/manifest-plan020-m0.json")
  self.assertIn('ChinaIPFile string // independent cold Rust CN table',d)
  self.assertIn('cn,e=splitroute.Direct("bypass-lan-cn",o.ChinaIPFile)',c)
  self.assertNotIn('if mode==2{cn=o.Bypass4}',c)
  self.assertIn('TestPlan029H1946Cold4096CNIndependentOfOSBypass',t)
  self.assertIn('ChinaIPFile:*chinaIPFile',a)
 def test_source_locked_one_expensive_test(self):
  w=read(".github/workflows/m0-wl-public-normal-full.yml")
  r=read("tools/m0_wl_native_step_runner.py")
  self.assertIn('WBD_PLAN029_P1_POLICY_ABBA_SCENE:',w)
  self.assertIn('[plan029-v3-real-p1-policy-abba]',w)
  self.assertIn('PASS_SCOPED_P1_SAME_RUST_V3_POLICY_ABBA_MEASURED',w)
  self.assertIn('if env.get("WBD_PLAN029_P1_POLICY_ABBA_SCENE")=="1":',r)
  self.assertIn("return 1850",r)
  # Real functional WinTun TCP45902 listener must accept the exact
  # public guest TUN source in both policy arms, not 10.66.0.1.
  self.assertIn("$env:WBD_PLAN029_P1_AB_SCENE -eq '1' -and",w)
  self.assertIn("$env:WBD_PLAN029_P1_POLICY_ABBA_SCENE -eq '1'",w)
  self.assertIn("'203.0.113.77'\n          }else{'10.66.0.1'}",w)
  self.assertIn("-RemoteAddress $tcpRemote -LocalPort 45902",w)
