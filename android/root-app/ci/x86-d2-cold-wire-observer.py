#!/usr/bin/env python3
"""CI-only read-only TCP flag observer for original Android FakeTCP cold path.

host: AF_PACKET read on Linux host loopback, counting original 443 SYN/SYNACK/RST.
guest: parse emulator -tcpdump PCAP's virtual Ethernet, matching 10.0.2.2:443.
NO packet bytes, IP addresses, credentials, PCAP, or payload leave the runner.
An observed SYN is only wire egress, never TLS/auth or true peer identity.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import struct
import time

DEST_GUEST = b"\x0a\x00\x02\x02"  # Emulator private host alias
HOST_LOOPBACK = b"\x7f\x00\x00\x01"
MAX_PACKETS = 350000


def counts():
    return {"syn": 0, "synack": 0, "rst": 0, "frames_examined": 0}


def classify(frame, counters, src_expected, dst_expected):
    # Both QEMU virtual Ethernet (DLT_EN10MB) and Linux loopback AF_PACKET
    # expose an Ethernet-format header. Never retain raw input bytes.
    if len(frame) < 54:
        return
    offset = 14
    etype = struct.unpack_from("!H", frame, 12)[0]
    for _ in range(2):
        if etype not in (0x8100, 0x88a8) or len(frame) < offset + 4:
            break
        etype = struct.unpack_from("!H", frame, offset + 2)[0]
        offset += 4
    if etype != 0x0800 or len(frame) < offset + 40:
        return
    if frame[offset] >> 4 != 4:
        return
    ihl = (frame[offset] & 15) * 4
    if ihl < 20 or frame[offset + 9] != 6 or len(frame) < offset + ihl + 20:
        return
    if struct.unpack_from("!H", frame, offset + 6)[0] & 0x1fff:
        return
    src = frame[offset + 12:offset + 16]
    dst = frame[offset + 16:offset + 20]
    start = offset + ihl
    source_port, dest_port = struct.unpack_from("!HH", frame, start)
    flags = frame[start + 13]
    if dest_port == 443 and dst == dst_expected and (flags & 0x12) == 0x02:
        counters["syn"] += 1
    elif source_port == 443 and src == src_expected:
        if (flags & 0x12) == 0x12 and not flags & 0x04:
            counters["synack"] += 1
        if flags & 0x04:
            counters["rst"] += 1


def sanitized_receipt(source, counter, format_seen):
    def status(key):
        return "OBSERVED" if counter[key] > 0 else "NOT_OBSERVED"
    return {
        "schema": "wbd-d2-s1-cold-wire-flags-only/v1",
        "capture": source,
        "wire_capture_format_valid": bool(format_seen),
        "syn": status("syn"),
        "synack": status("synack"),
        "rst": status("rst"),
        "tcp_frames_examined": min(counter["frames_examined"], MAX_PACKETS),
        "original_tls_authenticated": "NOT_PROVEN",
        "raw_payload_retained_or_uploaded": False,
    }


def write_receipt(destination, source, counter, valid):
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitized_receipt(source, counter, valid),
                               indent=2, sort_keys=True) + "\n")


def guest_pcap(path, destination):
    counter = counts()
    valid = False
    try:
        with open(path, "rb") as f:
            header = f.read(24)
            if len(header) != 24:
                raise ValueError("pcap header incomplete")
            magic = header[:4]
            if magic in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1"):
                endian = "<"
            elif magic in (b"\xa1\xb2\xc3\xd4", b"\xa1\xb2\x3c\x4d"):
                endian = ">"
            else:
                raise ValueError("pcap magic unsupported")
            # No alternate cooked/raw linktypes are silently treated as Ethernet.
            linktype = struct.unpack_from(endian + "I", header, 20)[0] & 0xffff
            if linktype != 1:
                raise ValueError("pcap Ethernet linktype required")
            valid = True
            for _ in range(MAX_PACKETS):
                record = f.read(16)
                if not record:
                    break
                if len(record) != 16:
                    raise ValueError("pcap record header truncated")
                caplen = struct.unpack_from(endian + "I", record, 8)[0]
                if not 0 < caplen <= 65536:
                    raise ValueError("pcap caplen invalid")
                frame = f.read(caplen)
                if len(frame) != caplen:
                    raise ValueError("pcap record truncated")
                counter["frames_examined"] += 1
                classify(frame, counter, DEST_GUEST, DEST_GUEST)
    except (OSError, ValueError, struct.error):
        valid = False
        counter = counts()
    write_receipt(destination, "android_emulator_virtual_ethernet", counter, valid)


def host_loopback(destination, max_seconds, interface="lo", expected_ip=HOST_LOOPBACK):
    counter = counts()
    terminated = False

    def stop(_signum, _frame):
        nonlocal terminated
        terminated = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW,
                             socket.htons(0x0003))
        sock.bind((interface, 0))
        sock.settimeout(0.3)
        # Packet socket CAP_NET_RAW is needed only for socket creation.
        # Drop back to the Actions runner UID before writing the 0600
        # private fixed-enum summary consumed by the D2 receipt.
        if os.geteuid() == 0 and "SUDO_UID" in os.environ:
            os.setgid(int(os.environ["SUDO_GID"]))
            os.setuid(int(os.environ["SUDO_UID"]))
    except (OSError, ValueError, KeyError):
        write_receipt(destination, "linux_host_tap" if interface=="wbdtapci0" else "linux_host_loopback", counter, False)
        return 1
    deadline = time.monotonic() + max_seconds
    try:
        while not terminated and time.monotonic() < deadline and counter["frames_examined"] < MAX_PACKETS:
            try:
                frame = sock.recv(65536)
            except socket.timeout:
                continue
            counter["frames_examined"] += 1
            classify(frame, counter, expected_ip, expected_ip)
    finally:
        sock.close()
        write_receipt(destination, "linux_host_tap" if interface=="wbdtapci0" else "linux_host_loopback", counter, True)
    return 0


def selftest():
    # Synthetic metadata-only Ethernet TCP flags (no payload, network access,
    # service, credentials or traffic replay). This test never proves WBD.
    eth = bytes(12) + struct.pack("!H", 0x0800)
    def frame(src, dst, sport, dport, flags):
        ipv4 = bytearray(20)
        ipv4[0] = 0x45
        ipv4[9] = 6
        ipv4[12:16], ipv4[16:20] = src, dst
        tcp = bytearray(20)
        struct.pack_into("!HH", tcp, 0, sport, dport)
        tcp[13] = flags
        return eth + bytes(ipv4) + bytes(tcp)
    guest = counts()
    classify(frame(bytes([10, 0, 2, 15]), DEST_GUEST, 30001, 443, 0x02),
             guest, DEST_GUEST, DEST_GUEST)
    classify(frame(DEST_GUEST, bytes([10, 0, 2, 15]), 443, 30001, 0x12),
             guest, DEST_GUEST, DEST_GUEST)
    classify(frame(DEST_GUEST, bytes([10, 0, 2, 15]), 443, 30001, 0x14),
             guest, DEST_GUEST, DEST_GUEST)
    assert (guest["syn"], guest["synack"], guest["rst"]) == (1, 1, 1)
    host = counts()
    classify(frame(HOST_LOOPBACK, HOST_LOOPBACK, 30001, 443, 0x02),
             host, HOST_LOOPBACK, HOST_LOOPBACK)
    classify(frame(HOST_LOOPBACK, HOST_LOOPBACK, 443, 30001, 0x12),
             host, HOST_LOOPBACK, HOST_LOOPBACK)
    assert (host["syn"], host["synack"], host["rst"]) == (1, 1, 0)
    print("D2_S1_READONLY_COLD_TCP_FLAGS_SYNTHETIC_CLASSIFIER_SELFTEST_PASS")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("host", "guest", "selftest"))
    ap.add_argument("--output")
    ap.add_argument("--input")
    ap.add_argument("--max-seconds", type=int, default=115)
    ap.add_argument("--interface", choices=("lo","wbdtapci0"), default="lo")
    ap.add_argument("--expected-ip", choices=("127.0.0.1","10.0.2.2"), default="127.0.0.1")
    args = ap.parse_args()
    if args.mode == "selftest":
        return selftest()
    if not args.output:
        ap.error("host/guest modes require --output")
    if args.mode == "host":
        if not 5 <= args.max_seconds <= 180:
            ap.error("bounded max-seconds required")
        if (args.interface, args.expected_ip) not in (("lo","127.0.0.1"),("wbdtapci0","10.0.2.2")):
            ap.error("host observer interface and address must match the fixed CI scope")
        return host_loopback(args.output, args.max_seconds, args.interface, socket.inet_aton(args.expected_ip))
    if not args.input:
        ap.error("guest mode requires an input pcap")
    guest_pcap(args.input, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
