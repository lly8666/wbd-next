"""Produce candidate screening summaries, never an automatic product rate policy."""
import argparse,collections,json,pathlib,statistics

def identity(run):
    hw=run.get("machine",{}).get("windows",{}).get("hardware")
    probe=run.get("machine",{}).get("windows",{}).get("probe") or {}
    wsl=run.get("machine",{}).get("wsl",{}).get("probe") or {}
    if isinstance(hw,list):hw=hw[0] if len(hw)==1 else {}
    hw=hw or {}
    name=" ".join((hw.get("Name") or run.get("windows_cpu") or "UNKNOWN").upper().split())
    versions=tuple(str(x.get(k,"unknown")) for x in (probe,wsl) for k in ("schema","python","openssl","zlib","seconds_per_sample","repeats"))
    duration=run.get("measurement_seconds")
    if duration is None:
        durations={x.get("duration_s") for x in run.get("rows",[])}
        duration=next(iter(durations)) if len(durations)==1 else None
    return (name,hw.get("NumberOfCores",run.get("cores")),hw.get("NumberOfLogicalProcessors",run.get("logical")),
            run.get("fixture"),run.get("product_source"),duration,versions)

def normalized(row):
    cap=row.get("rate_mbps",row.get("cap_mbps"))
    good=row.get("rx_mbps",row.get("goodput_mbps"))
    ok=row.get("qualified") is True and row.get("receipt","MEASURED_EXACT")=="MEASURED_EXACT"
    delta=row.get("tun_delta") or {}
    total=delta.get("tx_packets",0)+delta.get("tx_dropped",0)
    drop=delta["tx_dropped"]/total if total>0 and "tx_dropped" in delta else None
    return {"cap":cap,"goodput":good,"ok":ok,"kind":row.get("kind"),
            "fill":good/cap if isinstance(good,(int,float)) and cap else None,
            "tun_counter_drop_fraction":drop}

def report(database):
    groups=collections.defaultdict(list)
    for r in database["observations"]:groups[identity(r)].append(r)
    output=[]
    for key,runs in groups.items():
        by_rate=collections.defaultdict(list);probes=[]
        for run in runs:
            rows=[normalized(x) for x in run.get("rows",[])]
            bare=[r for r in rows if r["kind"]=="bare" and r["cap"]==250]
            good=[r["goodput"] for r in bare if r["ok"] and r["goodput"] is not None]
            drift=(max(good)-min(good))/max(good) if len(good)>=2 and max(good)>0 else None
            stable=bool(len(bare)>=2 and len(good)==len(bare) and drift is not None and drift<=.10)
            per_rate=collections.defaultdict(list)
            for r in rows:
                if r["kind"]=="wbd":per_rate[r["cap"]].append(r)
            for cap,legs in per_rate.items():
                fills=[r["fill"] for r in legs if r["ok"] and r["fill"] is not None]
                drops=[r["tun_counter_drop_fraction"] for r in legs if r["tun_counter_drop_fraction"] is not None]
                all_ok=len(fills)==len(legs) and bool(fills)
                by_rate[cap].append({"run_id":str(run["run_id"]),"legs":len(legs),"all_qualified":all_ok,
                   "worst_fill":min(fills) if fills else None,"bare250_drift":drift,"bare250_stable":stable,
                   "max_tun_counter_drop_fraction":max(drops) if drops else None,
                   "screen_pass":bool(stable and all_ok and min(fills)>=.85)})
            cpu=run.get("machine",{}).get("windows",{}).get("probe")
            if cpu:
                probes.append({"run_id":str(run["run_id"]),"windows_ops_per_wall_s":
                   {name:work.get("median_ops_per_wall_s") for name,work in cpu.get("workloads",{}).items()}})
        summary=[]
        for cap,obs in sorted(by_rate.items()):
            vals=[x["worst_fill"] for x in obs if x["worst_fill"] is not None]
            n=len({x["run_id"] for x in obs});passed=sum(x["screen_pass"] for x in obs)
            summary.append({"cap_mbps":cap,"independent_runs":n,"screen_pass_runs":passed,
                "worst_qualified_fill":min(vals) if vals else None,"median_worst_qualified_fill":statistics.median(vals) if vals else None,
                "eligible_for_long_validation":bool(key[0]!="UNKNOWN" and key[5] is not None and n>=3 and passed==len(obs)==len(runs)),
                "observations":obs})
        candidates=[r["cap_mbps"] for r in summary if r["eligible_for_long_validation"]]
        output.append({"windows_cpu":key[0],"exposed_cores":key[1],"logical_cpus":key[2],"fixture":key[3],
          "product_source":key[4],"measurement_seconds":key[5],"probe_versions":key[6],
          "independent_runs":len(runs),"classification":"UNCLASSIFIED","cpu_probe_scores":probes,
          "candidate_for_long_validation_mbps":max(candidates) if candidates else None,"rates":summary})
    return {"schema":"m0-machine-rate-screen-v1","policy":"Experimental only: >=3 independent same-group runs, all legs exact/direct, paired bare250 <=10% drift and worst qualified goodput/cap >=85%. TUN drop fraction is interface counter ratio, not flow loss. Candidate is not production rate or zero-loss claim. No automatic CPU ranking.","groups":output}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("database");p.add_argument("--out")
    a=p.parse_args();data=json.loads(pathlib.Path(a.database).read_text(encoding="utf-8-sig"));s=json.dumps(report(data),indent=2)+"\n"
    if a.out:pathlib.Path(a.out).write_text(s)
    else:print(s,end="")
