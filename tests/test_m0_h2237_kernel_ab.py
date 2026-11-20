"""H2237 kernel primitive-only negative tests (never original WBD PASS)."""
import hashlib
import json
import pathlib
import struct
import tempfile
import unittest
from unittest.mock import patch
from tools import m0_h2237_kernel_ab as H

ROOT=pathlib.Path(__file__).resolve().parents[1]

def test_ipv4_tcp(seq=0x12340000):
    body=bytes((k*13+41)&255 for k in range(1024))
    ip=bytearray(20)
    ip[0]=0x45
    ip[2:4]=(1064).to_bytes(2,"big")
    ip[4:6]=(43).to_bytes(2,"big")
    ip[6:8]=(0x4000).to_bytes(2,"big")
    ip[8]=64
    ip[9]=6
    ip[12:16]=bytes((10,248,81,2))
    ip[16:20]=bytes((10,248,82,2))
    ip[10:12]=H.csum(ip).to_bytes(2,"big")
    tcp=bytearray(20)
    tcp[0:2]=(44109).to_bytes(2,"big")
    tcp[2:4]=(44331).to_bytes(2,"big")
    tcp[4:8]=seq.to_bytes(4,"big")
    tcp[8:12]=(1).to_bytes(4,"big")
    tcp[12]=0x50
    tcp[13]=0x18
    tcp[14:16]=(65535).to_bytes(2,"big")
    pseudo=bytes(ip[12:20])+bytes((0,6))+(1044).to_bytes(2,"big")
    tcp[16:18]=H.csum(pseudo+tcp+body).to_bytes(2,"big")
    return bytes(ip)+bytes(tcp)+body

class H2237KernelOnly(unittest.TestCase):
    def test_independent_wire_parser_validates_full_tcp_and_ip(self):
        wire=test_ipv4_tcp()
        self.assertEqual(len(wire),1064)
        self.assertEqual(H.csum(wire[:20]),0)
        pseudo=wire[12:20]+bytes((0,6))+(1044).to_bytes(2,"big")
        self.assertEqual(H.csum(pseudo+wire[20:]),0)
        ethernet=bytes.fromhex("0a0b0c0d0e0f1011121314150800")
        data=ethernet+wire
        header=struct.pack("<IHHIIII",0xa1b2c3d4,2,4,0,0,65535,1)
        record=struct.pack("<IIII",0,0,len(data),len(data))
        with tempfile.TemporaryDirectory() as t:
            name=pathlib.Path(t)/"test.pcap"
            name.write_bytes(header+record+data)
            parsed=H.parse_pcap(name)
            self.assertEqual(list(parsed),[str(0x12340000)])
            self.assertEqual(parsed[str(0x12340000)]["sha256"],
                             hashlib.sha256(wire).hexdigest())
            corrupted=bytearray(data)
            corrupted[-10]^=0x80
            name.write_bytes(header+record+corrupted)
            with self.assertRaisesRegex(ValueError,"TCP_CHECKSUM_INVALID"):
                H.parse_pcap(name)
            corrupted=bytearray(data)
            corrupted[14+8]^=0x80
            name.write_bytes(header+record+corrupted)
            with self.assertRaisesRegex(ValueError,"IP_CHECKSUM_INVALID"):
                H.parse_pcap(name)

    def test_missing_kernel_stats_is_not_zero(self):
        before={name:{"rx_packets":10,"tx_packets":20}
                for name in ("client","router_in","router_out","server")}
        after={name:{"rx_packets":35,"tx_packets":42} for name in before}
        self.assertEqual(H.delta(before,after)["server"]["rx_packets"],25)
        after["server"]["rx_packets"]=5
        with self.assertRaisesRegex(RuntimeError,"COUNTER_RESET"):
            H.delta(before,after)

    def test_c_only_tests_primitive_not_wbd_or_automatic_default(self):
        c=(ROOT/"tools/m0_h2237_linux_tx_primitive.c").read_text()
        python=(ROOT/"tools/m0_h2237_kernel_ab.py").read_text()
        for phrase in ("AF_PACKET","SOCK_DGRAM","SOCK_RAW","IPPROTO_RAW",
                       "IP_HDRINCL","sendmmsg","MSG_DONTWAIT","SO_BINDTODEVICE",
                       "iovecs[i][0]","iovecs[i][1]"):
            self.assertIn(phrase,c)
        self.assertIn('legs=[(100000,"raw"),(100000,"packet")',python)
        self.assertIn('no_wbd_packet_or_real_data',python)
        self.assertIn("verified_equal_IPv4_TCP_bytes",python)
        self.assertIn("real_server_rx_packets",python)
        self.assertIn("paced_100kpps_real_Rx_qualification",python)
        self.assertNotIn("send_kernel_multimsg",python)
        self.assertNotIn("original_tls_connected",python)

if __name__=="__main__":unittest.main()
