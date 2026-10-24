#!/usr/bin/env python3
"""Extract actual duplicate Linux TCP payloads from a bounded owned inner pcap.
No user data or raw content is printed or committed."""
import hashlib, json, pathlib, struct, sys
src, out, receipt = map(pathlib.Path, sys.argv[1:4])
raw = src.read_bytes()
assert 24 <= len(raw) <= 33554432, "owned pcap bounded 32MiB"
if raw[:4] == bytes.fromhex("d4c3b2a1"): order="<"
elif raw[:4] == bytes.fromhex("a1b2c3d4"): order=">"
else: raise ValueError("classic little/big endian pcap expected")
link = struct.unpack_from(order+"I", raw, 20)[0]
assert link == 1, f"veth capture should be EN10MB, found {link}"
items, offset=[], 24
while offset+16 <= len(raw):
    ts_sec,ts_usec=struct.unpack_from(order+"II",raw,offset)
    timestamp_us=ts_sec*1000000+ts_usec
    n=struct.unpack_from(order+"I",raw,offset+8)[0];offset+=16
    assert n<=2048 and offset+n<=len(raw),"capture length exceeds packet bound"
    frame=raw[offset:offset+n];offset+=n
    if len(frame)<14 or frame[12:14]!=b"\x08\x00":continue
    ip=frame[14:]
    if len(ip)<40 or ip[0]>>4!=4 or ip[9]!=6:continue
    ihl=(ip[0]&15)*4
    declared=int.from_bytes(ip[2:4],"big")
    if not (20<=ihl<=60 and ihl+20<=declared<=len(ip)):continue
    packet=bytes(ip[:declared])
    tcp=packet[ihl:]
    th=(tcp[12]>>4)*4
    if not (20<=th<=60 and ihl+th<declared):continue
    data=tcp[th:]
    # exact src A and dest B, no confusion with ACKs/feedback
    if packet[12:16]!=bytes([10,252,31,1]) or packet[16:20]!=bytes([10,252,31,2]):continue
    if not (len(data)>=1305 and data[:3]==b"\x17\x03\x03"):continue
    declared_tls=int.from_bytes(data[3:5],"big")
    if declared_tls<1300:continue
    if len(packet)+33>1500-40:continue
    seq=int.from_bytes(tcp[4:8],"big")
    items.append((seq,packet,bytes(data),ihl+th+5,timestamp_us))
assert offset==len(raw),"trailing truncated packets"
pair=None
for i,(seq,packet,data,h,ts_us) in enumerate(items):
    for nxt in items[i+1:]:
        delta_us=nxt[4]-ts_us
        if seq==nxt[0] and data==nxt[2] and h==nxt[3] and delta_us>=100000:
            pair=(packet,nxt[1],h,seq,delta_us)
            break
    if pair:break
assert pair is not None, ("no witnessed Linux inner TCP payload retransmission; "
                          "do not synthesize duplicate after this assertion")
a,b,h,seq,delta_us=pair
assert len(a)>h+512 and len(b)>h+512
assert a[h:]==b[h:], "true captured B suffix must match"
with out.open("wb") as f:
    for p in (a,b):
        f.write(len(p).to_bytes(2,"big"));f.write(p)
result={
  "provenance":"NATIVE_LINUX_NETNS_VETH_TCP_CAPTURE",
  "outer_oracle":"two captured complete same-seq TLS ciphertext-bearing packets",
  "inner_tcp_seq":seq,"different_capture_events":True,
  "duplicate_interarrival_ms":delta_us/1000,
  "minimum_interval_ms_required":100,
  "inner_packet_lens":[len(a),len(b)],
  "h_prefix_lengths":[h,h],
  "tls_ciphertext_suffix_len":len(a)-h,
  "repeated_64":a[h:h+64]==b[h:h+64],
  "repeated_128":a[h:h+128]==b[h:h+128],
  "inner_pcap_sha256":hashlib.sha256(raw).hexdigest(),
  "inner_pcap_bytes_before_cleanup":len(raw),
  "contains_only_hashes_not_body":True,
  "raw_inner_pcap_retained":False
}
receipt.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
