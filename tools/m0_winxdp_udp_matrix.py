"""Original real product V2 UDP application; separate same-runner receipts.
Keep observed offered rates distinct from target. No product/protocol edits.
"""
import json,os,pathlib,re,shutil,subprocess,sys,time
from m0_wl_windows_bounded_cmd import run_captured
from m0_wl_perf_v2_config import read_scenario
ROOT=pathlib.Path.cwd()
OUT=ROOT/"result/wl-public"; E=ROOT/"result/winxdp-udp-matrix"; E.mkdir(parents=True,exist_ok=True)
CASES=[["fixed-base-first","fixed",16384,2048,32,"original",350,5,20,1200],["fixed-rx8192","fixed",8192,2048,32,"original",350,5,20,1200],["fixed-rx4096","fixed",4096,2048,32,"original",350,5,20,1200],["fixed-rx4096-small","fixed",4096,2048,32,"original",350,5,20,288],["fixed-tx1024","fixed",16384,1024,32,"original",350,5,20,1200],["fixed-feedback","fixed",16384,2048,32,"feedback",350,5,20,1200],["fixed-base-last","fixed",16384,2048,32,"original",350,5,20,1200],["normal-clean","normal",16384,2048,32,"original",350,0,20,1200],["game2-fec","game2-fec",16384,2048,32,"original",250,5,20,1200],["game4-fec","game4-fec",16384,2048,32,"original",250,5,20,1200],["auto","auto",16384,2048,32,"original",250,5,80,1200]]
def run_case(env,log,mode):
    # Existing inner mode budget: 240s Game, 690s other V2 scenes.
    # Leave cleanup room, but never continue on a timed-out outer owner.
    budget=320 if mode.startswith("game") else 760
    child=subprocess.Popen([sys.executable,"-u","tools/m0_wl_public_modes_e2e.py"],
                           env=env,stdout=log,stderr=subprocess.STDOUT)
    start=time.monotonic()
    while True:
        remaining=budget-(time.monotonic()-start)
        if remaining<=0:break
        try:return child.wait(timeout=min(30,remaining))
        except subprocess.TimeoutExpired:
            print("WINXDP_UDP_HEARTBEAT mode="+mode+" elapsed_s="+str(int(time.monotonic()-start)),flush=True)
    print("WINXDP_UDP_CASE_TIMEOUT mode="+mode+" budget_s="+str(budget),flush=True)
    if os.name=="nt":
        run_captured(["taskkill.exe","/PID",str(child.pid),"/T","/F"],20)
    if child.poll() is None:child.kill()
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:pass
    return 124

def main():
    global CASES
    if os.environ.get("WBD_XDP_UDP_PHASE")=="small-pps":CASES=[["fixed-rx4096-small","fixed",4096,2048,32,"original",350,5,20,288],["fixed-small8192","fixed",8192,2048,32,"original",350,5,20,288],["fixed-small16384","fixed",16384,2048,32,"original",350,5,20,288],["fixed-small16384-150","fixed",16384,2048,32,"original",150,5,20,288],["fixed-small16384-feedback","fixed",16384,2048,32,"feedback",350,5,20,288]]
    if os.environ.get("WBD_XDP_UDP_PHASE")=="capacity-sweep":CASES=[["fixed-small16384-50","fixed",16384,2048,32,"original",50,5,20,288],["fixed-small16384-100","fixed",16384,2048,32,"original",100,5,20,288],["fixed-small16384-150","fixed",16384,2048,32,"original",150,5,20,288],["fixed-small16384-250","fixed",16384,2048,32,"original",250,5,20,288],["fixed-small16384","fixed",16384,2048,32,"original",350,5,20,288],["fixed-small16384-feedback","fixed",16384,2048,32,"feedback",350,5,20,288],["fixed-small8192","fixed",8192,2048,32,"original",350,5,20,288],["fixed-rx4096-small","fixed",4096,2048,32,"original",350,5,20,288],["fixed-small16384-100-feedback","fixed",16384,2048,32,"feedback",100,5,20,288],["fixed-small16384-100-clean","fixed",16384,2048,32,"original",100,0,20,288],["normal-small-150","normal",16384,2048,32,"original",150,0,20,288],["auto-small-150","auto",16384,2048,32,"original",150,5,20,288],["game2-small-100","game2-fec",16384,2048,32,"original",100,5,20,288],["game4-small-100","game4-fec",16384,2048,32,"original",100,5,20,288]]
    if os.environ.get("WBD_XDP_UDP_PHASE")=="game-batch":CASES=[["game2-fec-1200-0","game2-fec",16384,2048,32,"original",250,5,20,1200],["game2-fec-1200-1","game2-fec",16384,2048,32,"game-batch",250,5,20,1200],["game2-fec-1200-2","game2-fec",16384,2048,32,"game-batch",250,5,20,1200],["game2-fec-1200-3","game2-fec",16384,2048,32,"original",250,5,20,1200],["game2-fec-288-0","game2-fec",16384,2048,32,"original",100,5,20,288],["game2-fec-288-1","game2-fec",16384,2048,32,"game-batch",100,5,20,288],["game2-fec-288-2","game2-fec",16384,2048,32,"game-batch",100,5,20,288],["game2-fec-288-3","game2-fec",16384,2048,32,"original",100,5,20,288],["game4-fec-1200-0","game4-fec",16384,2048,32,"original",250,5,20,1200],["game4-fec-1200-1","game4-fec",16384,2048,32,"game-batch",250,5,20,1200],["game4-fec-1200-2","game4-fec",16384,2048,32,"game-batch",250,5,20,1200],["game4-fec-1200-3","game4-fec",16384,2048,32,"original",250,5,20,1200],["game4-fec-288-0","game4-fec",16384,2048,32,"original",100,5,20,288],["game4-fec-288-1","game4-fec",16384,2048,32,"game-batch",100,5,20,288],["game4-fec-288-2","game4-fec",16384,2048,32,"game-batch",100,5,20,288],["game4-fec-288-3","game4-fec",16384,2048,32,"original",100,5,20,288]]
    if os.environ.get("WBD_XDP_UDP_PHASE")=="game-direction":CASES=[["game2-fec-dir-up","game2-fec",16384,2048,32,"original",100,5,20,288],["game2-fec-dir-down","game2-fec",16384,2048,32,"original",100,5,20,288],["game2-fec-dir-duplex50","game2-fec",16384,2048,32,"original",50,5,20,288],["game2-fec-dir-duplex100","game2-fec",16384,2048,32,"original",100,5,20,288],["game4-fec-dir-up","game4-fec",16384,2048,32,"original",100,5,20,288],["game4-fec-dir-down","game4-fec",16384,2048,32,"original",100,5,20,288],["game4-fec-dir-duplex50","game4-fec",16384,2048,32,"original",50,5,20,288],["game4-fec-dir-duplex100","game4-fec",16384,2048,32,"original",100,5,20,288]]
    rows=[]
    order=list(range(len(CASES)))
    if os.environ["H2478_REPLICA"] in "BDFHJL":order.reverse()
    if os.environ["H2478_REPLICA"]=="S" and os.environ.get("WBD_XDP_UDP_PHASE")!="game-direction":
        order=[0,1,2,3,8,9,10,11] if os.environ.get("WBD_XDP_UDP_PHASE")=="game-batch" else [0,2,4,10,11,12,13] if os.environ.get("WBD_XDP_UDP_PHASE")=="capacity-sweep" else [0,2,3] if os.environ.get("WBD_XDP_UDP_PHASE")=="small-pps" else [0,8,9,10]
    if os.environ.get("WBD_XDP_UDP_PHASE")=="game-batch" and os.environ["H2478_REPLICA"] in "BDFHJL":
        # BAAB inside each reversed four-run group.
        CASES=[[*c[:5],("game-batch" if c[5]=="original" else "original"),*c[6:]] for c in CASES]
    for i in order:
        name,mode,rx,tx,q,policy,rate,loss,delay,size=CASES[i]
        case=E/name;case.mkdir(exist_ok=False)
        path=ROOT/"scenarios"/("xdp-pressure-"+name+".json")
        shutil.copyfile(path,case/"scenario.json")
        expected=read_scenario(path)["scenario_sha256"]
        env=dict(os.environ,WBD_WL_PUBLIC_MODE=mode,WBD_WL_PUBLIC_MODES=mode,WBD_WL_V2_SCENARIO=str(path.relative_to(ROOT)).replace(chr(92),"/"),WBD_XDP_LAB_RX=str(rx),WBD_XDP_LAB_TX=str(tx),WBD_XDP_LAB_QUANTUM=str(q),WBD_XDP_LAB_POLICY=policy)
        for pattern in ("report.json","client.log","server.log","wl-n0-*-app.json","wl-n0-*-app.log","wl-n0-start.flag","gamefec-mode-stack.txt","windows-original-go-rust-process-1hz.jsonl"):
            for p in OUT.glob(pattern):p.unlink(missing_ok=True)
        print("WINXDP_UDP_BEGIN "+json.dumps({"name":name,"mode":mode,"rate":rate,"rx":rx,"tx":tx,"q":q,"policy":policy}),flush=True)
        with (case/"fixture.log").open("w") as log:
            rc=run_case(env,log,mode)
        for pat in ("report.json","client.log","server.log","wl-n0-*-app.json","wl-n0-*-app.log","wl-n0-netem-*.json","wl-v2-linux-tun-*.json","mode-batch.json","gamefec-mode-stack.txt","windows-original-go-rust-process-1hz.jsonl"):
            for p in OUT.glob(pat):
                if p.is_file() and not p.name.endswith("owned.json"):shutil.copyfile(p,case/p.name)
        r=json.loads((case/"report.json").read_text()) if (case/"report.json").exists() else {}
        s=(case/"client.log").read_text(errors="replace") if (case/"client.log").exists() else ""
        def receipts(marker):
            return [{k:int(v) for k,v in re.findall(r"(\w+)=(\d+)",l)} for l in s.splitlines() if marker in l]
        v=r.get("WL_V2",{})
        stats={}
        for role in ("windows","linux"):
            f=case/("wl-n0-"+role+"-app.json")
            if f.exists():
                a=json.loads(f.read_text());stats[role]={k:a.get(k) for k in ("sent_packets","sent_payload_mbps","received_first_packets","received_payload_mbps","duplicate_packets","invalid_packets","max_interdelivery_ms","sender_cpu_pct_one_core","business_udp_rtt","udp_socket_probe_deltas")}
        cpu_cores=None
        try:
            app=json.loads((case/"wl-n0-windows-app.json").read_text())
            start=app["measurement_start_monotonic_s"]; end=app["measurement_end_monotonic_s"]
            samples=[json.loads(l) for l in (case/"windows-original-go-rust-process-1hz.jsonl").read_text().splitlines() if l.strip()]
            samples=[v for v in samples if start+10<=v["monotonic_s"]<=end-5]
            if len(samples)>=2:
                cpu_cores=(samples[-1]["cpu_total_s"]-samples[0]["cpu_total_s"])/(samples[-1]["monotonic_s"]-samples[0]["monotonic_s"])
        except (OSError,ValueError,KeyError,ZeroDivisionError):pass
        delivered=v.get("first_delivered_mbps") or {}
        goodput=sum(delivered.values()) if isinstance(delivered,dict) else 0
        row={"name":name,"mode":mode,"policy":policy,"size":size,"rate":rate,"steady_process_cpu_cores":cpu_cores,
             "cpu_s_per_gib":cpu_cores*8589.934592/goodput if cpu_cores is not None and goodput>0 else None,
             "policy_observed":("WBD_XDP_GAME_BATCH_RECEIPT enabled=1" in s)==(policy=="game-batch"),"rc":rc,"stop":r.get("stop"),"scenario_identity":v.get("scenario_sha256")==expected,
             "status":v.get("status"),"target":v.get("target_mbps"),"offered":v.get("offered_mbps"),"delivered":v.get("first_delivered_mbps"),"first":v.get("first_delivery_fraction"),
             "tx":receipts("WBD_XDP_TX_STOP "),"rx":receipts("WBD_XDP_RX_STOP "),"tx_lab":receipts("WBD_XDP_TX_LAB "),"rx_lab":receipts("WBD_XDP_RX_LAB "),
             "fatal":[l[:500] for l in s.splitlines() if "WBD_WINDOWS_FEC_ARENA_FULL" in l or "WBD_WINDOWS_NATIVE_WORKER_FAILURE" in l],"stats":stats,"tun_fq":r.get("linux_tun_fq_kernel"),"tun_link":r.get("linux_tun_link_kernel")}
        rows.append(row)
        if os.environ.get("WBD_XDP_UDP_PHASE")=="game-batch":
            import statistics
            pair=[x for x in rows if x["mode"]==mode and x["size"]==size]
            if len(pair)==4:
                valid=all(x["rc"]==0 and x["scenario_identity"] and x["policy_observed"] and x["status"]=="MEASURED_BOTH_OS_KERNEL" and x["stop"]=="PASS_BOTH_OWNED" and x["cpu_s_per_gib"] is not None for x in pair)
                result={"mode":mode,"size":size,"valid":valid,"sequence":"".join("A" if x["policy"]=="original" else "B" for x in pair)}
                for arm,pol in (("A","original"),("B","game-batch")):
                    a=[x for x in pair if x["policy"]==pol]
                    result[arm]={"cpu_s_per_gib":statistics.mean(x["cpu_s_per_gib"] for x in a) if all(x["cpu_s_per_gib"] is not None for x in a) else None,"delivered":{k:statistics.mean(x["delivered"][k] for x in a) for k in ("windows","linux") if all(x.get("delivered") and k in x["delivered"] for x in a)}}
                print("WINXDP_GAME_BATCH_ABBA "+json.dumps(result),flush=True)
        (E/"summary.json").write_text(json.dumps(rows,indent=2))
        print("WINXDP_UDP_CASE "+json.dumps(row),flush=True)
        if rc==124 or row["stop"]!="PASS_BOTH_OWNED":
            print("WINXDP_UDP_OWNED_STOP_MISSING "+name+"\n"+(case/"fixture.log").read_text(errors="replace")[-3500:],flush=True)
            break
    return 0 if len(rows)==len(order) and all(x["rc"]==0 and x["scenario_identity"] for x in rows) else 2
if __name__=="__main__":raise SystemExit(main())
