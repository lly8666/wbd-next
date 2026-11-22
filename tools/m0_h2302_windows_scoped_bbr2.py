#!/usr/bin/env python3
"""H2302: disposable Win2025 runner ONLY, scoped real TCP BBR2 eligibility.

Read/restore original Custom TCP template; bind exactly one unique test remote
TCP port, establish a real kernel loopback TCP socket, remove exact filter in
finally. Not evidence the *socket* selected BBR2 or WBD goodput. Never touch
Internet template, current physical users, Wintun/FakeTCP, WBD defaults.
"""
import json
import os
import re
import socket
import subprocess
import sys

PORT = 18763

def netsh(*args):
    p = subprocess.run(["netsh", "interface", "tcp", *args],
                       capture_output=True, text=True, timeout=25,
                       check=False, errors="replace")
    if p.returncode:
        raise RuntimeError("H2302_NETSH_FAILED "+str(args)+" rc="+str(p.returncode)+
                           " stdout="+p.stdout[-1000:]+" stderr="+p.stderr[-1000:])
    return p.stdout

def read_provider(template):
    raw=netsh("show", "supplemental", "template="+template)
    m=re.search(r"(?im)^\s*Congestion Control Provider\s*:\s*([\w-]+)",raw)
    if not m: raise RuntimeError("H2302_OS_TEMPLATE_PROVIDER_UNREADABLE_"+template)
    return m.group(1).lower()

def port_filter_exists():
    raw=netsh("show", "supplementalports")
    return str(PORT) in raw

def real_test_socket():
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as server:
        server.settimeout(4)
        server.bind(("127.0.0.1",PORT))
        server.listen(1)
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as client:
            client.settimeout(4)
            client.connect(("127.0.0.1",PORT))
            with server.accept()[0] as accepted:
                accepted.sendall(b"H2302-real-kernel-TCP")
                if client.recv(64)!=b"H2302-real-kernel-TCP":
                    raise RuntimeError("H2302_REAL_TCP_NOT_RECEIVED")
            return {"local":client.getsockname(),"peer":client.getpeername()}

def main():
    if os.name!="nt" or os.environ.get("GITHUB_ACTIONS")!="true" or        not os.environ.get("RUNNER_TEMP"):
        raise RuntimeError("H2302_DISPOSABLE_GITHUB_WINDOWS_RUNNER_ONLY")
    original=read_provider("custom")
    internet=read_provider("internet")
    if original not in ("cubic","ctcp","bbr2","dctcp","default","none"):
        raise RuntimeError("H2302_CUSTOM_UNKNOWN_PROVIDER_REFUSE_EDIT_"+original)
    if port_filter_exists():
        raise RuntimeError("H2302_EXACT_TEST_PORT_ALREADY_FILTERED_REFUSE_EDIT")
    modified=False
    filter_attempted=False
    observation={}
    try:
        # Only the Custom template in this ephemeral runner; Internet stays
        # byte/field unchanged, never silently tweak other TCP stack knobs.
        modified=True
        netsh("set","supplemental","template=custom","congestionprovider=bbr2")
        if read_provider("custom")!="bbr2":
            raise RuntimeError("H2302_BBR2_NOT_EFFECTIVE_IN_CUSTOM_TEMPLATE")
        filter_attempted=True
        netsh("add","supplementalport","template=custom",
              "localport=*","remoteport="+str(PORT))
        if not port_filter_exists():
            raise RuntimeError("H2302_BBR2_REMOTEPORT_FILTER_MISSING")
        actual=real_test_socket()
        if read_provider("internet")!=internet:
            raise RuntimeError("H2302_INTERNET_TEMPLATE_CHANGED")
        observation={"original_custom":original,"candidate":"bbr2",
                     "test_port_filter_applied":True,
                     "real_tcp_loopback_connect":actual,
                     "actual_socket_congestion_provider":"NOT_PROVEN_BY_TEMPLATE_ONLY",
                     "wbd_real_app_or_3runner_goodput":"NOT_RUN"}
    finally:
        problems=[]
        if filter_attempted:
            try: netsh("delete","supplementalport","localport=*",
                       "remoteport="+str(PORT))
            except Exception as exc: problems.append("filter:"+str(exc))
        if modified:
            try: netsh("set","supplemental","template=custom",
                       "congestionprovider="+original)
            except Exception as exc: problems.append("provider:"+str(exc))
        try:
            if read_provider("custom")!=original or port_filter_exists() or                read_provider("internet")!=internet:
                problems.append("OS_TCP_TEMPLATE_RESTORE_READBACK_MISMATCH")
        except Exception as exc: problems.append("readback:"+str(exc))
        if problems: raise RuntimeError("H2302_TEST_OWNED_OS_TCP_RESTORE_FAILURE "+
                                       ";".join(problems))
    print("H2302_SCOPED_WINDOWS_REAL_BBR2_TEMPLATE_RESTORED "+
          json.dumps(observation,sort_keys=True),flush=True)

if __name__=="__main__":
    main()
