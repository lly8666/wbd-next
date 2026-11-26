"""H2475 local same-runner ceiling screening, shared deterministic case definitions."""
import json,pathlib
RATES=(125,250,400,600,800,125,175,325,500,700)
DIRECT={-10:(0,67108864),-11:(200,67108864),-12:(200,67108864)}
DIRECT_RATES={i:800 for i in DIRECT}
SECONDS=DIRECT_SECONDS=60
GUEST_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
def cases(root):
    template=json.loads((root/"tools/m0_h2442_matrix.json").read_text())[0]
    return [dict(template,budget=r,rate=r,loss=0,profile=-1,isolate=False,rcvbuf=67108864) for r in RATES]
def drops(before,after):
    try:
        if set(before["counters"])!=set(after["counters"]):raise ValueError("counter identity changed")
        vals={k:after["counters"][k]-v for k,v in before["counters"].items()}
        if not vals or min(vals.values())<0:raise ValueError("missing or reset counter")
        return {"available":True,"zero":not any(vals.values()),"deltas":vals}
    except (KeyError,TypeError,ValueError) as e:return {"available":False,"zero":False,"error":repr(e)}
def netem_active(before,after):
    try:
        out={d:after["netem_packets"][d]-before["netem_packets"][d] for d in ("eth0","ifbwlm0")}
        return {"packets":out,"both_used":all(v>0 for v in out.values())}
    except (KeyError,TypeError):return {"both_used":False}
def clean(row):
    return (row.get("status")=="MEASURED_EXACT" and row.get("business_drops",{}).get("zero") is True
            and row.get("netem_active",{}).get("both_used") is True
            and isinstance(row.get("rx_mbps"),(int,float)) and row["rx_mbps"]>=.85*row["rate_mbps"])
def midpoint(rows):
    results={r["case"]:r for r in rows}
    for i in range(4):
        if i not in results or i+1 not in results:break
        if clean(results[i]) and not clean(results[i+1]):return 6+i
        if not clean(results[i]):break
    return None
