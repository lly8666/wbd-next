"""H2459: native two-segment ZeroTier, real ARM L3, no product changes."""
import http.server, ipaddress, json, os, pathlib, platform, secrets, subprocess, sys, time
import m0_h2457_zt_access as z
import m0_h2228_three_runner_relay as h
from m0_h2455_segments import command

ROOT=pathlib.Path.cwd()
META=ROOT/"h2228-meta"
PEER=ROOT/"h2228-peer"
OUT=ROOT/"h2228-out"
LAN={"client":"10.248.81.2","server":"10.248.82.2"}
GW={"client":"10.248.81.1","server":"10.248.82.1"}
CIDR={"client":"10.248.81.0/24","server":"10.248.82.0/24"}
ROLES=("client","server","relay")
for p in (META,PEER,OUT):p.mkdir(exist_ok=True)

def save(p,obj):h.save(p,obj)
def read(p):return z.load(p)
def identity(role):
    v=z.identity()
    assert v.get("zt",{}).get("online"),v
    arch=platform.machine().lower()
    assert arch in (("amd64","x86_64") if role=="client" else ("aarch64","arm64"))
    assert (os.name=="nt")== (role=="client")
    row={"role":role,"source_sha":v["sha"],"run_id":v["run"],"node_id":v["zt"]["address"],"arch":arch}
    save(META/(role+".json"),row)
    return row

def validate(rows):
    assert set(rows)==set(ROLES)
    assert len({r["node_id"] for r in rows.values()})==3
    for role,r in rows.items():
        assert r["role"]==role and r["source_sha"]==os.environ["GITHUB_SHA"] and r["run_id"]==os.environ["GITHUB_RUN_ID"]
        assert r["arch"] in (("amd64","x86_64") if role=="client" else ("aarch64","arm64"))

def public_paths(peers,node):
    paths=[]
    for p in peers:
        if p.get("address")!=node or p.get("tunneled"):continue
        for q in p.get("paths",[]):
            try:ip=ipaddress.ip_address(q["address"].rsplit("/",1)[0])
            except (KeyError,ValueError):continue
            if q.get("preferred") and q.get("active") and not q.get("expired") and ip.is_global:
                paths.append(q["address"])
    return paths

def expected(role):
    if role=="relay":return {r:read(PEER/(r+".json"))["node_id"] for r in ("client","server")}
    return {"relay":read(PEER/"relay.json")["node_id"]}

def monitor(role,output,stopfile):
    ids=expected(role)
    with pathlib.Path(output).open("w",encoding="utf-8",buffering=1) as f:
        while not pathlib.Path(stopfile).exists():
            t=time.time()
            row={"role":role,"wall_unix":t,"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"]}
            try:
                peers=z.api("/peer")
                row["public_direct"]={r:public_paths(peers,node) for r,node in ids.items()}
                row["peers"]=[p for p in peers if p.get("address") in ids.values()]
            except Exception as e:row["error"]=repr(e)
            f.write(json.dumps(row)+"\n")
            time.sleep(max(0,1-(time.time()-t)))

def relay_start():
    rows={r:read(META/(r+".json")) for r in ROLES};validate(rows)
    node=rows["relay"]["node_id"];devices={}
    for role in ("client","server"):
        network=z.api("/controller/network/"+node+"______",{
            "name":"H2459-"+rows["relay"]["run_id"]+"-"+role,"private":True,
            "v4AssignMode":{"zt":True},
            "ipAssignmentPools":[{"ipRangeStart":GW[role],"ipRangeEnd":LAN[role]}],
            "routes":[{"target":CIDR[role],"via":None},{"target":CIDR["server" if role=="client" else "client"],"via":GW[role]}]
        })["id"]
        for member,ip in ((node,GW[role]),(rows[role]["node_id"],LAN[role])):
            z.api("/controller/network/"+network+"/member/"+member,{"authorized":True,"ipAssignments":[ip]})
        z.api("/network/"+network,{})
        local=z.zt_wait(network,GW[role]);dev=local["portDeviceName"]
        z.run("ip","link","set","dev",dev,"mtu","1200")
        rows[role].update(network_id=network,control_ip=LAN[role],gateway=GW[role])
        devices[role]=dev
    assert len(set(devices.values()))==2
    z.run("sysctl","-qw","net.ipv4.ip_forward=1")
    for side,dev in devices.items():
        z.run("iptables","-I","FORWARD","1","-i",dev,"-o",devices["server" if side=="client" else "client"],"-j","ACCEPT")
    forwarding={}
    for role,dev in devices.items():
        route=z.run("ip","route","get",LAN[role])
        assert "dev "+dev in route and "via " not in route,route
        other="server" if role=="client" else "client"
        transit=z.run("ip","route","get",LAN[other],"from",LAN[role],"iif",dev)
        assert "dev "+devices[other] in transit,transit
        forwarding[role]={"local":route,"transit":transit}
    rows["relay"].update(control_ip=GW["client"],control_token=secrets.token_hex(32))
    rows["client"]["windows_access_ip"]=LAN["client"]
    for role,row in rows.items():save(PEER/(role+".json"),row)
    save(OUT/"zt-local.json",{"role":"relay","devices":devices,"networks":{r:rows[r]["network_id"] for r in devices},"routes":z.run("ip","route"),"forwarding":forwarding,"mtu":1200})

def join(role):
    rows={r:read(PEER/(r+".json")) for r in ROLES};validate(rows)
    local=identity(role);assert local["node_id"]==rows[role]["node_id"]
    row=rows[role]
    z.api("/network/"+row["network_id"],{})
    info=z.zt_wait(row["network_id"],LAN[role])
    if role=="client":
        adapter=z.adapter_for(LAN[role])
        index=int(adapter["ifIndex"])
        z.run("pwsh","-NoProfile","-NonInteractive","-Command",
              "Set-NetIPInterface -AddressFamily IPv4 -InterfaceIndex "+str(index)+" -NlMtuBytes 1200")
        route=z.ps("Find-NetRoute -RemoteIPAddress '"+LAN["server"]+"' | Where-Object {$_.DestinationPrefix} | Select-Object -First 1 InterfaceIndex,DestinationPrefix,NextHop | ConvertTo-Json -Compress")
        assert int(route["InterfaceIndex"])==index and route["NextHop"]==GW[role],route
        data={"role":role,"adapter":adapter,"route":route,"mtu":1200}
    else:
        dev=info["portDeviceName"]
        z.run("ip","link","set","dev",dev,"mtu","1200")
        # Same original scoped RST suppression as H2228 server fixture.
        z.run("iptables","-w","-A","OUTPUT","-o",dev,"-p","tcp","--sport","443","--tcp-flags","RST","RST","-j","DROP")
        h.root("modprobe","tcp_bbr",allow_fail=True)
        z.run("sysctl","-qw","net.ipv4.tcp_congestion_control=bbr")
        route=z.run("ip","route","get",LAN["client"])
        assert "via "+GW[role] in route and "dev "+dev in route,route
        data={"role":role,"device":dev,"route":route,"mtu":1200}
    data["network_id"]=row["network_id"]
    save(OUT/"zt-local.json",data)

def linux_snapshot(namespace=None):
    prefix=["sudo","-n","ip","netns","exec",namespace] if namespace else []
    commands={"links":["ip","-s","-j","link","show"],"qdisc":["tc","-s","-j","qdisc","show"],"nstat":["nstat","-az"],"softnet":["cat","/proc/net/softnet_stat"]}
    return {k:command(prefix+v) for k,v in commands.items()}

def relay_control():
    cfg=read(OUT/"zt-local.json")
    h.RDEV=cfg["devices"]
    # Reuse the exact H2228 netem and fixed command control protocol.
    def relay_ns(_name,*args,**kw):
        # H2228 impair() also probes its original rcli0 name before iterating RDEV.
        return h.root(*(h.RDEV["client"] if a=="rcli0" else a for a in args),**kw)
    h.ns=relay_ns
    def snapshot(tag):
        return {**{r:{"qdisc":json.loads(h.root("tc","-s","-j","qdisc","show","dev",d).stdout),
                      "link":json.loads(h.root("ip","-s","-j","link","show","dev",d).stdout)}
                   for r,d in h.RDEV.items()},
                "host_segments":linux_snapshot(),"tag":tag}
    h.local_relay_snapshot=snapshot
    applied=h.impair(0,0,"iid")
    h.Control.client_ip=LAN["client"]
    h.Control.token=read(PEER/"relay.json")["control_token"]
    with http.server.ThreadingHTTPServer((GW["client"],18727),h.Control) as service:
        save(OUT/"relay-ready.json",{"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"devices":h.RDEV,"impair":applied})
        service.serve_forever()

def qualify(folder):
    folder=pathlib.Path(folder)
    summary=read(folder/"client"/"summary.json")
    assert summary["source_sha"]==os.environ["GITHUB_SHA"] and summary["run_id"]==os.environ["GITHUB_RUN_ID"]
    logs={}
    for role in ROLES:
        p=folder/role/"zt-paths.jsonl"
        logs[role]=[json.loads(line) for line in p.read_text().splitlines() if line] if p.is_file() else []
    rows=[]
    for case in summary["rows"]:
        a,b=case.get("measure_start_unix"),case.get("measure_end_unix")
        verdict={}
        for role,log in logs.items():
            # 1s sampling, allow <=4s gaps for scheduling and modest clock skew.
            relevant=[x for x in log if a is not None and b is not None and a-3<=x["wall_unix"]<=b+3]
            times=[x["wall_unix"] for x in relevant]
            expected_count=2 if role=="relay" else 1
            direct=bool(times and times[0]<=a+2 and times[-1]>=b-2 and
                all(y-x<=4 for x,y in zip(times,times[1:])) and all(
                    x.get("source_sha")==summary["source_sha"] and x.get("run_id")==summary["run_id"] and x.get("role")==role and
                    len(x.get("public_direct",{}))==expected_count and all(x["public_direct"].values())
                    for x in relevant))
            verdict[role]={"sampled_public_direct":direct,"samples":len(times)}
        rows.append({"case":case["case"],"path":verdict,"all_nodes_sampled_direct":all(v["sampled_public_direct"] for v in verdict.values()),
                     "receipt":case["status"],"rx_mbps":case.get("rx_mbps")})
    high=next((r for r in rows if r["case"]==-2),{})
    capacity=high.get("all_nodes_sampled_direct") and high.get("receipt")=="MEASURED_EXACT" and (high.get("rx_mbps") or 0)>=570
    exact=len(rows)==5 and all(r["receipt"]=="MEASURED_EXACT" and r["all_nodes_sampled_direct"] for r in rows)
    report={"source_sha":summary["source_sha"],"run_id":summary["run_id"],"rows":rows,
            "direct_400ms_600m_reference_at_least_570m":bool(capacity),"all_cases_qualified":bool(exact and capacity),
            "scope":"public direct peer sampled at 1s, not proof of each packet; 570Mbps is 95% of 600M direct pacing reference; incomplete business remains diagnostic, not a performance PASS"}
    save("h2459-qualification.json",report)
    print(json.dumps(report),flush=True)
    if not report["all_cases_qualified"]:raise SystemExit(2)

if __name__=="__main__":
    action=sys.argv[1]
    if action=="identity":identity(sys.argv[2])
    elif action=="relay-start":relay_start()
    elif action=="join":join(sys.argv[2])
    elif action=="relay-control":relay_control()
    elif action=="monitor":monitor(*sys.argv[2:])
    elif action=="qualify":qualify(sys.argv[2])
    else:raise ValueError(action)
