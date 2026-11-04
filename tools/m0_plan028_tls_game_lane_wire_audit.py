#!/usr/bin/env python3
"""Original-Go Game2/Game4 TLS first-flights from ONE bounded real TCP PCAP.
Inspect each lane of both OS source-IP generations. Raw PCAP is destroyed in
the native runner; output is only non-secret record shapes / hashes.
"""
import json
import pathlib
import struct
import sys

from m0_plan028_tls_wire_audit import audit as audit_one


def game_audit(raw, lanes=4):
    if lanes not in (2, 4):
        raise AssertionError("invalid original Game lane count")
    if len(raw) < 24:
        raise AssertionError("empty real TCP capture")
    magic = raw[:4]
    if magic == b"\xd4\xc3\xb2\xa1":
        endian = "<"
    elif magic == b"\xa1\xb2\xc3\xd4":
        endian = ">"
    else:
        raise AssertionError("not a classic tcpdump PCAP")
    link = struct.unpack_from(endian + "I", raw, 20)[0]
    if link not in (1, 113, 276):
        raise AssertionError("expected real Linux Ethernet/SLL/SLL2")
    sessions = {}
    off = 24
    total_frames = 0
    while off + 16 <= len(raw):
        sec, usec, included, original = struct.unpack_from(endian + "IIII", raw, off)
        rec = raw[off : off + 16 + included]
        off += 16
        if included > 65535 or off + included > len(raw):
            raise AssertionError("truncated TCP capture")
        frame = raw[off : off + included]
        off += included
        total_frames += 1
        if total_frames > 20000:
            raise AssertionError("unbounded wire capture")
        if link == 1:
            if len(frame) < 14:
                continue
            kind = frame[12:14]
            offset = 14
            if kind in (b"\x81\x00", b"\x88\xa8"):
                if len(frame) < 18:
                    continue
                kind, offset = frame[16:18], 18
            ip = frame[offset:] if kind == b"\x08\x00" else b""
        elif link == 113:
            ip = frame[16:] if len(frame) >= 16 and frame[14:16] == b"\x08\x00" else b""
        else:
            ip = frame[20:] if len(frame) >= 20 and frame[:2] == b"\x08\x00" else b""
        if len(ip) < 40 or (ip[0] >> 4) != 4 or ip[9] != 6:
            continue
        ihl = (ip[0] & 15) * 4
        size = int.from_bytes(ip[2:4], "big")
        if size < ihl + 20 or size > len(ip):
            continue
        tcp = ip[ihl:size]
        hlen = (tcp[12] >> 4) * 4
        if hlen < 20 or len(tcp) < hlen:
            continue
        src = ".".join(map(str, ip[12:16]))
        dst = ".".join(map(str, ip[16:20]))
        sport = int.from_bytes(tcp[0:2], "big")
        dport = int.from_bytes(tcp[2:4], "big")
        if src in ("10.25.0.2", "10.25.0.3") and dst == "10.25.0.1" and dport == 443:
            key = (src, sport)
            direction = "client"
        elif src == "10.25.0.1" and dst in ("10.25.0.2", "10.25.0.3") and sport == 443:
            key = (dst, dport)
            direction = "server"
        else:
            continue
        slot = sessions.setdefault(key, {"pcap": bytearray(raw[:24]), "syn": False, "syn_ack": False, "segments": []})
        slot["pcap"].extend(rec)
        flags = tcp[13]
        if direction == "client" and (flags & 0x12) == 0x02:
            slot["syn"] = True
        if direction == "server" and (flags & 0x12) == 0x12:
            slot["syn_ack"] = True
        if direction == "client" and len(tcp) > hlen:
            slot["segments"].append((int.from_bytes(tcp[4:8], "big"), tcp[hlen:]))
    sources = {source: sum(key[0] == source for key in sessions) for source in ("10.25.0.2", "10.25.0.3")}
    if sources != {"10.25.0.2": lanes, "10.25.0.3": lanes}:
        raise AssertionError("Game%d two generations must each expose %d distinct original TCP sessions: %r" % (lanes, lanes, sources))
    results = []
    seen_sid = set()
    baseline_extensions = None
    for (source, sourceport), session in sorted(sessions.items()):
        if not session["syn"] or not session["syn_ack"]:
            raise AssertionError("missing real SYN/SYN-ACK on lane %s:%d" % (source, sourceport))
        result = audit_one(bytes(session["pcap"]))
        if result["result"] != "REAL_TCP_STREAM_TLS_FIRST_FLIGHT_PASS" or result["session_id_length"] != 32:
            raise AssertionError("Game lane TLS first-flight failed")
        segments = session["segments"]
        if not segments:
            raise AssertionError("missing ClientHello TCP segments")
        start = segments[0][0]
        unique = {}
        for seq, payload in segments:
            unique.setdefault(seq, payload)
        assembled = bytearray()
        for seq, payload in sorted(unique.items(), key=lambda item: (item[0] - start) & 0xFFFFFFFF):
            delta = (seq - start) & 0xFFFFFFFF
            if delta == len(assembled):
                assembled.extend(payload)
            elif delta < len(assembled) and len(payload) > len(assembled) - delta:
                assembled.extend(payload[len(assembled) - delta:])
            else:
                if delta > len(assembled):
                    break
        if len(assembled) < 76 or assembled[43] != 32:
            raise AssertionError("invalid reassembled 32B SessionID at %s:%d" % (source, sourceport))
        session_id = bytes(assembled[44:76])
        if session_id in seen_sid:
            raise AssertionError("repeated deterministic SessionID across Game lanes/generations")
        seen_sid.add(session_id)
        ordered_extensions = result["extension_types"]
        # GREASE values may vary by uTLS and are structurally legitimate.
        canonical = tuple("grease" if ((int(x) & 0x0F0F) == 0x0A0A and (int(x) >> 8) == (int(x) & 255)) else x
                          for x in ordered_extensions)
        if baseline_extensions is None:
            baseline_extensions = canonical
        elif canonical != baseline_extensions:
            raise AssertionError("Game lane's TLS extension layout deviates from its identical configured uTLS baseline")
        results.append({"source_ip": source, "source_port": sourceport,
                        "client_hello_record_bytes": result["client_hello_record_bytes"],
                        "server_hello_record_bytes": result["server_hello_record_bytes"],
                        "tls_extensions": len(ordered_extensions),
                        "session_id_bytes": 32, "tcp_syn_and_synack": True,
                        "first_client_data": result["client_first_payload"],
                        "first_server_data": result["server_first_payload"],
                        "server_early_data_bytes": result["server_early_application_bytes"]})
    return {"result": "REAL_GAME%d_TWO_GENERATIONS_%d_CLIENTHELLO_NO_PRELUDE_PASS" % (lanes, 2*lanes),
            "original_tls": "real Go/FakeTCP 443", "client_generation_count": 2,
            "lanes_per_generation": lanes, "client_hello_sessions": len(results),
            "distinct_session_ids": len(seen_sid),
            "source_counts": sources, "per_lane": results,
            "scope": "real original Go TLS first-flight only, not full Finished trace or public website fingerprint"}


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit("usage: audit.py private-ephemeral-real-tcp.pcap [lanes=2|4]")
    lanes = int(sys.argv[2]) if len(sys.argv) == 3 else 4
    print(json.dumps(game_audit(pathlib.Path(sys.argv[1]).read_bytes(), lanes), sort_keys=True))
