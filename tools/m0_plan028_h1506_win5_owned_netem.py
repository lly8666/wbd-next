#!/usr/bin/env python3
"""H1506 owned Linux tc selectors for original 5-Windows fakeTCP 443..446.

Actual Windows->Linux packets are delayed/lost on WSL2 eth0 ingress IFB.
Only Linux->Windows original TLS/RAW TCP source ports 443..446 use a
netem leaf. WSL2/GitHub management TCP/UDP has no netem impairment.
Foreign qdiscs/IFBs are refused. Original eth0 policy is cleaned in
finally by the Windows 5-user supervising process.
"""
import argparse,json,os,pathlib,subprocess,time
IFB="ifbh1506"
OWNER="PLAN028_H1506_REAL_WINDOWS_FIVE_OUTER_TCP443_446"
PORTS=(443,444,445,446)
def cmd(*argv,check=True):
    p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     text=True,timeout=15)
    if check and p.returncode:
        raise RuntimeError("kernel tc "+repr(argv[:8])+" "+p.stderr[-400:])
    return p
def read_json(*x):
    p=cmd(*x)
    return json.loads(p.stdout or "[]")
def probe():
    return {
      "physical_eth0":read_json("tc","-s","-j","qdisc","show","dev","eth0"),
      "owned_ifb":read_json("tc","-s","-j","qdisc","show","dev",IFB),
      "outer_ingress_classifiers":cmd("tc","-s","filter","show","dev","eth0","parent","ffff:").stdout,
      "outer_egress_classifiers":cmd("tc","-s","filter","show","dev","eth0","parent","1:").stdout,
      "time_mono_ns":time.monotonic_ns()
    }
def true_bytes(v,device,kind,handle):
    rows=v["owned_ifb"] if device=="ifb" else v["physical_eth0"]
    matches=[x for x in rows if x.get("kind")==kind and x.get("handle")==handle]
    if len(matches)!=1:raise RuntimeError("original owned netem qdisc missing "+device)
    z=matches[0]
    backlog=z.get("backlog",0)
    if isinstance(backlog,dict):backlog=backlog.get("bytes",0)
    return {"bytes":int(z.get("bytes",0)),"packets":int(z.get("packets",0)),
            "drops":int(z.get("drops",0)),"backlog_bytes":int(backlog)}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("action",choices=("arm","sample","clean"))
    ap.add_argument("--loss",type=int,required=True,choices=(0,30))
    ap.add_argument("--out",type=pathlib.Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    lease=a.out/"h1506-netem-owned.json"
    if a.action=="arm":
        if lease.exists():raise RuntimeError("foreign owned H1506 netem lease")
        if cmd("ip","link","show","dev",IFB,check=False).returncode==0:
            raise RuntimeError("foreign IFB name, refuse overwrite")
        q=read_json("tc","-j","qdisc","show","dev","eth0")
        if any(x.get("kind") not in ("noqueue","pfifo_fast","fq_codel","mq")
                and x.get("parent") in (None,"root") for x in q):
            raise RuntimeError("foreign WSL eth0 root qdisc, refuse replace")
        if "ffff:" in cmd("tc","qdisc","show","dev","eth0").stdout:
            raise RuntimeError("foreign WSL2 eth0 ingress policy")
        state={"owner":OWNER,"source":os.environ.get("GITHUB_SHA"),
               "loss_percent":a.loss,"oneway_ms":200,"ingress":False,
               "root":False,"ifb":False,"ports":list(PORTS),
               "scope":"true_original_TCP443_446_only_non_VPN_management_unaffected"}
        lease.write_text(json.dumps(state,indent=2)+"\n")
        try:
            cmd("ip","link","add",IFB,"type","ifb")
            state["ifb"]=True;lease.write_text(json.dumps(state)+"\n")
            cmd("ip","link","set",IFB,"up")
            cmd("tc","qdisc","add","dev",IFB,"root","handle","10:",
                "netem","delay","200ms","loss",str(a.loss)+"%","limit","32768")
            # Root PRIO defaults unclassified traffic to 1:2; only
            # 1:1 is netem. Do not impair Windows management peers.
            cmd("tc","qdisc","add","dev","eth0","root","handle","1:","prio","bands","3",
                "priomap",*(["1"]*16))
            state["root"]=True;lease.write_text(json.dumps(state)+"\n")
            cmd("tc","qdisc","add","dev","eth0","parent","1:1","handle","20:",
                "netem","delay","200ms","loss",str(a.loss)+"%","limit","32768")
            cmd("tc","qdisc","add","dev","eth0","handle","ffff:","ingress")
            state["ingress"]=True;lease.write_text(json.dumps(state)+"\n")
            for i,port in enumerate(PORTS,1):
                cmd("tc","filter","add","dev","eth0","parent","ffff:","protocol","ip",
                    "prio",str(i),"u32","match","ip","protocol","6","0xff",
                    "match","ip","dport",str(port),"0xffff",
                    "action","mirred","egress","redirect","dev",IFB)
                cmd("tc","filter","add","dev","eth0","parent","1:","protocol","ip",
                    "prio",str(i),"u32","match","ip","protocol","6","0xff",
                    "match","ip","sport",str(port),"0xffff","flowid","1:1")
            measured=probe()
            assert measured["outer_ingress_classifiers"].count("mirred")>=4
            assert measured["outer_egress_classifiers"].count("flowid 1:1")>=4
            true_bytes(measured,"ifb","netem","10:")
            true_bytes(measured,"eth0","netem","20:")
            (a.out/"h1506-netem-before.json").write_text(json.dumps(measured)+"\n")
            print("H1506_REAL_OWNED_200MS_BOTH_DIRECTIONS_"+str(a.loss)+"PCT_KERNEL_TC_READY",flush=True)
        except BaseException:
            clean(lease)
            raise
    elif a.action=="sample":
        state=json.loads(lease.read_text())
        if state.get("owner")!=OWNER or state.get("loss_percent")!=a.loss:
            raise RuntimeError("foreign h1506 loss/owner while sample")
        v=probe()
        print(json.dumps({"source":state.get("source"),"scene_loss":a.loss,
            "actual_egress_linux_to_windows":true_bytes(v,"eth0","netem","20:"),
            "actual_ingress_windows_to_linux":true_bytes(v,"ifb","netem","10:"),
            "observed_monotonic_ns":v["time_mono_ns"]}),flush=True)
    else:clean(lease)
def clean(lease):
    if not lease.exists():return
    d=json.loads(lease.read_text())
    if d.get("owner")!=OWNER:raise RuntimeError("foreign original IFB owner")
    errs=[]
    for required,argv in [
      ("ingress",("tc","qdisc","del","dev","eth0","ingress")),
      ("root",("tc","qdisc","del","dev","eth0","root")),
      ("ifb",("ip","link","del",IFB))]:
        if not d.get(required):continue
        p=cmd(*argv,check=False)
        if p.returncode:errs.append(required+":"+p.stderr[-220:])
        else:
            d[required]=False;lease.write_text(json.dumps(d)+"\n")
    if errs:raise RuntimeError("owned tc cleanup failed "+"; ".join(errs))
    lease.unlink()
    print("H1506_REAL_OWNED_NETEM_200MS_ALL_RESOURCE_REMOVED",flush=True)
if __name__=="__main__":main()
