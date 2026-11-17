#!/usr/bin/env python3
"""PLAN029 H2019: inspect original WSL2 eth0 tcpdump bytes, never a synthetic receipt.

Captures opaque authenticated TLS-looking M1 records as real TCP payloads;
it cannot decrypt or directly infer padding from individual ciphertexts.
Only original Rust NPF acceptance counters + exact delivered application
TCP/UDP + this physical size distribution together validate the effect.
"""
import collections,ipaddress,json,struct,sys

def assess(raw,windows_source,peer_ip,outer_mtu):
 if not isinstance(raw,bytes) or len(raw)<24 or len(raw)>64*1024*1024:
  raise RuntimeError("bounded original eth0 pcap missing/oversized")
 magic=raw[:4]
 if magic in (b"\xd4\xc3\xb2\xa1",b"\x4d\x3c\xb2\xa1"):order="<"
 elif magic in (b"\xa1\xb2\xc3\xd4",b"\xa1\xb2\x3c\x4d"):order=">"
 else:raise RuntimeError("unrecognized tcpdump pcap magic")
 major,minor=struct.unpack_from(order+"HH",raw,4)
 linktype=struct.unpack_from(order+"I",raw,20)[0]
 if major!=2 or minor!=4 or linktype!=1:
  raise RuntimeError("real WSL2 eth0 capture must be classic Ethernet pcap")
 local=ipaddress.IPv4Address(windows_source).packed
 remote=ipaddress.IPv4Address(peer_ip).packed
 if not 576<=outer_mtu<=1500:raise RuntimeError("bad original measured MTU")
 pos=24;segments=0;app_records=0;lengths=[];max_l3=0;short=0
 while pos<len(raw):
  if pos+16>len(raw):raise RuntimeError("truncated pcap record header")
  ts_sec,ts_us,inc,wire_len=struct.unpack_from(order+"IIII",raw,pos);pos+=16
  if inc>4096 or inc>wire_len or pos+inc>len(raw):
   raise RuntimeError("corrupted or unbounded source pcap record")
  frame=raw[pos:pos+inc];pos+=inc
  if len(frame)<14:continue
  ether=struct.unpack_from("!H",frame,12)[0];start=14
  if ether in (0x8100,0x88a8) and len(frame)>=18:
   ether=struct.unpack_from("!H",frame,16)[0];start=18
  if ether!=0x0800 or len(frame)<start+20:continue
  ip=frame[start:]
  ihl=(ip[0]&15)*4
  if ip[0]>>4!=4 or ihl<20 or len(ip)<ihl+20 or ip[9]!=6:continue
  if ip[12:16]!=local or ip[16:20]!=remote:continue
  total=struct.unpack_from("!H",ip,2)[0]
  if total<ihl+20 or len(ip)<total:
   short+=1;continue
  tcp=ip[ihl:total]
  tcp_hdr=(tcp[12]>>4)*4
  if tcp_hdr<20 or tcp_hdr>len(tcp):continue
  if struct.unpack_from("!H",tcp,2)[0]!=443:continue
  payload=tcp[tcp_hdr:]
  if not payload:continue
  segments+=1;max_l3=max(max_l3,total)
  if total>outer_mtu:
   raise RuntimeError("genuine captured original encrypted payload exceeded outer MTU")
  if len(payload)>=31 and payload[:3]==b"\x17\x03\x03" and (
      struct.unpack_from("!H",payload,3)[0]==len(payload)-5):
   app_records+=1;lengths.append(len(payload))
 if pos!=len(raw):raise RuntimeError("pcap framing mismatch")
 if segments<5 or app_records<5:
  raise RuntimeError("too few true original outbound TLS-looking records in eth0 capture")
 counts=collections.Counter(lengths)
 if len(counts)<3 or max(lengths)-min(lengths)<50:
  raise RuntimeError("real encrypted M1 record lengths show no meaningful variation")
 return {
  "capture":"TRUE_WSL2_ETH0_TCPDUMP_FROM_ORIGINAL_WINDOWS_NPF",
  "source_windows_ip":windows_source,"server_physical_ip":peer_ip,
  "outer_mtu_limit":outer_mtu,"max_captured_l3_bytes":max_l3,
  "outbound_tcp_payload_segments":segments,
  "tls_looking_exact_record_count":app_records,
  "record_payload_min_bytes":min(lengths),
  "record_payload_max_bytes":max(lengths),
  "distinct_ciphertext_record_lengths":len(counts),
  "record_length_spread_bytes":max(lengths)-min(lengths),
  "top_lengths":[{"bytes":n,"count":v} for n,v in counts.most_common(12)],
  "raw_pcap_retained":False,
  "per_record_inferred_padding":"CANNOT_DECRYPT_FROM_PHYSICAL_PCAP_ONLY",
  "interpretation":"Opaque actual Ethernet record size distribution plus original M1 accepted pad counters and kernel business/Stop receipt"
 }
if __name__=="__main__":
 if len(sys.argv)!=5:raise SystemExit("pcap-file windows-ip peer-ip outer-mtu")
 from pathlib import Path
 print(json.dumps(assess(Path(sys.argv[1]).read_bytes(),sys.argv[2],
                         sys.argv[3],int(sys.argv[4])),sort_keys=True))
