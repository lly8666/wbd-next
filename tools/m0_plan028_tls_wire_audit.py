#!/usr/bin/env python3
"""Bounded native TCP byte-stream TLS first-flight audit, no PCAP retained.
Input is an ephemeral tcpdump classic pcap on the real kernel veth, output a
redacted JSON summary only. A record is NOT assumed to equal one TCP segment.
"""
import hashlib
import json
import pathlib
import struct
import sys

def audit(raw):
    if len(raw)<24: raise AssertionError("short pcap")
    magic=raw[:4]
    if magic==b"\xd4\xc3\xb2\xa1": endian="<"
    elif magic==b"\xa1\xb2\xc3\xd4": endian=">"
    else: raise AssertionError("pcap must use classic microsecond format")
    _,_,_,_,_,_,link=struct.unpack_from(endian+"IHHIIII",raw)
    if link!=1: raise AssertionError("veth must use ethernet capture")
    records=[]
    off=24
    while off+16<=len(raw):
        sec,usec,inc,orig=struct.unpack_from(endian+"IIII",raw,off)
        off+=16
        if inc>65535 or off+inc>len(raw):raise AssertionError("truncated frame")
        frame=raw[off:off+inc];off+=inc
        if len(frame)<34 or frame[12:14]!=b"\x08\x00":continue
        ip=frame[14:]
        ihl=(ip[0]&15)*4
        if len(ip)<ihl+20 or ip[9]!=6:continue
        total=int.from_bytes(ip[2:4],"big")
        if total>len(ip) or total<ihl+20:continue
        tcp=ip[ihl:total]
        hlen=(tcp[12]>>4)*4
        if hlen<20 or len(tcp)<hlen:continue
        sp=int.from_bytes(tcp[:2],"big");dp=int.from_bytes(tcp[2:4],"big")
        if sp!=443 and dp!=443:continue
        payload=tcp[hlen:]
        if not payload:continue
        src=".".join(map(str,ip[12:16]))
        dst=".".join(map(str,ip[16:20]))
        records.append((sec,usec,src,dst,sp,dp,int.from_bytes(tcp[4:8],"big"),payload))
    if not records:raise AssertionError("no actual TCP payload on 443")
    clients=[r for r in records if r[3]=="10.25.0.1" and r[5]==443]
    servers=[r for r in records if r[2]=="10.25.0.1" and r[4]==443]
    if not clients or not servers:raise AssertionError("no two-way TLS")
    # One original product client tuple: first SYN/ClientHello, no stitched
    # unrelated sessions. Handle retransmissions by TCP sequence de-duplication.
    port=clients[0][4]
    clients=[r for r in clients if r[4]==port]
    servers=[r for r in servers if r[5]==port]
    if not servers:raise AssertionError("no matching server TCP tuple")
    if (servers[0][0],servers[0][1]) < (clients[0][0],clients[0][1]):
        raise AssertionError("server emitted application payload before ClientHello")
    def reassemble(rows):
        unique={}
        for r in rows:unique.setdefault(r[6],r[7])
        start=rows[0][6]
        out=bytearray()
        for seq,p in sorted(unique.items(),key=lambda item:(item[0]-start)&0xffffffff):
            if seq==(start+len(out))&0xffffffff:out.extend(p)
            elif ((seq-start)&0xffffffff)<len(out):
                n=len(out)-((seq-start)&0xffffffff)
                if n<len(p):out.extend(p[n:])
            else:break
        return bytes(out),len(rows)
    c,cn=reassemble(clients)
    s,sn=reassemble(servers)
    def first(stream,expected,name):
        if len(stream)<9 or stream[:1]!=b"\x16" or stream[1]!=3:
            raise AssertionError(name+" first payload is not TLS handshake record")
        n=int.from_bytes(stream[3:5],"big")
        if n<38 or n>16384 or len(stream)<n+5:raise AssertionError(name+" TLS record length")
        if stream[5]!=expected:raise AssertionError(name+" wrong handshake message")
        hs=int.from_bytes(stream[6:9],"big")
        if hs>n-4:raise AssertionError(name+" impossible handshake length")
        return n+5
    cl=first(c,1,"client")
    sl=first(s,2,"server")
    # handshake header 4, ClientHello.legacy_version 2, random 32
    hs=c[5:cl]
    if len(hs)<43 or hs[4:6]!=b"\x03\x03":raise AssertionError("bad ClientHello legacy_version")
    sidpos=4+2+32
    if hs[sidpos]!=32:raise AssertionError("not 32B compatible TLS SessionID")
    pos=sidpos+1+32
    if pos+2>len(hs):raise AssertionError("ClientHello cipher suite length")
    suites=int.from_bytes(hs[pos:pos+2],"big");pos+=2+suites
    if suites%2 or not suites or pos>=len(hs):raise AssertionError("cipher suites malformed")
    compression=hs[pos];pos+=1+compression
    if pos+2>len(hs):raise AssertionError("compression malformed")
    extlen=int.from_bytes(hs[pos:pos+2],"big");pos+=2
    if pos+extlen!=len(hs):raise AssertionError("ClientHello extension length disagrees")
    end=pos+extlen;ex=[]
    while pos<end:
        if pos+4>end:raise AssertionError("short TLS extension header")
        typ=int.from_bytes(hs[pos:pos+2],"big")
        ln=int.from_bytes(hs[pos+2:pos+4],"big")
        pos+=4
        if pos+ln>end:raise AssertionError("TLS extension overrun")
        ex.append(typ);pos+=ln
    if 43 not in ex or 51 not in ex:raise AssertionError("TLS1.3 versions or keyshare missing")
    if b"WB-R1" in c[:cl] or b"WB-R1" in s[:sl]:
        raise AssertionError("project pre-TLS X25519 prelude leaked")
    return {
        "result":"REAL_TCP_STREAM_TLS_FIRST_FLIGHT_PASS",
        "client_first_payload":"TLS_Handshake_ClientHello",
        "server_first_payload":"TLS_Handshake_ServerHello",
        "server_early_application_bytes":0,
        "client_hello_record_bytes":cl,
        "server_hello_record_bytes":sl,
        "client_tcp_segments_observed":cn,
        "server_tcp_segments_observed":sn,
        "session_id_length":32,
        "extensions_count":len(ex),
        "extension_types":[str(x) for x in ex],
        "client_hello_sha256":hashlib.sha256(c[:cl]).hexdigest(),
        "tls_record_length_units":"TCP_reassembled",
        "qualified_traffic":"isolated_real_ipv4_tcp_netns_443; NOT full site fingerprint impersonation"
    }

if __name__=="__main__":
    if len(sys.argv)!=2:sys.exit("usage: audit.py ephemeral-private.pcap")
    print(json.dumps(audit(pathlib.Path(sys.argv[1]).read_bytes()),sort_keys=True))
