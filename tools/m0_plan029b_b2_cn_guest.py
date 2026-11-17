#!/usr/bin/env python3
"""029B B2: genuine Linux physical DNS & separate TUN DNS/business sockets.

The exact same overseas public A must be returned for CN and non-CN,
while CN DNS uses the sole physical resolver and both data packets arrive
on the original authenticated Linux TUN. No product helper/proxy installed.
"""
import json
import select
import socket
import struct
import sys
import time

physical, expected_host, lease, tunnel, overseas = sys.argv[1:6]
CN = b"\x03www\x02cn\x07example\x00"
GLOBAL = b"\x03www\x07globalx\x07example\x00"
EDGE = b"\x04edge\x03cdn\x07example\x00"
A = b"\x00\x01\x00\x01"
target = socket.inet_aton(overseas)
markers = {b"P29B-CN-TUNNEL", b"P29B-GLOBAL-TUNNEL"}
seen = {}
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as direct, \
     socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as tun_dns, \
     socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as business:
    direct.bind((physical, 53))
    tun_dns.bind((tunnel, 53))
    business.bind((overseas, 46113))
    print("PLAN029B_B2_REAL_LINUX_DNS_AND_TUNNEL_READY", flush=True)
    until = time.monotonic() + 36
    linger = None
    while time.monotonic() < until:
        if len(seen) == 4 and linger is None:
            linger = time.monotonic() + 0.5
        if linger and time.monotonic() >= linger:
            break
        r, _, _ = select.select([direct, tun_dns, business], [], [], .3)
        for sock in r:
            wire, peer = sock.recvfrom(2048)
            if sock is direct:
                label, expected, ip = "cn_dns", expected_host, CN
            elif sock is tun_dns:
                label, expected, ip = "global_dns", lease, GLOBAL
            else:
                label, expected, ip = "business", lease, None
            if peer[0] != expected:
                raise RuntimeError("B2 DNS/data observed wrong physical versus TUN peer " + label)
            if label == "business":
                if wire not in markers or wire.decode() in seen:
                    raise RuntimeError("B2 wrong or duplicate real TUN data")
                seen[wire.decode()] = {"source": peer[0],
                                       "tun_destination": overseas}
                sock.sendto(wire + b"-REPLY", peer)
                continue
            if len(wire) < 12 or wire[2:6] != b"\x01\x00\x00\x01" or \
               wire[12:] != ip + A:
                # H2093 one bounded first-error witness. The previous
                # H2092 packet did not match the expected question; never
                # call it a valid retry, never rewrite/cross-fallback.
                diag = {"lane": label, "peer": peer[0],
                        "peer_port": peer[1], "bytes": len(wire),
                        "dns_header12": wire[:12].hex(),
                        "question_prefix48": wire[12:60].hex(),
                        "expected_question": (ip + A).hex(),
                        "prior_expected_events": sorted(seen),
                        "source": "REAL_LINUX_KERNEL_UDP"}
                print("PLAN029B_B2_FIRST_INVALID_UPSTREAM_DNS " +
                      json.dumps(diag, sort_keys=True), flush=True)
                raise RuntimeError("B2 wrong real upstream domain/question")
            # The original Windows application deliberately retries its
            # same-id UDP ticket on a timeout, and the Rust owner may issue
            # a second UDP attempt to the *same* chosen physical/TUN DNS
            # endpoint. PLAN029 §4 permits at most two bounded attempts.
            # Never collapse, hide or accept unbounded repeated upstream
            # traffic, a different QNAME/qtype, another peer or a cross-lane
            # fallback: all are checked before counting this attempt.
            prior = seen.get(label)
            attempts = (prior["physical_attempts"] if prior else 0) + 1
            if attempts > 2:
                raise RuntimeError("B2 excessive same-endpoint DNS upstream retry")
            upstream_ids = list(prior["upstream_ids"]) if prior else []
            upstream_ids.append("%04x" % int.from_bytes(wire[:2], "big"))
            print("PLAN029B_B2_VALID_UPSTREAM_DNS " +
                  json.dumps({"lane": label, "attempt": attempts,
                              "peer": peer[0], "peer_port": peer[1],
                              "dns_id": upstream_ids[-1],
                              "question": "cn" if ip == CN else "noncn"},
                             sort_keys=True), flush=True)
            if label == "cn_dns":
                cname = (b"\xc0\x0c\x00\x05\x00\x01" +
                         struct.pack("!IH", 2, len(EDGE)) + EDGE)
                rrname = EDGE
                answer_count = 2
            else:
                cname = b""
                rrname = b"\xc0\x0c"
                answer_count = 1
            arec = rrname + b"\x00\x01\x00\x01" + struct.pack(
                "!IH", 2, 4) + target
            answer = (wire[:2] + b"\x81\x80\x00\x01" +
                      struct.pack("!H", answer_count) +
                      b"\x00\x00\x00\x00" + ip + A + cname + arec)
            sock.sendto(answer, peer)
            seen[label] = {"question": "www.cn.example" if ip == CN else "www.globalx.example",
                           "source": peer[0], "upstream": physical if label == "cn_dns" else tunnel,
                           "ttl": 2, "real_a": overseas,
                           "cname": bool(cname),
                           "physical_attempts": attempts, "upstream_ids": upstream_ids}
    if set(seen) != {"cn_dns", "global_dns", "P29B-CN-TUNNEL", "P29B-GLOBAL-TUNNEL"}:
        raise RuntimeError("B2 missing genuine split DNS or TUN data: " + repr(seen))
    print("PLAN029B_B2_REAL_LINUX_CN_PHYSICAL_DNS_AND_BOTH_TUNNEL_DATA " +
          json.dumps({"source_real_ip": overseas, "events": seen,
                      "physical_business_packets": 0,
                      "result": "PASS_REAL_PHYSICAL_CN_DNS_OVERSEAS_BOTH_TUNNEL"}, sort_keys=True),
          flush=True)
