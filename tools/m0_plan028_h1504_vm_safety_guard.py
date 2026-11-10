#!/usr/bin/env python3
"""Read-only native Linux VM watchdog for one bounded true 1800s fixture.

Only if host CPU remains saturated or MemAvailable collapses does this
watchdog send SIGINT to fixture parent (Python finally owns kernel cleanup).
Records first CPU/VM stress and never substitutes for original business PASS.
"""
import argparse,json,os,pathlib,signal,time
def sample():
    lines=pathlib.Path("/proc/stat").read_text().splitlines()
    cores={}
    for line in lines:
        p=line.split()
        if len(p)>=9 and p[0].startswith("cpu") and p[0][3:].isdigit():
            values=[int(x) for x in p[1:9]]
            cores[p[0]]=(sum(values),values[3]+values[4])
    mem={}
    for l in pathlib.Path("/proc/meminfo").read_text().splitlines():
        k,_,v=l.partition(":")
        if k in ("MemTotal","MemAvailable"):
            mem[k]=int(v.split()[0])*1024
    return cores,mem
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pid",required=True,type=int)
    ap.add_argument("--out",required=True,type=pathlib.Path)
    ap.add_argument("--period",type=int,default=10)
    a=ap.parse_args()
    assert a.pid>1 and a.period>=5
    a.out.parent.mkdir(parents=True,exist_ok=True)
    last,mem=sample()
    consecutive=0;rows=0;status="NORMAL_MONITOR_EXIT"
    start=time.monotonic()
    with a.out.open("w") as out:
        while True:
            time.sleep(a.period)
            try:os.kill(a.pid,0)
            except ProcessLookupError:break
            now,m=sample()
            vals=[]
            for name in last.keys()&now.keys():
                dt=now[name][0]-last[name][0]
                di=now[name][1]-last[name][1]
                if dt>0:vals.append(100*(dt-di)/dt)
            last=now
            if not vals:continue
            avg=sum(vals)/len(vals);maximum=max(vals)
            free_gb=m.get("MemAvailable",0)/2**30
            # 30s sustained host saturation, not a single hot Rust core
            # or an OS tick; this is a VM safety stop, never product FAIL.
            bad=(avg>=85.0 or maximum>=97.0 or free_gb<0.75)
            consecutive=consecutive+1 if bad else 0
            row={"elapsed_s":round(time.monotonic()-start,2),
                 "core_count":len(vals),"host_mean_busy_pct":round(avg,2),
                 "host_max_core_busy_pct":round(maximum,2),
                 "mem_available_gib":round(free_gb,3),
                 "capacity_guard_bad_consecutive":consecutive}
            out.write(json.dumps(row,sort_keys=True)+"\n");out.flush();rows+=1
            if consecutive>=3:
                status="VM_CAPACITY_LIMITED_CANCELLED_AFTER_30S_SUSTAINED"
                out.write(json.dumps({"classification":status,"trigger":row})+"\n");out.flush()
                os.kill(a.pid,signal.SIGINT)
                break
        out.write(json.dumps({"classification":status,"observations":rows,
                              "actual_monitor_elapsed_s":round(time.monotonic()-start,2)})+"\n")
        out.flush()
    print("H1504_NATIVE_ARM_VM_CAPACITY_GUARD",status,"samples",rows,flush=True)
    if status!="NORMAL_MONITOR_EXIT":raise SystemExit(2)
if __name__=="__main__":main()
