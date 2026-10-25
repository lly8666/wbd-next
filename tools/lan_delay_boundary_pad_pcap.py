#!/usr/bin/env python3
"""Independent actual outgoing TCP pcap + monotonic gate and selective pad audit.
The raw encrypted wire capture is owned by CI and deleted after SHA256 auditing.
"""
import argparse,hashlib,json,pathlib,struct

TEST_SNI=b"private.inner-wbd.example"
MTU=1500
UNDERLAY=40
MAX_WIRE=MTU-UNDERLAY
def timed_segments(raw,port):
    assert len(raw)>=24
    tag=raw[:4]
    order="<" if tag in (bytes.fromhex("d4c3b2a1"),bytes.fromhex("4d3cb2a1")) else ">"
    assert tag in [bytes.fromhex(x) for x in ("d4c3b2a1","4d3cb2a1","a1b2c3d4","a1b23c4d")]
    nanos=tag in [bytes.fromhex(x) for x in ("4d3cb2a1","a1b23c4d")]
    link=struct.unpack_from(order+"I",raw,20)[0]
    assert link in (1,113,0)
    offset=24;segs=[]
    while offset+16<=len(raw):
        sec,frac,cap,orig=struct.unpack_from(order+"IIII",raw,offset)
        offset+=16
        assert cap<=65535 and offset+cap<=len(raw)
        pkt=raw[offset:offset+cap];offset+=cap
        if link==1:
            if len(pkt)<14 or pkt[12:14]!=b"\x08\x00":continue
            ip=pkt[14:]
        elif link==113:
            if len(pkt)<16 or pkt[14:16]!=b"\x08\x00":continue
            ip=pkt[16:]
        else:
            if len(pkt)<4 or int.from_bytes(pkt[:4],"little")!=2:continue
            ip=pkt[4:]
        if len(ip)<40 or ip[0]>>4!=4 or ip[9]!=6:continue
        ihl=(ip[0]&15)*4
        total=int.from_bytes(ip[2:4],"big")
        if ihl<20 or total<ihl+20 or len(ip)<ihl+20:continue
        tcp=ip[ihl:]
        thl=(tcp[12]>>4)*4
        if thl<20 or total<ihl+thl:continue
        if int.from_bytes(tcp[2:4],"big")!=port:continue
        body=ip[ihl+thl:min(total,len(ip))]
        if not body:continue
        ts=sec+frac/(1e9 if nanos else 1e6)
        seq=int.from_bytes(tcp[4:8],"big")
        segs.append((seq,body,ts))
    assert offset==len(raw)
    return segs

def audit(pcap,port,manifest):
    raw=pcap.read_bytes()
    assert 0<len(raw)<=4*1024*1024
    meta=json.loads(manifest.read_text())
    specs=meta["records"]
    assert 20<=len(specs)<=60
    assert meta["MtuBytes"]==MTU and meta["OuterIPTCPOverhead"]==UNDERLAY
    assert 11000<=meta["ChosenHoldMs"]<=21000
    assert meta["inner_tls13_genuine"] and meta["outer_mutual_tls13_genuine"]
    assert meta["aes_fallback_tamper_rejected"] and meta["plaintext_roundtrip_all"]
    entries=timed_segments(raw,port)
    assert entries
    uniq={};duplicates=0
    for seq,body,ts in entries:
        if seq in uniq:
            assert uniq[seq][0]==body,"outer same-seq bytes changed"
            duplicates+=1
        else:uniq[seq]=(body,ts)
    base=min(uniq);wire=bytearray()
    for seq,(chunk,ts) in sorted(uniq.items()):
        ix=(seq-base)&0xffffffff
        assert ix<=len(wire),"outer TCP capture gap"
        overlap=len(wire)-ix
        if overlap:
            assert wire[ix:ix+min(overlap,len(chunk))]==chunk[:overlap]
        wire.extend(chunk[max(overlap,0):])
    assert TEST_SNI not in wire,"inner SNI marker leaked into outer TCP"
    frames=[];at=0
    while at<len(wire):
        assert at+5<=len(wire)
        typ=wire[at];version=wire[at+1:at+3]
        assert typ in (20,21,22,23) and version in (b"\x03\x01",b"\x03\x03")
        n=int.from_bytes(wire[at+3:at+5],"big")
        assert 0<n<=16640 and at+5+n<=len(wire)
        seq=(base+at)&0xffffffff
        first_time=min(
            (ts for start,(frag,ts) in uniq.items()
             if 0<=((seq-start)&0xffffffff)<len(frag)),
            default=None)
        assert first_time is not None,"missing TCP timestamp at record start"
        frames.append((seq,bytes(wire[at:at+5+n]),first_time))
        at+=5+n
    assert len(frames)>len(specs)
    hs=frames[:-len(specs)]
    observed=frames[-len(specs):]
    assert hs[0][1][0]==22
    assert any(b[1][0]==23 for b in hs)
    aes=0;xor=0;padded=0;unpadded=0;zero_room=0;pad_sum=0
    first_xor_ts=None;client_finished_ts=None
    label_map={}
    for (_,frame,ts),m in zip(observed,specs):
        name=m["label"]
        assert name not in label_map
        label_map[name]=(frame,ts)
        assert frame[:3]==b"\x17\x03\x03"
        assert int.from_bytes(frame[3:5],"big")==len(frame)-5
        assert int.from_bytes(frame[6:14],"big")==m["pn"]
        assert len(frame)==m["wire_bytes"]<=MAX_WIRE
        assert len(frame)+UNDERLAY<=MTU
        pad=m["PaddingBytes"]
        bound=m["LifecycleBoundary"]
        stage=m["Stage"]
        elapsed=m["ElapsedFromLastServerFlightMs"]
        assert 0<=elapsed<40000
        if name=="genuine_client_finished_completes_handshake_PAD":
            assert m["mode"]=="aes128_gcm_full" and pad>0 and bound
            client_finished_ts=ts
        if m["mode"]=="public_pn_xor_fast":
            xor+=1
            assert stage=="late" and not bound and pad==0
            assert frame[5]==1
            assert len(frame)==m["inner_bytes"]+15
            if first_xor_ts is None:first_xor_ts=ts
            pn=int.from_bytes(frame[6:14],"big")
            mask=(((pn<<17)|(pn>>47))&((1<<64)-1))^0x6c616e5f6e6f7365
            key=mask.to_bytes(8,"little")
            decoded=bytes(v^key[i%8] for i,v in enumerate(frame[14:]))
            assert decoded[0]==0 and decoded[1]>>4==4
            assert int.from_bytes(decoded[3:5],"big")==len(decoded)-1
            assert hashlib.sha256(decoded[1:]).hexdigest()==m["inner_sha256"]
            assert TEST_SNI not in decoded
        else:
            aes+=1
            assert m["mode"]=="aes128_gcm_full" and frame[5]==0
            assert len(frame)==m["inner_bytes"]+31+pad
            # Authenticated recovery and pad length strip are independently
            # exercised by native Go receiver, never inferred from pcap alone.
            if bound:
                if m["inner_bytes"]+31==MAX_WIRE:
                    assert pad==0;zero_room+=1
                else:assert pad>0;padded+=1;pad_sum+=pad
            else:
                assert pad==0,"one nonboundary packet padded"
                unpadded+=1
    assert 4<=xor<len(specs)
    assert aes>=12 and padded>=7 and unpadded>=7 and zero_room==1
    assert padded==meta["PaddedRecords"]
    assert unpadded+xor==meta["UnpaddedRecords"]
    assert pad_sum==meta["PaddingBytesTotal"]
    assert zero_room==meta["LargeNoRoomFallback"]
    assert client_finished_ts is not None and first_xor_ts is not None
    delta_ms=(first_xor_ts-client_finished_ts)*1000
    assert 11000<=delta_ms<=23000,(delta_ms,meta["ChosenHoldMs"])
    assert delta_ms+200>=meta["ChosenHoldMs"],(delta_ms,meta["ChosenHoldMs"])
    assert meta["ObservedFastElapsedMs"]>=meta["ChosenHoldMs"]
    a=label_map["TLS13_app_fast_after_hold_XOR"][0]
    b=label_map["TLS13_fast_same_app_new_PN_XOR"][0]
    assert a[6:14]!=b[6:14] and a[14:142]!=b[14:142]
    assert "TCP_ACK_middle_no_PAD_AES" in label_map
    assert "UDP_middle_no_PAD_AES" in label_map
    assert "QUIC_Initial_start_PAD" in label_map
    assert "TCP_FIN_end_PAD_AES" in label_map
    assert "TCP_RST_end_PAD_AES" in label_map
    assert "QUIC_CONNECTION_CLOSE_end_PAD_AES" in label_map
    assert "genuine_clienthello_oldseq_late_PAD_AES" in label_map
    assert "genuine_client_finished_completes_handshake_PAD" in label_map
    # The authenticated plaintext pad hash is audited in trusted fixture
    # metadata; no pad content or keys need to be published with raw PCAP.
    lifecycle_hashes=[m["PadSha256"] for m in specs if m["PaddingBytes"]>0]
    assert len(lifecycle_hashes)==padded
    assert len(set(lifecycle_hashes))==len(lifecycle_hashes),"non-random repeated lifecycle pad material"
    return {
       "scope":"NATIVE_REAL_LOOPBACK_TCP_PCAP_OUTER_MUTUAL_TLS13_CUSTOM_AES_OR_PUBLIC_XOR",
       "pcap_bytes_before_cleanup":len(raw),
       "pcap_sha256":hashlib.sha256(raw).hexdigest(),
       "raw_pcap_retained":False,
       "tls13_real_outer_handshake_records":len(hs),
       "custom_records":len(observed),
       "all_AES_records":aes,"fast_XOR_records":xor,
       "padded_lifecycle_AES_records":padded,
       "non_boundary_AES_records_explicitly_unpadded":unpadded,
       "fast_XOR_records_explicitly_unpadded":xor,
       "zero_room_lifecycle_records_unpadded":zero_room,
       "total_random_padding_bytes":pad_sum,
       "some_packets_not_padded":(unpadded+xor+zero_room)>0,
       "ALL_packets_padded":False,
       "path_mtu":MTU,
       "max_record_plus_underlay":max(len(frame)+UNDERLAY for _,frame,_ in observed),
       "hold_random_target_ms":meta["ChosenHoldMs"],
       "observed_pcap_client_finished_to_first_XOR_ms":round(delta_ms,3),
       "sensitive_inner_TLS13_test_SNI_absent_entire_wire":True,
       "fallback_go_AES_GCM_native_roundtrip_and_tag_failure":True,
       "original_late_ClientHello_retransmission_still_AES_and_padded":True,
       "XOR_mask_publicly_reversible_and_not_secure":True,
       "real_live_TLS_classifier":"NOT_IMPLEMENTED_test_oracle_only",
       "native_WBD_Rust_AEAD_wire":"NOT_TESTED_this_wire_lab_Go_AES_GCM",
       "tcp_payload_segments":len(entries),
       "duplicate_outer_TCP_segments":duplicates,
    }

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--pcap",type=pathlib.Path,required=True)
    ap.add_argument("--port",type=int,required=True)
    ap.add_argument("--manifest",type=pathlib.Path,required=True)
    ap.add_argument("--output",type=pathlib.Path,required=True)
    a=ap.parse_args()
    result=audit(a.pcap,a.port,a.manifest)
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
