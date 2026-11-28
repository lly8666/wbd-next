"""QA only: matched app exchange over WSL bare TCP, no WBD process.
Same socket buffers/offer/window/CUBIC as the tunneled RTT quartet.
WSL root sender (not NAT origin namespace), so this is a path-capacity reference,
not an isolated carrier-only experiment. The sender's actual MSS is checked.
"""
import json, os, pathlib, socket, subprocess, sys, threading, time
from m0_winxdp_pressure_tcp import exchange, client as pressure_client, summarize

SECONDS=65
RATE=650
MSS=1349
PORT=5202

def source(host):
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        # B04 run46106349947 measured 1361 for requested 1361 on this path.
        # Use the observed socket behavior; retain the actual MSS acceptance gate.
        listener.setsockopt(socket.IPPROTO_TCP,socket.TCP_MAXSEG,MSS)
        listener.bind((host,PORT))
        listener.listen(1)
        listener.settimeout(90)
        print("SOURCE_READY",flush=True)
        s,_=listener.accept()
        with s:
            s.setsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,b"cubic")
            cc=s.getsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,32).split(b"\0")[0].decode()
            mss=s.getsockopt(socket.IPPROTO_TCP,socket.TCP_MAXSEG)
            s.settimeout(40)
            assert s.recv(1)==b"\0"
            s.sendall(b"R")
            result=summarize([exchange(s,SECONDS,RATE,True,False,False)],SECONDS)
            result.update(cc=cc,mss=mss)
            print(json.dumps(result),flush=True)

def run():
    from m0_h2475_fixture import wsl,wpath,shape,snapshot
    from m0_winxdp_pressure_client import exact_flows
    root=pathlib.Path.cwd()
    out=root/"h2476-out/bare"
    out.mkdir(parents=True,exist_ok=False)
    peer=os.environ["WBD_PLAN024_NATIVE_VERIFIED_GUEST_IP4"]
    host=os.environ["WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4"]
    # Same root values as pressure_server.setup; dedicated CI guest only.
    for k,v in (("net.ipv4.tcp_rmem","4096 87380 67108864"),
                ("net.ipv4.tcp_wmem","4096 65536 67108864"),
                ("net.core.rmem_max","67108864"),("net.core.wmem_max","67108864")):
        wsl("sysctl","-qw",k+"="+v)
    rows=[]
    seq="BAAB" if os.environ["H2478_REPLICA"]=="B" else "ABBA"
    for i,arm in enumerate(seq):
        d=out/("case-"+str(i));d.mkdir()
        delay=200 if arm=="A" else 20
        p=None;worker=None
        row={"arm":arm,"case":i,"delay_ms":delay,"rate":RATE,"path":"bare-wsl-root","valid":False}
        try:
            shape(d,0)
            shape(d,200)
            for dev,handle in (("eth0","20:"),("ifbwlm0","10:")):
                wsl("tc","qdisc","change","dev",dev,"root","handle",handle,"netem","delay",str(delay)+"ms","loss","0%","limit","32768")
            row["shape"]={dev:wsl("tc","-s","qdisc","show","dev",dev) for dev in ("eth0","ifbwlm0")}
            with (d/"source.log").open("w",encoding="utf-8") as f:
                p=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--exec","env","WBD_XDP_STRESS_PHASE=carrier-abba","python3",wpath(root/"tools/m0_winxdp_bare_supply.py"),"source",peer],stdout=f,stderr=subprocess.STDOUT)
                deadline=time.monotonic()+30
                while "SOURCE_READY" not in (d/"source.log").read_text(encoding="utf-8",errors="replace"):
                    if p.poll() is not None or time.monotonic()>deadline:raise RuntimeError("bare source not ready")
                    time.sleep(.2)
                before=snapshot()
                samples=[]
                def connected():
                    nonlocal worker
                    t=time.monotonic()
                    def observe():
                        for at in (15,30,45,55):
                            time.sleep(max(0,t+at-time.monotonic()))
                            try:samples.append({"elapsed_s":time.monotonic()-t,"ss":wsl("ss","-tinm","( sport = :5202 )")})
                            except Exception as e:samples.append({"error":repr(e)})
                    worker=threading.Thread(target=observe,daemon=True);worker.start()
                client=pressure_client(peer,PORT,host,SECONDS,{"streams":1,"rate":RATE,"direction":"down","rcvbuf":67108864,"sndbuf":16777216},connected)
                if worker:worker.join(5)
                after=snapshot()
                rc=p.wait(20)
            sender=json.loads((d/"source.log").read_text(encoding="utf-8").splitlines()[-1])
            packets={k:after["netem_packets"][k]-before["netem_packets"][k] for k in ("eth0","ifbwlm0")}
            row.update(client=client,sender=sender,source_rc=rc,netem_packets=packets,snapshots=samples,rx_mbps=client["rx_mbps"],exact_hash=exact_flows(client,sender),counter_delta={k:v-before["counters"].get(k,v) for k,v in after["counters"].items()})
            row["valid"]=rc==0 and sender["cc"]=="cubic" and sender["mss"]==MSS and client["end"]==sender["end"]=="eof" and row["exact_hash"] and all(v>0 for v in packets.values()) and len(samples)==4 and all("ss" in s and "cubic" in s["ss"] for s in samples)
        except Exception as e:
            row["error"]=repr(e)
        finally:
            if p and p.poll() is None:
                p.terminate();p.wait(10)
            shape(d,0)
            (d/"result.json").write_text(json.dumps(row,indent=2),encoding="utf-8")
        rows.append(row)
        print("WINXDP_BARE_SUPPLY_CASE "+json.dumps({k:row.get(k) for k in ("arm","case","delay_ms","rx_mbps","exact_hash","valid","error","netem_packets","counter_delta")}|{"cc":row.get("sender",{}).get("cc"),"mss":row.get("sender",{}).get("mss")}),flush=True)
        if not row["valid"]:break
    (out/"bare-summary.json").write_text(json.dumps({"sequence":seq,"rows":rows,"scope":"direct WSL TCP; root sender without tunnel; no product CPU comparison"},indent=2),encoding="utf-8")
    if len(rows)!=4 or not all(r["valid"] for r in rows):raise SystemExit(2)

if __name__=="__main__":
    if sys.argv[1:2]==["source"]:source(sys.argv[2])
    else:run()
