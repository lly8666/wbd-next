#!/usr/bin/env python3
"""H2300 test-only inner kernel TCP congestion capability & scoped socket probe.

NO WBD product mutation, fake-TCP congestion claim, sysctl/netsh setter, route,
FEC ON, global OS mutation, or benchmark performance success. A *real*
original Wintun/TUN app socket must later read back the same effective setting.
"""
import argparse
import json
import os
import pathlib
import socket
import subprocess
import sys


def read_linux_control_file(name):
    root = pathlib.Path("/proc/sys/net/ipv4")
    path = root / name
    return path.read_text(encoding="ascii").strip()


def get_linux_socket_cc(sock):
    # IPPROTO_TCP/TCP_CONGESTION is a Linux-specific real TCP socket option.
    key = getattr(socket, "TCP_CONGESTION", None)
    if key is None:
        raise RuntimeError("LINUX_TCP_CONGESTION_NOT_EXPOSED")
    raw = sock.getsockopt(socket.IPPROTO_TCP, key, 64)
    return raw.split(b"\0", 1)[0].decode("ascii")


def set_linux_socket_cc_verified(sock, algorithm):
    """Change ONLY a caller-owned actual TCP socket, never the host default.

    Called before connect on the emitting socket (or before listen on the
    accepting socket). Linux passive sockets inherit the listener policy;
    the tester must verify every accepted socket's actual option separately.
    """
    if sys.platform != "linux":
        raise RuntimeError("H2300_LINUX_OWNED_SOCKET_REQUIRED")
    if algorithm not in ("cubic", "reno", "bbr"):
        raise RuntimeError("H2300_UNSUPPORTED_TEST_CC")
    avail = set(read_linux_control_file("tcp_available_congestion_control").split())
    if algorithm not in avail:
        raise RuntimeError("H2300_KERNEL_CC_UNAVAILABLE_" + algorithm)
    key = getattr(socket, "TCP_CONGESTION", None)
    if key is None:
        raise RuntimeError("LINUX_TCP_CONGESTION_NOT_EXPOSED")
    before = get_linux_socket_cc(sock)
    sock.setsockopt(socket.IPPROTO_TCP, key, algorithm.encode("ascii"))
    actual = get_linux_socket_cc(sock)
    if actual != algorithm:
        raise RuntimeError("H2300_LINUX_SOCKET_CC_APPLIED_NOT_READBACK")
    return {"before": before, "requested": algorithm, "applied": actual,
            "scope": "ONE_OWNED_KERNEL_TCP_SOCKET_NOT_WBD_FAKETCP"}


def probe_linux(algorithm=None):
    if sys.platform != "linux":
        raise RuntimeError("H2300_LINUX_ONLY")
    names = read_linux_control_file("tcp_available_congestion_control").split()
    default = read_linux_control_file("tcp_congestion_control")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        before = get_linux_socket_cc(sock)
        changed = (set_linux_socket_cc_verified(sock, algorithm)
                   if algorithm is not None else None)
    return {
        "os": "linux", "source": "live_kernel_proc_and_TCP_CONGESTION",
        "available": names, "kernel_default": default, "new_socket_before": before,
        "one_owned_unconnected_test_socket": changed,
        "persistent_global_setting_changed": False,
        "proof_of_3runner_or_original_WBD_application": False
    }


def probe_windows():
    if os.name != "nt":
        raise RuntimeError("H2300_WINDOWS_ONLY")
    # Read-only. 'bbr2' in Microsoft netsh documentation does NOT establish
    # build support or actual selected congestion provider on the 45902 flow.
    queries = (
        ["netsh", "interface", "tcp", "show", "supplemental", "template=internet"],
        ["netsh", "interface", "tcp", "show", "supplemental", "template=custom"],
        ["netsh", "interface", "tcp", "show", "supplementalports"],
    )
    observations = []
    for args in queries:
        p = subprocess.run(args, capture_output=True, text=True,
                           timeout=15, check=False, errors="replace")
        observations.append({"cmd": " ".join(args), "returncode": p.returncode,
                             "stdout": p.stdout[-9000:], "stderr": p.stderr[-1000:]})
    return {
        "os": "windows", "source": "READ_ONLY_NETSH_SUPPLEMENTAL_TEMPLATE",
        "observations": observations, "any_os_template_changed": False,
        "effective_bbr2_on_specific_socket": "NOT_PROVEN",
        "scope": "OBSERVATION_ONLY_NO_GLOBAL_TCP_CHANGE",
        "proof_of_3runner_or_original_WBD_application": False
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["linux-read", "linux-owned-socket", "windows-read"])
    ap.add_argument("--algorithm", choices=("cubic", "reno", "bbr"),
                    default=None)
    args = ap.parse_args()
    if args.command == "linux-read":
        if args.algorithm is not None:
            ap.error("--algorithm requires linux-owned-socket")
        result = probe_linux()
    elif args.command == "linux-owned-socket":
        if not args.algorithm:
            ap.error("--algorithm required")
        result = probe_linux(args.algorithm)
    else:
        if args.algorithm is not None:
            ap.error("--algorithm only supported on Linux test socket")
        result = probe_windows()
    print("H2300_ORIGINAL_INNER_KERNEL_TCP_CC_CAPABILITY " +
          json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
