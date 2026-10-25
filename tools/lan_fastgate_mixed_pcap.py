#!/usr/bin/env python3
"""Independent bounded Linux outer TCP pcap audit for test-only mixed AEAD/XOR.
Never claims outer data are standards-compliant TLS13 AEAD records.
"""
import argparse,hashlib,json,pathlib
from selective_crypto_capture_analyze import packets

SENSITIVE=b"private.inner-wbd.example"
def analyze(raw_path,port,manifest_path):
    raw=raw_path.read_bytes()
    assert 0<len(raw)<=4*1024*1024
    meta=json.loads(manifest_path.read_text())
    specs=meta["records"]
    assert len(specs)>=15
    assert meta["inner_tls13_genuine"] and meta["outer_mutual_tls13_genuine"]
    assert meta["aes_fallback_tamper_rejected"] and meta["plaintext_roundtrip_all"]
    segments=[(seq,b) for dst,seq,b in packets(raw) if dst==port and b]
    assert segments
    unique={}
    retx=0
    for seq,data in segments:
        if seq in unique:
            assert unique[seq]==data,"same outer TCP seq modified"
            retx+=1
        else:unique[seq]=data
    base=min(unique)
    data=bytearray()
    for seq,chunk in sorted(unique.items()):
        at=(seq-base)&0xffffffff
        assert at<=len(data),"gap in observed actual outer TCP stream"
        overlap=len(data)-at
        if overlap:
            assert data[at:at+min(len(chunk),overlap)]==chunk[:overlap],"conflicting overlap"
        data.extend(chunk[max(0,overlap):])
    frames=[]
    at=0
    while at<len(data):
        assert at+5<=len(data),"truncated TLS-looking header"
        typ=data[at];version=bytes(data[at+1:at+3])
        assert typ in (20,21,22,23)
        assert version in (b"\x03\x01",b"\x03\x03")
        n=int.from_bytes(data[at+3:at+5],"big")
        assert 0<n<=16640 and at+5+n<=len(data),"truncated/bad length record"
        frames.append((base+at,bytes(data[at:at+5+n])))
        at+=5+n
    assert len(frames)>len(specs)
    handshake=frames[:-len(specs)]
    observed=frames[-len(specs):]
    assert handshake[0][1][0]==22
    assert any(f[1][0]==23 for f in handshake),"no encrypted real TLS handshake seen"
    assert len(set(seq for seq,w in observed))==len(specs),"outer seq not unique per new packet"
    assert SENSITIVE not in data,"inner genuine ClientHello test SNI escaped AES fallback"
    # The server roundtrip checks AES decryption with an ephemeral key; here
    # only the passive OUTER wire bytes are inspected.
    modes={"aes128_gcm_full":0,"public_pn_xor_fast":1}
    cats={}
    records={}
    for (seq,w),expect in zip(observed,specs):
        label=expect["label"]
        mode=modes[expect["mode"]]
        assert w[:3]==b"\x17\x03\x03"
        assert len(w)==expect["wire_bytes"],(label,len(w),expect["wire_bytes"])
        assert w[5]==mode,(label,"wire mode mismatch")
        assert int.from_bytes(w[6:14],"big")==expect["pn"]
        overhead=31 if mode==0 else 15
        assert len(w)==expect["inner_bytes"]+overhead
        cats[expect["mode"]]=cats.get(expect["mode"],0)+1
        records[label]=(seq,w)
        if mode==1:
            pn=int.from_bytes(w[6:14],"big")
            k=((pn<<17)|(pn>>47))&((1<<64)-1)
            k^=0x6c616e5f6e6f7365
            mask=k.to_bytes(8,"little")
            payload=bytes(b^mask[i%8] for i,b in enumerate(w[14:]))
            assert payload[0]==0 and payload[1]>>4==4
            assert int.from_bytes(payload[3:5],"big")==len(payload)-1
            assert hashlib.sha256(payload[1:]).hexdigest()==expect["inner_sha256"]
            assert SENSITIVE not in payload
        else:
            # XOR-ing AES bytes with its same public PN must not recover the
            # original packet; this is ONLY an appearance check, AEAD decrypt
            # and tamper tests are executed on the receiving Go host.
            pn=int.from_bytes(w[6:14],"big")
            k=(((pn<<17)|(pn>>47))&((1<<64)-1))^0x6c616e5f6e6f7365
            mask=k.to_bytes(8,"little")
            scrambled=bytes(b^mask[i%8] for i,b in enumerate(w[14:]))
            assert hashlib.sha256(scrambled[1:]).hexdigest()!=expect["inner_sha256"]
    assert cats["aes128_gcm_full"]>=10 and cats["public_pn_xor_fast"]>=3
    assert all("AES" in s["label"] for s in specs if s["mode"]=="aes128_gcm_full")
    assert all("XOR" in s["label"] for s in specs if s["mode"]=="public_pn_xor_fast")
    a=records["tls13_app_fast_first_XOR"][1]
    b=records["tls13_app_fast_retransmitted_new_outer_PN_XOR"][1]
    assert a[6:14]!=b[6:14]
    assert a[15:79]!=b[15:79] and a[15:143]!=b[15:143]
    assert a[14:]!=b[14:]
    # Source class cases: actual local TLS1.3 CH/SF, retransmissions, unknown,
    # byte-identical protected TLS edge and app, HTTP, ACK, FIN, UDP, TLS12.
    for partial in ("genuine_clienthello_sni_alpn_AES",
                    "clienthello_retransmit_old_seq_AES",
                    "genuine_serverhello_flight_chunk0_AES",
                    "handshake_boundary_retransmission_AES",
                    "tls13_app_but_unconfirmed_flow_AES",
                    "same_tls13_ciphertext_marked_PROTECTED_EDGE_AES",
                    "ordinary_http_TCP_AES","TCP_ACK_only_AES","TCP_FIN_AES",
                    "UDP_dns_like_AES","TLS12_like_unconfirmed_AES",
                    "unknown_flow_same_170303_AES",
                    "same_TLS13_app_marked_Alert_AES",
                    "TLS13_app_under_safe_seq_even_with_trust_AES"):
        assert partial in records,partial
    assert "tls13_app_fast_small_XOR" in records
    return{
        "scope":"REAL_NATIVE_LOOPBACK_OUTER_TCP_PCAP_GENUINE_MUTUAL_TLS13_BOOTSTRAP_THEN_LAB_ONLY_MIXED_AESGCM_XOR",
        "raw_pcap_sha256":hashlib.sha256(raw).hexdigest(),
        "raw_pcap_bytes_before_cleanup":len(raw),
        "raw_pcap_retained":False,
        "observed_client_pre_data_tls_handshake_records":len(handshake),
        "outer_payload_tcp_segments":len(segments),
        "outer_same_seq_retransmissions":retx,
        "mixed_steady_outer_record_count":len(observed),
        "aes_full_fallback_records":cats["aes128_gcm_full"],
        "public_pn_xor_fast_records":cats["public_pn_xor_fast"],
        "sni_marker_absent_from_entire_outer_capture":True,
        "clienthello_and_serverhello_and_retransmit_all_fallback_aes":True,
        "unconfirmed_tls13_like_and_tls12_like_fallback_aes":True,
        "HTTP_ACK_FIN_UDP_fallback_aes":True,
        "fast_repeated_same_inner_no_64_128B_identity":True,
        "fast_public_mask_byte_exact_recovery":True,
        "fallback_aes_validated_by_authenticated_go_receiver":True,
        "native_WBD_Rust_AEAD_wire":"NOT_TESTED",
        "real_flow_classifier":"NOT_TESTED_trusted_test_oracle",
        "xor_integrity_security":"NONE",
        "cryptographic_TLS13_data_stream_after_bootstrap":False,
    }
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--pcap",required=True,type=pathlib.Path)
    ap.add_argument("--port",required=True,type=int)
    ap.add_argument("--manifest",required=True,type=pathlib.Path)
    ap.add_argument("--output",required=True,type=pathlib.Path)
    args=ap.parse_args()
    r=analyze(args.pcap,args.port,args.manifest)
    args.output.write_text(json.dumps(r,indent=2)+"\n")
    print(json.dumps(r,indent=2))
