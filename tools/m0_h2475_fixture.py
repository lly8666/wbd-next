"""Use the actual WSL guest's executable PATH for all test-only commands."""
import json,pathlib,re,subprocess,sys,time
from m0_h2475_profile import GUEST_PATH
from m0_wl_windows_bounded_cmd import run_captured
ROOT=pathlib.Path.cwd()
def wpath(p):
    p=p.resolve()
    return "/mnt/"+p.drive[0].lower()+"/"+"/".join(p.relative_to(p.anchor).parts)
def wsl(*a,timeout=30):
    p=run_captured(["wsl.exe","-d","Ubuntu","-u","root","--exec","/usr/bin/env","PATH="+GUEST_PATH,*map(str,a)],timeout,max_output_bytes=8*1024*1024)
    if p.returncode:raise RuntimeError(f"guest {a[0]} rc={p.returncode}: "+(p.stderr+p.stdout)[-1000:])
    return p.stdout.strip()
def save(p,d):p.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8")
def readback():
    q={d:wsl("tc","-s","qdisc","show","dev",d) for d in ("eth0","ifbwlm0")}
    filters=wsl("tc","-s","filter","show","dev","eth0","ingress")
    return {"qdisc":q,"filters":filters}
def verify(row):
    for d in ("eth0","ifbwlm0"):
        if not re.search(r"\bnetem\b[^\n]*\bdelay\s+200(?:\.0+)?ms\b",row["qdisc"][d],re.I):
            raise RuntimeError("missing actual 200ms netem: "+d)
    for port in (443,5202):
        if not re.search(r"\bmatch\s+%08x/0000ffff\b"%port,row["filters"],re.I):
            raise RuntimeError("missing ingress TCP destination filter: "+str(port))
    if row["filters"].count("mirred")<2:raise RuntimeError("missing IFB redirects")
def shape(directory,delay):
    directory.mkdir(parents=True,exist_ok=True)
    args=("python3",wpath(ROOT/"tools/m0_wl_netem.py"),"arm" if delay else "cleanup",wpath(directory),"v2",wpath(ROOT/"scenarios/h2441-win-bbr-clean.json"))
    if delay:
        assert delay==200
        wsl(*args,timeout=60)
        try:
            wsl("tc","filter","add","dev","eth0","parent","ffff:","protocol","ip","prio","2","u32","match","ip","protocol","6","0xff","match","ip","dport","5202","0xffff","action","mirred","egress","redirect","dev","ifbwlm0")
            row=readback();save(directory/"actual-netem-readback.json",row);verify(row)
        except BaseException:
            wsl("python3",wpath(ROOT/"tools/m0_wl_netem.py"),"cleanup",wpath(directory),"v2",wpath(ROOT/"scenarios/h2441-win-bbr-clean.json"),timeout=60)
            raise
    else:
        if (directory/"wl-n0-netem-owned.json").exists():
            wsl("python3",wpath(ROOT/"tools/m0_wl_netem.py"),"snapshot",wpath(directory),"v2",wpath(ROOT/"scenarios/h2441-win-bbr-clean.json"),timeout=45)
        wsl(*args,timeout=60)
    return {"delay_ms":delay,"loss_pct":0}
def cleanup_ok(receipt):
    # This is a fresh dedicated CI guest. Deleting an owned root can
    # regenerate kernel default qdiscs with new identities. Record both
    # complete states and require absence of all test-owned objects.
    allowed={"noqueue","pfifo_fast","fq_codel","mq"}
    return (not receipt["ifb_present"] and not receipt["owner_present"]
            and all(receipt[k] and all(q["kind"] in allowed and q.get("handle")!="ffff:" for q in receipt[k])
                    for k in ("before","after")))
def preflight(directory):
    directory.mkdir(parents=True,exist_ok=True)
    commands=wsl("sh","-c","command -v tc; command -v ip; command -v ss; command -v python3; command -v sudo")
    save(directory/"commands.json",{"path":GUEST_PATH,"commands":commands,"tc_version":wsl("tc","-V")})
    before=json.loads(wsl("tc","-j","qdisc","show","dev","eth0"))
    save(directory/"default-qdisc-before.json",before)
    try:shape(directory,200)
    finally:shape(directory,0)
    after=json.loads(wsl("tc","-j","qdisc","show","dev","eth0"))
    links=json.loads(wsl("ip","-j","link","show"))
    receipt={"before":before,"after":after,"identical":before==after,
             "ifb_present":any(x["ifname"]=="ifbwlm0" for x in links),
             "owner_present":(directory/"wl-n0-netem-owned.json").exists()}
    receipt["passed"]=cleanup_ok(receipt)
    save(directory/"preflight.json",receipt)
    print("H2475_NETEM_RESTORE "+json.dumps(receipt),flush=True)
    if not receipt["passed"]:raise RuntimeError("default queue or owned netem cleanup check failed")
    print("H2475_REAL_NETEM_PREFLIGHT_PASS",flush=True)
# Single WSL invocation for each boundary, no packet capture or payload retention.
SNAPSHOT=r"""
import json,subprocess,pathlib,time
def cmd(*a):return json.loads(subprocess.check_output(a,text=True))
links={};qdiscs={};counters={};netem={}
for x in cmd("ip","-s","-j","link","show"):
    d=x["ifname"]
    if d not in ("eth0","ifbwlm0","wbds0","h2442exit"):continue
    stats=x.get("stats64",x.get("stats"))
    links[d]=stats
    for side in ("rx","tx"):
        for k in ("dropped","errors"):
            counters[f"{d}.{side}.{k}"]=int(stats[side][k])
for q in cmd("tc","-s","-j","qdisc","show"):
    d=q.get("dev")
    if d not in links:continue
    key="|".join(str(q.get(k,"")) for k in ("dev","kind","handle","parent","root"))
    qdiscs[key]=q
    counters["qdisc."+key]=int(q["drops"])
    if q["kind"]=="netem":netem[d]=int(q["packets"])
rows=[line.split() for line in pathlib.Path("/proc/net/softnet_stat").read_text().splitlines()]
counters["guest_softnet_drops"]=sum(int(row[1],16) for row in rows)
assert "eth0" in links
print(json.dumps({"wall_unix":time.time(),"links":links,"qdiscs":qdiscs,"counters":counters,"netem_packets":netem}))
"""
def snapshot():
    return json.loads(wsl("python3","-c",SNAPSHOT,timeout=20))
if __name__=="__main__":preflight(pathlib.Path(sys.argv[1]))
