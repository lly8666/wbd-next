"""Parser-only regression. Synthetic frames are NEVER handshake qualification.

The real PLAN028 verdict comes only from source-locked kernel TCP captures.
These tiny inert records protect dynamic WSL2 server-IP tuple selection.
"""
import pathlib
import struct
import sys
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from m0_plan028_tls_wire_audit import audit

def _record(kind,body):
    hs=bytes([kind])+len(body).to_bytes(3,"big")+body
    return b"\x16\x03\x03"+len(hs).to_bytes(2,"big")+hs

def _frame(source,dest,sport,dport,seq,payload):
    import ipaddress
    src=ipaddress.IPv4Address(source).packed
    dst=ipaddress.IPv4Address(dest).packed
    ip=b"\x45\x00"+(40+len(payload)).to_bytes(2,"big")+b"\x00\x01\x00\x00\x40\x06\x00\x00"+src+dst
    tcp=struct.pack("!HHIIBBHHH",sport,dport,seq,0,0x50,0x18,8192,0,0)
    return b"\x00"*12+b"\x08\x00"+ip+tcp+payload

def _pcap(server_first=False):
    ext=(b"\x00\x2b\x00\x03\x02\x03\x04"+
         b"\x00\x33\x00\x02\x00\x00")
    body=(b"\x03\x03"+b"\x01"*32+b"\x20"+b"\x03"*32+
          b"\x00\x02\x13\x01"+b"\x01\x00"+len(ext).to_bytes(2,"big")+ext)
    client=_frame("172.19.12.2","172.19.12.14",41031,443,100,_record(1,body))
    server=_frame("172.19.12.14","172.19.12.2",443,41031,200,_record(2,b"\x00"*40))
    items=[(server,1),(client,2)] if server_first else [(client,1),(server,2)]
    out=bytearray(struct.pack("<IHHIIII",0xa1b2c3d4,2,4,0,0,65535,1))
    for packet,t in items:
        out+=struct.pack("<IIII",t,0,len(packet),len(packet))+packet
    return bytes(out)

class RealCaptureParserOnly(unittest.TestCase):
    def test_wsl2_dynamic_server_ip_and_exact_expected_ip(self):
        raw=_pcap()
        inferred=audit(raw)
        pinned=audit(raw,server_ip="172.19.12.14")
        for data in (inferred,pinned):
            self.assertEqual(data["actual_tls_server_ipv4"],"172.19.12.14")
            self.assertEqual(data["client_first_payload"],"TLS_Handshake_ClientHello")
            self.assertEqual(data["server_first_payload"],"TLS_Handshake_ServerHello")
            self.assertEqual(data["session_id_length"],32)
            self.assertEqual(data["client_tcp_segments_observed"],1)
        with self.assertRaisesRegex(AssertionError,"selected server"):
            audit(raw,server_ip="172.19.12.99")

    def test_no_server_application_bytes_before_client_hello(self):
        with self.assertRaisesRegex(AssertionError,"before ClientHello"):
            audit(_pcap(server_first=True),server_ip="172.19.12.14")

if __name__=="__main__":
    unittest.main()
