"""H2464 fixture-only IPv4-in-IPv4 access segment over existing Tailscale.
Keep Windows eth0-facing vEthernet, server VXLAN, relay namespace and netem.
No tailnet route advertisements or ACL changes.
"""
import json,pathlib,sys
import m0_h2228_three_runner_relay as h
import m0_h2462_capacity as b

TUN="h2464ip"
STATE={"client":pathlib.Path("h2442-out/h2464-client-state.json"),
       "relay":pathlib.Path("h2228-out/h2464-relay-state.json")}
SERVER=h.CIDR["server"]
BR=h.BR["client"]
VETH=h.VHOST["client"]
GW=h.GW["client"]
LAN=h.LAN["client"]

def run(*args,allow_fail=False):return h.root(*args,allow_fail=allow_fail).stdout
def info(role):
    peers={r:b.load(b.PEER/(r+".json")) for r in ("client","relay")}
    return peers[role]["tail_ip"],peers["relay" if role=="client" else "client"]["tail_ip"],peers["client"]["windows_access_ip"]
def route(dst):return run("ip","route","get",dst)
def link_exists(name):return h.root("ip","link","show","dev",name,allow_fail=True).returncode==0
def stats(name):
    if not link_exists(name):return None
    link=json.loads(run("ip","-s","-j","link","show","dev",name))[0]
    return link.get("stats64",link.get("stats",{}))

def snapshot(role):
    local,remote,win=info(role)
    active=STATE[role].is_file()
    row={"role":role,"mode":"ipip" if active else "vxlan","tunnel":stats(TUN),"vxlan":stats(h.VX["client"]),
         "tail_route":route(remote)}
    if role=="client":
        row["business_route"]=route(h.LAN["server"])
        assert ("dev "+TUN if active else "dev "+BR) in row["business_route"],row
    else:
        row["namespace_route"]=h.ns(h.ROUTER,"ip","route","get",win).stdout
        assert "via "+LAN in row["namespace_route"] and "dev "+h.RDEV["client"] in row["namespace_route"],row
        if active:
            row["windows_route"]=route(win)
            row["server_route"]=route(h.LAN["server"])
            assert "dev "+TUN in row["windows_route"] and "dev "+VETH in row["server_route"],row
    return row

def rollback(role):
    p=STATE[role]
    if not p.is_file():return snapshot(role)
    state=b.load(p)
    # Reverse only commands that actually succeeded in this fixture.
    errors=[]
    while state["undo"]:
        args=state["undo"][-1]
        try:run(*args)
        except Exception as e:
            errors.append({"command":args,"error":repr(e)});break
        state["undo"].pop();b.save(p,state)
    if errors:raise RuntimeError("fixture rollback failed: "+repr(errors))
    p.unlink()
    return snapshot(role)

def activate(role):
    p=STATE[role]
    if p.is_file():return snapshot(role)
    local,remote,win=info(role)
    assert not link_exists(TUN),"unexpected preexisting tunnel"
    state={"undo":[]};b.save(p,state)
    def step(args,undo):
        run(*args)
        state["undo"].append(undo);b.save(p,state)
    try:
        step(["ip","tunnel","add",TUN,"mode","ipip","local",local,"remote",remote,"dev","tailscale0","ttl","64"],
             ["ip","tunnel","del",TUN])
        run("ip","link","set","dev",TUN,"mtu","1200","up")
        if role=="client":
            step(["ip","route","replace",SERVER,"dev",TUN],
                 ["ip","route","replace",SERVER,"via",GW,"dev",BR])
            pairs=[("eth0",TUN),(TUN,"eth0")]
        else:
            # Existing relay namespace sees the same next hop and the same
            # two netem egress devices; only its client-side host transport changes.
            step(["ip","link","set",VETH,"nomaster"],["ip","link","set",VETH,"master",BR])
            step(["ip","addr","add",LAN+"/24","dev",VETH],["ip","addr","del",LAN+"/24","dev",VETH])
            step(["ip","route","add",win+"/32","dev",TUN],["ip","route","del",win+"/32","dev",TUN])
            step(["ip","route","add",SERVER,"via",GW,"dev",VETH],["ip","route","del",SERVER,"via",GW,"dev",VETH])
            old=run("sysctl","-n","net.ipv4.ip_forward").strip()
            if old!="1":step(["sysctl","-qw","net.ipv4.ip_forward=1"],["sysctl","-qw","net.ipv4.ip_forward="+old])
            pairs=[(VETH,TUN),(TUN,VETH)]
        for i,o in pairs:
            rule=["FORWARD","1","-i",i,"-o",o,"-j","ACCEPT"]
            step(["iptables","-w","-I",*rule],["iptables","-w","-D",rule[0],*rule[2:]])
        return snapshot(role)
    except Exception:
        rollback(role)
        raise

def apply(role,mode):
    assert role in STATE and mode in ("vxlan","ipip","snapshot")
    if mode=="snapshot":return snapshot(role)
    return activate(role) if mode=="ipip" else rollback(role)

def traffic(before,after,received):
    if received<=0:return False
    try:
        # With real download through the candidate, client IPIP RX and relay
        # IPIP TX byte deltas must each carry at least the app receipt bytes.
        for role,side in (("client","rx"),("relay","tx")):
            a=before[role]["tunnel"][side]["bytes"];z=after[role]["tunnel"][side]["bytes"]
            if z-a<received*.95:return False
        return True
    except (KeyError,TypeError):return False

if __name__=="__main__":print(json.dumps(apply(*sys.argv[1:])))
