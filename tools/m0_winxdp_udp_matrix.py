"""Original real product V2 UDP application; separate same-runner receipts.
Keep observed offered rates distinct from target. No product/protocol edits.
"""
import json,os,pathlib,re,shutil,subprocess,sys
from m0_wl_perf_v2_config import read_scenario
ROOT=pathlib.Path.cwd()
OUT=ROOT/"result/wl-public"; E=ROOT/"result/winxdp-udp-matrix"; E.mkdir(parents=True,exist_ok=True)
CASES=[["fixed-base-first","fixed",16384,2048,32,"original",350,5,20,1200],["fixed-rx8192","fixed",8192,2048,32,"original",350,5,20,1200],["fixed-rx4096","fixed",4096,2048,32,"original",350,5,20,1200],["fixed-rx4096-small","fixed",4096,2048,32,"original",350,5,20,288],["fixed-tx1024","fixed",16384,1024,32,"original",350,5,20,1200],["fixed-feedback","fixed",16384,2048,32,"feedback",350,5,20,1200],["fixed-base-last","fixed",16384,2048,32,"original",350,5,20,1200],["normal-clean","normal",16384,2048,32,"original",350,0,20,1200],["game2-fec","game2-fec",16384,2048,32,"original",250,5,20,1200],["game4-fec","game4-fec",16384,2048,32,"original",250,5,20,1200],["auto","auto",16384,2048,32,"original",250,5,80,1200]]
def main():
    global CASES
    if os.environ.get("WBD_XDP_UDP_PHASE")=="small-pps":CASES=[["fixed-rx4096-small","fixed",4096,2048,32,"original",350,5,20,288],["fixed-small8192","fixed",8192,2048,32,"original",350,5,20,288],["fixed-small16384","fixed",16384,2048,32,"original",350,5,20,288],["fixed-small16384-150","fixed",16384,2048,32,"original",150,5,20,288],["fixed-small16384-feedback","fixed",16384,2048,32,"feedback",350,5,20,288]]
    rows=[]
    order=list(range(len(CASES)))
    if os.environ["H2478_REPLICA"] in "BDFHJL":order.reverse()
    if os.environ["H2478_REPLICA"]=="S":order=[0,2,3] if os.environ.get("WBD_XDP_UDP_PHASE")=="small-pps" else [0,8,9,10]
    for i in order:
        name,mode,rx,tx,q,policy,rate,loss,delay,size=CASES[i]
        case=E/name;case.mkdir(exist_ok=False)
        path=ROOT/"scenarios"/("xdp-pressure-"+name+".json")
        shutil.copyfile(path,case/"scenario.json")
        expected=read_scenario(path)["scenario_sha256"]
        env=dict(os.environ,WBD_WL_PUBLIC_MODE=mode,WBD_WL_PUBLIC_MODES=mode,WBD_WL_V2_SCENARIO=str(path.relative_to(ROOT)).replace(chr(92),"/"),WBD_XDP_LAB_RX=str(rx),WBD_XDP_LAB_TX=str(tx),WBD_XDP_LAB_QUANTUM=str(q),WBD_XDP_LAB_POLICY=policy)
        for pattern in ("report.json","client.log","server.log","wl-n0-*-app.json","wl-n0-*-app.log","wl-n0-start.flag"):
            for p in OUT.glob(pattern):p.unlink(missing_ok=True)
        print("WINXDP_UDP_BEGIN "+json.dumps({"name":name,"mode":mode,"rate":rate,"rx":rx,"tx":tx,"q":q,"policy":policy}),flush=True)
        with (case/"fixture.log").open("w") as log:
            rc=subprocess.run([sys.executable,"-u","tools/m0_wl_public_modes_e2e.py"],env=env,stdout=log,stderr=subprocess.STDOUT).returncode
        for pat in ("report.json","client.log","server.log","wl-n0-*-app.json","wl-n0-*-app.log","wl-n0-netem-*.json","wl-v2-linux-tun-*.json","mode-batch.json"):
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
        row={"name":name,"mode":mode,"rc":rc,"stop":r.get("stop"),"scenario_identity":v.get("scenario_sha256")==expected,
             "status":v.get("status"),"offered":v.get("offered_mbps"),"delivered":v.get("first_delivered_mbps"),"first":v.get("first_delivery_fraction"),
             "tx":receipts("WBD_XDP_TX_STOP "),"rx":receipts("WBD_XDP_RX_STOP "),"tx_lab":receipts("WBD_XDP_TX_LAB "),"rx_lab":receipts("WBD_XDP_RX_LAB "),
             "fatal":[l[:500] for l in s.splitlines() if "WBD_WINDOWS_FEC_ARENA_FULL" in l or "WBD_WINDOWS_NATIVE_WORKER_FAILURE" in l],"stats":stats,"tun_fq":r.get("linux_tun_fq_kernel"),"tun_link":r.get("linux_tun_link_kernel")}
        rows.append(row)
        (E/"summary.json").write_text(json.dumps(rows,indent=2))
        print("WINXDP_UDP_CASE "+json.dumps(row),flush=True)
        if row["stop"]!="PASS_BOTH_OWNED":
            print("WINXDP_UDP_OWNED_STOP_MISSING "+name+"\n"+(case/"fixture.log").read_text(errors="replace")[-3500:],flush=True)
            break
    return 0 if len(rows)==len(order) and all(x["rc"]==0 and x["scenario_identity"] for x in rows) else 2
if __name__=="__main__":raise SystemExit(main())
