#!/usr/bin/env python3
"""H2227: fail-closed cross-VM raw-AF_PACKET performance fixture (NOT a benchmark result).

The x86 and ARM64 Actions runners join an authenticated Tailscale tailnet.
A private Linux VXLAN Ethernet underlay on top provides the L2 link required
by the *real* native WBD AF_PACKET / fake-TCP driver. tc netem is attached
ONLY to the owned private veth, never tailscale0 or GitHub management traffic.
WBD original-Go TLS and Rust binaries are built by the existing source-locked
dual-native builder, not mocked. BBR only governs genuine kernel TCP sockets
(the iperf3 inner flow/baseline), NOT WBD's raw outer fake-TCP packets.

This tool does not edit the WBD wire or performative outer retry policy.
"""
import argparse
import hashlib
import http.client
import http.server
import ipaddress
import json
import os
import pathlib
import re
import secrets
import signal
import socket
import subprocess
import sys
import time

NS="h227peer"
BR="h227br"
VX="h227vx"
HOST="h227host"
WAN="wan0"
IP={"server":"10.247.27.1","client":"10.247.27.2"}
ALLOWED_LOSS=(0.0,0.1,1.0,3.0)
ALLOWED_DELAY=(5,20,50)
PORT=18727

def check(condition,message):
    if not condition: raise RuntimeError("H2227_FAIL_CLOSED_"+message)

def run(*command,timeout=35,check_result=True):
    p=subprocess.run(list(command),text=True,stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,timeout=timeout)
    if check_result and p.returncode:
        raise RuntimeError("H2227_COMMAND_FAILED "+repr(command)+" "+
            p.stderr[-350:].replace("\n"," "))
    return p

def sudo(*args,timeout=35):
    return run("sudo","-n",*args,timeout=timeout)

def native(*args,timeout=35):
    return sudo("ip","netns","exec",NS,*args,timeout=timeout)

def expected(role):
    check(role in IP,"INVALID_ROLE")
    return IP[role]

def token_for_run(sha,run_id):
    check(bool(re.fullmatch(r"[0-9a-f]{40}",sha)),"BAD_SOURCE")
    check(bool(re.fullmatch(r"[1-9][0-9]{4,19}",str(run_id))),"BAD_RUN_ID")
    return hashlib.sha256(("WBD-H2227-CI-ONLY/"+str(run_id)+"/"+sha).encode()).hexdigest()

def tsip():
    p=run("tailscale","ip","-4")
    v=p.stdout.strip()
    check(len(v.splitlines())==1,"TAILSCALE_IP_AMBIGUOUS")
    addr=ipaddress.ip_address(v)
    check(addr.version==4 and addr in ipaddress.ip_network("100.64.0.0/10"),"TAILSCALE_IPV4_REQUIRED")
    return v

def self_meta(role):
    arch=os.uname().machine
    check((role,arch) in (("server","aarch64"),("client","x86_64")),
          "DISTINCT_NATIVE_ISA_REQUIRED")
    sha=os.environ["GITHUB_SHA"]
    run_id=os.environ["GITHUB_RUN_ID"]
    return {"schema_version":1,"role":role,"arch":arch,
        "source_sha":sha,"run_id":run_id,"tail_ip":tsip(),
        "underlay_ip":expected(role),"topology":"TS-VXLAN-L2-NATIVE-AF_PACKET",
        "not_physical_isp":True}

def validate_peer(peer,role,local_meta):
    check(isinstance(peer,dict),"INVALID_PEER_FORMAT")
    check(peer.get("schema_version")==1,"PEER_SCHEMA")
    check(peer.get("role")==role,"PEER_ROLE")
    check(peer.get("source_sha")==local_meta["source_sha"],"SOURCE_MISMATCH")
    check(peer.get("run_id")==local_meta["run_id"],"RUN_ID_MISMATCH")
    check(peer.get("arch")==("aarch64" if role=="server" else "x86_64"),
          "ARCH_MISMATCH")
    check(peer.get("underlay_ip")==expected(role),"UNDERLAY_IP_MISMATCH")
    other=ipaddress.ip_address(peer.get("tail_ip",""))
    ours=ipaddress.ip_address(local_meta["tail_ip"])
    check(other.version==4 and other in ipaddress.ip_network("100.64.0.0/10") and other!=ours,
          "NO_DISTINCT_TAILSCALE_PEER")
    check(peer.get("topology")=="TS-VXLAN-L2-NATIVE-AF_PACKET",
          "NO_AUTHENTIC_L2_TOPOLOGY")
    if role=="server":
        secret=peer.get("control_token","")
        check(isinstance(secret,str) and
              bool(re.fullmatch(r"[0-9a-f]{64}",secret)),
              "MISSING_ONE_TIME_CONTROL_TOKEN")
    return str(other)

def write_json(path,record):
    path=pathlib.Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")

def setup_net(role,peer_tail,local_tail):
    expected(role)
    peer=ipaddress.ip_address(peer_tail)
    own=ipaddress.ip_address(local_tail)
    check(peer.version==own.version==4 and peer!=own,"BAD_TAILSCALE_PEERS")
    check(run("ip","netns","list").stdout.find(NS)<0,
          "PREEXISTING_OWNED_NAMESPACE_NO_STEAL")
    # Built-in BBR kernels may have no loadable module; readback is the gate.
    run("sudo","-n","modprobe","tcp_bbr",check_result=False)
    sudo("sysctl","-q","-w","net.ipv4.tcp_congestion_control=bbr")
    check(run("sysctl","-n","net.ipv4.tcp_congestion_control").stdout.strip()=="bbr",
          "BBR_NOT_ACTIVE")
    # Record whether the authenticated VM-to-VM overlay traverses a
    # Tailscale relay; DERP speed is an infrastructure ceiling, not WBD.
    tailscale_probe=run("tailscale","ping","--c","3",str(peer),
                       timeout=24,check_result=False)
    path_text=(tailscale_probe.stdout+" "+tailscale_probe.stderr).lower()
    if "derp" in path_text:
        tail_path="RELAY_OR_DERP_NOT_PRODUCT_CAPACITY"
    elif tailscale_probe.returncode==0:
        tail_path="DIRECT_CANDIDATE_BUT_VERIFY_RUNNER_CAPACITY"
    else:
        tail_path="UNVERIFIED_TAILSCALE_PATH"
    sudo("ip","netns","add",NS)
    try:
        native("ip","link","set","lo","up")
        sudo("ip","link","add",BR,"type","bridge")
        sudo("ip","link","set",BR,"up")
        # Remote unicast VXLAN: WBD sees Ethernet AF_PACKET while Tailscale
        # carries only encrypted UDP outside the private impairment devices.
        sudo("ip","link","add",VX,"type","vxlan","id","227",
             "local",str(own),"remote",str(peer),"dev","tailscale0",
             "dstport","4789","nolearning")
        sudo("ip","link","set",VX,"master",BR)
        sudo("ip","link","set",VX,"up")
        sudo("ip","link","add",HOST,"type","veth","peer","name",WAN)
        sudo("ip","link","set",WAN,"netns",NS)
        sudo("ip","link","set",HOST,"master",BR)
        sudo("ip","link","set",HOST,"up")
        native("ip","addr","add",expected(role)+"/24","dev",WAN)
        native("ip","link","set",WAN,"mtu","1200")
        native("ip","link","set",WAN,"up")
        check(native("sysctl","-n","net.ipv4.tcp_congestion_control").stdout.strip()=="bbr",
              "NETNS_REAL_INNER_TCP_BBR_NOT_ACTIVE")
        native("sysctl","-q","-w","net.ipv4.conf.all.rp_filter=0")
        # Raw FakeTCP SYN uses our own userspace TCP stream/reply, not a
        # kernel-owned listener: suppress only OUTER wan0 RST, never TUN TCP.
        native("iptables","-w","-A","OUTPUT","-o",WAN,
               "-p","tcp","--tcp-flags","RST","RST","-j","DROP")
        set_netem(0,5)
        # Proven owned source route; no management interface impairment.
        chk=native("ip","-o","route","get",expected("client" if role=="server" else "server")).stdout
        check(WAN in chk,"UNDERLAY_ROUTE_NOT_OWNED")
        return {"role":role,"ns":NS,"wan":WAN,"vxlan":VX,
                "tail":str(own),"other_tail":str(peer),
                "bbr":"bbr","inner_tcp_only":True,
                "tailscale_path":tail_path,
                "tailscale_ping_evidence":tailscale_probe.stdout[-600:],
                "underlay":expected(role),"route":chk.strip()}
    except BaseException:
        teardown()
        raise

def teardown():
    # Only deterministic H2227-owned objects. Never touch tailscale0.
    for args in [("ip","netns","del",NS),("ip","link","del",HOST),
                 ("ip","link","del",VX),("ip","link","del",BR)]:
        run("sudo","-n",*args,check_result=False)

def set_netem(loss,delay):
    loss=float(loss)
    delay=int(delay)
    check(loss in ALLOWED_LOSS and delay in ALLOWED_DELAY,
          "IMPAIRMENT_NOT_ALLOWLISTED")
    native("tc","qdisc","replace","dev",WAN,"root","netem",
           "delay",str(delay)+"ms","loss",str(loss)+"%","limit","32768")
    parsed=json.loads(native("tc","-s","-j","qdisc","show",
                              "dev",WAN).stdout)
    check(any(v.get("kind")=="netem" for v in parsed),
          "NETEM_NOT_INSTALLED")
    return {"loss_pct":loss,"delay_ms":delay,"qdisc":parsed,
            "only_owned_veth":WAN,"tailscale_untouched":True}

def snapshot(role,phase,full=False):
    before=run("ip","netns","list").stdout
    check(NS in before,"SOURCE_NETNS_MISSING")
    q=json.loads(native("tc","-s","-j","qdisc","show","dev",WAN).stdout)
    sock=native("ss","-tinm",timeout=10).stdout[:20000]
    processes=native("ps","-eo","pid,ppid,pcpu,rss,stat,comm").stdout.splitlines()
    owned=[line.strip() for line in processes if
           "wbd-v4-" in line or "iperf3" in line][:80]
    stats=native("ip","-s","-j","link","show","dev",WAN).stdout
    return {"role":role,"phase":phase,"ns":NS,"wan":WAN,
        "qdisc":q,"link":json.loads(stats),"tcp":sock if full else sock[:6000],
        "wbd_native_cpu_rss_processes":owned,
        "timestamp_ns":time.monotonic_ns(),
        "tcp_cc":native("sysctl","-n","net.ipv4.tcp_congestion_control").stdout.strip()}

class Controller(http.server.BaseHTTPRequestHandler):
    token=None
    peer_ip=None
    role="server"
    def log_message(self,fmt,*a): pass
    def do_GET(self):
        if self.path!="/health":self.send_error(404);return
        if self.client_address[0]!=self.peer_ip or \
           self.headers.get("X-WBD-Test-Token")!=self.token:
            self.send_error(403);return
        self.respond({"ready":True,"source":"H2227_SERVER_REAL_L2"})
    def do_POST(self):
        if self.path!="/impair":self.send_error(404);return
        if self.client_address[0]!=self.peer_ip or \
           self.headers.get("X-WBD-Test-Token")!=self.token:
            self.send_error(403);return
        try:
            length=int(self.headers.get("Content-Length","0"))
            check(0<length<=128,"UNBOUNDED_CONTROL_BODY")
            obj=json.loads(self.rfile.read(length))
            check(set(obj)=={"loss_pct","delay_ms"},"CONTROL_FIELDS")
            out=set_netem(obj["loss_pct"],obj["delay_ms"])
            self.respond({"applied":True,"loss_pct":out["loss_pct"],
                "delay_ms":out["delay_ms"],"qdisc":out["qdisc"]})
        except (ValueError,RuntimeError) as exc:
            self.send_error(400,str(exc)[:120])
    def respond(self,obj):
        b=json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(b)))
        self.end_headers()
        self.wfile.write(b)

def post_control(host,token,loss,delay,health=False):
    check(len(token)==64 and bool(re.fullmatch(r"[0-9a-f]+",token)),
          "INVALID_RUN_TOKEN")
    c=http.client.HTTPConnection(host,PORT,timeout=8)
    headers={"X-WBD-Test-Token":token}
    if health:
        c.request("GET","/health",headers=headers)
    else:
        body=json.dumps({"loss_pct":float(loss),"delay_ms":int(delay)})
        headers["Content-Type"]="application/json"
        c.request("POST","/impair",body=body,headers=headers)
    response=c.getresponse()
    data=response.read(200000)
    check(response.status==200,"REMOTE_CONTROL_NOT_READY_"+str(response.status))
    o=json.loads(data)
    c.close()
    return o

def iperf_case(address,port,duration,streams,reverse,output,peer_pid=None):
    check(address in ("10.247.27.1","10.66.0.1"),"IPERF_UNTRUSTED_ADDRESS")
    check(port in (5201,5202) and 3<=duration<=30
          and streams in (1,4,8),"IPERF_INVALID_CASE")
    check(not (port==5202 and address!="10.247.27.1"),
          "BASELINE_ADDR_MISMATCH")
    check(not (port==5201 and address!="10.66.0.1"),
          "BUSINESS_ADDR_MISMATCH")
    command=["sudo","-n","ip","netns","exec",NS,"iperf3","-J",
             "-c",address,"-p",str(port),"-t",str(duration),
             "-P",str(streams),"-O","1","-C","bbr"]
    if reverse:command.append("-R")
    t0=time.monotonic()
    p=None;timeout=False
    try:p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,timeout=duration+18)
    except subprocess.TimeoutExpired as exc:
        timeout=True
        p=subprocess.CompletedProcess(command,124,exc.stdout or "",exc.stderr or "")
    stdout=p.stdout.decode("utf-8","replace") if isinstance(p.stdout,bytes) else str(p.stdout or "")
    stderr=p.stderr.decode("utf-8","replace") if isinstance(p.stderr,bytes) else str(p.stderr or "")
    pathlib.Path(str(output)+".iperf.txt").write_text(stdout[:500000])
    pathlib.Path(str(output)+".stderr.txt").write_text(stderr[-4000:])
    status="ERROR"
    mbps=None
    iperf=None
    try:iperf=json.loads(stdout)
    except (ValueError,TypeError):pass
    if p.returncode==0 and isinstance(iperf,dict) and "end" in iperf and \
         not iperf.get("error"):
        end=iperf["end"]
        summary=end.get("sum_received" if reverse else "sum_sent",{})
        bps=summary.get("bits_per_second")
        seconds=summary.get("seconds",0)
        if isinstance(bps,(float,int)) and bps>0 and seconds>=duration*0.6:
            mbps=round(bps/1e6,3)
            status="PASS_OBSERVED_TCP_APPLICATION"
    alive=None
    if peer_pid:
        try:os.kill(int(peer_pid),0);alive=True
        except ProcessLookupError:alive=False
    intervals=[]
    retransmits=None
    if isinstance(iperf,dict):
        for part in iperf.get("intervals",[])[:40]:
            if not isinstance(part,dict):continue
            block=part.get("sum",{})
            if not isinstance(block,dict):continue
            bps=block.get("bits_per_second")
            if isinstance(bps,(int,float)) and bps>=0:
                intervals.append(round(bps/1e6,3))
        end=iperf.get("end",{})
        if isinstance(end,dict):
            block=end.get("sum_sent",{})
            if isinstance(block,dict):
                retransmits=block.get("retransmits")
    rec={"status":status,"business_mbps":mbps,
        "wbd_outer_raw_fake_tcp_not_kernel_bbr":True,
        "interval_mbps":intervals,"kernel_tcp_retransmits":retransmits,
        "metric":"iperf3 end.sum_received" if reverse else "iperf3 end.sum_sent",
        "seconds_requested":duration,"elapsed_s":round(time.monotonic()-t0,3),
        "streams":streams,"direction":"download" if reverse else "upload",
        "port":port,"raw_baseline":port==5202,
        "rc":p.returncode,"timed_out":timeout,
        "client_worker_alive_after":alive,
        "error":str(iperf.get("error",""))[:250] if isinstance(iperf,dict) else stderr[-250:],
        "source_sha":os.environ.get("GITHUB_SHA","unknown"),
        "run_id":os.environ.get("GITHUB_RUN_ID","unknown")}
    write_json(output,rec)
    # Source-qualified failure, never turn early TCP abort into 0Mbps.
    return rec

def expected_matrix():
    """Exact *names* for the cross-VM, 2-direction, 2-mode × loss × fq trial.

    A cold failure must not count as five finished TCP flows. A repeated
    workload cannot substitute for another loss or direction.
    """
    direct={"raw-0-upload","raw-0-download"}
    app=set()
    scenarios=((0,600),(0,0),(0.1,600),(1,600),(3,600))
    for loss,fq in scenarios:
        for direction in ("upload","download"):
            direct.add(f"raw-{loss}-fq{fq}-{direction}")
        for mode in ("normal","fec-fixed"):
            for duration,streams,direction in (
                (3,1,"upload"),(12,1,"upload"),(12,1,"download"),
                (12,4,"upload"),(12,4,"download")):
                app.add(f"{mode}-loss{loss}-fq{fq}-"
                        f"{duration}s-{streams}p-{direction}")
    check(len(direct)==12 and len(app)==50,"INVALID_FIXED_EXPECTED_MATRIX")
    return direct,app

def summary(directory):
    root=pathlib.Path(directory)
    recs=[]
    suffixes=[]
    for p in sorted(root.glob("case-*.json")):
        match=re.fullmatch(r"case-\d{3}-(.+)\.json",p.name)
        check(match is not None,"CASE_FILENAME_NOT_SOURCE_OWNED")
        suffixes.append(match.group(1))
        try:
            rec=json.loads(p.read_text())
            check(isinstance(rec,dict),"CASE_NOT_JSON_OBJECT")
            check(rec.get("status") in ("PASS_OBSERVED_TCP_APPLICATION","ERROR"),
                  "CASE_MISSING_SOURCE_STATUS")
        except (OSError,ValueError,RuntimeError) as exc:
            rec={"status":"ERROR","business_mbps":None,"raw_baseline":False,
                 "error":"CASE_RESULT_UNPARSABLE_"+type(exc).__name__}
        recs.append({"file":p.name,**rec})
    check(bool(recs),"NO_ACTUAL_TCP_CASES")
    direct,app=expected_matrix()
    observed=set(suffixes)
    duplicates=sorted(x for x in observed if suffixes.count(x)>1)
    missing_direct=sorted(direct-observed)
    missing_app=sorted(app-observed)
    modes=[x for x in recs if not x.get("raw_baseline")]
    baselines=[x for x in recs if x.get("raw_baseline")]
    failures=[x for x in recs if x["status"]=="ERROR" or
        x.get("client_worker_alive_after") is False]
    matrix_incomplete=bool(missing_direct or missing_app or duplicates)
    if matrix_incomplete:
        failures.append({"status":"ERROR","error":"INCOMPLETE_SOURCE_LOCKED_MATRIX",
            "missing_direct":missing_direct,"missing_app":missing_app,
            "duplicate_case_suffixes":duplicates})
    clean_baseline=[x["business_mbps"] for x in baselines
        if isinstance(x.get("business_mbps"),(float,int)) and
        ("raw-0-fq600" in x["file"] or "raw-0-upload" in x["file"] or
         "raw-0-download" in x["file"])]
    clean_peak=max(clean_baseline,default=0.0)
    topology=root/"topology-client.json"
    tail_path="UNKNOWN_NO_PAIR_TOPOLOGY"
    if topology.is_file():
        tail_path=json.loads(topology.read_text()).get("tailscale_path",tail_path)
    compare=(clean_peak>=800 and
             tail_path=="DIRECT_CANDIDATE_BUT_VERIFY_RUNNER_CAPACITY")
    grade_proofs=[]
    for p in sorted(root.glob("*-fec6-proof.json")):
        # Post Stop actual Rust readback; the similarly named case-ERROR
        # is not permitted as a PASS proof of FEC6.
        if p.name.startswith("case-"):continue
        try:grade_proofs.append({"file":p.name,**json.loads(p.read_text())})
        except (ValueError,OSError):
            grade_proofs.append({"file":p.name,"status":"ERROR"})
    if matrix_incomplete:
        classification="FAIL_INCOMPLETE_TWO_RUNNER_APP_MATRIX"
    elif failures:
        classification="FAIL_REAL_TWO_RUNNER_APPLICATION_OR_WORKER"
    else:
        classification="REAL_TWO_RUNNER_APPPATH_SCOPED"
    return {
        "classification":classification,
        "matrix_complete":not matrix_incomplete,
        "expected_direct_cases":len(direct),"expected_business_cases":len(app),
        "actual_direct_cases":len(baselines),"actual_business_cases":len(modes),
        "missing_direct_case_suffixes":missing_direct,
        "missing_business_case_suffixes":missing_app,
        "capacity_reference":"COMPARABLE_800MBPS_BASELINE" if compare else
            "INFRA_OR_TS_LIMITED_BELOW_800MBPS_DO_NOT_ATTRIBUTE_80MBPS_TO_WBD",
        "tailscale_path":tail_path,
        "clean_direct_baseline_peak_mbps":clean_peak,
        "cases":recs,"fails":failures,"fec6_post_stop_proofs":grade_proofs,
        "baseline_mbps":[x.get("business_mbps") for x in baselines],
        "business_mbps":[x.get("business_mbps") for x in modes],
        "not_a_physical_windows_isp_test":True,
        "xray_same_host_comparison":"NOT_RUN",
        "exact_underlay_bbr":"NOT_APPLICABLE_RAW_AF_PACKET",
        "outer_fake_retransmission_policy":"UNCHANGED"}

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("metadata");a.add_argument("role",choices=tuple(IP))
    a.add_argument("output")
    a=sub.add_parser("topology");a.add_argument("role",choices=tuple(IP))
    a.add_argument("peer");a.add_argument("out")
    a=sub.add_parser("teardown")
    a=sub.add_parser("impair");a.add_argument("loss",type=float)
    a.add_argument("delay",type=int)
    a=sub.add_parser("server-control");a.add_argument("peer")
    a=sub.add_parser("remote-impair");a.add_argument("peer")
    a.add_argument("loss",type=float);a.add_argument("delay",type=int)
    a=sub.add_parser("remote-health");a.add_argument("peer")
    a=sub.add_parser("snapshot");a.add_argument("role",choices=tuple(IP))
    a.add_argument("phase");a.add_argument("out")
    a=sub.add_parser("iperf");a.add_argument("kind",choices=("baseline","wbd"))
    a.add_argument("duration",type=int);a.add_argument("streams",type=int)
    a.add_argument("direction",choices=("upload","download"))
    a.add_argument("out");a.add_argument("--pid",type=int)
    a=sub.add_parser("summary");a.add_argument("dir");a.add_argument("out")
    a=sub.add_parser("selftest")
    args=p.parse_args()
    if args.command=="selftest":
        local={"schema_version":1,"role":"client","arch":"x86_64",
          "source_sha":"a"*40,"run_id":"123456","tail_ip":"100.88.8.7"}
        peer=dict(local,role="server",arch="aarch64",
          tail_ip="100.88.8.8",underlay_ip=IP["server"],
          topology="TS-VXLAN-L2-NATIVE-AF_PACKET",control_token="c"*64)
        validate_peer(peer,"server",local)
        for bad in (dict(peer,source_sha="b"*40),
                    dict(peer,arch="x86_64"),dict(peer,tail_ip=local["tail_ip"]),
                    dict(peer,topology="SAME_RUNNER")):
            try:validate_peer(bad,"server",local)
            except RuntimeError:continue
            raise AssertionError("invalid cross-runner source admitted")
        check(token_for_run("a"*40,"123456")!=token_for_run("a"*40,"123457"),
              "RUN_TOKEN_COLLISION")
        try:iperf_case("8.8.8.8",5201,3,1,False,"/dev/null")
        except RuntimeError:pass
        else:raise AssertionError("arbitrary untrusted iperf target accepted")
        print("H2227_FIXTURE_SELFTEST_PASS source_pair_isolation=1 no_fake_iperf=1")
    elif args.command=="metadata":
        meta=self_meta(args.role)
        if args.role=="server":
            meta["control_token"]=secrets.token_hex(32)
        write_json(args.output,meta)
    elif args.command=="topology":
        local=self_meta(args.role)
        peer=json.loads(pathlib.Path(args.peer).read_text())
        other=validate_peer(peer,"server" if args.role=="client" else "client",local)
        write_json(args.out,setup_net(args.role,other,local["tail_ip"]))
    elif args.command=="teardown":teardown()
    elif args.command=="impair":
        print(json.dumps(set_netem(args.loss,args.delay)))
    elif args.command=="server-control":
        local=self_meta("server")
        other=validate_peer(json.loads(pathlib.Path(args.peer).read_text()),"client",local)
        server_meta=json.loads(pathlib.Path("h2227-meta/server.json").read_text())
        check(server_meta["source_sha"]==local["source_sha"] and
              server_meta["run_id"]==local["run_id"],
              "LOCAL_SERVER_TOKEN_NOT_SOURCE_LOCKED")
        Controller.token=server_meta["control_token"]
        Controller.peer_ip=other
        http.server.ThreadingHTTPServer((local["tail_ip"],PORT),Controller).serve_forever()
    elif args.command in ("remote-impair","remote-health"):
        peer=json.loads(pathlib.Path(args.peer).read_text())
        local=self_meta("client")
        other=validate_peer(peer,"server",local)
        print(json.dumps(post_control(other,peer["control_token"],
            getattr(args,"loss",0),getattr(args,"delay",5),
            health=args.command=="remote-health")))
    elif args.command=="snapshot":
        write_json(args.out,snapshot(args.role,args.phase,True))
    elif args.command=="iperf":
        addr="10.247.27.1" if args.kind=="baseline" else "10.66.0.1"
        port=5202 if args.kind=="baseline" else 5201
        rec=iperf_case(addr,port,args.duration,args.streams,
                       args.direction=="download",args.out,args.pid)
        print(json.dumps(rec))
        if rec["status"]!="PASS_OBSERVED_TCP_APPLICATION":
            sys.exit(2)
    elif args.command=="summary":
        s=summary(args.dir);write_json(args.out,s)
        print(s["classification"])
        if s["fails"]:sys.exit(2)

if __name__=="__main__":
    try:main()
    except (RuntimeError,ValueError,KeyError,subprocess.TimeoutExpired) as exc:
        print("H2227_FIXTURE_FAIL "+str(exc),file=sys.stderr)
        sys.exit(2)
