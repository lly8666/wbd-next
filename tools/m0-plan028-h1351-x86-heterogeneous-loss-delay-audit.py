#!/usr/bin/env python3
"""PLAN028 H1351: independent true native Linux weaknet gradient business audit.

The original H1286 180s reporter has unrelated L1 timer expectations; this
L2 ledger reads original app/TUN/OS bins, genuine qdisc and per-VM CPU directly.
Configured random physical loss MUST NOT be reclassified as zero-loss.
"""
import argparse
import json
import pathlib
import re
import statistics

NAMES=("alice","bob","carol","dave","erin")
MODES=("normal","fec-auto","game2","game4","fec-fixed")
SOURCE="6c5fd909b9f42d1af89c698cdaabc79bbb72e589"
LOSS=(0,1,5,15,30)
DELAY=(0,50,150,250,250)
RATES=(9,9,7,7,6)
PHASES=(("first_wave",30,.2),("sustained",60,.35),
        ("overload",30,.5),("recovery",50,.35))

def read(p):
 return json.loads(pathlib.Path(p).read_text())

def assess(root):
 plan=read(root/"h1250-matrix-plan.json")
 assert plan["source_sha"]==SOURCE
 assert plan["network_scope"]=="native Linux x86_64/x86_64 6-netns"
 assert plan["h1351_specialization"]["profile"]=="H1351_REAL_HETEROGENEOUS_0_1_5_15_30PCT_AND_0_50_150_250MS"
 assert [c["who"] for c in plan["clients"]]==list(NAMES)
 assert [c["mode"] for c in plan["clients"]]==list(MODES)
 assert [c["loss_pct"] for c in plan["clients"]]==list(LOSS)
 assert [c["oneway_delay_ms"] for c in plan["clients"]]==list(DELAY)
 assert [c["c2s_target_mbps"] for c in plan["clients"]]==list(RATES)
 assert [(x["name"],x["seconds"],x["rate_scale"]) for x in plan["capacity_phase_schedule"]]==list(PHASES)
 assert plan["application_load_seconds"]==180 and plan["warmup_seconds"]==10
 assert plan["fast_scene"]=="pressure" and not plan["long_scene"]
 assert all(int(x)==600 for x in plan["rotation_seconds"].values())
 assert len(set(x["lease"] for x in plan["clients"]))==5
 for stage in ("installed","after"):
  n=read(root/("h1312-static-neighbour-"+stage+".json"))
  assert n["kind"]=="TEST_ONLY_PHYSICAL_VETH_L2_CONTROL" and n["source_sha"]==SOURCE,stage
  assert n["native_owner_count"]==10 and len(n["entries"])==10,stage
  assert n["data_netem_unchanged"] and not n["product_or_route_key_modified"],stage
  assert all(x["neighbor_state"]=="PERMANENT" and x["lladdr_present"] for x in n["entries"]),stage
 server=(root/"h1250-product-server.log").read_text(errors="replace")
 assert "V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443" in server
 assert "V4_PUBLIC_SHARED_TUN_STOP generation=" in server
 prior=read(root/"h1286-rapid-report.json")
 assert prior["source_sha"]==SOURCE and prior["server_single_port"]==443
 queue=prior["server_per_authenticated_lease_tun"]
 assert set(queue)=={x["lease"] for x in plan["clients"]}
 assert all(q["pending_overflow"]==0 and q["offered"]==q["direct_delivered"] for q in queue.values())
 sample=read(root/"h1301-netem-clock.json")["samples"]
 assert len(sample)>=100
 physical={}
 for direction,key in (("uplink","client_uplink_netem"),("downlink","host_downlink_netem")):
  valid=[row[key] for row in sample if row.get(key,{}).get("kind")=="netem"]
  assert len(valid)>=100
  packets=valid[-1]["packets"]-valid[0]["packets"]
  drops=valid[-1]["drops"]-valid[0]["drops"]
  actual=100*drops/(packets+drops) if packets+drops else 0
  assert packets>1000 and drops>100 and 28<=actual<=32,(direction,packets,drops,actual)
  physical[direction]={"kernel_packets_sent":packets,"kernel_netem_dropped":drops,
                       "real_kernel_loss_pct":round(actual,3)}
 streams={}
 generator_caps=[]
 all_stop=True
 app_error=[]
 total_tcp={}
 for spec in plan["clients"]:
  who=spec["who"]
  c=read(root/("h1250-c-"+who+".json"))
  s=read(root/("h1250-s-"+who+".json"))
  assert c["role"]=="client" and s["role"]=="server"
  assert c["start_ns"]==s["start_ns"]==plan["start_monotonic_ns"]
  assert c["end_ns"]-c["start_ns"]==180_000_000_000
  assert s["end_ns"]-s["start_ns"]==180_000_000_000
  if c["capacity_exceeded"] or s["capacity_exceeded"]:
   generator_caps.append(who)
  if c["errors"] or s["errors"]:
   app_error.append({"who":who,"client":c["errors"],"server":s["errors"]})
  text=(root/("h1250-product-"+who+".log")).read_text(errors="replace")
  lease=re.findall(r"V4_PUBLIC_LEASE_APPLIED role=client.*os_readback=(10\.66\.0\.\d+)/32",text)
  assert lease and set(lease)=={spec["lease"]},(who,lease,spec["lease"])
  valid_stop="V4_PUBLIC_SHARED_TUN_STOP generation=" in text
  all_stop=all_stop and valid_stop
  assert ("V4_ORIGINAL_GO_GAME_NATIVE_READY role=client" in text if who in ("carol","dave")
          else "V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client" in text),who
  streams[who]=(c,s,spec)
  if who in ("alice","bob"):
   rows={}
   for direction,tx,rx in (("uplink",c,s),("downlink",s,c)):
    count_tx=sum(x["tx_packets"] for x in tx["stats"]["tcp"])
    count_rx=sum(x["rx_packets"] for x in rx["stats"]["tcp"])
    rows[direction]={"framed_sent":count_tx,"framed_received":count_rx,
                     "pending_at_deadline":tx["tcp_pending_at_deadline"]}
    if count_tx==0 or count_rx!=count_tx or tx["tcp_pending_at_deadline"]:
     app_error.append({"who":who,"direction":direction,"true_TCP":rows[direction]})
   total_tcp[who]=rows
 phases=[]
 fill_errors=[]
 loss_error=[]
 start=10
 for name,duration,scale in PHASES:
  a,b=start*100,(start+duration)*100
  ticks=[q for q in sample if start*1000000000<=q["mono_ns"]-plan["start_monotonic_ns"]
         <(start+duration)*1000000000]
  busy=[];soft=[];percore={}
  for first,last in zip(ticks,ticks[1:]):
   for core,left in first.get("host_core_jiffies",{}).items():
    right=last.get("host_core_jiffies",{}).get(core)
    if right is None:continue
    delta=[v-u for u,v in zip(left,right)]
    total=sum(delta)
    if total<=0:continue
    val=100*(total-delta[3]-delta[4])/total
    busy.append(val)
    soft.append(100*delta[6]/total)
    percore.setdefault(core,[]).append(val)
  assert len(busy)>=40 and len(percore)>=1,(name,len(busy))
  row={"phase":name,"seconds":[start,start+duration],"rate_scale":scale,
       "actual_vm_logical_cores":len(percore),
       "host_busy_mean_pct":round(statistics.mean(busy),2),
       "host_softirq_mean_pct":round(statistics.mean(soft),2),
       "per_core_busy_mean_pct":{key:round(statistics.mean(v),2) for key,v in sorted(percore.items())},
       "client_app":{}}
  for who,(c,s,spec) in streams.items():
   row["client_app"][who]={}
   for direction,tx,rx in (("uplink",c,s),("downlink",s,c)):
    payload={}
    for protocol in ("udp","tcp"):
     sent=sum(tx["tx_bytes_bins_10ms"][protocol][a:b])
     received=sum(rx["rx_bytes_bins_10ms"][protocol][a:b])
     payload[protocol]={"actual_sent_mbps":round(sent*8/duration/1e6,3),
                        "actual_received_mbps":round(received*8/duration/1e6,3),
                        "delivered_fraction":round(received/sent,5) if sent else None}
    offered=sum(payload[p]["actual_sent_mbps"] for p in ("udp","tcp"))
    target=spec["c2s_target_mbps"]*scale
    fill=round(offered/target,4)
    if fill<.95:fill_errors.append({"phase":name,"who":who,"direction":direction,"actual_fill":fill})
    udp_fraction=payload["udp"]["delivered_fraction"]
    if udp_fraction is None or udp_fraction<.95:
     loss_error.append({"phase":name,"who":who,"direction":direction,
                        "actual_udp_delivery_fraction":udp_fraction})
    row["client_app"][who][direction]={"expected_inner_mbps":round(target,3),
         "actual_offered_mbps":round(offered,3),"fill_fraction":fill,**payload}
  phases.append(row)
  start+=duration
 assert start==180
 gaps={}
 for who in NAMES:
  directions=prior["clients"][who]["directions"]
  gaps[who]={direction:directions[direction]["largest_10ms_bucket_no_receive_while_sender_active_ms"]
             for direction in ("uplink","downlink")}
  if any(g>=750 for g in gaps[who].values()):
   loss_error.append({"who":who,"native_app_gap_ms":gaps[who]})
 near_limit=[{"phase":p["phase"],"host_busy_mean_pct":p["host_busy_mean_pct"]}
             for p in phases if p["host_busy_mean_pct"]>=95
              or any(q>=95 for q in p["per_core_busy_mean_pct"].values())]
 stable=not app_error and not loss_error and all_stop
 if not stable:
  label="FAIL_REAL_APP_RECOVERY_OR_OWNER_IN_WEAKNET"
 elif generator_caps or fill_errors:
  label="CAPACITY_LIMITED_OR_GENERATOR_LIMITED"
 elif near_limit:
  label="HOST_NEAR_LIMIT_WEAKNET_VM"
 else:
  label="PASS_SCOPED_NATIVE_X86_REAL_LOSS_0_1_5_15_30_AND_DELAY_0_50_150_250"
 return {"schema_version":1,"source_sha":SOURCE,
  "original_product_source_sha":SOURCE,
  "kind":"H1351_ORIGINAL_TLS_RUST_L2_NATIVE_OS_LOSS_DELAY_GRADIENT",
  "rotation_not_triggered_by_design":"600s timers, 180s app; not L1 proof",
  "original_native_server443":True,"auth_user_count":5,
  "observed_VM_logical_cores_each_phase":[p["actual_vm_logical_cores"] for p in phases],
  "physical_loss_pct_configured":list(LOSS),"oneway_delay_ms_configured":list(DELAY),
  "real_Erin_30pct_qdisc":physical,"test_only_real_veth_ARP_10of10":True,
  "actual_UDP_app_phases":phases,"real_TCP_framed_alice_bob":total_tcp,
  "max_active_send_without_receive_ms":gaps,
  "all_five_exact_final_Stop":all_stop,"server_shared_TUN_exact_Stop":True,
  "per_client_server_pending_queue":queue,
  "generator_capacity_exceeded":generator_caps,"target_fill_below_95pct":fill_errors,
  "real_app_errors":app_error,"real_udp_delivery_or_gap_failures":loss_error,
  "hot_guest_CPU":near_limit,
  "measurement_complete":True,"real_business_stability_pass":stable,
  "classification":label,"limitations":[
   "Actual 30% kernel qdisc loss is expected physical impairment, not application data loss",
   "Only Erin external qdisc sampled at 500ms; other physical tc rates are configured in independent veth qdiscs",
   "Linux hosted native x86 VM guest vCPU/softirq is not Windows/ARM64 capacity",
   "Original TLS/Rust ISA-L unchanged binary source; L1 rotations parked and L3 not run",
   "p99 is receive-only original same-runner data; no cross-device clock comparison"]}

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--art",required=True)
 ap.add_argument("--out",required=True)
 args=ap.parse_args()
 result=assess(pathlib.Path(args.art))
 pathlib.Path(args.out).write_text(json.dumps(result,indent=2)+"\n")
 print("M0_PLAN028_H1351_NATIVE_HETEROGENEOUS_TRUE_WEAKNET_OBSERVED",
       result["classification"],
       [(p["phase"],p["host_busy_mean_pct"]) for p in result["actual_UDP_app_phases"]],flush=True)

if __name__=="__main__":
 main()
