#!/usr/bin/env python3
"""Host/core/worker CPU diagnostics. Raw counters and interval deltas; missing data null.
No extra product hot-path instrumentation; cgroup v1 and v2 supported."""
import os,pathlib,re,time,statistics,math
P=pathlib.Path
def read(path):
    try:return P(path).read_text()
    except OSError:return None
def cgfiles(pid):
    # Discover controller and actual task cgroup path via mountinfo, not fixed v2 root.
    entries=read(f"/proc/{pid}/cgroup") or ""
    mounts=read(f"/proc/{pid}/mountinfo") or ""
    result={}
    for entry in entries.splitlines():
        _,controllers,group=entry.split(":",2)
        for line in mounts.splitlines():
            if " - " not in line:continue
            pre,post=line.split(" - ",1);a=pre.split();b=post.split()
            if len(a)<5 or len(b)<3:continue
            if b[0]=="cgroup2" and controllers=="":names=("cpu.max","cpu.stat","cpu.pressure","cpuset.cpus.effective")
            elif b[0]=="cgroup" and "cpu" in controllers.split(",") and "cpu" in b[2].split(","):names=("cpu.cfs_quota_us","cpu.cfs_period_us","cpu.stat","cpu.shares","cpuacct.usage")
            else:continue
            root=a[3];mount=a[4]
            rel=group[len(root):].lstrip("/") if root!="/" and (group==root or group.startswith(root+"/")) else group.lstrip("/")
            base=P(mount)/rel
            for name in names:
                value=read(base/name)
                if value is not None:result[str(base/name)]=value
    return {"membership":entries,"files":result}
def cpu_environment():
    return {"logical_affinity":sorted(os.sched_getaffinity(0)),"clock_ticks":os.sysconf("SC_CLK_TCK"),"schedstats":read("/proc/sys/kernel/sched_schedstats"),"cpu_online":read("/sys/devices/system/cpu/online"),"self_cgroup":cgfiles("self"),"cpu_pressure":read("/proc/pressure/cpu")}
def sample_cpu(pids,t):
    out={"elapsed_s":time.monotonic()-t,"cores":{},"psi":read("/proc/pressure/cpu"),"loadavg":read("/proc/loadavg"),"workers":{},"cgroup":{}}
    for line in (read("/proc/stat") or "").splitlines():
        a=line.split()
        if a and re.fullmatch(r"cpu\d*",a[0]):out["cores"][a[0]]=list(map(int,a[1:9]))
        elif a and a[0] in ("procs_running","procs_blocked"):out[a[0]]=int(a[1])
    for role,pid in pids.items():
        out["cgroup"][role]=cgfiles(pid)
        for task in P(f"/proc/{pid}/task").glob("*/stat"):
            raw=read(task)
            if not raw:continue
            try:
                comm=raw.split("(",1)[1].rsplit(")",1)[0];v=raw.rsplit(")",1)[1].split()
                sched=read(task.parent/"schedstat")
                out["workers"][role+":"+task.parent.name]={"name":comm,"ticks":int(v[11])+int(v[12]),"start_ticks":int(v[19]),"last_cpu":int(v[36]),"schedstat_ns":list(map(int,sched.split()[:3])) if sched else None}
            except (ValueError,IndexError):continue
    return out
def p95(v):
    return sorted(v)[math.ceil(len(v)*.95)-1] if v else None
def psi_total(s):
    m=re.search(r"(?m)^some .*?\btotal=(\d+)",s or "")
    return int(m[1]) if m else None
def summarize_cpu(samples):
    a=[x for x in samples if 15<=x["elapsed_s"]<=45]
    if len(a)<2:return {"status":"INSUFFICIENT","sample_count":len(a)}
    tick=os.sysconf("SC_CLK_TCK");cores={};workers={};psi=[];runq=[];steal=[];softirq=[];throttle={}
    for x,y in zip(a,a[1:]):
        dt=y["elapsed_s"]-x["elapsed_s"]
        if dt<=0:continue
        for k,v in y["cores"].items():
            if k not in x["cores"]:continue
            d=[b-c for b,c in zip(v,x["cores"][k])];total=sum(d)
            if total<=0 or min(d)<0:continue
            busy=sum(d[i] for i in (0,1,2,5,6))/total*100
            cores.setdefault(k,[]).append(busy)
            if k=="cpu":
                softirq.append(d[6]/total*100);steal.append(d[7]/total*100)
        t0,t1=psi_total(x["psi"]),psi_total(y["psi"])
        if t0 is not None and t1 is not None and t1>=t0:psi.append((t1-t0)/dt/10000)
        if "procs_running" in y:runq.append(y["procs_running"])
        for k,v in y["workers"].items():
            u=x["workers"].get(k)
            if not u or u["start_ticks"]!=v["start_ticks"]:continue
            w=workers.setdefault(k,{"name":v["name"],"cpu_pct":[],"runqueue_wait_pct":[]})
            w["cpu_pct"].append(max(0,v["ticks"]-u["ticks"])/tick/dt*100)
            if u["schedstat_ns"] and v["schedstat_ns"]:
                w["runqueue_wait_pct"].append(max(0,v["schedstat_ns"][1]-u["schedstat_ns"][1])/dt/1e7)
        for role,g in y["cgroup"].items():
            old=x["cgroup"].get(role,{}).get("files",{})
            for file,txt in g["files"].items():
                if not file.endswith("/cpu.stat") or file not in old:continue
                def values(s):return {k:int(v) for k,v in re.findall(r"(?m)^(\w+)\s+(\d+)$",s)}
                m,n=values(old[file]),values(txt)
                entry=throttle.setdefault(role+":"+file,{"nr_throttled":0,"throttled_seconds":0})
                entry["nr_throttled"]+=max(0,n.get("nr_throttled",0)-m.get("nr_throttled",0))
                for field,scale in (("throttled_usec",1e6),("throttled_time",1e9)):
                    if field in n and field in m:entry["throttled_seconds"]+=max(0,n[field]-m[field])/scale
    def stats(v):return {"mean":statistics.mean(v),"p95":p95(v),"max":max(v)} if v else None
    return {"status":"MEASURED","sample_count":len(a),"window_s":a[-1]["elapsed_s"]-a[0]["elapsed_s"],"host_busy_pct":stats(cores.pop("cpu",[])),"per_core_busy_pct":{k:stats(v) for k,v in cores.items()},"cpu_psi_some_pct":stats(psi),"softirq_pct":stats(softirq),"steal_pct":stats(steal),"runnable_tasks":stats(runq),"workers":{k:{"name":v["name"],"cpu_pct":stats(v["cpu_pct"]),"runqueue_wait_pct":stats(v["runqueue_wait_pct"])} for k,v in workers.items()},"cgroup_throttle_delta":throttle}
