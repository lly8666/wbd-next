import pathlib
import tempfile
import unittest
from tools.m0_linux_two_end_mtu_receipt import verify
class LinuxTwoEndRealReceiptTests(unittest.TestCase):
 def case(self,mode,outer,server_outer,client_mtu,server_mtu,server_mss=None):
  sm=server_mss or server_outer-40
  cm=outer-40
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp)
   for side,configured,local,peer,inner,first,offer in (
     ("client",outer,cm,sm,client_mtu,"SYNACK",cm),
     ("server",server_outer,sm,cm,server_mtu,"SYN",sm)):
    log="\n".join((
      f"V4_PUBLIC_ACTUAL_HANDSHAKE_MSS_V1 side={side} generation=1 kind=syn local_advertised_mss={local} tcp_option_bytes=0204{local:04x}",
      f"V4_PUBLIC_ACTUAL_PEER_{first}_MSS_V1 side={side} peer_advertised_mss={peer}",
      f"V4_PUBLIC_MTU_PREPARE role={side} mtu_budget_version=3 outer_config={configured} interface=1500 advertised_mss={local} record_offer={offer} tun_planned={configured-(71 if mode=='normal' else 85)}",
      f"V4_PUBLIC_MTU role={side} mtu_budget_version=3 outer_config={configured} interface=1500 advertised_mss={local} peer_mss={peer} local_record_cap={offer} peer_record_cap={min(cm,sm)} record_wire={min(cm,sm)} tun_mtu={inner} fec=fixed lanes=1",
     ))
    (root/(side+".log")).write_text(log)
   (root/"mtu-boundary.txt").write_text(
     f"ARM64_REAL_MTU_BOUNDARY_PASS mode={mode} direction=c2s inner_ipv4={client_mtu} df_plus_one=REJECTED\n"+
     f"ARM64_REAL_MTU_BOUNDARY_PASS mode={mode} direction=s2c inner_ipv4={server_mtu} df_plus_one=REJECTED\n")
   return verify(root,mode,outer,server_outer)
 def test_normal_fixed_auto_1460(self):
  for mode,inner in (("normal",1389),("fec-fixed",1375),("fec-auto",1375)):
   result=self.case(mode,1460,1460,inner,inner)
   self.assertEqual(result["client"]["local_advertised_mss"],1420)
   self.assertEqual(result["server"]["agreed_record_wire_cap"],1420)
 def test_explicit_1500_fixed(self):
  result=self.case("fec-fixed",1500,1500,1415,1415)
  self.assertEqual(result["server"]["inner_tun_os_applied"],1415)
 def test_asymmetric_real_peer_mss_lowers_both(self):
  result=self.case("fec-fixed",1500,1280,1195,1195)
  self.assertEqual(result["client"]["received_peer_mss"],1240)
  self.assertEqual(result["server"]["received_peer_mss"],1460)
 def test_green_but_old_56b_1333_is_rejected(self):
  with self.assertRaisesRegex(ValueError,"hidden FEC1 56B"):
   self.case("fec-fixed",1460,1460,1333,1333)
if __name__=="__main__":unittest.main()
