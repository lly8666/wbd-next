#!/usr/bin/env python3
"""H2286 ORIGINAL Go TLS/Rust ARM server, real AF_PACKET wan0 + native TUN TCP.

Test-only temporary network namespace and exact iptables scope. No fake packet,
no fake TLS READY, no synthetic Rust counters. Must be coupled with real signed
Windows Npcap/Wintun original Go client, independent ARM relay and native ARM.
"""
import hashlib
import json
import os
import pathlib
import re
import secrets
import shutil
import signal
import subprocess
import sys
import time
import m0_h2276_three_runner_tcp as core
import m0_wl_loss_tcp_probe as tcp

ROOT=pathlib.Path("h2286-out")
NETNS="h2286sv"
HOST_DEV="h2286host"
PEER_DEV="wan0"
GATEWAY="10.248.82.1"
SERVER_IP="10.248.82.2"
APP_IP="10.66.0.1"
APP_PEER="10.66.0.2"
SERVER_PORT=443
FRONT_PORT=18727


def require(cond,label):
    core.require(cond,"H2286_"+label)


def cmd(*args,timeout=50):
    p=subprocess.run([str(x) for x in args],text=True,capture_output=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError("H2286_ARM_COMMAND_FAILED "+repr(args[:10])+" "+(p.stderr or p.stdout)[-500:])
    return p.stdout.strip()


def root(*args):
    return cmd("sudo","-n",*args)


def ns(*args):
    return root("ip","netns","exec",NETNS,*args)


def own_meta(group):
    own=core.load(core.ROOT/"server-peer.json")
    require(os.name=="posix" and own["role"]=="server" and own["group"]==group,
            "ARM64_SOURCE_ROLE_ID")
    require(os.uname().machine=="aarch64","NATIVE_ARM64")
    return own


def server_nat_rules(own,relay):
    ip=own["tail_ip"]
    peer=core.verify(own,relay,"relay")
    return [
     ("-t","nat","-I","PREROUTING","1","-i","tailscale0",
      "-s",peer+"/32","-d",ip+"/32","-p","tcp",
      "--dport",str(FRONT_PORT),"-j","DNAT",
      "--to-destination",SERVER_IP+":"+str(SERVER_PORT)),
     ("-t","nat","-I","POSTROUTING","1","-o",HOST_DEV,
      "-d",SERVER_IP+"/32","-p","tcp","--dport","443",
      "-j","SNAT","--to-source",GATEWAY),
     ("-I","FORWARD","1","-i","tailscale0","-o",HOST_DEV,
      "-s",peer+"/32","-d",SERVER_IP+"/32","-p","tcp",
      "--dport","443","-j","ACCEPT"),
     ("-I","FORWARD","1","-i",HOST_DEV,"-o","tailscale0",
      "-s",SERVER_IP+"/32","-d",peer+"/32","-p","tcp",
      "--sport","443","-j","ACCEPT"),
    ]


def reverse_rule(row):
    x=list(row);idx=x.index("-I");x[idx]="-D";x.pop(idx+2)
    return x


def build_network(own,relay):
    require(NETNS not in cmd("ip","netns","list"),"OWNED_NETNS_ALREADY_EXISTS")
    require(subprocess.run(["ip","link","show",HOST_DEV],capture_output=True).returncode!=0,
            "FOREIGN_HOST_VETH_EXISTS")
    ROOT.mkdir(exist_ok=True)
    orig=cmd("sysctl","-n","net.ipv4.ip_forward")
    (ROOT/"forward-before.txt").write_text(orig+"\n")
    for key in ("net.core.rmem_max","net.core.wmem_max"):
        (ROOT/("sysctl-"+key.replace(".","-")+".txt")).write_text(
            cmd("sysctl","-n",key)+"\n")
        root("sysctl","-w",key+"=16777216")
    root("ip","netns","add",NETNS)
    if os.environ.get("WBD_H2302_WINDOW_ABA")=="1":
        # Test-owned netns only. Ensure a 16MiB TCP receive request can be
        # realized inside the actual ARM socket namespace, not just host sysctl.
        # This namespace is destroyed by the existing owned Stop.
        for key in ("net.core.rmem_max","net.core.wmem_max"):
            ns("sysctl","-w",key+"=16777216")
    root("ip","link","add",HOST_DEV,"type","veth","peer","name",PEER_DEV)
    root("ip","link","set",PEER_DEV,"netns",NETNS)
    ns("ip","link","set","lo","up")
    root("ip","addr","add",GATEWAY+"/24","dev",HOST_DEV)
    root("ip","link","set",HOST_DEV,"mtu","1280")
    root("ip","link","set",HOST_DEV,"up")
    ns("ip","addr","add",SERVER_IP+"/24","dev",PEER_DEV)
    ns("ip","link","set",PEER_DEV,"mtu","1280")
    ns("ip","link","set",PEER_DEV,"up")
    ns("ip","route","add","default","via",GATEWAY,"dev",PEER_DEV)
    ns("sysctl","-w","net.ipv4.conf.all.rp_filter=0")
    ns("iptables","-w","-I","OUTPUT","1","-o",PEER_DEV,
       "-p","tcp","--sport","443","--tcp-flags","RST","RST","-j","DROP")
    root("sysctl","-w","net.ipv4.ip_forward=1")
    applied=[]
    try:
        for rule in server_nat_rules(own,relay):
            root("iptables","-w",*rule)
            applied.append(rule)
    except Exception:
        for row in reversed(applied):
            root("iptables","-w",*reverse_rule(row))
        root("sysctl","-w","net.ipv4.ip_forward="+orig)
        raise
    core.save(ROOT/"nat-owned.json",{
       "source_sha":own["source_sha"],"group":own["group"],"run_id":own["run_id"],
       "netns":NETNS,"guest_only":False,"port":FRONT_PORT,
       "original_ip_forward":orig,"rules":[list(x) for x in applied]})
    return applied


def stop_network():
    # Stop ONLY processes explicitly inside our owned temporary netns.
    if NETNS in cmd("ip","netns","list"):
        p=cmd("sudo","-n","ip","netns","pids",NETNS)
        pids=[int(x) for x in p.split() if x.isdecimal()]
        for pid in pids:
            if pid>1:subprocess.run(["sudo","-n","kill","-TERM",str(pid)],
                                     capture_output=True,timeout=4)
        for tick in range(80):
            left=cmd("sudo","-n","ip","netns","pids",NETNS).strip()
            if not left:break
            time.sleep(.125)
        remaining=cmd("sudo","-n","ip","netns","pids",NETNS)
        for x in remaining.split():
            if x.isdecimal() and int(x)>1:
                subprocess.run(["sudo","-n","kill","-KILL",x],
                               capture_output=True,timeout=4)
        if (ROOT/"original-arm-server.log").exists():
            log=(ROOT/"original-arm-server.log").read_text(errors="replace")
            core.save(ROOT/"original-stop.json",{
                "source":"REAL_ORIGINAL_GO_TLS_RUST_ARM_PROCESS_OWNED_NETNS_TERMINATION",
                "server_go_log_real_ready":("V4_PUBLIC_" in log),
                "actual_rust_owner_stop_logged":("STOP" in log.upper()),
                "signal_scope":"OWNED_NETNS_ONLY","killed_extra_after_10s":bool(remaining.strip())})
    owner=ROOT/"nat-owned.json"
    if owner.exists():
        record=json.loads(owner.read_text())
        for rule in reversed(record["rules"]):
            root("iptables","-w",*reverse_rule(rule))
        root("sysctl","-w","net.ipv4.ip_forward="+record["original_ip_forward"])
        owner.unlink()
    elif (ROOT/"forward-before.txt").exists():
        root("sysctl","-w","net.ipv4.ip_forward="+
             (ROOT/"forward-before.txt").read_text().strip())
    for key in ("net.core.rmem_max","net.core.wmem_max"):
        path=ROOT/("sysctl-"+key.replace(".","-")+".txt")
        if path.exists():
            root("sysctl","-w",key+"="+path.read_text().strip())
    if NETNS in cmd("ip","netns","list"):
        root("ip","netns","del",NETNS)
    if subprocess.run(["ip","link","show",HOST_DEV],capture_output=True).returncode==0:
        root("ip","link","del",HOST_DEV)
    for name in ("key.pem","route-key-private.hex"):
        path=ROOT/name
        if path.exists():path.unlink()
    print("H2286_ARM_OWNED_NETNS_VETH_KERNEL_NAT_AND_TEST_SECRETS_CLEANED",flush=True)


def credential(own):
    """The test-only credential is random and lasts only as a private job artifact."""
    key=ROOT/"route-key-private.hex"
    key.write_text(secrets.token_hex(32)+"\n",encoding="ascii")
    key.chmod(0o600)
    cert=ROOT/"cert.pem"
    private=ROOT/"key.pem"
    cmd("openssl","req","-x509","-newkey","rsa:2048","-sha256","-days","1",
        "-nodes","-keyout",private,"-out",cert,
        "-subj","/CN=wbd-v4.example.test",
        "-addext","subjectAltName=DNS:wbd-v4.example.test",timeout=35)
    private.chmod(0o600)
    return key,cert,private


def native_product(own,relay):
    bundle=pathlib.Path("linux-plan029-public-bundle").resolve()
    mani=json.loads((bundle/"manifest.json").read_text())
    frozen=os.environ.get("WBD_H2286_ARM_PRODUCT_FROZEN_SOURCE","")
    if frozen:
        require(frozen=="97db898f3a1fbebcdeea7f2a1b9d9c3dfcd32573",
                "ONLY_VERIFIED_ARCHIVED_ARM_NATIVE_SOURCE")
    expected=frozen or own["source_sha"]
    # H2286 workflow itself MUST prove git diff compiled product inputs is
    # EXACT EMPTY before setting this flag; no cross-source product claim.
    require(mani["source_sha"]==expected and
            mani["architecture"]=="aarch64" and
            mani["original_go_sha"]=="a7a82db31fe736ffedee330795a3234d358f1984",
            "ORIGINAL_GO_RUST_ARM_BINARY_MANIFEST")
    for name in ("wbd-v4-server","libwbd_engine.so"):
        blob=bundle/name
        require(blob.is_file() and blob.stat().st_size>100000 and
                hashlib.sha256(blob.read_bytes()).hexdigest()==mani["sha256"][name],
                "NATIVE_ARM_SHA256_"+name)
    key,cert,private=credential(own)
    server=[str(bundle/"wbd-v4-server"),
            "--raw-interface",PEER_DEV,"--local-ip",SERVER_IP,
            "--local-port","443","--tun-name","wbds0","--tun-ipv4","10.66.0.1/24",
            "--server-name","wbd-v4.example.test",
            "--route-key-hex-file",str(key.resolve()),
            "--username","wbd-ci-native","--password","native-tls-ci-only",
            "--tunnel-id","102030405060708090a0b0c0d0e0f001",
            "--manual-client-lease4",APP_PEER+"/32",
            "--tls-cert",str(cert.resolve()),"--tls-key",str(private.resolve()),
            "--mode","normal","--outer-repair","off","--peer-persona","windows11",
            "--outer-mtu","1280"]
    log=(ROOT/"original-arm-server.log").open("w")
    # Opt-in native archived Rust counters: exact route /32 TCP-vs-UDP
    # new-packet drops and downstream inbox pressure. No queue changes.
    route_diag=(["WBD_SHARED_TUN_ROUTE_DIAG=1"]
                if os.environ.get("WBD_H2306_TCP_PROGRESS")=="1" else [])
    proc=subprocess.Popen(["sudo","-n","ip","netns","exec",NETNS,
                          "env","LD_LIBRARY_PATH="+str(bundle),*route_diag,*server],
                          stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
    (ROOT/"server.pid").write_text(str(proc.pid)+"\n")
    for tick in range(150):
        if proc.poll() is not None:
            log.flush()
            raise RuntimeError("H2286_REAL_ORIGINAL_ARM_SERVER_EXIT "+(ROOT/"original-arm-server.log").read_text(errors="replace")[-900:])
        link=subprocess.run(["sudo","-n","ip","netns","exec",NETNS,
                             "ip","link","show","wbds0"],
                             capture_output=True,timeout=5)
        if link.returncode==0:
            break
        time.sleep(.25)
    else:
        raise RuntimeError("H2286_ORIGINAL_ARM_SERVER_REAL_TUN_NOT_CREATED")
    require(proc.poll() is None,"ORIGINAL_ARM_SERVER_EXITED_EARLY")
    # Real Linux kernel UDP app starts BEFORE Windows TLS owner Apply.
    udp_log=(ROOT/"arm-inner-udp.log").open("w")
    udp=subprocess.Popen(["sudo","-n","ip","netns","exec",NETNS,
          sys.executable,"-u","tools/m0_h2286_inner_udp.py",
          APP_IP,APP_PEER,own["source_sha"],str(ROOT/"udp-stop.flag")],
          stdout=udp_log,stderr=subprocess.STDOUT)
    (ROOT/"arm-inner-udp.pid").write_text(str(udp.pid)+"\n")
    for tick in range(90):
        if ("H2286_TRUE_OS_TUN_UDP_BIND" in
                (ROOT/"arm-inner-udp.log").read_text(errors="replace")):
            break
        if udp.poll() is not None:
            raise RuntimeError("H2286_REAL_ARM_INNER_UDP_FAILED "+
                 (ROOT/"arm-inner-udp.log").read_text(errors="replace")[-400:])
        time.sleep(.2)
    else:
        raise RuntimeError("H2286_REAL_ARM_PRODUCT_TUN_UDP_NOT_LISTENING")
    # Cert/key are short-lived private per-workflow artifact; no product credentials.
    receipt={"source_sha":own["source_sha"],"run_id":own["run_id"],
         "group":own["group"],"real_original_arm_go_tls_rust_running":True,
         "real_original_arm_tun_created":True,
         "original_product_server_pid":proc.pid,
         "test_only_route_key_artifact":"PRIVATE_REPO_ONE_DAY",
         "original_arm_native_binary_compiled_source_sha":expected,
         "fixture_source_sha":own["source_sha"],
         "local_port":443,"front_port":FRONT_PORT,
         "server_ip_in_kernel_veth":SERVER_IP,"server_tun":APP_IP,
         "client_lease":APP_PEER+"/32",
         "server_cert_sha256":hashlib.sha256(cert.read_bytes()).hexdigest(),
         "original_product_goodput":"NOT_RUN_UNTIL_REMOTE_WIN_NATIVE",
         "no_python_business_server":True}
    core.save(ROOT/"server-ready.json",receipt)
    print("H2286_ARM_ORIGINAL_GO_TLS_RUST_AND_TRUE_AF_PACKET_TUN_READY",flush=True)


def check_server_and_run_app(group):
    own=own_meta(group)
    serverlog=ROOT/"original-arm-server.log"
    require((ROOT/"server-ready.json").exists(),"NOT_READY_ORIGINAL_ARM_SERVER")
    previous=tcp.WINDOW_TEST_BYTES
    tcp.WINDOW_TEST_BYTES=2*1024*1024
    try:
        # Explicit TRUE kernel TCP application on ORIGINAL Go/Rust owned TUN.
        before=core.os_host_cpu()
        require(os.environ.get("WBD_H2286_PRODUCT_FULL_WIN_ARM")=="1",
                "EXPLICIT_NATIVE_PRODUCT_TCP_TEST_PROFILE_REQUIRED")
        with subprocess.Popen(["sudo","-n","ip","netns","exec",NETNS,
                               "env","WBD_H2286_PRODUCT_FULL_WIN_ARM=1",
                               "WBD_H2302_WINDOW_ABA="+os.environ.get("WBD_H2302_WINDOW_ABA","0"),
                               "WBD_H2302_INNER_TCP_TEST_BYTES="+os.environ.get("WBD_H2302_INNER_TCP_TEST_BYTES","2097152"),
                               "WBD_H2306_TCP_PROGRESS="+os.environ.get("WBD_H2306_TCP_PROGRESS","0"),
                               sys.executable,"-u","tools/m0_wl_loss_tcp_probe.py",
                               "server",APP_IP,APP_PEER,own["source_sha"]],
                              stdout=(ROOT/"tcp-inner-server.log").open("w"),
                              stderr=subprocess.STDOUT) as proc:
            for tick in range(120):
                text=(ROOT/"tcp-inner-server.log").read_text(errors="replace")
                if "M029_H2271_NATIVE_TCP_SERVER_READY" in text:break
                if proc.poll() is not None:raise RuntimeError("H2286_INNER_NATIVE_ARM_TCP_APP_EXIT "+text[-750:])
                time.sleep(.2)
            else:raise RuntimeError("H2286_ARM_ORIGINAL_TUN_TCP_LISTENER_NOT_READY")
            print("H2286_ARM_ORIGINAL_PRODUCT_INNER_TCP_READY",flush=True)
            # tcpdump observes ORIGINAL kernel TUN on its actual native
            # interface. Only formatted IPv4/TCP headers, never packet bytes,
            # decrypted payload or an artificial TCP listener/ACK.
            dump_out=(ROOT/"tcp-tun-headers.log").open("w")
            dump_err=(ROOT/"tcpdump-stderr.log").open("w")
            dump=subprocess.Popen(["sudo","-n","ip","netns","exec",NETNS,
                 "tcpdump","-n","-tt","-l","-i","wbds0","-s","96",
                 "-c","400","ip and tcp"],
                 stdout=dump_out,stderr=dump_err)
            for tick in range(80):
                if "listening on wbds0" in (ROOT/"tcpdump-stderr.log").read_text(errors="replace"):
                    break
                if dump.poll() is not None:
                    raise RuntimeError("H2288_REAL_ARM_TUN_TCPDUMP_EXIT "+
                        (ROOT/"tcpdump-stderr.log").read_text(errors="replace")[-650:])
                time.sleep(.1)
            else:
                raise RuntimeError("H2288_REAL_ARM_TUN_TCPDUMP_NO_KERNEL_LISTENER")
            tracer_log=(ROOT/"tcp-passive-trace.log").open("w")
            tracer=subprocess.Popen(["sudo","-n","ip","netns","exec",NETNS,
                 "env","WBD_H2306_TCP_PROGRESS="+os.environ.get("WBD_H2306_TCP_PROGRESS","0"),
                 sys.executable,"-u","tools/m0_h2287_tun_tcp_trace.py",
                 str(ROOT/"tcp-passive-headers.json")],
                 stdout=tracer_log,stderr=subprocess.STDOUT)
            try:
                for tick in range(80):
                    trace_text=(ROOT/"tcp-passive-trace.log").read_text(errors="replace")
                    if "H2287_REAL_ARM_RUST_TUN_TCP_LISTENING_AND_PASSIVE_CAPTURE_READY" in trace_text:
                        break
                    if tracer.poll() is not None:
                        raise RuntimeError("H2287_REAL_TUN_PASSIVE_HEADER_TRACER_EXIT "+
                                           trace_text[-900:])
                    time.sleep(.1)
                else:
                    raise RuntimeError("H2287_REAL_TUN_PASSIVE_TRACER_NOT_READY")
                try:rc=proc.wait(timeout=440)
                except subprocess.TimeoutExpired:
                    proc.kill();raise RuntimeError("H2286_REAL_WBD_TUN_TCP_SERVER_TIMED_OUT")
            finally:
                if tracer.poll() is None:
                    tracer.terminate()
                try:tracer.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    tracer.kill();tracer.wait(timeout=5)
                tracer_log.close()
                if dump.poll() is None:
                    dump.send_signal(signal.SIGINT)
                try:dump.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    dump.kill();dump.wait(timeout=5)
                dump_out.close();dump_err.close()
            require((ROOT/"tcp-passive-headers.json").exists(),
                    "H2287_TUN_PASSIVE_TRACE_MISSING")
            require((ROOT/"tcpdump-stderr.log").is_file() and
                    "listening on wbds0" in
                    (ROOT/"tcpdump-stderr.log").read_text(errors="replace"),
                    "H2288_ARM_TUN_TRUE_READ_ONLY_TCPDUMP_NOT_RUNNING")
            require(rc==0,"REAL_WBD_INNER_APPLICATION_FAILED")
        (ROOT/"udp-stop.flag").write_text(own["source_sha"]+"\n")
        for tick in range(80):
            if (ROOT/"udp-stop.flag.udp.json").exists():break
            time.sleep(.2)
        require((ROOT/"udp-stop.flag.udp.json").exists(),
                "TRUE_ARM_NATIVE_TUN_BIDIR_UDP_NOT_COMPLETED")
        udp_receipt=json.loads((ROOT/"udp-stop.flag.udp.json").read_text())
        require(udp_receipt["real_native_os_udp_received"]>=12,
                "TRUE_ARM_NATIVE_TUN_NO_UDP_RECEIVED")
        log=serverlog.read_text(errors="replace")
        require("V4_PUBLIC_" in log and "M4" in log.upper(),
                "ACTUAL_ORIGINAL_GO_RUST_MARKERS_NOT_SEEN")
        proof={"group":group,"source_sha":own["source_sha"],
              "real_original_arm_go_tls_rust_tun_native_tcp":True,
              "original_arm_server_log_marker":True,
              "tcp_inner_arm_server_finished":True,
              "native_true_arm_tun_udp":udp_receipt,
              "arm_host_allcore_cpu_percent":core.cpu_busy_percent(before,core.os_host_cpu()),
              "tcp_server_log_tail":(ROOT/"tcp-inner-server.log").read_text(errors="replace")[-1200:]}
        core.save(ROOT/"server-result.json",proof)
        print("H2286_ARM_ORIGINAL_PRODUCT_TRUE_TUN_TCP_DELIVERED",flush=True)
    finally:tcp.WINDOW_TEST_BYTES=previous


def main():
    action,group=sys.argv[1:3]
    require(action in ("start","app","clean"),"ACTION")
    if action=="clean":
        stop_network();return
    own=own_meta(group)
    if action=="start":
        relay=core.load(sys.argv[3])
        core.verify(own,relay,"relay")
        try:
            build_network(own,relay)
            native_product(own,relay)
        except:
            with contextlib.suppress(Exception): stop_network()
            raise
    else:
        check_server_and_run_app(group)


if __name__=="__main__":
    import contextlib
    try:main()
    except Exception as err:
        ROOT.mkdir(exist_ok=True)
        core.save(ROOT/"first-error.json",{
            "status":"FAIL_H2286_ORIGINAL_ARM_PRODUCT_OR_HARNESS_NOT_PRODUCT_PASS",
            "first_error_type":type(err).__name__,
            "first_error_message":str(err)[-1000:]})
        print("H2286_ARM_REAL_PRODUCT_FAILURE "+str(err),file=sys.stderr,flush=True)
        raise
