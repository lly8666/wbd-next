import unittest
from tools.m0_wl_public_mss_contract import verified_plan028_shared_manual_two_generation_v4_mss as verify

class SharedMssTest(unittest.TestCase):
 def test_two_real_sessions_and_rejects_bad_tcp_options(self):
  w=""
  for g in (1,2):
   w+=f"WBD_WINDOWS_COLD_MSS_BUDGET_V1 side=client generation={g} mode=normal configured_outer_mtu=1460 physical_outer_mtu=1500 effective_outer_mtu=1460 local_advertised_mss=1420 inner_mtu_planned=1389 limiting_reason=configured_outer_ipv4 source=RUST_V1_REAL_OS\n"
   w+=f"WBD_WINDOWS_ACTUAL_SYN_MSS_V1 side=client generation={g} local_advertised_mss=1420 tcp_option_bytes=0204058c\n"
   w+=f"WBD_WINDOWS_PEER_SYNACK_MSS_V1 side=client generation={g} peer_advertised_mss=1420 local_advertised_mss=1420\n"
  l="V4_PUBLIC_MTU_PREPARE role=server mtu_budget_version=3 outer_config=1460 interface=1500 advertised_mss=1420 record_offer=1420 tun_planned=1389\n"
  for count in (1,2):
   l+="V4_PUBLIC_ACTUAL_HANDSHAKE_MSS_V1 side=server generation=1 kind=SYNACK local_advertised_mss=1420 tcp_option_bytes=0204058c\n"
   l+=f"V4_PUBLIC_MULTI_SESSION_READY role=server one_port=443 active_detached_flows={count} auto_lease=0 original_TLS=1 Rust_M4=1\n"
  self.assertEqual([r["generation"] for r in verify(w,l,1460)],[1,2])
  self.assertEqual(verify(w,l,1460)[1]["linux_received_peer_syn_mss"],"NOT_LOGGED_SHARED_MANUAL")
  for badw,badl in ((w,l.replace("active_detached_flows=2","active_detached_flows=3")),(w.replace("generation=2 peer_advertised_mss=1420","generation=2 peer_advertised_mss=1360"),l),(w,l.replace("tcp_option_bytes=0204058c","tcp_option_bytes=0204058d"))):
   with self.assertRaises(ValueError):verify(badw,badl,1460)
  with self.assertRaises(ValueError):verify(w,l,1280)
