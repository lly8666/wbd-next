#!/usr/bin/env python3
"""Read-only H1520 kernel tc measurement: five isolated outer veth pairs, two directions.

Each direction is the complete protected outer IPv4 path. Never count FEC
symbols/record repeats as independent application delivery. No test sends.
"""
import argparse,json,os,pathlib,subprocess,time

NAMES=("alice","bob","carol","dave","erin")
def alive(pid):
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False
def tc(dev,ns=None):
    argv=["sudo","-n"]
    if ns:argv+=["ip","netns","exec",ns]
    argv+=["tc","-s","-j","qdisc","show","dev",dev]
    p=subprocess.run(argv,capture_output=True,text=True,timeout=6)
    if p.returncode:raise RuntimeError("real tc "+dev+" "+p.stderr[-160:])
    candidates=[v for v in json.loads(p.stdout) if v.get("kind")=="netem"]
    if len(candidates)!=1:raise RuntimeError("actual owned netem root absent "+dev)
    z=candidates[0]
    return {"bytes":int(z["bytes"]),"packets":int(z["packets"]),
            "drops":int(z.get("drops",0))}
def snapshot(tag):
    up=[];down=[]
    for i in range(5):
        up.append(tc("p"+str(i)+tag,"n"+str(i)+tag))
        down.append(tc("h"+str(i)+tag))
    return {"up":up,"down":down}
def mbps_delta(new,old,dt):
    if not 0<dt<30:raise ValueError("unbounded real measurement window")
    u=[new["up"][i]["bytes"]-old["up"][i]["bytes"] for i in range(5)]
    d=[new["down"][i]["bytes"]-old["down"][i]["bytes"] for i in range(5)]
    if min(u+d)<0:raise ValueError("qdisc replaced or counters rolled over")
    return {"up_mbps":round(sum(u)*8/dt/1e6,3),
            "down_mbps":round(sum(d)*8/dt/1e6,3),
            "total_outer_mbps":round(sum(u+d)*8/dt/1e6,3),
            "per_client_outer_up_mbps":[round(v*8/dt/1e6,3) for v in u],
            "per_client_outer_down_mbps":[round(v*8/dt/1e6,3) for v in d]}
def phase(t):
    if t<=10:return "warmup"
    if t<=100:return "first_wave"
    if t<=280:return "sustained"
    if t<=370:return "overload"
    return "recovery"
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pid",type=int,required=True)
    ap.add_argument("--art",type=pathlib.Path,required=True)
    ap.add_argument("--scene",choices=("loss0","loss30"),required=True)
    a=ap.parse_args()
    a.art.mkdir(exist_ok=True,parents=True)
    meta={"schema_version":1,"scene":a.scene,"status":"NOT_RUN",
          "producer":"tc -s -j qdisc show: each of ten real veth netem qdiscs",
          "scope":"both directions, five physical client veths, complete outer IP not inner application"}
    try:
        plan_path=a.art/"h1250-matrix-plan.json"
        deadline=time.monotonic()+230
        while not plan_path.exists() or not (a.art/"h1250-qdisc-before.txt").exists():
            if not alive(a.pid):raise RuntimeError("original product quit before tc/app plan")
            if time.monotonic()>deadline:raise RuntimeError("real original netem fixtures not ready")
            time.sleep(.5)
        plan=json.loads(plan_path.read_text())
        assert plan["H1520_outer_600_profile"]=="outer100to150-"+a.scene
        assert plan["application_load_seconds"]==600
        assert [v["oneway_delay_ms"] for v in plan["clients"]]==[200]*5
        assert [v["loss_pct"] for v in plan["clients"]]==([30 if a.scene=="loss30" else 0]*5)
        meta["original_product_source_sha"]=plan["source_sha"]
        meta["real_traffic_start_ns"]=plan["start_monotonic_ns"]
        target_ns=plan["start_monotonic_ns"]
        while time.monotonic_ns()<target_ns:
            if not alive(a.pid):raise RuntimeError("original product exited before first application")
            time.sleep(min(1,(target_ns-time.monotonic_ns())/1e9))
        tag=os.environ["GITHUB_RUN_ID"][-6:]
        old=snapshot(tag);last=time.monotonic()
        rows=0
        with (a.art/"h1520-outer-10s.jsonl").open("w") as out:
            while rows<61 and time.monotonic_ns()-target_ns<600_000_000_000:
                time.sleep(10)
                now=time.monotonic();current=snapshot(tag)
                data=mbps_delta(current,old,now-last)
                elapsed=(time.monotonic_ns()-target_ns)/1e9
                delta_drop={}
                for direction in ("up","down"):
                    delta_drop[direction]=[current[direction][i]["drops"]-
                        old[direction][i]["drops"] for i in range(5)]
                row={"elapsed_s":round(elapsed,2),"phase":phase(elapsed),
                     "scene":a.scene,"sample_seconds":round(now-last,3),
                     **data,"qdisc_drops_delta":delta_drop}
                out.write(json.dumps(row,sort_keys=True)+"\n");out.flush()
                if rows%3==0:print("H1520_REAL_OUTER_10S "+json.dumps(row),flush=True)
                old=current;last=now;rows+=1
                if not alive(a.pid):break
        meta.update(status="MEASURED_REAL_KERNEL",sample_count=rows,
                    measured_duration_s=round(time.monotonic_ns()/1e9-target_ns/1e9,2),
                    last_qdisc_counters=old)
    except BaseException as e:
        meta["status"]="MEASUREMENT_FAILED_OR_NATIVE_EARLY_EXIT"
        meta["first_error"]=repr(e)
        raise
    finally:
        (a.art/"h1520-outer-observer.json").write_text(json.dumps(meta,indent=2)+"\n")
if __name__=="__main__":main()
