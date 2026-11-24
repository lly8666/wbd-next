#!/usr/bin/env python3
"""H2285: REAL Win2025 Winsock -> WSL2 IPv4 NAT -> ARM kernel relay -> ARM TCP.

First prove the original Windows Npcap peer's WSL2 physical-side L3 route
can reach an OFF-HOST ARM64 server through a SEPARATE ARM64 Linux relay.
No fake WBD driver/TLS/Go/Rust assertion: this is a kernel route preflight.

Each of two independent three-runner groups shares only source, run and shape.
No separate fourth Runner; WSL2 is a guest of the actual Windows client.
"""
import contextlib
import io
import ipaddress
import json
import os
import pathlib
import re
import socket
import subprocess
import sys
import time

import m0_h2276_three_runner_tcp as core

tcp=core.tcp
ROOT=core.ROOT
PORT=core.PORT
NET=core.TAIL
MAX_BUFFER=2*1024*1024
if os.environ.get("WBD_H2359_SUPPLY")=="1":
    tcp.BULK_FLOWS,MAX_BUFFER=tcp.supply_profile("high")


def require(ok, label):
    core.require(ok, "H2285_"+label)


def wsl(*cmd, timeout=50, tolerate=False):
    require(os.name=="nt","ONLY_ACTUAL_WINDOWS_HOST_CAN_OWN_WSL2")
    p=subprocess.run(["wsl.exe","-d","Ubuntu","-u","root","--",*[str(x) for x in cmd]],
                     capture_output=True,text=True,timeout=timeout)
    if p.returncode and not tolerate:
        raise RuntimeError("H2285_WSL_COMMAND_FAIL "+repr(cmd)+" "+(p.stderr or p.stdout)[-500:])
    return p


def guest_eth0():
    out=wsl("ip","-4","-o","addr","show","dev","eth0").stdout
    hit=re.search(r"\binet\s+(\d+(?:\.\d+){3})/(\d{1,2})",out)
    require(hit is not None,"REAL_WSL2_ETH0_IP_ABSENT")
    ip=ipaddress.ip_address(hit.group(1))
    require(ip.is_private and not ip.is_loopback and not ip.is_link_local,
            "ONLY_PRIVATE_ORIGINAL_WSL2_ETH0")
    return str(ip)


def windows_guest_source(ip):
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        s.connect((ip,PORT))
        picked=s.getsockname()[0]
    require(ipaddress.ip_address(picked).is_private and
            picked != ip,"WINDOWS_GUEST_VETH_ROUTE_NOT_ISOLATED")
    return picked


def nat_rules(win,guest,relay):
    """Exactly scoped owned TCP test rule set (never DNAT original TLS secrets)."""
    require(ipaddress.ip_address(win).is_private and
            ipaddress.ip_address(guest).is_private and
            ipaddress.ip_address(relay) in NET,
            "GUEST_AND_RELAY_IP_REJECT")
    return [
      ("-t","nat","-I","PREROUTING","1","-i","eth0",
       "-s",win+"/32","-d",guest+"/32","-p","tcp","--dport",str(PORT),
       "-j","DNAT","--to-destination",relay+":"+str(PORT)),
      ("-t","nat","-I","POSTROUTING","1","-o","eth0",
       "-d",relay+"/32","-p","tcp","--dport",str(PORT),"-j","MASQUERADE"),
      ("-I","FORWARD","1","-i","eth0","-o","eth0",
       "-s",win+"/32","-d",relay+"/32","-p","tcp",
       "--dport",str(PORT),"-j","ACCEPT"),
      ("-I","FORWARD","1","-i","eth0","-o","eth0",
       "-s",relay+"/32","-d",win+"/32","-p","tcp",
       "--sport",str(PORT),"-j","ACCEPT"),
    ]


def reversible_rule(args):
    """Rewrite insertion to exact owned deletion, no blanket flush."""
    x=list(args)
    idx=x.index("-I")
    x[idx]="-D"
    # -I CHAIN 1 specification: deletion doesn't accept the rule index.
    del x[idx+2]
    return x


def guest_counters(win,guest,relay):
    facts={}
    for table,chain in (("nat","PREROUTING"),("nat","POSTROUTING"),
                        ("filter","FORWARD")):
        p=wsl("iptables","-t",table,"-L",chain,"-v","-n","-x",timeout=15)
        vals=[]
        for line in p.stdout.splitlines():
            cols=line.split()
            if (len(cols)>=8 and cols[0].isdigit() and cols[1].isdigit() and
                (win in line or guest in line or relay in line) and
                ("18727" in line)):
                vals.append({"packets":int(cols[0]),"bytes":int(cols[1]),
                             "description":line[-260:]})
        facts[table+"_"+chain]=vals
    return facts


def nat_live_receipt(rows):
    require(rows.get("nat_PREROUTING") and rows.get("nat_POSTROUTING"),
            "GUEST_REAL_BIDIR_NAT_RULE_COUNTERS_ABSENT")
    require(sum(r["packets"] for r in rows["nat_PREROUTING"])>0 and
            sum(r["packets"] for r in rows["nat_POSTROUTING"])>0,
            "GUEST_REAL_FORWARD_TRAFFIC_NOT_SEEN_IN_NAT")
    return {"status":"REAL_WSL2_KERNEL_DNAT_SNAT_COUNTERS_POSITIVE",
            "scope":"ORIGINAL_WINDOWS_HOST_TO_GUEST_KERNEL_L3_ONLY_NO_WBD"}


def server(own,relay):
    core.verify(own,relay,"relay")
    require(os.name=="posix","NATIVE_ARM_SERVER")
    original={k:core.run("sysctl","-n",k).stdout.strip()
              for k in ("net.core.rmem_max","net.core.wmem_max")}
    t0=time.monotonic()
    cpu0=core.os_host_cpu()
    previous_tcp_buffer=tcp.WINDOW_TEST_BYTES
    try:
        for key in original:
            core.run("sudo","-n","sysctl","-w",key+"=16777216")
        tcp.WINDOW_TEST_BYTES=MAX_BUFFER
        print("H2285_REAL_ARM_TCP_SERVER_STAGE_READY",flush=True)
        tcp.server(own["tail_ip"],relay["relay_ip"],own["source_sha"])
    finally:
        tcp.WINDOW_TEST_BYTES=previous_tcp_buffer
        for key,val in original.items():
            core.run("sudo","-n","sysctl","-w",key+"="+val)
    output=dict(group=own["group"],source_sha=own["source_sha"],
        run_id=own["run_id"],server_os="REAL_NATIVE_ARM64_LINUX",
        real_relay_peer=relay["relay_ip"],
        stage_id="windows_wsl2_forwarded_via_arm_relay",
        true_original_go_tls_rust="NOT_RUN",
        actual_kernel_tcp_server_finished=True,
        arm_host_allcore_busy_pct=core.cpu_busy_percent(cpu0,core.os_host_cpu()),
        server_wall_s=round(time.monotonic()-t0,3),
        owned_kernel_sysctls_restored=True)
    core.save(ROOT/"server-result.json",output)
    print("H2285_REAL_ARM_TCP_SERVER_DONE",flush=True)


def client(own,relay,arm):
    win=own["tail_ip"]
    endpoint=core.verify(own,relay,"relay")
    core.verify(own,arm,"server")
    require(all((relay["relay_ip"]==endpoint,relay["client_ip"]==win,
                 relay["server_ip"]==arm["tail_ip"])),
            "TRIPLET_PEERS_NAT_GUARD")
    output=dict(group=own["group"],source_sha=own["source_sha"],
       run_id=own["run_id"],status="NOT_RUN",
       client_os="REAL_WINDOWS2025_WINSOCK",
       guest_os="REAL_UBUNTU_WSL2_ON_THE_SAME_WINDOWS_RUNNER",
       relay_os="INDEPENDENT_ARM64_LINUX_KERNEL_RELAY",
       server_os="INDEPENDENT_ARM64_LINUX_KERNEL_TCP",
       original_wbd_go_tls_rust_npcap_wintun="NOT_RUN_ROUTE_FEASIBILITY_ONLY",
       client_relay_tail_path=core.ping_class(endpoint),
       client_arm_tail_path=core.ping_class(arm["tail_ip"]))
    core.save(ROOT/"client-result.json",output)
    require(output["client_relay_tail_path"]["status"]=="DIRECT_CANDIDATE" and
            output["client_arm_tail_path"]["status"]=="DIRECT_CANDIDATE",
            "INFRA_DERP_MAKES_ROUTE_UNQUALIFIED")
    guest=guest_eth0()
    local=windows_guest_source(guest)
    output.update(guest_ipv4=guest,windows_vethernet_src_ipv4=local,
                  original_windows_peer_local_target=guest,
                  off_host_arm_server=arm["tail_ip"])
    original_forward=wsl("sysctl","-n","net.ipv4.ip_forward").stdout.strip()
    previous_tcp_buffer=tcp.WINDOW_TEST_BYTES
    rules=nat_rules(local,guest,endpoint)
    applied=[]
    try:
        wsl("sysctl","-w","net.ipv4.ip_forward=1")
        for rule in rules:
            wsl("iptables","-w",*rule)
            applied.append(rule)
        shape=core.remote_shape(relay,-1)
        tcp.WINDOW_TEST_BYTES=MAX_BUFFER
        buffer=io.StringIO()
        host_before=core.os_host_cpu()
        t=time.monotonic()
        with contextlib.redirect_stdout(buffer):
            tcp.client(local,guest,own["source_sha"])
        rows=[json.loads(x.split(tcp.MARK+"CLIENT_DONE ",1)[1])
              for x in buffer.getvalue().splitlines()
              if tcp.MARK+"CLIENT_DONE " in x]
        require(len(rows)==1 and rows[0]["sparse_echo_received"]==160 and
                rows[0]["bulk_remote_received_bytes"]>0 and
                rows[0]["bind"]==local and rows[0]["peer"]==guest,
                "NOT_REAL_OS_KERNEL_TCP_ARMSERVER_BYTES")
        guest_counts=guest_counters(local,guest,endpoint)
        guest_proof=nat_live_receipt(guest_counts)
        qdisc=core.netem_phase_receipt(shape["netem"]["qdisc"],
                    core.remote_diag(relay)["kernel_tc"],-1)
        output.update(status="PASS_H2285_NATIVE_WSL2_L3_FORWARD_TO_INDEPENDENT_ARM_TCP_SCOPED",
          real_tailscale_route_not_wbd_product=True,
          wsl_l3_owned_tcp_nat=guest_proof,guest_tcp_nat_counters=guest_counts,
          two_relay_kernel_egress_packet_directions=qdisc,
          delivered=rows[0],
          bulk_wall_s=rows[0]["bulk_wall_s"],
          windows_host_allcore_busy_pct=core.cpu_busy_percent(
             host_before,core.os_host_cpu()),
          stage_wall_s=round(time.monotonic()-t,3),
          per_leg_160_sparse_echoes_received=160)
        core.save(ROOT/"client-result.json",output)
        print("H2285_REAL_WSL2_L3_FORWARDED_ARM_TCP_VERIFIED "+
              json.dumps({"group":own["group"],"mbps":rows[0]["bulk_receiver_goodput_mbps"],
                "p99_ms":rows[0]["sparse_tcp_rtt_p99_ms"]}),flush=True)
    except Exception as err:
        output["status"]="FAIL_H2285_L3_ROUTE_OR_NATIVE_KERNEL_TCP_NOT_PRODUCT"
        output["first_error_type"]=type(err).__name__
        output["first_error_message"]=str(err)[-420:]
        core.save(ROOT/"client-result.json",output)
        raise
    finally:
        tcp.WINDOW_TEST_BYTES=previous_tcp_buffer
        for rule in reversed(applied):
            wsl("iptables","-w",*reversible_rule(rule))
        wsl("sysctl","-w","net.ipv4.ip_forward="+original_forward)
        print("H2285_OWNED_WSL_ROUTE_RULES_AND_IP_FORWARD_RESTORED",flush=True)


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("role",choices=("server","client"))
    p.add_argument("group",choices=("a","b"))
    p.add_argument("relay")
    p.add_argument("arm",nargs="?")
    a=p.parse_args()
    own=core.load(ROOT/(a.role+"-peer.json"))
    require(own["role"]==a.role and own["group"]==a.group,"OWNER_IDENTITY")
    relay=core.load(a.relay)
    if a.role=="server":
        require(a.arm is None,"SERVER_ARGS")
        server(own,relay)
    else:
        require(bool(a.arm),"CLIENT_ARM_PEER_MISSING")
        client(own,relay,core.load(a.arm))


if __name__=="__main__":
    main()
