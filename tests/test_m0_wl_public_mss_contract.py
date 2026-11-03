import unittest
from tools.m0_wl_public_mss_contract import verified_current_v4_mss
class CurrentMssWire(unittest.TestCase):
 def test_1460_and_negative_peer(self):
  w="WBD_WINDOWS_COLD_MSS_BUDGET_V1 side=client generation=1 mode=0 configured_outer_mtu=1460 physical_outer_mtu=1500 effective_outer_mtu=1460 local_advertised_mss=1420 inner_mtu_planned=1389 limiting_reason=configured_outer_ipv4 source=RUST_V1_REAL_OS\nWBD_WINDOWS_ACTUAL_SYN_MSS_V1 side=client generation=1 local_advertised_mss=1420 tcp_option_bytes=0204058c\nWBD_WINDOWS_PEER_SYNACK_MSS_V1 side=client generation=1 peer_advertised_mss=1420 local_advertised_mss=1420\n"
  l="2026 V4_PUBLIC_MTU_PREPARE role=server mtu_budget_version=3 outer_config=1460 interface=1500 advertised_mss=1420 record_offer=1420 tun_planned=1389\n2026 V4_PUBLIC_ACTUAL_PEER_SYN_MSS_V1 side=server peer_advertised_mss=1420\n2026 V4_PUBLIC_ACTUAL_HANDSHAKE_MSS_V1 side=server generation=1 kind=SYNACK local_advertised_mss=1420 tcp_option_bytes=0204058c\n"
  v=verified_current_v4_mss(w,l,1460)
  self.assertEqual((v["windows_local_syn_mss"],v["linux_expected_normal_inner"]),(1420,1389))
  for bad in (w.replace("physical_outer_mtu=1500","physical_outer_mtu=1280"),w.replace("peer_advertised_mss=1420","peer_advertised_mss=1360")):
   with self.assertRaises(ValueError):verified_current_v4_mss(bad,l,1460)
  with self.assertRaises(ValueError):verified_current_v4_mss(w,l.replace("advertised_mss=1420","advertised_mss=1360"),1460)
 def test_1280_real_go_syn_synack_source_vector(self):
  w=("WBD_WINDOWS_COLD_MSS_BUDGET_V1 side=client generation=1 mode=0 configured_outer_mtu=1280 physical_outer_mtu=1500 effective_outer_mtu=1280 local_advertised_mss=1240 inner_mtu_planned=1209 limiting_reason=configured_outer_ipv4 source=RUST_V1_REAL_OS\n"
     "WBD_WINDOWS_ACTUAL_SYN_MSS_V1 side=client generation=1 local_advertised_mss=1240 tcp_option_bytes=020404d8\n"
     "WBD_WINDOWS_PEER_SYNACK_MSS_V1 side=client generation=1 peer_advertised_mss=1240 local_advertised_mss=1240\n")
  l=("2026 V4_PUBLIC_MTU_PREPARE role=server mtu_budget_version=3 outer_config=1280 interface=1500 advertised_mss=1240 record_offer=1240 tun_planned=1209\n"
     "2026 V4_PUBLIC_ACTUAL_PEER_SYN_MSS_V1 side=server peer_advertised_mss=1240\n"
     "2026 V4_PUBLIC_ACTUAL_HANDSHAKE_MSS_V1 side=server generation=1 kind=SYNACK local_advertised_mss=1240 tcp_option_bytes=020404d8\n")
  actual=verified_current_v4_mss(w,l,1280)
  self.assertEqual((actual["windows_local_syn_mss"],actual["linux_expected_normal_inner"]),(1240,1209))
  self.assertEqual(actual["proof"],"ACTUAL_GO_TCP_OPTIONS_AND_INBOUND_PEER")
  with self.assertRaises(ValueError):
   verified_current_v4_mss(w.replace("local_advertised_mss=1240","local_advertised_mss=1420"),l,1280)
  with self.assertRaises(ValueError):
   verified_current_v4_mss(w,l,1500)
if __name__=="__main__":unittest.main()
