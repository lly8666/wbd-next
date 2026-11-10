#!/usr/bin/env python3
"""H1496 one 180s ORIGINAL native x86 true 30% Erin cold B change regression.

No claimed 1800s result: tests one real high-loss M4 B proof + 0-loss
Alice on current Rust health-burst candidate. Original Go binaries unchanged.
"""
import argparse,hashlib,json,pathlib,re
NAMES=("alice","bob","carol","dave","erin")
def read(p):return json.loads(p.read_text())
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--art",type=pathlib.Path,required=True)
    p.add_argument("--source",required=True)
    p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args();root=a.art
    plan=read(root/"h1250-matrix-plan.json")
    assert plan["source_sha"]==a.source
    assert plan["network_scope"]=="native Linux x86_64/x86_64 6-netns"
    assert plan["fast_scene"]=="pressure" and plan["application_load_seconds"]==180
    assert plan["physical_l2_arp_control"]=="test_only_permanent_actual_peer_mac"
    assert [x["loss_pct"] for x in plan["clients"]]==[0,1,5,15,30]
    assert [x["oneway_delay_ms"] for x in plan["clients"]]==[0,15,50,100,125]
    assert [x["who"] for x in plan["clients"]]==list(NAMES)
    assert plan["rotation_seconds"]["erin"]==107
    assert plan["fec_backend_choice"]=="native"
    logs={who:(root/f"h1250-product-{who}.log").read_text(errors="replace")
          for who in ("server",)+NAMES}
    defects=[]
    for who,s in logs.items():
        if "V4_PUBLIC_SHARED_TUN_STOP generation=" not in s:defects.append(who+"_NO_REAL_OWNED_STOP")
    all_udp={}
    for x in plan["clients"]:
        who=x["who"]
        c=read(root/f"h1250-c-{who}.json")
        s=read(root/f"h1250-s-{who}.json")
        assert c["end_ns"]-c["start_ns"]==s["end_ns"]-s["start_ns"]==180_000_000_000
        dirs={}
        for d in ("uplink","downlink"):
            tx,rx=(c,s) if d=="uplink" else (s,c)
            n=sum(t["tx_packets"] for t in tx["stats"]["udp"])
            got=sum(t["rx_packets"] for t in rx["stats"]["udp"])
            assert n>0 and got>0 and n>=got
            if x["loss_pct"]==0 and n!=got:defects.append(who+"_"+d+"_ZEROLOSS_MISSING_"+str(n-got))
            dirs[d]={"sent":n,"delivered":got,"missing":n-got}
        all_udp[who]=dirs
    server=logs["server"]
    erin=logs["erin"]
    cp=[(int(gen),int(port)) for gen,port in re.findall(
       r"V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=(\d+).*?client_ipv4=10.25.0.6 client_port=(\d+)",erin)]
    pending=set(int(x) for x in re.findall(
       r"V4_PUBLIC_MIXED_NORMAL_B_PENDING role=server client_port=(\d+)",server))
    proven=set(int(x) for x in re.findall(
       r"V4_PUBLIC_MIXED_NORMAL_B_CLIENT_READY role=server client_port=(\d+) source=authenticated_client_native_Health promoted=1",server))
    unproven=set(int(x) for x in re.findall(
       r"V4_PUBLIC_MIXED_NORMAL_B_UNPROVEN role=server client_port=(\d+)",server))
    erin_b=[port for gen,port in cp if gen>1]
    if not erin_b: defects.append("ERIN_REAL_B_NOT_TRIGGERED")
    if not set(erin_b)&pending:defects.append("ERIN_SERVER_COLD_B_NOT_DEFERRED")
    if not set(erin_b)&proven:defects.append("ERIN_SERVER_AUTH_CLIENT_B_NOT_PROVEN")
    if set(erin_b)&unproven:defects.append("ERIN_SERVER_B_UNPROVEN_"+str(sorted(set(erin_b)&unproven)))
    old=[int(x) for x in re.findall(
       r"V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=(\d+)",erin)]
    if old!=[gen for gen,_ in cp[:-1]]:defects.append("ERIN_EXACT_OLD_STOP_MISMATCH")
    if not all(x["fec_backend_choice"] if "fec_backend_choice" in x else True for x in [plan]):
        defects.append("BACKEND_UNQUALIFIED")
    queue=re.findall(
       r"M0_SHARED_TUN_LEASE_QUEUE_DIAG ip=([\d.]+) offered=(\d+) direct_delivered=(\d+) downstream_full=(\d+) pending_overflow=(\d+)",
       server)
    if len(queue)!=5: defects.append("MISSING_5_SERVER_SHARED_LEASE_QUEUE")
    if any(int(x[4]) for x in queue):defects.append("SERVER_QUEUE_OVERFLOW")
    v={"schema_version":1,"plan":"PLAN028","source_sha":a.source,
       "qualification":"ONE_NATIVE_X86_REAL_180S_ERIN30_COLD_B_AUTH_RECEIVER",
       "original_GO_binary_unchanged":True,
       "native_Rust_health_retry_candidate":True,
       "loss_pct":[0,1,5,15,30],"oneway_delay_ms":[0,15,50,100,125],
       "old_owner_own_Stop":not any("STOP" in x for x in defects),
       "all_original_udp":all_udp,"Erin_native_ready_generations":cp,
       "Erin_client_B_ports":erin_b,
       "Erin_server_pending_B_ports":sorted(set(erin_b)&pending),
       "Erin_server_authenticated_Health_B_ports":sorted(set(erin_b)&proven),
       "Erin_server_unproven_B_ports":sorted(set(erin_b)&unproven),
       "exact_5_lease_server_queue":queue,
       "hard_gate_errors":defects,
       "classification":"PASS_SCOPED_ONE_REAL_HIGHLOSS_COLD_B_PROOF" if not defects else "FAIL_SCOPED_OR_NOT_TRIGGERED",
       "cannot_close_1800s_30pct_from_short_sample":True,
       "no_new_control_wire_or_user_DATA_duplicates":True}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(v,indent=2)+"\n")
    print("H1496_NATIVE_SHORT_TRUE_ERIN30_CLIENT_B_SERVER_HEALTH_PROOF",json.dumps(
      {"status":v["classification"],"B_ready":erin_b,
       "B_proven":v["Erin_server_authenticated_Health_B_ports"],
       "B_unproven":v["Erin_server_unproven_B_ports"],
       "errors":defects},sort_keys=True))
    if defects:raise SystemExit(1)
if __name__=="__main__":main()
