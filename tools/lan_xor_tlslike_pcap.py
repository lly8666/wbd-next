#!/usr/bin/env python3
"""Bounded independent capture of INSECURE TLS-looking XOR experiment.
No raw pcap or user payload in the retained report. Not a TLS session parser.
"""
import argparse
import hashlib
import json
import pathlib
from selective_crypto_capture_analyze import packets

def analyze(path: pathlib.Path, port: int):
    raw = path.read_bytes()
    assert 0 < len(raw) <= 4 * 1024 * 1024, "owned pcap must be <=4MiB"
    segments = [(seq, data) for dst, seq, data in packets(raw)
                if dst == port and data]
    assert segments, "no outer TCP application bytes captured"
    unique = {}
    outer_same_seq = 0
    for seq, data in segments:
        if seq in unique:
            assert unique[seq] == data, "same outer TCP Seq changed on retransmit"
            outer_same_seq += 1
        else:
            unique[seq] = data
    base = min(unique)
    stream = bytearray()
    for seq, data in sorted(unique.items()):
        delta = (seq - base) & 0xffffffff
        assert delta <= len(stream), "missing observed outer stream bytes"
        overlap = len(stream) - delta
        if overlap:
            assert stream[delta: delta + min(overlap, len(data))] == data[:overlap]
        stream.extend(data[max(0, overlap):])
    records = []
    off = 0
    while off < len(stream):
        assert off + 5 <= len(stream), "truncated TLS-like header"
        assert stream[off:off + 3] == b"\x17\x03\x03", "not TLS-like application data"
        body = int.from_bytes(stream[off + 3:off + 5], "big")
        end = off + 5 + body
        assert 30 <= body <= 16640 and end <= len(stream), "bounded framing mismatch"
        records.append((base + off, bytes(stream[off:end])))
        off = end
    assert len(records) == 4, "must capture fixed/fixed/rolling/rolling"
    seqs = [x[0] for x in records]
    assert len(set(seqs)) == 4, "must be four distinct new outer TCP sequence positions"
    lengths = [len(x[1]) for x in records]
    assert lengths == [1360] * 4, f"unexpected per-IP-packet lengths {lengths}"
    pn = [int.from_bytes(x[1][5:13], "big") for x in records]
    assert pn == [0, 1, 2, 3], f"wrong packet-local nonce inputs {pn}"
    f0, f1, r2, r3 = [item[1] for item in records]
    f64 = f0[15:79] == f1[15:79]
    f128 = f0[15:143] == f1[15:143]
    r64 = r2[15:79] == r3[15:79]
    r128 = r2[15:143] == r3[15:143]
    assert f64 and f128, "fixed XOR must demonstrate repeated-body negative control"
    assert not r64 and not r128, "rolling mask must remove direct 64/128B repeat"
    canary = bytes([10, 11, 12, 13, 10, 21, 22, 23])
    assert canary not in stream, "unobfuscated fixture IP address detected"
    return {
        "scope": "ESTABLISHED_LOOPBACK_TCP_FIXTURE_NOT_WBD_TUN_OR_TLS_HANDSHAKE",
        "raw_pcap_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_pcap_bytes_before_cleanup": len(raw),
        "pcap_raw_retained": False,
        "outer_tcp_payload_segments": len(segments),
        "outer_same_tcp_seq_retransmit_segments": outer_same_seq,
        "different_new_outer_seq_positions": True,
        "records": len(records),
        "record_lengths_bytes": lengths,
        "inner_ipv4_packet_bytes_per_record": 1345,
        "tlslike_header_170303_every_record": True,
        "fixed_xor_repeat64": f64,
        "fixed_xor_repeat128": f128,
        "rolling_xor_repeat64": r64,
        "rolling_xor_repeat128": r128,
        "inner_address_canary_visible": False,
        "tls_handshake": "NOT_TESTED",
        "authenticated_go_bootstrap": "NOT_TESTED",
        "real_tun_product_path": "NOT_TESTED",
        "security": "NONE_INSECURE_OBFUSCATION_ACCEPTS_TAMPERING_AND_REPLAY",
        "wire_observation": "ROLLING_XOR_REMOVES_SIMPLE_CONTIGUOUS_DUPLICATE_BUT_NOT_TLS_INDISTINGUISHABILITY"
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pcap", type=pathlib.Path, required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--output", type=pathlib.Path, required=True)
    a = ap.parse_args()
    result = analyze(a.pcap, a.port)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
