#!/usr/bin/env python3
"""Offline native Go/Rust original 600s M4 evidence; never rerun network.
A Normal B is accepted ONLY after original server B_PENDING -> B_CLIENT_READY,
authenticated native Health and unique original TCP source port.
"""
import argparse,json,pathlib,re
NAMES=("alice","bob","carol","dave","erin")
NORMAL=("alice","bob","erin")
def load(p):return json.loads(p.read_text())
def proof(art,scene,source,band_min=100):
    plan=load(art/"h1250-matrix-plan.json")
    result=load(art/"h1461-six-hundred-report.json")
    measured_file=art/"h1520-verdict.json"
    measured=load(measured_file) if measured_file.is_file() else None
    observer=load(art/"h1520-outer-observer.json")
    assert plan["source_sha"]==result["source_sha"]==observer["original_product_source_sha"]==source
    assert observer["status"]=="MEASURED_REAL_KERNEL"
    assert band_min in (100,300)
    if band_min==300:
        assert plan["H1531_outer_600_profile"]=="outer300to350-"+scene
        assert plan["H1531_outer_target_mbps_total_both_directions"]==[300,350]
    else:
        assert plan["H1520_outer_600_profile"]=="outer100to150-"+scene
    assert result["duration_seconds"]==600
    server=(art/"h1250-product-server.log").read_text(errors="replace")
    lines=server.splitlines()
    init={(ip,int(p)) for ip,p in re.findall(
      r"V4_PUBLIC_MIXED_NORMAL_READY role=server port=443 client_ipv4=([\d.]+) client_port=(\d+)",server)}
    def stage(fragment):
        out={}
        for ix,line in enumerate(lines):
            if fragment not in line:continue
            m=re.search(r"\bclient_port=(\d+)\b",line)
            if m:out.setdefault(int(m.group(1)),[]).append((ix,line))
        return out
    pending=stage("V4_PUBLIC_MIXED_NORMAL_B_PENDING role=server")
    confirmed=stage("V4_PUBLIC_MIXED_NORMAL_B_CLIENT_READY role=server")
    denied=set(stage("V4_PUBLIC_MIXED_NORMAL_B_UNPROVEN"))|set(stage("V4_PUBLIC_MIXED_NORMAL_B_PROMOTE_REJECT"))
    all_ports={}
    reviewed={}
    faults=[]
    for who in NORMAL:
        log=(art/("h1250-product-"+who+".log")).read_text(errors="replace")
        gens=[(int(g),ip,int(p)) for g,ip,p in re.findall(
         r"V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=(\d+).*?client_ipv4=([\d.]+) client_port=(\d+)",log)]
        old=[int(x) for x in re.findall(r"V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=(\d+)",log)]
        if len(gens)<5 or old!=[g for g,_,_ in gens[:-1]]:
            faults.append(who+"_not_enough_ready_or_old_exact_stop")
        for gen,ip,p in gens:
            if p in all_ports:faults.append("shared_client_port_collision_"+str(p))
            all_ports[p]=(who,gen,ip)
        first=bool(gens and (gens[0][1],gens[0][2]) in init)
        if not first:faults.append(who+"_initial_M4_missing")
        bb=[]
        for gen,ip,p in gens[1:]:
            pn=pending.get(p,[]);ok=confirmed.get(p,[])
            valid=(len(pn)==len(ok)==1 and pn[0][0]<ok[0][0]
              and "source=authenticated_client_native_Health promoted=1" in ok[0][1]
              and p not in denied)
            if not valid:faults.append(who+"_B_server_M4_unproven_gen"+str(gen)+"_port"+str(p))
            bb.append({"gen":gen,"ip":ip,"port":p,"server_B_pending":len(pn),
               "server_authenticated_native_M4":len(ok),"valid":valid})
        reviewed[who]={"initial_exact_M4":first,"B_promotions":bb,
          "old_exact_stop":old,"client_generation_count":len(gens),
          "fully_auth_server_M4":first and all(x["valid"] for x in bb)}
    stops={}
    for role in ("server",)+NAMES:
        path=art/("h1250-product-"+role+".log")
        stops[role]=path.exists() and "V4_PUBLIC_SHARED_TUN_STOP generation=" in path.read_text(errors="replace")
    if not all(stops.values()):faults.append("missing_one_of_six_original_owned_stops")
    progress={}
    loss=30 if scene=="loss30" else 0
    for who in NAMES:
        client=result["clients"][who]
        if who not in NORMAL and client["rotation"]["result"]!="PASS_SCOPED":
            faults.append(who+"_game_native_M4_not_proven")
        for direction,leg in client["directions"].items():
            sent=sum(int(x["actual_udp_sent"]) for x in leg["phases"])
            got=sum(int(x["unique_udp_delivered"]) for x in leg["phases"])
            tcp=leg["true_tcp"]
            gap=int(leg["largest_10ms_bucket_no_receive_while_sender_active_ms"])
            progress[who+"_"+direction]={"sent":sent,"unique_received":got,
                "max_active_rx_gap_ms":gap,"tcp_received":tcp["framed_app_received"]}
            if sent==0 or got==0 or gap>=750:faults.append(who+"_"+direction+"_no_real_progress_or_gap")
            if loss==0 and got!=sent:faults.append(who+"_"+direction+"_zero_loss_missing")
            if loss==30 and got/sent<.4:faults.append(who+"_"+direction+"_30pct_loss_too_many_missing")
            if who in ("alice","bob") and tcp["framed_app_received"]<=0:
                faults.append(who+"_"+direction+"_real_tcp_missing")
    for a in result.get("alerts",[]):
        k=a.get("kind")
        if k in ("CLIENT_NORMAL_READY_WITHOUT_SERVER_NATIVE_M4","ROTATION_CONTINUITY_NOT_PROVEN") and (
             a.get("who") in NORMAL and reviewed[a["who"]]["fully_auth_server_M4"]):continue
        if k=="RECOVERY_DELIVERY_BELOW_95PCT" and loss==30:continue
        faults.append("unexplained_original_alert_"+str(a))
    samples=[json.loads(x) for x in (art/"h1520-outer-10s.jsonl").read_text().splitlines() if x.strip()]
    steady=[x for x in samples if x["phase"] in ("sustained","recovery") and x["sample_seconds"]>=8]
    if len(steady)<28:faults.append("insufficient_original_kernel_outer_10s_receipts")
    mean=round(sum(x["total_outer_mbps"] for x in steady)/len(steady),3) if steady else 0
    in_band=sum(band_min<=x["total_outer_mbps"]<=band_min+50 for x in steady)
    fraction=in_band/len(steady) if steady else 0
    band=(band_min<=mean<=band_min+50 and fraction>=.7)
    if not any(x["up_mbps"]>=40 and x["down_mbps"]>=40 for x in steady):
        faults.append("original_outer_physical_duplex_not_substantive")
    classification=("FAIL_REAL_NATIVE_OWNER_OR_BUSINESS" if faults else
      "PASS_SCOPED_REAL_NATIVE_600S_BUSINESS_AND_OUTER_"+str(band_min)+"_"+str(band_min+50) if band else
      "PASS_SCOPED_REAL_NATIVE_600S_BUSINESS_OUTER_TARGET_UNMET")
    return {"scene":scene,"source_sha":source,"classification":classification,
      "real_full_outer_both_directions_mean_mbps":mean,"band_target":[band_min,band_min+50],
      "band_100_150_pass":band if band_min==100 else None,"target_band_pass":band,
      "steady_10s_kernel_windows":len(steady),"windows_in_target":in_band,
      "server_B_pending_total":sum(len(x) for x in pending.values()),
      "server_B_authenticated_M4_confirmed_total":sum(len(x) for x in confirmed.values()),
      "normal_client_per_generation_original_Health_proof":reviewed,
      "original_udp_tcp_delivery":progress,"all_six_stop":stops,
      "hard_faults":faults,
      "original_false_reporter_hard_errors_preserved":measured["hard_errors"] if measured else None,
      "original_reporter_alerts_preserved":result.get("alerts"),
      "not_real_network_rerun":True}
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--art",type=pathlib.Path,required=True)
    ap.add_argument("--scene",required=True,choices=("loss0","loss30"))
    ap.add_argument("--source",required=True)
    ap.add_argument("--out",type=pathlib.Path,required=True)
    ap.add_argument("--band-min",type=int,choices=(100,300),default=100)
    ap.add_argument("--strict-band",action="store_true")
    a=ap.parse_args()
    x=proof(a.art,a.scene,a.source,a.band_min)
    a.out.parent.mkdir(exist_ok=True,parents=True)
    a.out.write_text(json.dumps(x,indent=2)+"\n")
    print("H1525_EXACT_NATIVE_SERVER_HEALTH_M4_REPLAY "+json.dumps({
        "scene":a.scene,"classification":x["classification"],
        "real_outer_mbps":x["real_full_outer_both_directions_mean_mbps"],
        "server_B_proof":{n:{"ok":z["fully_auth_server_M4"],
          "count":len(z["B_promotions"])} for n,z in x["normal_client_per_generation_original_Health_proof"].items()},
        "hard_faults":x["hard_faults"],"six_stop":x["all_six_stop"]},sort_keys=True),flush=True)
    if x["hard_faults"] or (a.strict_band and not x["target_band_pass"]):raise SystemExit(1)
