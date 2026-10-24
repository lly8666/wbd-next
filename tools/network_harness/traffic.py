"""Independent paced TX/RX, UDP + framed real TCP + concurrent RTT probes.

All workers share ONE Linux kernel monotonic clock. No per-packet files/logs.
Application bytes include our integrity/sequence header, exclude IP/TCP/UDP.
TCP application records are NOT claimed to be single wire packets.
"""
import argparse
import array
import bisect
import collections
import errno
import hashlib
import json
import math
import os
import selectors
import socket
import struct
import time
from pathlib import Path

HEADER = struct.Struct("!4sBBHQQII")  # magic, version, kind, phase, seq, sent_ns, size, CRC
MAGIC = b"WBN1"
UDP, PROBE, ECHO, TCP = 0, 1, 2, 3


class Histogram:
    """100us buckets through 30 seconds; bounded, explicit overflow."""
    def __init__(self):
        self.bins = collections.Counter()
        self.count = self.overflow = 0
        self.maximum_ms = 0.0

    def add(self, ms):
        self.count += 1
        self.maximum_ms = max(self.maximum_ms, ms)
        if ms > 30000:
            self.overflow += 1
        self.bins[min(300000, max(0, math.ceil(ms * 10)))] += 1

    def result(self):
        out = {"n": self.count, "overflow_over_30s": self.overflow, "max_ms": self.maximum_ms}
        for name, q in [("p50_ms", .5), ("p95_ms", .95), ("p99_ms", .99), ("p999_ms", .999)]:
            remaining = math.ceil(self.count * q)
            out[name] = None
            for b, count in sorted(self.bins.items()):
                remaining -= count
                if remaining <= 0:
                    out[name] = b / 10 if b < 300000 else None
                    break
        return out


def bodies(sizes, seed):
    # Hash once per configured size; validation compares whole deterministic body.
    import zlib
    out = {}
    for size in sizes:
        body = hashlib.shake_256(f"WBD-harness/{seed}/{size}".encode()).digest(size - HEADER.size)
        out[size] = (body, zlib.crc32(body))
    return out


def fresh_stats():
    return {"tx_packets": 0, "tx_bytes": 0, "rx_packets": 0, "rx_bytes": 0,
            "send_errors": 0, "emsgsize": 0, "backpressure": 0, "duplicates": 0,
            "invalid": 0, "late": 0, "reordered": 0, "scheduled": 0,
            "probe_sent": 0, "probe_received": 0,
            "latency": Histogram(), "send_lag": Histogram(), "rtt": Histogram()}


class Worker:
    def __init__(self, config, role, local, peer, port, output, start_ns, peer_port=None):
        self.config, self.role, self.local, self.peer = config, role, local, peer
        self.port, self.output, self.start_ns = port, Path(output), start_ns
        self.peer_port = port if peer_port is None else peer_port
        self.sel = selectors.DefaultSelector()
        self.phases = [{"name": "warmup", "seconds": config["warmup_s"],
                        "rate_scale": config["traffic"].get("warmup_rate_scale",1)}] + config["phases"]
        self.ends, elapsed = [], 0
        for ph in self.phases:
            elapsed += ph["seconds"]
            self.ends.append(start_ns + int(elapsed * 1e9))
        self.end_ns = self.ends[-1]
        self.stats = {proto: [fresh_stats() for _ in self.phases] for proto in ["udp", "tcp"]}
        t = config["traffic"]
        self.cycle = [size for size, weight in t["sizes"] for _ in range(weight)]
        self.body = bodies(set(self.cycle) | {64}, config["seed"])
        self.seq = {"udp": 0, "tcp": 0}
        self.high = {"udp": -1, "tcp": -1}
        self.seen = {proto: bytearray((t["max_packets"] + 7) // 8) for proto in self.seq}
        count = math.ceil((elapsed + config["drain_s"]) * 100) + 1
        self.tx_bins = {p: array.array("I", [0]) * count for p in self.seq}
        self.rx_bins = {p: array.array("I", [0]) * count for p in self.seq}
        self.tx_byte_bins = {p: array.array("I", [0]) * count for p in self.seq}
        self.rx_byte_bins = {p: array.array("I", [0]) * count for p in self.seq}
        # Windows Winsock offers no Linux SO_RXQ_OVFL ancillary counter;
        # missing host queue drop telemetry is UNKNOWN, never asserted zero.
        self.socket_drops = 0 if os.name == 'posix' else None
        self.probe_seq, self.probe_outstanding, self.probe_seen = 0, {}, set()
        self.streams = []
        self.read_buffers = {}
        self.pending = {}
        self.errors = collections.Counter()
        self.capacity_exceeded = False
        self.effective_buffers = {}

    def bind_udp(self, port, key):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)
        if os.name == "posix":
            s.setsockopt(socket.SOL_SOCKET, 40, 1)  # Linux SO_RXQ_OVFL
            if key == "udp":
                s.setsockopt(socket.IPPROTO_IP, 10, 0 if self.config["traffic"]["allow_fragmentation"] else 2)
        elif key == "udp" and not self.config["traffic"]["allow_fragmentation"]:
            # Windows Winsock IP_DONTFRAGMENT; fail-closed when unsupported.
            # Python 3.12's Windows socket module omits the name even
            # though WinSock2 ws2tcpip.h defines IP_DONTFRAGMENT = 14.
            # Microsoft documents the DWORD option; verify Winsock
            # readback, never silently downgrade to IP fragmentation.
            opt = getattr(socket, "IP_DONTFRAGMENT", 14)
            s.setsockopt(socket.IPPROTO_IP, opt, 1)
            if s.getsockopt(socket.IPPROTO_IP, opt) != 1:
                raise RuntimeError("Windows IPv4 DF socket readback failed")
        s.bind((self.local, port))
        s.setblocking(False)
        self.effective_buffers[key] = {"rcvbuf": s.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF),
                                       "sndbuf": s.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)}
        self.sel.register(s, selectors.EVENT_READ, key)
        return s

    def tcp_preconnect_buffers(self, sock):
        # Apply before SYN/accept so window-scale negotiation sees desired RX size.
        # Normal baseline deliberately leaves socket defaults untouched.
        if self.config["network"].get("tcp_window_profile_selected")=="large":
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,8*1024*1024)
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,8*1024*1024)

    def connect_streams(self):
        if self.config["traffic"]["udp_share"] == 1:
            return
        if self.role == "server":
            listen = socket.socket()
            listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_preconnect_buffers(listen)
            listen.bind((self.local, self.port + 2))
            listen.listen(32)
            listen.settimeout(15)
            for _ in range(self.config["traffic"]["tcp_flows"]):
                s, _ = listen.accept()
                self.streams.append(s)
            listen.close()
        else:
            for _ in range(self.config["traffic"]["tcp_flows"]):
                deadline = time.monotonic() + 15
                while True:
                    s = socket.socket()
                    self.tcp_preconnect_buffers(s)
                    # Bounded A/B diagnostic only: force one Linux TCP
                    # socket pacing ceiling without editing any TCP sysctl,
                    # the WBD product, normal app rate, or other sockets.
                    pacing=self.config["network"].get("tcp_socket_pacing_mbps_selected",0)
                    if pacing:
                        opt=getattr(socket,"SO_MAX_PACING_RATE",47)
                        limit=pacing*1_000_000//8  # Linux option uses bytes/s
                        s.setsockopt(socket.SOL_SOCKET,opt,limit)
                        if s.getsockopt(socket.SOL_SOCKET,opt)!=limit:
                            raise RuntimeError("per-socket pace readback mismatch")
                    s.bind((self.local, 0))
                    s.settimeout(1)
                    try:
                        s.connect((self.peer, self.peer_port + 2))
                        self.streams.append(s)
                        break
                    except OSError:
                        s.close()
                        if time.monotonic() > deadline:
                            raise
                        time.sleep(.1)
        for s in self.streams:
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            profile=self.config["network"].get("tcp_socket_pacing_mbps_selected",0)
            self.effective_buffers.setdefault("tcp",[]).append({
                "sndbuf":s.getsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF),
                "rcvbuf":s.getsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF),
                "SO_MAX_PACING_RATE_bytes_s":(
                    s.getsockopt(socket.SOL_SOCKET,getattr(socket,"SO_MAX_PACING_RATE",47))
                    if profile and self.role=="client" else "NOT_SET")})
            s.setblocking(False)
            self.sel.register(s, selectors.EVENT_READ, "tcp")
            self.read_buffers[s] = bytearray()

    def packet(self, kind, phase, seq, size, now):
        body, crc = self.body[size]
        return HEADER.pack(MAGIC, 1, kind, phase, seq, now, size, crc) + body

    def bucket(self, now):
        return min(len(self.tx_bins["udp"]) - 1, max(0, (now - self.start_ns) // 10000000))

    def sent(self, proto, phase, size, now):
        st = self.stats[proto][phase]
        st["tx_packets"] += 1
        st["tx_bytes"] += size
        self.tx_bins[proto][self.bucket(now)] += 1
        self.tx_byte_bins[proto][self.bucket(now)] += size

    def receive(self, data, now, proto):
        fallback = self.stats[proto][min(len(self.phases)-1, bisect.bisect_right(self.ends, now))]
        if len(data) < HEADER.size:
            fallback["invalid"] += 1
            return
        magic, version, kind, phase, seq, sent, size, crc = HEADER.unpack_from(data)
        if (magic != MAGIC or version != 1 or size != len(data) or size not in self.body
                or phase >= len(self.phases) or sent > now or sent < self.start_ns
                or self.body[size] != (data[HEADER.size:], crc)):
            fallback["invalid"] += 1
            return
        if kind == PROBE:
            try:
                self.probe.sendto(self.packet(ECHO, phase, seq, size, sent), (self.peer, self.peer_port + 1))
            except OSError:
                self.errors["probe_echo_send_error"] += 1
            return
        st = self.stats[proto][phase]
        if kind == ECHO:
            if self.probe_outstanding.get(seq) != (sent, phase):
                self.errors["duplicate_or_unknown_probe_echo"] += 1
                return
            del self.probe_outstanding[seq]
            st["probe_received"] += 1
            st["rtt"].add((now - sent) / 1e6)
            return
        if kind != (UDP if proto == "udp" else TCP) or seq >= self.config["traffic"]["max_packets"]:
            st["invalid"] += 1
            return
        i, bit = divmod(seq, 8)
        if self.seen[proto][i] & (1 << bit):
            st["duplicates"] += 1
            return
        self.seen[proto][i] |= 1 << bit
        st["reordered"] += int(seq < self.high[proto])
        self.high[proto] = max(seq, self.high[proto])
        st["rx_packets"] += 1
        st["rx_bytes"] += size
        delay = (now - sent) / 1e6
        st["latency"].add(delay)
        st["late"] += int(delay > self.config["traffic"]["deadline_ms"])
        self.rx_bins[proto][self.bucket(now)] += 1
        self.rx_byte_bins[proto][self.bucket(now)] += size

    def flush_tcp(self, s, now):
        if s not in self.pending:
            return
        data, offset, phase, size = self.pending[s]
        try:
            n = s.send(memoryview(data)[offset:])
            offset += n
            if offset == len(data):
                self.sent("tcp", phase, size, now)
                del self.pending[s]
                self.sel.modify(s, selectors.EVENT_READ, "tcp")
            else:
                self.pending[s][1] = offset
        except BlockingIOError:
            pass
        except OSError as e:
            self.errors[f"tcp_send_errno_{e.errno}"] += 1
            del self.pending[s]
            self.sel.modify(s, selectors.EVENT_READ, "tcp")

    def io(self, timeout):
        for key, mask in self.sel.select(timeout):
            s, proto = key.fileobj, key.data
            if mask & selectors.EVENT_WRITE:
                self.flush_tcp(s, time.monotonic_ns())
            if not mask & selectors.EVENT_READ:
                continue
            for _ in range(128):  # bounded fairness; TX deadlines always get a turn
                try:
                    if proto == "tcp":
                        data = s.recv(131072)
                        if not data:
                            self.sel.unregister(s)
                            break
                        b = self.read_buffers[s]
                        b.extend(data)
                        while len(b) >= 4:
                            size = struct.unpack_from("!I", b)[0]
                            if not HEADER.size <= size <= 65507:
                                raise ValueError("invalid TCP application frame length")
                            if len(b) < size + 4:
                                break
                            self.receive(bytes(b[4:4+size]), time.monotonic_ns(), "tcp")
                            del b[:4+size]
                    else:
                        if os.name == "posix":
                            data, ancillary, flags, _ = s.recvmsg(65536, 128)
                            for level, typ, value in ancillary:
                                if level == socket.SOL_SOCKET and typ == 40:
                                    self.socket_drops = max(self.socket_drops, struct.unpack("I", value)[0])
                            if flags & socket.MSG_TRUNC:
                                self.errors["udp_truncated"] += 1
                        else:
                            # Winsock lacks recvmsg; Windows socket drop
                            # must come from independent ETW/interface readback.
                            data, _ = s.recvfrom(65536)
                        self.receive(data, time.monotonic_ns(), "udp")
                except BlockingIOError:
                    break
                except OSError as e:
                    self.errors[f"receive_errno_{e.errno}"] += 1
                    break

    def run(self):
        self.udp = self.bind_udp(self.port, "udp")
        self.probe = self.bind_udp(self.port + 1, "probe")
        self.connect_streams()
        if time.monotonic_ns() >= self.start_ns:
            raise RuntimeError("application setup exceeded declared start; invalid injection")
        self.output.with_suffix(".ready").write_text("ready\n")
        t = self.config["traffic"]
        rate = t["c2s_mbps" if self.role == "client" else "s2c_mbps"] * 1e6 / 8
        shares = {"udp": t["udp_share"], "tcp": 1-t["udp_share"]}
        due = {p: self.start_ns for p in shares}
        # Explicit 0Hz is a genuine idle/keepalive experiment: no
        # application probing packets anywhere in its observation horizon.
        probe_due = self.start_ns if t["probe_hz"] else (1 << 63) - 1
        while time.monotonic_ns() < self.end_ns + int(self.config["drain_s"] * 1e9):
            now = time.monotonic_ns()
            phase = bisect.bisect_right(self.ends, now)
            if self.start_ns <= now < self.end_ns:
                if now >= probe_due:
                    seq = self.probe_seq
                    self.probe_seq += 1
                    try:
                        self.probe.sendto(self.packet(PROBE, phase, seq, 64, now), (self.peer, self.port+1))
                        self.probe_outstanding[seq] = (now, phase)
                        self.stats["udp"][phase]["probe_sent"] += 1
                    except OSError:
                        self.errors["probe_send_error"] += 1
                    probe_due = now + int(1e9 / t["probe_hz"])
                for proto, share in shares.items():
                    bps = rate * share * self.phases[phase]["rate_scale"]
                    if not bps:
                        due[proto] = now
                        continue
                    # Catch-up bounded to 64 records / iteration. Never wait for receipt.
                    for _ in range(64):
                        if now < due[proto]:
                            break
                        seq = self.seq[proto]
                        if seq >= t["max_packets"]:
                            self.capacity_exceeded = True
                            due[proto] = self.end_ns
                            break
                        size = self.cycle[seq % len(self.cycle)]
                        st = self.stats[proto][phase]
                        st["scheduled"] += 1
                        st["send_lag"].add(max(0, now - due[proto]) / 1e6)
                        interval = size / bps * 1e9
                        due[proto] += max(1, int(interval))
                        data = self.packet(UDP if proto == "udp" else TCP, phase, seq, size, now)
                        if proto == "tcp":
                            candidates = self.streams[seq % len(self.streams):] + self.streams[:seq % len(self.streams)]
                            s = next((stream for stream in candidates if stream not in self.pending), None)
                            if s is None:
                                st["backpressure"] += 1
                                continue
                            self.seq[proto] += 1
                            self.pending[s] = [struct.pack("!I", size) + data, 0, phase, size]
                            self.sel.modify(s, selectors.EVENT_READ | selectors.EVENT_WRITE, "tcp")
                            self.flush_tcp(s, now)
                        else:
                            try:
                                n = self.udp.sendto(data, (self.peer, self.peer_port))
                                if n != size:
                                    raise RuntimeError("partial UDP send")
                                self.seq[proto] += 1
                                self.sent(proto, phase, size, now)
                            except OSError as e:
                                st["send_errors"] += 1
                                st["emsgsize"] += int(e.errno == errno.EMSGSIZE)
                        # Do not build an unbounded catch-up burst when generator falls behind.
                        if now - due[proto] > max(20_000_000, int(t["burst_ms"] * 1e6)):
                            self.errors["pacing_catchup_limited"] += 1
                            due[proto] = now
                next_due = min([probe_due] + [due[p] for p in shares if rate * shares[p] * self.phases[phase]["rate_scale"] > 0])
                timeout = min(.002, max(0, (next_due - time.monotonic_ns()) / 1e9))
                if t["burst_ms"]:
                    timeout = t["burst_ms"] / 1000
            else:
                timeout = .002
            self.io(timeout)
        result = {"role": self.role, "start_ns": self.start_ns, "end_ns": self.end_ns,
                  "clock": "same host monotonic_ns; cross-host directional delay UNQUALIFIED unless independently synchronized", "units": "application bytes including test header",
                  "stats": {}, "tx_bins_10ms": self.tx_bins, "rx_bins_10ms": self.rx_bins,
                  "tx_bytes_bins_10ms": self.tx_byte_bins, "rx_bytes_bins_10ms": self.rx_byte_bins,
                  "socket_drops": self.socket_drops, "effective_buffers": self.effective_buffers,
                  "errors": self.errors, "capacity_exceeded": self.capacity_exceeded,
                  "tcp_pending_at_deadline": len(self.pending)}
        for proto, rows in self.stats.items():
            result["stats"][proto] = []
            for phase, st in zip(self.phases, rows):
                result["stats"][proto].append({"phase": phase["name"], **{
                    k: v.result() if isinstance(v, Histogram) else v for k, v in st.items()}})
        self.output.write_text(json.dumps(result, default=lambda x: list(x), separators=(",", ":")))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for name in ["config", "role", "local", "peer", "output"]:
        ap.add_argument("--" + name, required=True)
    ap.add_argument("--port", type=int, default=45901)
    ap.add_argument("--start-ns", type=int, required=True)
    ap.add_argument("--peer-port", type=int)
    a = ap.parse_args()
    Worker(json.loads(Path(a.config).read_text()), a.role, a.local, a.peer,
           a.port, a.output, a.start_ns, peer_port=a.peer_port).run()
