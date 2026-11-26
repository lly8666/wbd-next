"""H2475 local same-runner ceiling screening, shared deterministic case definitions."""
import json,pathlib
RATES=(650,650,650,650,650,650)
MODES=('copy','both','loan','all','copy','all')
DIRECT={-11:(200,67108864)}
DIRECT_RATES={i:650 for i in DIRECT}
SECONDS=DIRECT_SECONDS=60
GUEST_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
def cases(root):
    template=json.loads((root/"tools/m0_h2442_matrix.json").read_text())[0]
    return [dict(template,budget=r,rate=r,loss=0,profile=-1,isolate=True,rcvbuf=67108864) for r in RATES]
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
def midpoint(rows):return None
def comparable(row):
    return row.get("status")=="MEASURED_EXACT" and row.get("netem_active",{}).get("both_used") is True and row.get("steady_drops",{}).get("available") is True
