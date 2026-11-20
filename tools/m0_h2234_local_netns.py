#!/usr/bin/env python3
"""H2234 reproducible local *one-runner* 3-netns / kernel-netem original WBD.

This is NOT three physical machines, WAN/DERP or a cross-VM CPU comparison.
Original compiled Go TLS+Rust data plane, real TUN and AF_PACKET, genuine
Linux TCP BBR/iperf3 and router egress netem. No fake outer transport,
per-packet Go callback, packet capture, or unowned namespace cleanup.
"""
import hashlib
import json
import os
import pathlib
import re
import secrets
import shlex
import signal
import subprocess
import sys
import threading
import time

# Running a script as tools/x.py does not guarantee the repository parent
# is on sys.path. Reuse the existing canonical native/iperf parser explicitly.
REPO=pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:sys.path.insert(0,str(REPO))
from tools import m0_h2228_three_runner_relay as H
from tools.m0_h2233_low_loss_diag import delta_qdisc, socket_mss_readback

IP_C="10.248.81.2"
GW_C="10.248.81.1"
IP_S="10.248.82.2"
GW_S="10.248.82.1"
USER="bench0"
PASS="H2234-ONLY-PASS"
SERVER="wbd-h2234.example.test"

def command(*argv,allow_fail=False,timeout=60):
    p=subprocess.run(argv,text=True,capture_output=True,timeout=timeout)
    if p.returncode and not allow_fail:
        raise RuntimeError("H2234_COMMAND_FAILED "+
            repr(argv[:5])+" "+p.stderr[-380:])
    return p

def root(*args,**kw):
    return command("sudo","-n",*args,**kw)

def ns(name,*args,**kw):
    return root("ip","netns","exec",name,*args,**kw)

def save(path,obj):
    pathlib.Path(path).write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n")

def ready(log,needle,seconds=65):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if log.exists() and needle in log.read_text(errors="replace"):
            return True
        time.sleep(0.2)
    return False

def original_m4_batch_stage_receipt(log):
    """Exactly one genuine per-client Rust M4 Stop; missing isn't zero."""
    matches=re.findall(r"V4_PUBLIC_M4_BATCH_STAGE_STOP role=client[^\n]*",log)
    if len(matches)!=1:
        raise RuntimeError("H2235_CLIENT_M4_STAGE_RECEIPT_MISSING_OR_DUPLICATED")
    result={k:int(v) for k,v in re.findall(r"(\w+)=(\d+)",matches[0])}
    required=("generation","batches","copied","collect_turns","collect_ns",
              "prepare_ns","seal_ns","sendmmsg_ns","settle_ns",
              "driver_route_ns","driver_header_ns","driver_iovec_ns",
              "driver_syscall_ns","driver_classify_ns",
              "max_collect_ns","max_prepare_ns","max_seal_ns",
              "max_sendmmsg_ns","max_settle_ns","original_owner",
              "no_wire_or_queue_change")
    if not all(k in result for k in required):
        raise RuntimeError("H2235_M4_STAGE_INCOMPLETE_OR_TRUNCATED")
    if (result["batches"]<1 or result["copied"]<1 or
        result["original_owner"]!=1 or result["no_wire_or_queue_change"]!=1):
        raise RuntimeError("H2235_M4_STAGE_NOT_REAL_OWNER_BATCH")
    return result

class OwnedLocal:
    def __init__(self,build,out,tmp):
        self.build=build;self.out=out;self.tmp=tmp
        runid=os.environ["GITHUB_RUN_ID"][-7:]
        self.client="h34c"+runid
        self.router="h34r"+runid
        self.server="h34s"+runid
        self.namespaces=[]
        self.procs={};self.opened=[]
        self.client_pidfile=self.tmp/"client.pid"
        self.server_pidfile=self.tmp/"server.pid"
        self.clientlog=self.out/"client.log"
        self.serverlog=self.out/"server.log"
        self.ipname={"client":IP_C,"router_client":GW_C,
                     "server":IP_S,"router_server":GW_S}

    def spawn(self,role,name,program):
        pidfile=self.tmp/(role+".pid")
        log=self.out/(role+".log")
        handle=log.open("w");self.opened.append(handle)
        shell='echo "$$" > "$1"; shift; exec "$@"'
        p=subprocess.Popen(["sudo","-n","ip","netns","exec",name,
            "bash","-c",shell,"bash",str(pidfile),*program],
            stdout=handle,stderr=subprocess.STDOUT)
        self.procs[role]=p
        return log

    def start_network(self):
        for name in (self.client,self.router,self.server):
            root("ip","netns","add",name)
            self.namespaces.append(name)
            root("ip","-n",name,"link","set","lo","up")
        for a,remote_name,b,nleft,nright in (
            ("c","rcli0","c34x","client","router"),
            ("s","rsrv0","s34x","server","router")):
            left="h34"+a+"w";right="h34"+a+"r"
            root("ip","link","add",left,"type","veth","peer","name",right)
            root("ip","link","set",left,"netns",getattr(self,nleft))
            root("ip","link","set",right,"netns",getattr(self,nright))
            root("ip","-n",getattr(self,nleft),"link","set",left,"name","wan0")
            root("ip","-n",getattr(self,nright),"link","set",right,"name",remote_name)
        for name,nic,addr in (
            (self.client,"wan0",IP_C+"/24"),
            (self.router,"rcli0",GW_C+"/24"),
            (self.router,"rsrv0",GW_S+"/24"),
            (self.server,"wan0",IP_S+"/24")):
            root("ip","-n",name,"addr","add",addr,"dev",nic)
            root("ip","-n",name,"link","set","dev",nic,"mtu","1200")
            root("ip","-n",name,"link","set",nic,"up")
        root("ip","-n",self.client,"route","replace","10.248.82.0/24",
             "via",GW_C,"dev","wan0")
        root("ip","-n",self.server,"route","replace","10.248.81.0/24",
             "via",GW_S,"dev","wan0")
        ns(self.router,"sysctl","-q","-w","net.ipv4.ip_forward=1")
        for name in (self.client,self.server):
            ns(name,"sysctl","-q","-w","net.ipv4.tcp_congestion_control=bbr")
            for key,val in (
                ("net.ipv4.tcp_rmem","4096 87380 67108864"),
                ("net.ipv4.tcp_wmem","4096 65536 67108864"),
                ("net.core.rmem_max","67108864"),
                ("net.core.wmem_max","67108864"),
                ("net.ipv4.tcp_window_scaling","1")):
                ns(name,"sysctl","-q","-w",key+"="+val)
            if ns(name,"sysctl","-n","net.ipv4.tcp_congestion_control").stdout.strip()!="bbr":
                raise RuntimeError("H2234_KERNEL_BBR_NOT_APPLIED")
        ns(self.client,"iptables","-w","-A","OUTPUT","-o","wan0","-p","tcp",
           "--dport","443","--tcp-flags","RST","RST","-j","DROP")
        ns(self.server,"iptables","-w","-A","OUTPUT","-o","wan0","-p","tcp",
           "--sport","443","--tcp-flags","RST","RST","-j","DROP")
        if ns(self.router,"sysctl","-n","net.ipv4.ip_forward").stdout.strip()!="1":
            raise RuntimeError("H2234_ROUTER_FORWARD_DISABLED")
        save(self.out/"topology.json",{
            "source_sha":os.environ["GITHUB_SHA"],
            "run_id":os.environ["GITHUB_RUN_ID"],
            "type":"SAME_VM_THREE_DISTINCT_NETNS_L3_ROUTER_NO_NAT",
            "not_three_runners_or_physical_wan":True,
            "link_mtu":1200,
            "client_ip":IP_C,"router_client":GW_C,
            "server_ip":IP_S,"router_server":GW_S})

    def impairment(self,loss):
        if loss not in (0,1,5):
            raise RuntimeError("H2234_INVALID_NETEM_TARGET")
        args=["delay","0ms","loss","0%"] if loss==0 else (
            ["delay","200ms","loss","gemodel",
             str(H.ge_params(float(loss))["transition_good_bad_pct"])+"%",
             "25%","90%","0.1%"])
        for iface in ("rcli0","rsrv0"):
            ns(self.router,"tc","qdisc","replace","dev",iface,"root","netem",
               *args,"limit","65536")
        save(self.out/("netem-"+str(loss)+".json"),{
            "loss_target_pct":loss,
            "router_only_real_kernel_egress":True,
            "two_routes_no_nat":True,"oneway_extra_ms":200 if loss else 0,
            "jitter_extra_ms":0,"gilbert":H.ge_params(float(loss)) if loss else None,
            "readback":self.router_snapshot()})

    def router_snapshot(self):
        return {side:{
            "qdisc":json.loads(ns(self.router,"tc","-s","-j","qdisc",
                                  "show","dev",dev).stdout),
            "link":json.loads(ns(self.router,"ip","-s","-j","link",
                                 "show","dev",dev).stdout),
            "offload_features":ns(self.router,"ethtool","-k",dev,
                                  allow_fail=True).stdout[-5000:]}
            for side,dev in (("client","rcli0"),("server","rsrv0"))}

    def start_server(self):
        secret=hashlib.sha256(
            ("H2234/"+os.environ["GITHUB_RUN_ID"]+"/"+os.environ["GITHUB_SHA"]).encode()).hexdigest()
        route=self.tmp/"route-key.hex";route.write_text(secret+"\n")
        route.chmod(0o600)
        cert=self.tmp/"cert.pem";key=self.tmp/"key.pem"
        with (self.out/"openssl.log").open("w") as log:
            subprocess.run(["openssl","req","-x509","-newkey","rsa:2048",
                "-sha256","-days","1","-nodes",
                "-keyout",str(key),"-out",str(cert),
                "-subj","/CN="+SERVER,
                "-addext","subjectAltName=DNS:"+SERVER],
                check=True,stdout=log,stderr=subprocess.STDOUT)
        key.chmod(0o600)
        users=self.tmp/"users.json"
        save(users,{USER:PASS});users.chmod(0o600)
        self.spawn("server",self.server,[
            "env","LD_LIBRARY_PATH="+str(self.build),
            "WBD_H2235_M4_STAGE_DIAG=1",
            str(self.build/"wbd-v4-server"),
            "--raw-interface","wan0","--local-ip",IP_S,"--local-port","443",
            "--tun-name","wbds0","--tun-ipv4","10.66.0.1/24",
            "--server-name",SERVER,
            "--route-key-hex-file",str(route),
            "--users-file",str(users),"--lease-pool","10.66.0.128/25",
            "--tls-cert",str(cert),"--tls-key",str(key),
            "--outer-mtu","1160","--mode","shared"])
        if not ready(self.serverlog,"V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443",70):
            raise RuntimeError("H2234_REAL_SERVER_COLD_NOT_READY")
        for role,addr,port in (("iperf-direct",IP_S,"5202"),
                               ("iperf-wbd","10.66.0.1","5201")):
            self.spawn(role,self.server,["iperf3","-s","-B",addr,"-p",port])
        until=time.monotonic()+12
        while time.monotonic()<until:
            txt=ns(self.server,"ss","-ltn").stdout
            if ":5201 " in txt and ":5202 " in txt:break
            time.sleep(.2)
        else:raise RuntimeError("H2234_REAL_IPERF_LISTENERS_MISSING")

    def start_client(self,loss):
        self.client_pidfile.unlink(missing_ok=True)
        port=44100+loss
        self.clientlog=self.spawn("client",self.client,[
            "env","LD_LIBRARY_PATH="+str(self.build),
            "WBD_M0_RAW_TX_SOCKET_DIAG=1",
            "WBD_H2235_M4_STAGE_DIAG=1",
            # H2240 original owner: enabled only in the isolated trace-runner.
            # Existing external observer samples TX copied/CPU each 500ms;
            # the unique Shared TUN reader emits its own 200ms local full.
            *(['WBD_H2240_TUN_TIMELINE=1',
               'WBD_PLAN028_EXTERNAL_STAGE_DIAG=1']
              if os.environ.get("WBD_H2240_NATIVE_TEST")=="1" else []),
            str(self.build/"wbd-v4-client"),
            "--raw-interface","wan0","--local-ip",IP_C,
            "--local-port",str(port),"--peer-ip",IP_S,"--peer-port","443",
            "--tun-name","wbdc0","--server-name",SERVER,
            "--route-key-hex-file",str(self.tmp/"route-key.hex"),
            "--username",USER,"--password",PASS,"--auto-ip",
            "--installation-id-file",str(self.tmp/("install-"+str(loss))),
            "--mode","normal","--fec-profile","6","--outer-repair","on",
            "--outer-mtu","1160","--tun-fq-maxrate-mbps","600"])
        if not ready(self.clientlog,"V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client",85):
            raise RuntimeError("H2234_REAL_CLIENT_TLS_RUST_NOT_READY")
        txt=self.clientlog.read_text(errors="replace")
        if not re.search(r"V4_PUBLIC_LEASE_APPLIED role=client.*os_readback=10\.66\.0\.\d+/32",txt):
            raise RuntimeError("H2234_REAL_LEASE_OS_READBACK_MISSING")
        if ns(self.client,"ip","link","show","wbdc0",allow_fail=True).returncode:
            raise RuntimeError("H2234_NATIVE_TUN_NOT_CREATED")
        root("ip","-n",self.client,"route","replace",
             "10.66.0.1/32","dev","wbdc0")

    def owned_pid(self,role):
        pidfile=self.tmp/(role+".pid")
        try:pid=int(pidfile.read_text().strip())
        except (ValueError,OSError):return None
        if pid<=1 or pid>=4194304:return None
        expected=("wbd-v4-client" if role=="client" else
                  "wbd-v4-server" if role=="server" else "iperf3")
        actual=root("ps","-o","comm=","-p",str(pid),
                    allow_fail=True).stdout.strip()
        return pid if actual==expected else None

    def stop_client(self,loss):
        pid=self.owned_pid("client")
        if pid is None:raise RuntimeError("H2234_UNOWNED_OR_DEAD_CLIENT_PID")
        root("kill","-TERM",str(pid),allow_fail=True)
        if not ready(self.clientlog,"V4_PUBLIC_SHARED_TUN_STOP generation=",30):
            raise RuntimeError("H2234_CLIENT_SHARED_TUN_OWNED_STOP_UNPROVEN_"+str(loss))
        text=self.clientlog.read_text(errors="replace")
        (self.out/("loss"+str(loss)+"-client.log")).write_text(text[-350000:])
        markers=re.findall(r"V4_PUBLIC_SHARED_TUN_STOP generation=\d+ routed=(\d+) unrouted=(\d+) backpressure=(\d+) reader_joined=1 queue_full_drops=(\d+) retired_drops=(\d+) queue_byte_drops=(\d+) queue_age_drops=(\d+)",text)
        if not markers:raise RuntimeError("H2234_NO_ORIGINAL_RUST_QUEUE_READBACK")
        if "V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=client" not in text:
            raise RuntimeError("H2234_CLIENT_OWNER_STOP_NOT_DRAINED")
        stage_values=original_m4_batch_stage_receipt(text)
        routed,unrouted,backpressure,full,retired,byte,age=map(int,markers[-1])
        return {"status":"REAL_RUST_OWNED_STOP","routed":routed,"unrouted":unrouted,
                "backpressure":backpressure,"queue_full_drops":full,
                "retired":retired,"queue_byte_drops":byte,"queue_age_drops":age,
                "scope":"ONE_GENERATION_PER_LOSS_UP_AND_DOWN_20S",
                "m4_original_tx_batch_stages":stage_values}

    def iperf_case(self,index,loss,kind,direction,duration,streams):
        label=("clear-zero" if loss==0 else "delay200-loss"+str(loss)+"-burst")
        filename="case-%03d-%s-%s-%ds-%dp-%s.json"%(index,label,kind,duration,streams,direction)
        path=self.out/filename
        before=self.router_snapshot()
        save(self.out/("before-"+path.stem+"-router.json"),before)
        def sample_ss():
            time.sleep(4)
            try:
                txt=ns(self.client,"ss","-tinm","state","established",
                       allow_fail=True).stdout
                pathlib.Path(str(path)+".tcp-info.txt").write_text(txt)
            except Exception as error:
                pathlib.Path(str(path)+".tcp-info-error.txt").write_text(
                    type(error).__name__)
        monitor=threading.Thread(target=sample_ss,daemon=True)
        if duration==20:monitor.start()
        # Same original H2228 native socket runner + H2234 opt-in external
        # PID/TID sample; using its canonical iperf receiver-goodput parser.
        H.NODE=self.client
        result=H.iperf(kind,duration,streams,direction,path,
            str(self.client_pidfile) if kind=="wbd" else None)
        if duration==20:monitor.join(timeout=3)
        after=self.router_snapshot()
        save(self.out/("after-"+path.stem+"-router.json"),after)
        observed_mss=socket_mss_readback(path,kind) if duration==20 else {
            "status":"NOT_RUN_CLEAN_REFERENCE","mss":[]}
        # True case-level kernel skb receipt, not inferred segment loss.
        router=delta_qdisc(before,after)
        cpu=result.get("stage_sampler",{}).get("threads",{}).get("wbd-m4-tx",{})
        delivered=result.get("receiver_bytes")
        cpu_per_gib=(round(cpu["run_ns"]/1e9/(delivered/1073741824),4)
            if kind=="wbd" and direction=="upload" and
               cpu.get("intervals",0)>=5 and cpu.get("run_ns",0)>0 and
               isinstance(delivered,(int,float)) and delivered>0 else None)
        return {"case":path.name,**result,
            "kernel_tcp_mss_source_qualified":observed_mss,
            "router_case_qdisc":router,
            "local_original_tx_thread_cpu_seconds_per_receiver_gib":cpu_per_gib}

    def stop_server(self):
        pid=self.owned_pid("server")
        if pid is None:raise RuntimeError("H2234_UNOWNED_OR_DEAD_SERVER_PID")
        root("kill","-TERM",str(pid),allow_fail=True)
        if not ready(self.serverlog,"V4_PUBLIC_SHARED_TUN_STOP generation=",30):
            raise RuntimeError("H2234_SERVER_ORIGINAL_RUST_OWNED_STOP_UNPROVEN")
        log=self.serverlog.read_text(errors="replace")
        # Original server emits the joined Rust reader and owned OS cleanup
        # receipts, not the client-only role=server marker.
        if not re.search(r"V4_PUBLIC_SHARED_TUN_STOP generation=\d+ .*reader_joined=1 ",log):
            raise RuntimeError("H2234_SERVER_SHARED_TUN_READER_NOT_JOINED")
        if "V4_PUBLIC_SERVER_MASQUERADE_STOP_DRAINED owned_rule_deleted=1" not in log:
            raise RuntimeError("H2234_SERVER_OS_RESOURCE_STOP_NOT_DRAINED")
        if "V4_PUBLIC_MIXED_NORMAL_STOP_DRAINED reason=server-close remaining_flows=0" not in log:
            raise RuntimeError("H2234_SERVER_GENERATIONS_NOT_ALL_RETIRED")
        return True

    def cleanup(self):
        for role in reversed(list(self.procs)):
            pid=self.owned_pid(role)
            if pid is not None:
                root("kill","-TERM",str(pid),allow_fail=True)
            p=self.procs[role]
            if p.poll() is None:
                try:p.wait(timeout=2)
                except subprocess.TimeoutExpired:p.kill()
        for name in reversed(self.namespaces):
            root("ip","netns","del",name,allow_fail=True)
        for handle in self.opened:
            handle.close()

def main():
    workspace=pathlib.Path(os.environ["GITHUB_WORKSPACE"])
    runid=os.environ["GITHUB_RUN_ID"]
    source=os.environ["GITHUB_SHA"]
    if not re.fullmatch("[a-f0-9]{40}",source):
        raise RuntimeError("H2234_MISSING_EXACT_GIT_SOURCE")
    build=workspace/"linux-plan029-public-bundle"
    for name in ("wbd-v4-client","wbd-v4-server","libwbd_engine.so"):
        if not (build/name).is_file():raise RuntimeError("H2234_MISSING_REAL_BUILD_"+name)
    if not pathlib.Path("/dev/net/tun").is_char_device():
        raise RuntimeError("H2234_REAL_TUN_NOT_AVAILABLE")
    out=workspace/"h2234-local-result"
    out.mkdir(parents=True,exist_ok=True)
    tmp=pathlib.Path(os.environ["RUNNER_TEMP"])/("h2234-"+runid)
    tmp.mkdir(mode=0o700,parents=True,exist_ok=False)
    os.environ["WBD_H2233_FOCUS"]="1"
    os.environ["WBD_H2234_TRACE"]="1"
    os.environ["WBD_H2233_MSS"]="1037"
    node=OwnedLocal(build,out,tmp)
    cases=[];readbacks={}
    server_stop_verified=False
    status="NOT_RUN"
    try:
        node.start_network()
        node.start_server()
        node.impairment(0)
        cases.append(node.iperf_case(0,0,"direct","upload",12,8))
        cases.append(node.iperf_case(1,0,"direct","download",12,8))
        clear={direction:next(x.get("receiver_goodput_mbps") for x in cases
               if x["direction"]==direction) for direction in ("upload","download")}
        if not all(isinstance(x,(float,int)) and x>=500 for x in clear.values()):
            status="NOT_RUN_LOW_LOSS_SAME_VM_INSUFFICIENT_CAPACITY"
        else:
            i=2
            # Baseline the same real WBD owner before assigning any loss
            # amplification; cold generation and Stop remain independent.
            node.start_client(0)
            for direction in ("upload","download"):
                cases.append(node.iperf_case(i,0,"wbd",direction,20,4));i+=1
            readbacks["0"]=node.stop_client(0)
            for loss in (1,5):
                node.impairment(loss)
                for direction in ("upload","download"):
                    cases.append(node.iperf_case(i,loss,"direct",direction,20,4));i+=1
                node.start_client(loss)
                for direction in ("upload","download"):
                    cases.append(node.iperf_case(i,loss,"wbd",direction,20,4));i+=1
                readbacks[str(loss)]=node.stop_client(loss)
            status="PASS_REAL_LOCAL_NETNS_TCP_CASES" if all(
                x["status"]=="PASS_REAL_KERNEL_IPERF3_TCP" for x in cases
            ) else "FAIL_REAL_LOCAL_NETNS_TCP_CASES"
    finally:
        if node.serverlog.exists() and node.owned_pid("server") is not None:
            try:server_stop_verified=node.stop_server()
            except (RuntimeError,OSError):server_stop_verified=False
        node.cleanup()
        if status=="PASS_REAL_LOCAL_NETNS_TCP_CASES" and not server_stop_verified:
            status="FAIL_SERVER_OWNED_STOP_NOT_VERIFIED"
        result={
            "schema_version":1,"checkpoint":"H2234_LOCAL_SINGLE_RUNNER",
            "source_sha":source,"run_id":runid,"status":status,
            "network_scope":"SAME_VM_CLIENT_ROUTER_SERVER_THREE_REAL_LINUX_NETNS",
            "real_original_go_tls_rust_tun_afpacket":True,
            "real_independent_three_runner_wan":False,
            "not_a_physical_windows_result":True,
            "not_a_cross_vm_cpu_gain":True,
            "product_causal_speed_qualified":False,
            "per_mode_scope":"NORMAL_FEC_OFF_ONLY",
            "target_architecture":os.uname().machine,
            "original_outer_repair_and_no_hol_unchanged":True,
            "mode":"normal_fec_off","router_netem":"real_kernel_l3_no_nat_ge_1_5pct_fixed200ms",
            "num_real_tcp_cases":len(cases),
            "all_expected_cases_completed":len(cases)==12,
            "server_owned_stop_verified":server_stop_verified,
            "cases":cases,"rust_shared_tun_per_loss_stop":readbacks}
        save(out/"summary.json",result)
    if status!="PASS_REAL_LOCAL_NETNS_TCP_CASES":
        raise RuntimeError("H2234_SAME_VM_DIAGNOSTIC_"+status)
    print("H2234_REAL_ORIGINAL_GO_TLS_RUST_LOCAL_NETNS_DIAGNOSTIC_PASS_NOT_WAN",flush=True)

if __name__=="__main__":main()
