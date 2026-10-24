#!/usr/bin/env python3
"""Bounded offline pcap audit. No payload, trace or keys in output."""
import argparse
import hashlib
import json
import pathlib
import struct

def packets(raw: bytes):
    if raw[:4] in (bytes.fromhex("d4c3b2a1"), bytes.fromhex("4d3cb2a1")):
        order = "<"
    elif raw[:4] in (bytes.fromhex("a1b2c3d4"), bytes.fromhex("a1b23c4d")):
        order = ">"
    else:
        raise ValueError("only classic libpcap accepted")
    if len(raw) < 24:
        raise ValueError("truncated pcap")
    link = struct.unpack_from(order + "I", raw, 20)[0]
    offset = 24
    while offset + 16 <= len(raw):
        cap = struct.unpack_from(order + "I", raw, offset + 8)[0]
        offset += 16
        if cap > 65535 or offset + cap > len(raw):
            raise ValueError("bad bounded pcap packet")
        data = raw[offset:offset + cap]
        offset += cap
        if link == 1:  # ethernet/loopback EN10MB
            if len(data) < 14 or data[12:14] != b"\x08\x00":
                continue
            ip = data[14:]
        elif link == 113:  # Linux SLL v1
            if len(data) < 16 or data[14:16] != b"\x08\x00":
                continue
            ip = data[16:]
        elif link == 0:  # BSD loopback DLT_NULL
            if len(data) < 4 or int.from_bytes(data[:4], "little") != 2:
                continue
            ip = data[4:]
        else:
            raise ValueError(f"unsupported pcap linktype {link}")
        if len(ip) < 40 or ip[0] >> 4 != 4 or ip[9] != 6:
            continue
        ihl = (ip[0] & 15) * 4
        declared = int.from_bytes(ip[2:4], "big")
        if ihl < 20 or ihl + 20 > len(ip) or declared < ihl + 20:
            continue
        tcp = ip[ihl:]
        tcp_head = (tcp[12] >> 4) * 4
        if tcp_head < 20 or ihl + tcp_head > declared:
            continue
        yield (int.from_bytes(tcp[2:4], "big"),
               int.from_bytes(tcp[4:8], "big"),
               ip[ihl + tcp_head:min(declared, len(ip))])
    if offset != len(raw):
        raise ValueError("truncated pcap tail")

def analyze(path: pathlib.Path, port: int):
    raw = path.read_bytes()
    assert 0 < len(raw) <= 33554432, "32MiB owned pcap cap"
    entries = [(seq, payload) for dst, seq, payload in packets(raw)
               if dst == port and payload]
    assert entries, "no observed outer TCP payload"
    positions = {}
    retransmissions = 0
    for seq, payload in entries:
        if seq in positions:
            assert positions[seq] == payload, "outer same-Seq ciphertext changed"
            retransmissions += 1
        else:
            positions[seq] = payload
    # Build the actual observed *outer TCP byte stream*, not independent
    # packet fragment searches that might miscount same-sequence captures.
    base = min(positions)
    stream = bytearray()
    for seq, payload in sorted(positions.items()):
        delta = (seq - base) & 0xffffffff
        assert delta <= len(stream), "outer TCP capture has a gap"
        overlap = len(stream) - delta
        if overlap:
            assert stream[delta:delta + min(len(payload), overlap)] == payload[:overlap]
        stream.extend(payload[max(0, overlap):])
    records = []
    pos = 0
    while pos < len(stream):
        assert pos + 5 <= len(stream) and stream[pos:pos + 3] == b"\x17\x03\x03"
        record_len = int.from_bytes(stream[pos + 3:pos + 5], "big") + 5
        assert record_len >= 33 and pos + record_len <= len(stream)
        records.append((base + pos, bytes(stream[pos:pos + record_len])))
        pos += record_len
    assert len(records) == 4, f"expected 2 baseline + 2 candidate records; got {len(records)}"
    a1, a2, b1, b2 = records
    assert a1[0] != a2[0] and b1[0] != b2[0]
    # Exact candidate wire offsets: 5B outer, 10B HP, then authenticated TLS B.
    same64 = b1[1][15:79] == b2[1][15:79]
    same128 = b1[1][15:143] == b2[1][15:143]
    assert same64 and same128, "expected constructed retransmission counterexample not visible"
    assert a1[1][14:142] != a2[1][14:142], "FULL control unexpectedly identical"
    canary = bytes([10, 11, 12, 13, 10, 21, 22, 23])
    result = {
        "scope": "native loopback TCP capture of lab wire only",
        "pcap_sha256": hashlib.sha256(raw).hexdigest(),
        "pcap_bytes_before_owned_cleanup": len(raw),
        "tcp_payload_segments_seen": len(entries),
        "outer_same_seq_duplicate_segments": retransmissions,
        "wire_records": len(records),
        "full_wire_lengths": [len(a1[1]), len(a2[1])],
        "selective_wire_lengths": [len(b1[1]), len(b2[1])],
        "different_outer_seq_positions": b1[0] != b2[0],
        "same_tls_ciphertext_64": same64,
        "same_tls_ciphertext_128": same128,
        "clear_inner_ip_header_canary_found": canary in stream,
        "appearance": "LAB_CAPTURE_CONFIRMS_REPEATED_INNER_CIPHERTEXT_ACROSS_OUTER_SEQ",
        "inner_retransmission_cause": "CONTROLLED_SAME_INNER_TCP_SEQ_RESEND_NOT_KERNEL_TUN_RETRANSMISSION",
        "go_tls_outer_handshake": "NOT_TESTED",
        "real_driver_and_p99": "NOT_TESTED",
        "classifier": "IDEAL_TRUSTED_TLS_ORACLE",
        "raw_pcap_retained": False,
    }
    return result

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pcap", required=True, type=pathlib.Path)
    ap.add_argument("--port", required=True, type=int)
    ap.add_argument("--output", required=True, type=pathlib.Path)
    args = ap.parse_args()
    result = analyze(args.pcap, args.port)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
