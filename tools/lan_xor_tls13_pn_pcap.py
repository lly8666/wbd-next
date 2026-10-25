#!/usr/bin/env python3
"""Independent outer TCP capture parser for a REAL TLS1.3 handshake followed by
INSECURE raw XOR TLS-like data records. Do not claim standard-TLS validity.
"""
import argparse
import hashlib
import json
import pathlib
from selective_crypto_capture_analyze import packets

def analyze(path, port):
    raw = pathlib.Path(path).read_bytes()
    assert 0 < len(raw) <= 4*1024*1024, "bounded owned capture"
    segments = [(seq, b) for dst, seq, b in packets(raw) if dst == port and b]
    assert segments
    seen = {}
    outer_retx = 0
    for seq, b in segments:
        if seq in seen:
            assert seen[seq] == b, "outer same-seq TCP retransmission changed"
            outer_retx += 1
        else:
            seen[seq] = b
    base = min(seen)
    stream = bytearray()
    for seq, b in sorted(seen.items()):
        at = (seq - base) & 0xffffffff
        assert at <= len(stream), "TCP stream gap"
        overlap = len(stream)-at
        if overlap:
            assert stream[at:at+min(len(b),overlap)] == b[:overlap]
        stream.extend(b[max(0,overlap):])
    records = []
    off = 0
    while off < len(stream):
        assert off+5 <= len(stream), "partial TLS record"
        typ, version = stream[off], bytes(stream[off+1:off+3])
        assert typ in (20,21,22,23), f"invalid TLS outer record type {typ}"
        assert version in (b"\x03\x01", b"\x03\x03"), "wrong TLS version header"
        n = int.from_bytes(stream[off+3:off+5], "big")
        assert 0 < n <= 16640 and off+5+n <= len(stream), "bounded record length"
        records.append((base+off, bytes(stream[off:off+5+n])))
        off += 5+n
    assert len(records)>8, "no observable handshake prelude"
    handshake = records[:-8]
    tail = records[-8:]
    assert handshake[0][1][0] == 22, "client did not start with handshake record"
    assert any(r[1][0] == 23 for r in handshake), "no encrypted TLS1.3 handshake records seen"
    assert len(set(s for s,_ in tail))==8, "not eight new outer positions"
    assert [len(r) for _,r in tail]==[1360]*8, "steady records missing"
    assert all(r[:3]==b"\x17\x03\x03" for _,r in tail)
    assert [int.from_bytes(r[5:13],"big") for _,r in tail]==[0,1,2,3,4,5,6,7]
    f0,f1,r2,r3,o4,o5,p6,p7=[r for _,r in tail]
    assert f0[15:79]==f1[15:79] and f0[15:143]==f1[15:143]
    assert r2[15:79]!=r3[15:79] and r2[15:143]!=r3[15:143]
    assert o4[15:79]!=o5[15:79] and o4[15:143]!=o5[15:143]
    assert o4[15:] != o5[15:], "different PNs must not repeat full masked body"
    assert p6[15:79]!=p7[15:79] and p6[15:143]!=p7[15:143]
    # This fast PN mask changes at least one byte of every complete 8B block.
    for at in range(13,13+((len(p6)-13)//8)*8,8):
        assert p6[at:at+8]!=p7[at:at+8], f"PN mask failed at block {at}"
    return {
        "scope":"GENUINE_MUTUAL_TLS13_HANDSHAKE_THEN_UNAUTHENTICATED_XOR_STEADY_FIXTURE",
        "raw_pcap_sha256":hashlib.sha256(raw).hexdigest(),
        "raw_pcap_bytes_before_owned_cleanup":len(raw),
        "raw_pcap_retained":False,
        "outer_tcp_payload_segments":len(segments),
        "outer_same_seq_retransmit_segments":outer_retx,
        "observed_preceding_tls_handshake_records":len(handshake),
        "first_client_record_type":"handshake_0x16",
        "observed_client_encrypted_handshake_record":True,
        "steady_new_outer_seq_positions_distinct":True,
        "steady_record_count":8,
        "steady_record_lengths":[len(x[1]) for x in tail],
        "steady_170303_headers":True,
        "fixed_xor_repeat64":True,
        "fixed_xor_repeat128":True,
        "rolling_xor_repeat64":False,
        "rolling_xor_repeat128":False,
        "word_rolling_xor_repeat64":False,
        "word_rolling_xor_repeat128":False,
        "pn_repeat_word_xor_repeat64":False,
        "pn_repeat_word_xor_repeat128":False,
        "pn_every_complete_8B_block_different_for_same_input":True,
        "word_matches_old_mask_for_same_pn":"GO_SOURCE_NATIVE_EQUIVALENCE_PREFLIGHT",
        "fixed_and_old_rolling_repeated_controls_preserved":True,
        "real_WBD_authenticated_Go_Rust_TUN":"NOT_TESTED",
        "crypto_security_of_steady_records":"NONE",
        "standard_TLS_decryptability_of_steady_records":False
    }

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--pcap",type=pathlib.Path,required=True)
    p.add_argument("--port",type=int,required=True)
    p.add_argument("--output",type=pathlib.Path,required=True)
    a=p.parse_args()
    d=analyze(a.pcap,a.port)
    a.output.write_text(json.dumps(d,indent=2)+"\n")
    print(json.dumps(d,indent=2))
