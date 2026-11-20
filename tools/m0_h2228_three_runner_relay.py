#!/usr/bin/env python3
"""H2228: real 3-runner routed WAN. No product source, retransmission or FEC changes.

Client x86_64 --(VXLAN/Tailscale A)--> ARM64 kernel L3 relay
           --(VXLAN/Tailscale B)--> Server x86_64.
Both WAN halves have distinct Layer-2 domains. Only ARM *router namespace*
egress is impaired, once per traffic direction. Never impair tailscale0,
GitHub management traffic, endpoints, or the iperf3 app process directly.

Fixed 200ms one-way *added* delay, 15ms Gaussian jitter with 25% correlation,
and Gilbert-Elliott 4-packet mean bad-state bursts (or iid diagnostic A/B).
No tc rate cap: relay bandwidth is a MEASUREMENT/QUALIFICATION prerequisite.
"""
import argparse
import hashlib
import http.client
import http.server
import ipaddress
import json
import math
import os
import pathlib
import re
import secrets
import subprocess
import sys
import time

NODE="h228node"
ROUTER="h228rt"
BR={"client":"h228bc","server":"h228bs"}
VX={"client":"h228vc","server":"h228vs"}
VHOST={"client":"h228hc","server":"h228hs"}
LAN={"client":"10.248.81.2","server":"10.248.82.2"}
GW={"client":"10.248.81.1","server":"10.248.82.1"}
RDEV={"client":"rcli0","server":"rsrv0"}
CIDR={"client":"10.248.81.0/24","server":"10.248.82.0/24"}
VXID={"client":"2281","server":"2282"}
# Reuse the already-proven H2227 tailnet CI ACL control port.
CONTROL_PORT=18727
LOSSES=(0.0,1.0,5.0,10.0,20.0)
ROLES={"client":"x86_64","server":"x86_64","relay":"aarch64"}
TAILNET=ipaddress.ip_network("100.64.0.0/10")

def guard(expr,message):
    if not expr:raise RuntimeError("H2228_FAIL_CLOSED_"+message)

def cmd(*args,timeout=30,allow_fail=False):
    p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if p.returncode and not allow_fail:
        raise RuntimeError("H2228_COMMAND_FAIL "+repr(args)+": "+p.stderr[-340:])
    return p

def root(*args,**kw):
    return cmd("sudo","-n",*args,**kw)

def ns(name,*args,**kw):
    return root("ip","netns","exec",name,*args,**kw)

def save(path,contents):
    p=pathlib.Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(contents,indent=2,sort_keys=True)+"\n")

def tailscale_ip():
    lines=cmd("tailscale","ip","-4").stdout.strip().splitlines()
    guard(len(lines)==1,"TAIL_IPV4_UNIQUE")
    a=ipaddress.ip_address(lines[0])
    guard(a in TAILNET,"TAIL_EXPECT_100_64_SLASH10")
    return str(a)

def metainfo(role):
    guard(role in ROLES and os.uname().machine==ROLES[role],
          "NATIVE_RUNNER_ARCH_MISMATCH")
    sha=os.environ["GITHUB_SHA"];runid=os.environ["GITHUB_RUN_ID"]
    guard(bool(re.fullmatch(r"[a-f0-9]{40}",sha)) and
          bool(re.fullmatch(r"[1-9][0-9]{4,19}",runid)), "SOURCE_RUN_ID")
    d={"schema":1,"role":role,"arch":os.uname().machine,
       "source_sha":sha,"run_id":runid,"tail_ip":tailscale_ip(),
       "network":"H2228-THREE-PHYSICAL-GHA-VM-L3-RELAY",
       "physical_windows_isp":"NOT_RUN"}
    if role=="relay":d["control_token"]=secrets.token_hex(32)
    return d

def validate_pair(our,other,role):
    guard(isinstance(other,dict) and role in ROLES,"INVALID_REMOTE_META")
    for k,v in (("schema",1),("role",role),("arch",ROLES[role]),
                ("source_sha",our["source_sha"]),("run_id",our["run_id"]),
                ("network","H2228-THREE-PHYSICAL-GHA-VM-L3-RELAY")):
        guard(other.get(k)==v,"REMOTE_META_"+k)
    addr=ipaddress.ip_address(other.get("tail_ip",""))
    guard(addr in TAILNET and str(addr)!=our["tail_ip"],
          "REMOTE_TAIL_IP_NOT_DISTINCT")
    if role=="relay":
        guard(bool(re.fullmatch(r"[0-9a-f]{64}",other.get("control_token",""))),
              "NO_RANDOM_RELAY_CONTROL_TOKEN")
    return str(addr)

def peer_file(path,our,role):
    p=json.loads(pathlib.Path(path).read_text())
    validate_pair(our,p,role)
    return p

def bbr(name):
    root("modprobe","tcp_bbr",allow_fail=True)
    # Each new netns starts with its own TCP CC default (typically cubic),
    # regardless of global host readback. Explicitly set BOTH. Do not
    # misclassify an unconfigured netns as a missing BBR kernel module.
    root("sysctl","-q","-w","net.ipv4.tcp_congestion_control=bbr")
    ns(name,"sysctl","-q","-w","net.ipv4.tcp_congestion_control=bbr")
    target=ns(name,"sysctl","-n","net.ipv4.tcp_congestion_control").stdout.strip()
    guard(target=="bbr","NAMESPACE_BBR_READBACK")
    # Real BBR long-fat path needs >50MiB receive/socket window to occupy
    # 1Gbps x 400ms RTT. The same settings apply to direct/WBD cases.
    for k,v in (
        ("net.ipv4.tcp_rmem","4096 87380 67108864"),
        ("net.ipv4.tcp_wmem","4096 65536 67108864"),
        ("net.core.rmem_max","67108864"),
        ("net.core.wmem_max","67108864"),
        ("net.ipv4.tcp_window_scaling","1"),
    ):
        ns(name,"sysctl","-q","-w",k+"="+v)
    return {"tcp_cc":target,"tcp_rmem":ns(name,"sysctl","-n","net.ipv4.tcp_rmem").stdout.strip(),
            "tcp_wmem":ns(name,"sysctl","-n","net.ipv4.tcp_wmem").stdout.strip()}

def vxlan(name,local_ip,remote_ip,interface,vxid,bridge):
    root("ip","link","add",interface,"type","vxlan","id",vxid,
         "local",local_ip,"remote",remote_ip,"dev","tailscale0",
         "dstport","4789","nolearning")
    root("ip","link","set",interface,"master",bridge)
    root("ip","link","set",interface,"up")

def install_endpoint(role,peer):
    guard(role in ("client","server"),"NODE_ROLE")
    our=metainfo(role)
    validate_pair(our,peer,"relay")
    guard(NODE not in cmd("ip","netns","list").stdout,"OWNED_NAMESPACE_ALREADY_EXISTS")
    root("ip","netns","add",NODE)
    try:
        ns(NODE,"ip","link","set","lo","up")
        root("ip","link","add",BR[role],"type","bridge")
        root("ip","link","set",BR[role],"up")
        vxlan(role,our["tail_ip"],peer["tail_ip"],VX[role],VXID[role],BR[role])
        root("ip","link","add",VHOST[role],"type","veth","peer","name","wan0")
        root("ip","link","set","wan0","netns",NODE)
        root("ip","link","set",VHOST[role],"master",BR[role])
        root("ip","link","set",VHOST[role],"up")
        ns(NODE,"ip","addr","add",LAN[role]+"/24","dev","wan0")
        ns(NODE,"ip","link","set","wan0","mtu","1200")
        ns(NODE,"ip","link","set","wan0","up")
        other="server" if role=="client" else "client"
        ns(NODE,"ip","route","replace",CIDR[other],"via",GW[role],"dev","wan0")
        ns(NODE,"sysctl","-q","-w","net.ipv4.conf.all.rp_filter=0")
        ns(NODE,"sysctl","-q","-w","net.ipv4.conf.wan0.rp_filter=0")
        # Suppress kernel RST only on the synthetic WBD underlay TCP:443.
        # Ordinary direct iperf3:5202 kernel TCP continues unmodified.
        match=["--dport","443"] if role=="client" else ["--sport","443"]
        ns(NODE,"iptables","-w","-A","OUTPUT","-o","wan0","-p","tcp",
           *match,"--tcp-flags","RST","RST","-j","DROP")
        cc=bbr(NODE)
        rt=ns(NODE,"ip","route","get",LAN[other]).stdout.strip()
        guard("via "+GW[role] in rt and "dev wan0" in rt,
              "CLIENT_SERVER_MUST_ROUTE_THROUGH_RELAY")
        return {"role":role,"node":NODE,"subnet":CIDR[role],
                "gateway":GW[role],"route":rt,
                "net_iface_mtu":1200,"tcp":cc,"impairments":"RELAY_ONLY",
                "peer_tail_ip":peer["tail_ip"]}
    except BaseException:
        cleanup(role)
        raise

def install_relay(client,server):
    our=metainfo("relay")
    validate_pair(our,client,"client")
    validate_pair(our,server,"server")
    guard(len({our["tail_ip"],client["tail_ip"],server["tail_ip"]})==3,
          "THREE_DISTINCT_RUNNERS_REQUIRED")
    guard(ROUTER not in cmd("ip","netns","list").stdout,"RELAY_NAMESPACE_ALREADY_EXISTS")
    root("ip","netns","add",ROUTER)
    try:
        ns(ROUTER,"ip","link","set","lo","up")
        for role,peer in (("client",client),("server",server)):
            root("ip","link","add",BR[role],"type","bridge")
            root("ip","link","set",BR[role],"up")
            vxlan(role,our["tail_ip"],peer["tail_ip"],
                  VX[role],VXID[role],BR[role])
            root("ip","link","add",VHOST[role],"type","veth",
                 "peer","name",RDEV[role])
            root("ip","link","set",RDEV[role],"netns",ROUTER)
            root("ip","link","set",VHOST[role],"master",BR[role])
            root("ip","link","set",VHOST[role],"up")
            ns(ROUTER,"ip","addr","add",GW[role]+"/24","dev",RDEV[role])
            ns(ROUTER,"ip","link","set",RDEV[role],"mtu","1200")
            ns(ROUTER,"ip","link","set",RDEV[role],"up")
            ns(ROUTER,"sysctl","-q","-w","net.ipv4.conf."+RDEV[role]+".rp_filter=0")
        ns(ROUTER,"sysctl","-q","-w","net.ipv4.conf.all.rp_filter=0")
        ns(ROUTER,"sysctl","-q","-w","net.ipv4.ip_forward=1")
        guard(ns(ROUTER,"sysctl","-n","net.ipv4.ip_forward").stdout.strip()=="1",
              "KERNEL_L3_FORWARD_DISABLED")
        for role in ("client","server"):
            ns(ROUTER,"iptables","-w","-I","FORWARD","1","-i",RDEV[role],
               "-o",RDEV["server" if role=="client" else "client"],
               "-j","ACCEPT")
        # Explicit no MASQUERADE: real client original IP traverses L3 hop.
        applied=impair(0,0,"iid")
        return {"role":"relay","relay_ns":ROUTER,"arch":"aarch64",
            "client_vxid":VXID["client"],"server_vxid":VXID["server"],
            "networks":[CIDR["client"],CIDR["server"]],
            "traffic":"REAL_IPV4_L3_ROUTING_NO_NAT",
            "two_different_L2_segments":True,"tail_client":client["tail_ip"],
            "tail_server":server["tail_ip"],"impair_readback":applied,
            "physical_speed_not_implied":True}
    except BaseException:
        cleanup("relay")
        raise

def ge_params(loss):
    """Stationary mean loss = q_bad*0.9 + (1-q_bad)*0.001.
    In bad state, leave at r=25%/packet: mean burst length ~=4 pkts.
    """
    guard(loss in (1.,5.,10.,20.),"GILBERT_LOSS_SET")
    target=loss/100
    bad=(target-0.001)/(0.9-0.001)
    r=0.25
    p=(r*bad)/(1-bad)
    guard(0<p<1 and 0<bad<1,"GE_MODEL_INVALID")
    return {"transition_good_bad_pct":round(p*100,6),
            "transition_bad_good_pct":25.0,
            "bad_loss_pct":90.0,"good_loss_pct":0.1,
            "analytical_mean_loss_pct":loss,"mean_bad_burst_packets":4.0}

def impair(loss,delay,model):
    loss=float(loss);delay=int(delay)
    guard(loss in LOSSES,"UNAPPROVED_PACKET_LOSS")
    guard(delay in (0,200) and ((delay==0)==(loss==0) or delay==200),
          "UNAPPROVED_DELAY_LOSS_PAIR")
    guard(model in ("iid","burst"),"UNAPPROVED_LOSS_MODEL")
    check=ns(ROUTER,"ip","link","show","dev","rcli0").returncode
    guard(check==0,"RELAY_ROUTE_NOT_CREATED")
    extras=["loss","random",str(loss)+"%"] if loss>0 else ["loss","0%"]
    ge=None
    if model=="burst" and loss:
        ge=ge_params(loss)
        extras=["loss","gemodel",str(ge["transition_good_bad_pct"])+"%",
                "25%","90%","0.1%"]
    delay_terms=["delay","0ms"] if delay==0 else [
        "delay","200ms","15ms","25%","distribution","normal"]
    receipts={}
    for role in ("client","server"):
        device=RDEV[role]
        ns(ROUTER,"tc","qdisc","replace","dev",device,"root","netem",
           *delay_terms,*extras,"limit","65536")
        q=json.loads(ns(ROUTER,"tc","-s","-j","qdisc","show","dev",device).stdout)
        guard(any(x.get("kind")=="netem" for x in q),
              "QDISC_READBACK_NOT_NETEM_"+device)
        receipts[device]=q
    return {"loss_target_pct":loss,"one_way_added_delay_ms":delay,
        "jitter_ms":15 if delay else 0,"jitter_correlation_pct":25 if delay else 0,
        "loss_model":model,"gilbert":ge,"qdisc_packet_limit":65536,
        "bandwidth_rate_cap":"NONE","apply_to":"RELAY_ROUTER_ONLY_EGRESS_BOTH_DIRECTIONS",
        "qdiscs":receipts,"no_tailscale_or_endpoint_qdisc_changed":True}

def local_relay_snapshot(tag):
    d={}
    for role,dev in RDEV.items():
        d[role]={"qdisc":json.loads(ns(ROUTER,"tc","-s","-j","qdisc",
            "show","dev",dev).stdout),
            "link":json.loads(ns(ROUTER,"ip","-s","-j","link","show",
                                "dev",dev).stdout)}
    d["tailscaled_ps"]=cmd("ps","-C","tailscaled","-o","pid,pcpu,rss,stat,comm",
                            allow_fail=True).stdout[-3000:]
    d["softnet_stat"]=pathlib.Path("/proc/net/softnet_stat").read_text()[:8000]
    d["linux_relay_routing"]=ns(ROUTER,"ip","route").stdout
    for role in ("client","server"):
        path=pathlib.Path("h2228-out")/("tail-to-"+role+".json")
        if path.is_file():
            d["tail_to_"+role]=json.loads(path.read_text())
    d["tag"]=tag
    return d

class Control(http.server.BaseHTTPRequestHandler):
    client_ip=None
    token=None
    def log_message(self,*args):pass
    def authorized(self):
        return self.client_address[0]==self.client_ip and \
           self.headers.get("X-H2228-Token")==self.token
    def result(self,x):
        raw=json.dumps(x).encode()
        self.send_response(200);self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(raw)));self.end_headers()
        self.wfile.write(raw)
    def do_GET(self):
        if not self.authorized():self.send_error(403);return
        if self.path=="/health":self.result({"role":"REAL_ARM64_KERNEL_ROUTER","alive":True})
        elif self.path=="/snapshot":self.result(local_relay_snapshot("remote"))
        else:self.send_error(404)
    def do_POST(self):
        if not self.authorized():self.send_error(403);return
        if self.path!="/impair":self.send_error(404);return
        try:
            length=int(self.headers.get("Content-Length","0"))
            guard(0<length<=128,"CONTROL_BODY_UNBOUNDED")
            o=json.loads(self.rfile.read(length))
            guard(set(o)=={"loss_pct","delay_ms","model"},"CONTROL_EXTRA_FIELDS")
            self.result(impair(o["loss_pct"],o["delay_ms"],o["model"]))
        except (RuntimeError,ValueError,TypeError) as e:
            self.send_error(400,str(e)[:140])

def remote(peer,action,loss=0,delay=0,model="iid"):
    host=peer["tail_ip"];token=peer["control_token"]
    guard(host in [str(ipaddress.ip_address(host))] and
          ipaddress.ip_address(host) in TAILNET,"REMOTE_IP_NOT_TAILSCALE")
    guard(bool(re.fullmatch("[0-9a-f]{64}",token)),"CONTROL_TOKEN_INVALID")
    conn=http.client.HTTPConnection(host,CONTROL_PORT,timeout=8)
    headers={"X-H2228-Token":token}
    if action in ("health","snapshot"):
        try:conn.request("GET","/"+action,headers=headers)
        except OSError as e:raise RuntimeError("RELAY_CONTROL_CONNECT_FAILED_18727_"+type(e).__name__) from e
    else:
        guard(action=="impair","REMOTE_CONTROL_ACTION")
        body=json.dumps({"loss_pct":float(loss),"delay_ms":int(delay),
                         "model":model})
        try:conn.request("POST","/impair",body=body,
            headers=dict(headers,**{"Content-Type":"application/json"}))
        except OSError as e:raise RuntimeError("RELAY_CONTROL_POST_FAILED_18727_"+type(e).__name__) from e
    try:
        rsp=conn.getresponse()
        raw=rsp.read(250000)
    except (OSError,TimeoutError) as e:
        raise RuntimeError("RELAY_CONTROL_TIMEOUT_OR_ACL_PORT_18727_"+type(e).__name__) from e
    conn.close()
    guard(rsp.status==200,"REMOTE_CONTROL_HTTP_"+str(rsp.status)+
          "_"+raw[:120].decode("utf-8","replace"))
    return json.loads(raw)

def local_node_snapshot(role,tag):
    d={"role":role,"tag":tag,"tcp_cc":ns(NODE,"sysctl","-n",
        "net.ipv4.tcp_congestion_control").stdout.strip(),
       "ip_route":ns(NODE,"ip","route").stdout,
       "node_iptables_rsts":ns(NODE,"iptables","-w","-S","OUTPUT").stdout,
       "ss_tcp":ns(NODE,"ss","-tinm").stdout[-30000:],
       "wan_link":json.loads(ns(NODE,"ip","-s","-j","link","show","dev","wan0").stdout)}
    return d

def iperf(kind,duration,streams,direction,out):
    guard(kind in ("direct","wbd") and
          duration in (3,12,18,20) and streams in (1,4,8) and
          direction in ("upload","download"),"BAD_IPERF_REQUEST")
    host=LAN["server"] if kind=="direct" else "10.66.0.1"
    port=5202 if kind=="direct" else 5201
    args=["sudo","-n","ip","netns","exec",NODE,"iperf3","-J","-C","bbr",
          "-c",host,"-p",str(port),"-P",str(streams),"-t",str(duration),
          "-O","2"]
    if direction=="download":args.append("-R")
    t=time.monotonic()
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=duration+40)
        stdout=p.stdout;stderr=p.stderr;returncode=p.returncode
    except subprocess.TimeoutExpired as e:
        stdout=e.stdout or b"";stderr=e.stderr or b"";returncode=124
        if isinstance(stdout,bytes):stdout=stdout.decode(errors="replace")
        if isinstance(stderr,bytes):stderr=stderr.decode(errors="replace")
    pathlib.Path(str(out)+".stdout.txt").write_text(stdout[-350000:])
    pathlib.Path(str(out)+".stderr.txt").write_text(stderr[-6000:])
    parsed=None;speed=None;interval=[];retransmits=None;secs=0
    try:parsed=json.loads(stdout)
    except ValueError:pass
    if isinstance(parsed,dict):
        for part in parsed.get("intervals",[])[:60]:
            row=part.get("sum",{})
            if "bits_per_second" in row:
                interval.append(round(row["bits_per_second"]/1e6,3))
        end=parsed.get("end",{})
        row=end.get("sum_received" if direction=="download" else "sum_sent",{})
        secs=row.get("seconds",0)
        bps=row.get("bits_per_second")
        retransmits=end.get("sum_sent",{}).get("retransmits")
        if returncode==0 and not parsed.get("error") and isinstance(bps,(float,int)) and \
             bps>0 and secs>=duration*0.6:
            speed=round(bps/1e6,3)
    record={"status":"PASS_REAL_KERNEL_IPERF3_TCP" if speed is not None else
              "ERROR_TCP_CRASH_ABORT_OR_UNREACHABLE",
            "mbps":speed,"elapsed_s":round(time.monotonic()-t,3),
            "seconds_requested":duration,"seconds_observed":secs,
            "kind":kind,"direction":direction,"streams":streams,
            "tcp_cc_requested":"bbr","tcp_app_not_outer_bbr":True,
            "iperf3_rc":returncode,"tcp_retransmits":retransmits,
            "ramp_interval_mbps":interval,"parse_error":parsed.get("error","") if isinstance(parsed,dict) else
             stderr[-250:],"source_sha":os.environ.get("GITHUB_SHA"),
            "run_id":os.environ.get("GITHUB_RUN_ID")}
    save(out,record)
    return record



def classify_final_tail_ping(raw,rc):
    """DERP can be used for the FIRST ping while NAT hole punching resolves.
    Use last actual reply, never 'DERP appeared anywhere' as false cap proof.
    A direct last reply is a candidate only; compare clean BBR throughput.
    """
    lines=[x.strip() for x in raw.splitlines() if x.strip().startswith("pong from ")]
    if not lines or rc!=0:return "UNKNOWN_NOT_QUALIFIED"
    last=lines[-1]
    if "via DERP" in last:return "DERP_OR_RELAY_INFRA_LIMIT"
    if re.search(r"via (?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]+",last):
        return "DIRECT_CANDIDATE"
    return "UNKNOWN_NOT_QUALIFIED"

def expected_cases(model):
    guard(model in ("iid","burst"),"CASE_MODEL")
    exp={
        "clear-zero-direct-12s-8p-upload",
        "clear-zero-direct-12s-8p-download",
    }
    for loss in (0,1,5,10,20):
        prefix=f"delay200-loss{loss}-{model}"
        for direction in ("upload","download"):
            exp.add(f"{prefix}-direct-20s-4p-{direction}")
            exp.add(f"{prefix}-wbd-20s-4p-{direction}")
        exp.add(f"{prefix}-wbd-3s-1p-upload")
    guard(len(exp)==27,"SOURCE_CASE_MATRIX_SIZE")
    return exp

def result_summary(mode,model,directory):
    rootpath=pathlib.Path(directory)
    required=expected_cases(model)
    rows=[];actual=[]
    for p in sorted(rootpath.glob("case-*.json")):
        m=re.fullmatch(r"case-\d{3}-(.+)\.json",p.name)
        guard(m is not None,"CASE_NAME_UNEXPECTED")
        suffix=m.group(1)
        actual.append(suffix)
        try:
            record=json.loads(p.read_text())
            guard(isinstance(record,dict),"CASE_NOT_JSON")
            guard(record.get("status") in ("PASS_REAL_KERNEL_IPERF3_TCP",
                 "ERROR_TCP_CRASH_ABORT_OR_UNREACHABLE"),
                  "CASE_STATUS_UNTRUSTWORTHY")
        except (ValueError,OSError,RuntimeError) as exc:
            record={"status":"ERROR_TCP_CRASH_ABORT_OR_UNREACHABLE",
                    "mbps":None,"error":"UNPARSABLE_"+type(exc).__name__}
        rows.append({"file":p.name,"case":suffix,**record})
    missing=sorted(required-set(actual))
    duplicates=sorted(x for x in set(actual) if actual.count(x)>1)
    failures=[x for x in rows if x["status"]!="PASS_REAL_KERNEL_IPERF3_TCP"]
    direct={x["case"]:x["mbps"] for x in rows
            if x["case"] in required and x.get("kind")=="direct"}
    app={x["case"]:x["mbps"] for x in rows
            if x["case"] in required and x.get("kind")=="wbd"}
    clear=[direct.get("clear-zero-direct-12s-8p-"+direction)
           for direction in ("upload","download")]
    relay_links=[]
    for p in (rootpath/"relay-health.json",rootpath/"clear-before-relay.json",
              rootpath/"after-unimpaired-relay.json"):
        if p.is_file():relay_links.append(p.name)
    # Relay may be bottleneck due to 2 Tailscale encrypt+decrypt hops.
    # Both clean directions must be high enough, and direct TS paths are
    # needed to compare WBD capacity with physical 1Gbps user observation.
    direct_evidence=all(isinstance(x,(float,int)) and x>=800 for x in clear)
    snapshots=list(rootpath.glob("*-relay.json"))
    tail_status=set()
    for p in snapshots:
        try:
            rec=json.loads(p.read_text())
            for key in ("client","server"):
                label=rec.get("tail_to_"+key,{}).get("tail_path")
                if label:tail_status.add(label)
        except (ValueError,OSError):pass
    relay_path_ok=tail_status=={"DIRECT_CANDIDATE"}
    capacity_qualified=direct_evidence and relay_path_ok
    snapshots_rtt=[]
    for loss in (0,1,5,10,20):
        f=rootpath/f"delay200-loss{loss}-{model}-observed-rtt.txt"
        if not f.is_file():continue
        value=re.search(r"(?:rtt|round-trip) min/avg/max/(?:mdev|stddev)\s*=\s*([0-9.]+)/([0-9.]+)/([0-9.]+)/([0-9.]+)",f.read_text())
        snapshots_rtt.append({"loss_target_pct":loss,
             "observed_rtt_avg_ms":float(value.group(2)) if value else None,
             "ping_excerpt":f.read_text()[-600:]})
    per_loss=[]
    for loss in (0,1,5,10,20):
        prefix=f"delay200-loss{loss}-{model}"
        row={"loss_target_pct":loss,"delay_one_way_added_ms":200,
             "jitter_sigma_ms":15,"burst_model":model}
        for direction in ("upload","download"):
            row["direct_"+direction+"_mbps"]=direct.get(
                 f"{prefix}-direct-20s-4p-{direction}")
            row["wbd_"+direction+"_mbps"]=app.get(
                 f"{prefix}-wbd-20s-4p-{direction}")
            a=row["direct_"+direction+"_mbps"];b=row["wbd_"+direction+"_mbps"]
            row["wbd_over_direct_"+direction+"_ratio"]=(
                round(b/a,4) if isinstance(a,(int,float)) and a>0
                and isinstance(b,(int,float)) else None)
        row["wbd_tcp_uplink_3sec_mbps"]=app.get(f"{prefix}-wbd-3s-1p-upload")
        per_loss.append(row)
    if missing or duplicates:
        status="FAIL_INCOMPLETE_THREE_RUNNER_TCP_MATRIX"
    elif failures:
        status="FAIL_REAL_THREE_RUNNER_TCP_OR_WBD_COLD"
    else:
        status="PASS_REAL_THREE_RUNNER_TCP_MATRIX"
    return {
      "schema_version":1,"status":status,
      "source_sha":os.environ.get("GITHUB_SHA",""),
      "run_id":os.environ.get("GITHUB_RUN_ID",""),
      "client_native_arch":"x86_64","relay_native_arch":"aarch64",
      "server_native_arch":"x86_64",
      "real_three_runner_l3_relay":True,
      "all_three_distinct_native_machines":True,
      "actual_kernel_forwarding":True,
      "normal_outer_performative_retransmission":"UNCHANGED_ON",
      "normal_mode":mode,
      "tc_loss_model":model,
      "delay_added_one_way_ms":200,
      "jitter_normal_sigma_ms":15,
      "expected_direct_cases":12,"expected_business_cases":15,
      "observed_qualified_cases":len(rows),
      "missing_case_names":missing,"duplicate_case_names":duplicates,
      "failures":failures,
      "clean_0ms_0pct_direct_8stream_reference_mbps":{
          "upload":clear[0],"download":clear[1]},
      "relay_capacity_qualification":">=800Mbps_BOTH_DIRECTIONS_DIRECT_TAILSCALE" if
       capacity_qualified else "INFRA_RELAY_OR_DERP_UNQUALIFIED_DO_NOT_ATTRIBUTE_TO_WBD",
      "tailscale_path_indicators":sorted(tail_status),
      "observed_rtt":snapshots_rtt,
      "loss_scenarios":per_loss,
      "raw_cases":rows,
      "relay_snapshot_files":len(snapshots),
      "genuine_user_windows_isp_xray_reference":"NOT_RUN",
      "physical_client_uplink_3sec_crash":"NOT_RUN",
      "outer_fake_tcp_kernel_bbr":False
    }

def cleanup(role):
    if role=="relay":
        root("ip","netns","del",ROUTER,allow_fail=True)
        for side in ("client","server"):
            for name in (VHOST[side],VX[side],BR[side]):
                root("ip","link","del",name,allow_fail=True)
    else:
        root("ip","netns","del",NODE,allow_fail=True)
        for name in (VHOST[role],VX[role],BR[role]):
            root("ip","link","del",name,allow_fail=True)

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="act",required=True)
    a=sub.add_parser("meta");a.add_argument("role",choices=ROLES);a.add_argument("out")
    a=sub.add_parser("relay-net");a.add_argument("client");a.add_argument("server");a.add_argument("out")
    a=sub.add_parser("node-net");a.add_argument("role",choices=("client","server"))
    a.add_argument("relay");a.add_argument("out")
    a=sub.add_parser("control-serve");a.add_argument("client");a.add_argument("relay")
    a=sub.add_parser("remote");a.add_argument("relay");a.add_argument("action",
        choices=("health","impair","snapshot"));a.add_argument("out")
    a.add_argument("--loss",type=float,default=0.0)
    a.add_argument("--delay",type=int,default=0)
    a.add_argument("--model",choices=("iid","burst"),default="burst")
    a=sub.add_parser("node-snapshot");a.add_argument("role",choices=("client","server"))
    a.add_argument("tag");a.add_argument("out")
    a=sub.add_parser("relay-snapshot");a.add_argument("tag");a.add_argument("out")
    a=sub.add_parser("iperf");a.add_argument("kind",choices=("direct","wbd"))
    a.add_argument("duration",type=int);a.add_argument("streams",type=int)
    a.add_argument("direction",choices=("upload","download"));a.add_argument("out")
    a=sub.add_parser("result");a.add_argument("mode",choices=("normal","fec-fixed"))
    a.add_argument("model",choices=("iid","burst"));a.add_argument("directory")
    a.add_argument("out")
    a=sub.add_parser("clean");a.add_argument("role",choices=ROLES)
    args=p.parse_args()
    if args.act=="meta":save(args.out,metainfo(args.role))
    elif args.act=="relay-net":
        own=metainfo("relay");save(args.out,install_relay(
           peer_file(args.client,own,"client"),
           peer_file(args.server,own,"server")))
    elif args.act=="node-net":
        own=metainfo(args.role);save(args.out,install_endpoint(
            args.role,peer_file(args.relay,own,"relay")))
    elif args.act=="control-serve":
        own=metainfo("relay")
        client=peer_file(args.client,own,"client")
        relay=json.loads(pathlib.Path(args.relay).read_text())
        guard(relay["role"]=="relay" and
              relay["source_sha"]==own["source_sha"] and
              relay["run_id"]==own["run_id"],"RELAY_TOKEN_NOT_LOCAL_SOURCE")
        Control.client_ip=client["tail_ip"]
        Control.token=relay["control_token"]
        http.server.ThreadingHTTPServer((own["tail_ip"],CONTROL_PORT),Control).serve_forever()
    elif args.act=="remote":
        own=metainfo("client");peer=peer_file(args.relay,own,"relay")
        save(args.out,remote(peer,args.action,args.loss,args.delay,args.model))
    elif args.act=="node-snapshot":
        save(args.out,local_node_snapshot(args.role,args.tag))
    elif args.act=="relay-snapshot":
        save(args.out,local_relay_snapshot(args.tag))
    elif args.act=="iperf":
        row=iperf(args.kind,args.duration,args.streams,args.direction,args.out)
        print("H2228_REAL_IPERF "+json.dumps(row))
        if row["status"]!="PASS_REAL_KERNEL_IPERF3_TCP":sys.exit(2)
    elif args.act=="result":
        record=result_summary(args.mode,args.model,args.directory)
        save(args.out,record)
        print("H2228_REAL_THREE_RUNNER_MATRIX "+record["status"]+
              " capacity="+record["relay_capacity_qualification"])
    elif args.act=="clean":cleanup(args.role)
if __name__=="__main__":
    try:main()
    except (RuntimeError,KeyError,ValueError,subprocess.TimeoutExpired,
            FileNotFoundError,OSError,TimeoutError) as e:
        print("H2228_RELAY_FIXTURE_FAIL "+str(e),file=sys.stderr)
        sys.exit(2)
