#!/usr/bin/env python3
"""PLAN029 x86_64 Native Normal/off A(64) -> B(256) -> A'(64) same-SOURCE.

Three real Linux namespaces/underlay L3 router, original Go TLS and Rust
AF_PACKET/TUN, real four-stream kernel TCP and concurrent UDP/TCP echo.
Every leg creates new exact original OS/crypto owners and verifies owned Stop.
Only the server-side developer-only Rust M1 inbox slots change; same built
binaries, source, traffic, qdisc, runner. Not physical WAN or perf PASS by itself.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import signal
import subprocess
import time

ROOT=Path(os.environ["GITHUB_WORKSPACE"])
SHA=os.environ["GITHUB_SHA"]
RUN=os.environ["GITHUB_RUN_ID"]
ATTEMPT=os.environ["GITHUB_RUN_ATTEMPT"]
ARCH=os.environ["WBD_PLAN029_LINUX_EXPECTED_ARCH"]
BUNDLE=ROOT/"linux-plan029-public-bundle"
OUT=ROOT/"m029-inbox-ge1-abca"
TMP=Path(os.environ["RUNNER_TEMP"])/("m029-inbox-"+RUN+"-"+ATTEMPT)
CLIENT_IP="10.248.81.2"
SERVER_IP="10.248.82.2"
CLIENT_TUN="wbdc0"
SERVER_TUN="wbds0"
SERVER_INNER="10.66.0.1"
COUNT=160
# Same H2228 stationary GE formula: good loss 0.1%, bad loss 90%,
# bad->good probability 25%, and target 1% average packet/skb loss.
_GE_BAD=(0.01-0.001)/(0.90-0.001)
GE_GOOD_BAD_PCT=round(100*(0.25*_GE_BAD)/(1-_GE_BAD),6)
assert abs(GE_GOOD_BAD_PCT-0.252809)<0.0000005
PHASES=(("original_before",64),("inbox256_candidate",256),("original_after",64))
CLK=os.sysconf(os.sysconf_names["SC_CLK_TCK"])

def command(*args,timeout=50,allow_fail=False):
    res=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if res.returncode and not allow_fail:
        raise RuntimeError("COMMAND_"+str(args[:6])+"_STATUS_"+str(res.returncode)+" "+res.stderr[-300:])
    return res

def root(*args,**kw):
    return command("sudo","-n",*args,**kw)

def ns(name,*args,**kw):
    return root("ip","netns","exec",name,*args,**kw)

def save(name,data):
    (OUT/name).write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")

def ready(path,marker,timeout=85):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if path.is_file() and marker in path.read_text(errors="replace"):
            return True
        time.sleep(.2)
    return False

def cpu_seconds(pid):
    # /proc/PID/stat task+threads CPU, fields 14 and 15 (utime+stime).
    raw=Path(f"/proc/{pid}/stat").read_text()
    fields=raw.rsplit(")",1)[1].split()
    return (int(fields[11])+int(fields[12]))/CLK

def cpu_and_mem(pid):
    c=cpu_seconds(pid)
    status=Path(f"/proc/{pid}/status").read_text()
    rss=re.search(r"^VmRSS:\s+(\d+) kB$",status,re.M)
    return {"cpu_s":c,"rss_kib":int(rss.group(1)) if rss else None}

def qdisc_delta(old,new):
    a=next((x for x in old if x.get("kind")=="netem"),None)
    b=next((x for x in new if x.get("kind")=="netem"),None)
    if a is None or b is None or a.get("handle")!=b.get("handle"):
        return {"status":"UNKNOWN_NETEM_QDISC_CHANGED"}
    return {"netem_skb_emitted_delta":max(0,int(b.get("packets",0))-int(a.get("packets",0))),
            "netem_skb_drop_delta":max(0,int(b.get("drops",0))-int(a.get("drops",0))),
            "unit":"kernel skb, not necessarily one IP packet"}

def iperf_json(namespace,dest,source,port,seconds,streams):
    argv=["sudo","-n","ip","netns","exec",namespace,"iperf3","-c",dest,
          "-B",source,"-p",str(port),"-P",str(streams),"-t",str(seconds),"-J"]
    a=time.monotonic_ns()
    proc=subprocess.run(argv,text=True,capture_output=True,timeout=seconds+38)
    b=time.monotonic_ns()
    if proc.returncode:
        raise RuntimeError(f"IPERF_REAL_TCP_STATUS_{proc.returncode} "+
                           proc.stderr[-250:])
    value=json.loads(proc.stdout)
    if value.get("error"):
        raise RuntimeError("IPERF_REAL_TCP_"+str(value["error"]))
    end=value["end"]
    rec=end.get("sum_received")
    sent=end.get("sum_sent")
    if not rec or not sent or rec["bytes"]<=0:
        raise RuntimeError("IPERF_NO_GENUINE_RECEIVER_DELIVERY")
    return {"start_monotonic_ns":a,"end_monotonic_ns":b,
            "receiver_bytes":rec["bytes"],"receiver_bps":rec["bits_per_second"],
            "sender_bytes":sent["bytes"],"tcp_streams":streams,
            "tcp_retransmissions":sent.get("retransmits"),
            "real_kernel_tcp":True}

class Owned:
    def __init__(self,index,slots):
        self.index=index
        self.slots=slots
        tag=RUN[-6:]+str(index)
        self.client="m29c"+tag
        self.server="m29s"+tag
        self.router="m29r"+tag
        self.ns_created=[]
        self.processes={}
        self.logs={}
        self.handles=[]
        self.secret_dir=TMP/f"leg-{index}"
        self.secret_dir.mkdir(mode=0o700)
        self.names=(self.client,self.server,self.router)

    def spawn(self,role,place,argv):
        log=self.secret_dir/(role+".log")
        pidfile=self.secret_dir/(role+".pid")
        output=log.open("w")
        self.handles.append(output)
        proc=subprocess.Popen(["sudo","-n","ip","netns","exec",place,
            "bash","-c",'echo "$$" > "$1"; shift; exec "$@"',"bash",str(pidfile),*argv],
            stdout=output,stderr=subprocess.STDOUT)
        self.processes[role]=(proc,pidfile)
        self.logs[role]=log
        return log

    def pid(self,role):
        proc,pidfile=self.processes[role]
        if not pidfile.is_file():
            raise RuntimeError("OWNED_PID_MISSING_"+role)
        value=int(pidfile.read_text())
        name=root("ps","-o","comm=","-p",str(value),allow_fail=True).stdout.strip()
        expect={"server":"wbd-v4-server","client":"wbd-v4-client",
                "bulk-server":"iperf3","direct-server":"iperf3",
                "echo-server":"python3"}.get(role)
        if value<2 or name!=expect:
            raise RuntimeError(f"OWNED_PID_IDENTITY_{role}_{name}")
        return value

    def stop(self,role,required_marker=None):
        proc,pidfile=self.processes[role]
        pid=self.pid(role)
        root("kill","-TERM",str(pid),allow_fail=True)
        if required_marker and not ready(self.logs[role],required_marker,30):
            raise RuntimeError("OWNED_STOP_RECEIPT_MISSING_"+role)
        try:proc.wait(timeout=12)
        except subprocess.TimeoutExpired:
            raise RuntimeError("OWNED_STOP_JOIN_TIMEOUT_"+role)
        if role in ("client","server"):
            contents=self.logs[role].read_text(errors="replace")
            receipt=re.search(
                r"V4_PUBLIC_SHARED_TUN_STOP generation=(\d+) routed=(\d+) unrouted=(\d+) backpressure=(\d+) reader_joined=1 queue_full_drops=(\d+) retired_drops=(\d+) queue_byte_drops=(\d+) queue_age_drops=(\d+)",
                contents)
            if not receipt:raise RuntimeError("OWNED_RUST_STOP_COUNTERS_MISSING_"+role)
            fields=("generation","routed","unrouted","backpressure","queue_full_drops",
                    "retired_drops","queue_byte_drops","queue_age_drops")
            return dict(zip(fields,map(int,receipt.groups())))
        return {"owner":"terminated","pid_identity_checked":True}

    def network(self):
        for name in self.names:
            root("ip","netns","add",name)
            self.ns_created.append(name)
            root("ip","-n",name,"link","set","lo","up")
        for side,endpoint,route_iface,endpoint_ip,router_ip in (
            ("c",self.client,"rcli0",CLIENT_IP,"10.248.81.1"),
            ("s",self.server,"rsrv0",SERVER_IP,"10.248.82.1")):
            left="m29"+side+"w"+str(self.index)
            right="m29"+side+"r"+str(self.index)
            root("ip","link","add",left,"type","veth","peer","name",right)
            root("ip","link","set",left,"netns",endpoint)
            root("ip","link","set",right,"netns",self.router)
            root("ip","-n",endpoint,"link","set",left,"name","wan0")
            root("ip","-n",self.router,"link","set",right,"name",route_iface)
            for n,dev,addr in ((endpoint,"wan0",endpoint_ip+"/24"),
                               (self.router,route_iface,router_ip+"/24")):
                root("ip","-n",n,"addr","add",addr,"dev",dev)
                root("ip","-n",n,"link","set","dev",dev,"mtu","1200")
                root("ip","-n",n,"link","set",dev,"up")
        root("ip","-n",self.client,"route","replace","10.248.82.0/24",
             "via","10.248.81.1","dev","wan0")
        root("ip","-n",self.server,"route","replace","10.248.81.0/24",
             "via","10.248.82.1","dev","wan0")
        ns(self.router,"sysctl","-q","-w","net.ipv4.ip_forward=1")
        for n in (self.client,self.server):
            ns(n,"sysctl","-q","-w","net.ipv4.tcp_congestion_control=bbr")
        ns(self.client,"iptables","-w","-A","OUTPUT","-o","wan0",
           "-p","tcp","--dport","443","--tcp-flags","RST","RST","-j","DROP")
        ns(self.server,"iptables","-w","-A","OUTPUT","-o","wan0",
           "-p","tcp","--sport","443","--tcp-flags","RST","RST","-j","DROP")

    def start_product(self):
        route=self.secret_dir/"route.hex"
        route.write_text(hashlib.sha256((RUN+"/"+SHA+"/"+str(self.index)).encode()).hexdigest()+"\n")
        route.chmod(0o600)
        cert=self.secret_dir/"cert.pem"
        key=self.secret_dir/"key.pem"
        with (self.secret_dir/"cert-generation.log").open("w") as o:
            subprocess.run(["openssl","req","-x509","-newkey","rsa:2048",
              "-sha256","-days","1","-nodes","-keyout",str(key),"-out",str(cert),
              "-subj","/CN=wbd-m029.example.test",
              "-addext","subjectAltName=DNS:wbd-m029.example.test"],
              stdout=o,stderr=subprocess.STDOUT,check=True)
        key.chmod(0o600)
        users=self.secret_dir/"users.json"
        users.write_text(json.dumps({"bench0":"m029-scope-pass"})+"\n")
        users.chmod(0o600)
        server_env=["LD_LIBRARY_PATH="+str(BUNDLE),
                    "WBD_M0_029_INBOX_SLOTS_TEST="+str(self.slots)]
        # The multi-lease fair scheduler is OFF for this single-lease test.
        self.spawn("server",self.server,["env",*server_env,
            str(BUNDLE/"wbd-v4-server"),"--raw-interface","wan0",
            "--local-ip",SERVER_IP,"--local-port","443",
            "--tun-name",SERVER_TUN,"--tun-ipv4",SERVER_INNER+"/24",
            "--server-name","wbd-m029.example.test",
            "--route-key-hex-file",str(route),"--users-file",str(users),
            "--lease-pool","10.66.0.128/25","--tls-cert",str(cert),
            "--tls-key",str(key),"--outer-mtu","1160","--mode","shared"])
        if not ready(self.logs["server"],"V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443",70):
            raise RuntimeError("ORIGINAL_SERVER_NOT_READY")
        self.spawn("bulk-server",self.server,
                   ["iperf3","-s","-B",SERVER_INNER,"-p","5201"])
        self.spawn("direct-server",self.server,
                   ["iperf3","-s","-B",SERVER_IP,"-p","5202"])
        self.spawn("echo-server",self.server,["env","GITHUB_SHA="+SHA,"GITHUB_RUN_ID="+RUN,
                   "python3","-u",str(ROOT/"tools/m0_h2244_smallflow_echo.py"),
                   "server","--bind",SERVER_INNER])
        if not ready(self.logs["echo-server"],"H2244_ECHO_SERVER_READY",15):
            raise RuntimeError("NATIVE_ECHO_NOT_READY")
        self.spawn("client",self.client,["env","LD_LIBRARY_PATH="+str(BUNDLE),
            str(BUNDLE/"wbd-v4-client"),"--raw-interface","wan0",
            "--local-ip",CLIENT_IP,"--local-port","44100",
            "--peer-ip",SERVER_IP,"--peer-port","443","--tun-name",CLIENT_TUN,
            "--server-name","wbd-m029.example.test",
            "--route-key-hex-file",str(route),"--tls-ca-pem",str(cert),
            "--username","bench0","--password","m029-scope-pass","--auto-ip",
            "--installation-id-file",str(self.secret_dir/"install"),
            "--mode","normal","--fec-profile","6",
            "--outer-repair","on","--outer-mtu","1160"])
        if not ready(self.logs["client"],"V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client",85):
            raise RuntimeError("ORIGINAL_CLIENT_NOT_READY")
        contents=self.logs["client"].read_text(errors="replace")
        match=re.findall(r"V4_PUBLIC_LEASE_APPLIED role=client.*os_readback=(10\.66\.0\.\d+)/32",contents)
        if not match:raise RuntimeError("AUTHENTICATED_LEASE_OS_READBACK_MISSING")
        self.lease=match[-1]
        if not ready(self.logs["server"],"M0_PLAN029_NATIVE_INBOX_BOUND role=server",20):
            raise RuntimeError("COLD_NATIVE_INBOX_RECEIPT_MISSING")
        report=self.logs["server"].read_text(errors="replace")
        slots_seen=re.findall(
            r"M0_PLAN029_NATIVE_INBOX_BOUND role=server generation=\d+ slots=(\d+) probe_only=1",
            report)
        if len(slots_seen)!=1 or int(slots_seen[0])!=self.slots:
            raise RuntimeError("COLD_NATIVE_INBOX_NOT_APPLIED_EXACTLY")
        root("ip","-n",self.client,"route","replace",SERVER_INNER+"/32",
             "dev",CLIENT_TUN)
        return self.lease

    def impair(self):
        # Identical GE1% and +200ms each direction, applied only AFTER TLS.
        for dev in ("rcli0","rsrv0"):
            ns(self.router,"tc","qdisc","replace","dev",dev,"root","netem",
               "delay","200ms","loss","gemodel",f"{GE_GOOD_BAD_PCT:.6f}%",
               "25%","90%","0.1%","limit","65536")
        return {dev:json.loads(ns(self.router,"tc","-s","-j","qdisc","show",
                                 "dev",dev).stdout) for dev in ("rcli0","rsrv0")}

    def measure(self,label):
        # Direct original kernel TCP reference is outside the WBD accounting
        # window; do not mix its qdisc skb/drop deltas into WBD measurements.
        direct=iperf_json(self.client,SERVER_IP,CLIENT_IP,5202,5,4)
        time.sleep(3)
        before={dev:json.loads(ns(self.router,"tc","-s","-j","qdisc","show",
                "dev",dev).stdout) for dev in ("rcli0","rsrv0")}
        cpu0={who:cpu_and_mem(self.pid(who)) for who in ("server","client")}
        small_out=OUT/(label+"-echo.json")
        self.spawn("small-"+label,self.client,["env","GITHUB_SHA="+SHA,
          "GITHUB_RUN_ID="+RUN,"python3","-u",str(ROOT/"tools/m0_h2244_smallflow_echo.py"),
          "client","--server",SERVER_INNER,"--output",str(small_out),
          "--count",str(COUNT),"--gap-ms","80","--start-delay","2"])
        perf=iperf_json(self.client,SERVER_INNER,self.lease,5201,20,4)
        process=self.processes["small-"+label][0]
        process.wait(timeout=20)
        if process.returncode or not small_out.exists():
            raise RuntimeError("TRUE_SMALL_FLOW_PROBE_FAILED_"+label)
        small=json.loads(small_out.read_text())
        if small["status"]!="PASS_SCOPED_REAL_INNER_UDP_TCP_ECHO" or (
            small["source_sha"]!=SHA or small["run_id"]!=RUN):
            raise RuntimeError("TRUE_SMALL_FLOW_SOURCE_OR_DELIVERY_FAIL_"+label)
        if not (perf["start_monotonic_ns"]<=small["probe_start_monotonic_ns"]
                <small["probe_end_monotonic_ns"]<=perf["end_monotonic_ns"]+500_000_000):
            raise RuntimeError("TRUE_CONCURRENT_SMALL_PROBE_NOT_OVERLAPPED_"+label)
        cpu1={who:cpu_and_mem(self.pid(who)) for who in ("server","client")}
        after={dev:json.loads(ns(self.router,"tc","-s","-j","qdisc","show",
                "dev",dev).stdout) for dev in ("rcli0","rsrv0")}
        gib=perf["receiver_bytes"]/1073741824
        delta={who:{"cpu_seconds":round(cpu1[who]["cpu_s"]-cpu0[who]["cpu_s"],5),
                    "cpu_seconds_per_rx_gib":round((cpu1[who]["cpu_s"]-cpu0[who]["cpu_s"])/gib,5),
                    "rss_start_kib":cpu0[who]["rss_kib"],
                    "rss_end_kib":cpu1[who]["rss_kib"]}
               for who in ("server","client")}
        return {"real_direct_tcp":direct,"original_product_tcp":perf,
                "smallflow":{k:small[k] for k in ("status","udp","tcp","count_requested",
                                                   "probe_start_monotonic_ns","probe_end_monotonic_ns")},
                "cpu_and_rss":delta,
                "router_kernel_skb":{dev:qdisc_delta(before[dev],after[dev])
                                     for dev in ("rcli0","rsrv0")}}

    def cleanup(self):
        # Do not clean up resources we did not create. Every actual PID is
        # checked against expected comm before terminating it.
        for role in reversed(list(self.processes)):
            proc,pidfile=self.processes[role]
            if proc.poll() is None and pidfile.is_file():
                try:
                    pid=int(pidfile.read_text())
                    name=root("ps","-o","comm=","-p",str(pid),allow_fail=True).stdout.strip()
                    allowed=name in ("wbd-v4-client","wbd-v4-server","iperf3","python3")
                    if allowed:root("kill","-TERM",str(pid),allow_fail=True)
                except (ValueError,OSError):
                    pass
            if proc.poll() is None:
                try:proc.wait(timeout=4)
                except subprocess.TimeoutExpired:proc.terminate()
        for name in reversed(self.ns_created):
            root("ip","netns","del",name,allow_fail=True)
        for h in self.handles:h.close()

def main():
    if (platform.machine()!=ARCH or ARCH!="x86_64"
        or os.environ.get("GITHUB_ACTIONS")!="true" or len(SHA)!=40
        or not BUNDLE.joinpath("manifest.json").is_file()):
        raise SystemExit("M029_NATIVE_AARCH64_ACTION_SOURCE_REQUIRED")
    manifest=json.loads((BUNDLE/"manifest.json").read_text())
    if manifest.get("source_sha")!=SHA or manifest.get("architecture")!=ARCH:
        raise SystemExit("M029_BUILD_MANIFEST_SOURCE_ISA_MISMATCH")
    for name,expected in manifest["sha256"].items():
        if hashlib.sha256((BUNDLE/name).read_bytes()).hexdigest()!=expected:
            raise SystemExit("M029_EXACT_BUNDLE_BYTES_MISMATCH_"+name)
    TMP.mkdir(mode=0o700,parents=True,exist_ok=False)
    OUT.mkdir(exist_ok=False)
    state={"schema_version":1,"source_sha":SHA,"run_id":RUN,"attempt":ATTEMPT,
           "architecture":ARCH,"kernel":platform.release(),
           "old_and_new_same_build_manifest":manifest["sha256"],
           "topology":"single native Linux x86_64 VM, three isolated netns, true Go TLS Rust raw/TUN",
           "scenario":"GE1% stationary two L3 router qdiscs; +200ms each direction; 4 TCP + 160 UDP/TCP",
           "netem_ge_stationary_parameters":{"target_loss_pct":1.0,"good_to_bad_pct":GE_GOOD_BAD_PCT,
                                            "bad_to_good_pct":25.0,"bad_loss_pct":90.0,
                                            "good_loss_pct":0.1},
           "driver":"original unmodified AF_PACKET/TUN; no fixed cap and no reader gate",
           "product_mode":"normal/off","only_changed_setting":"server Rust m0_v4_probe inbox 64 vs 256",
           "phases":[],"status":"NOT_RUN","scope_exclusions":[
               "physical WAN","different host/ISA inference","12-lease fairness",
               "cross-host CPU","Windows/Game/FEC qualification"]}
    save("summary.json",state)
    try:
        for idx,(label,slots) in enumerate(PHASES):
            node=Owned(idx,slots)
            try:
                node.network()
                lease=node.start_product()
                impair=node.impair()
                time.sleep(10)
                measurement=node.measure(label)
                stop_client=node.stop("client","V4_PUBLIC_SHARED_TUN_STOP generation=")
                stop_server=node.stop("server","V4_PUBLIC_SHARED_TUN_STOP generation=")
                row={"name":label,"server_inbox_slots":slots,
                     "authenticated_lease":lease,"injected_kernel_netem":impair,
                     "measure":measurement,"owned_stop":{"server":stop_server,"client":stop_client},
                     "status":"PASS_SCOPED_REAL_SOURCE_MEASURED_NOT_PRODUCT_GAIN"}
                state["phases"].append(row)
                save("summary.json",state)
            finally:
                node.cleanup()
        if [x["server_inbox_slots"] for x in state["phases"]]!=[64,256,64]:
            raise RuntimeError("INBOX_ABA_PHASES_MISMATCH")
        state["status"]="PASS_SCOPED_REAL_ABA_MEASURED_NOT_PRODUCT_GAIN"
        save("summary.json",state)
        print("M029_TRUE_LINUX_X86_INBOX64_256_64_GE1_ABA_MEASURED",flush=True)
    except BaseException as exc:
        state["status"]="FAIL_OR_INCONCLUSIVE_REAL_NATIVE_ABA"
        state["error_class"]=type(exc).__name__
        state["error_summary"]=str(exc)[-350:]
        save("summary.json",state)
        raise

if __name__=="__main__":main()
