#!/usr/bin/env python3
"""H1357 L1 source-locked five-client genuine Go TLS443 native Rust two+
handover gate: actual Game2 Fixed6 original M4, owner, true duplex app.
"""
import argparse,json,pathlib,re
SOURCE="24e1fe6c4eab2a1abb7fb8a6d2093abaf57c0f73"
NAMES=("alice","bob","carol","dave","erin")
MODES=("normal","fec-auto","game2","game4","fec-fixed")
def load(path):return json.loads(path.read_text())
def gap_ms(tx,rx):
    cur=maximal=0
    for sent,received in zip(tx[:18000],rx[:18000]):
        cur=cur+1 if sent and not received else 0
        maximal=max(maximal,cur)
    return maximal*10
def assess(root):
    plan=load(root/"h1250-matrix-plan.json")
    spec=plan["h1357_specialization"]
    assert plan["source_sha"]==SOURCE==spec["original_product_source"]
    assert plan["network_scope"]=="native Linux aarch64/aarch64 6-netns"
    assert plan["server_port"]==443 and plan["application_load_seconds"]==180
    assert [c["who"] for c in plan["clients"]]==list(NAMES)
    assert [c["mode"] for c in plan["clients"]]==list(MODES)
    assert [c["loss_pct"] for c in plan["clients"]]==[0]*5
    assert [c["oneway_delay_ms"] for c in plan["clients"]]==[0,10,20,30,0]
    assert plan["rotation_seconds"]=={"alice":97,"bob":101,"carol":103,"dave":89,"erin":107}
    for stage in ("installed","after"):
        n=load(root/("h1312-static-neighbour-"+stage+".json"))
        assert n["native_owner_count"]==10
        assert all(x["neighbor_state"]=="PERMANENT" for x in n["entries"])
    prior=load(root/"h1286-rapid-report.json")
    assert prior["source_sha"]==SOURCE and prior["server_single_port"]==443
    server=(root/"h1250-product-server.log").read_text(errors="replace")
    assert "V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443" in server
    assert "V4_PUBLIC_SHARED_TUN_STOP generation=" in server
    assert "V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=2 mode=fixed profile=6" in server
    assert "V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=4 mode=off profile=0" in server
    # Game4 Off has no FEC backend readback; require original Off mode instead.
    errors=[];capacity=[];rotation={};business={};stop=True
    for csp in plan["clients"]:
        who=csp["who"];c=load(root/("h1250-c-"+who+".json"));s=load(root/("h1250-s-"+who+".json"))
        if c["errors"] or s["errors"]:errors.append({"who":who,"app_errors":[c["errors"],s["errors"]]})
        if c["capacity_exceeded"] or s["capacity_exceeded"]:capacity.append(who)
        assert c["start_ns"]==s["start_ns"]==plan["start_monotonic_ns"]
        assert c["end_ns"]-c["start_ns"]==180_000_000_000
        assert s["end_ns"]-s["start_ns"]==180_000_000_000
        log=(root/("h1250-product-"+who+".log")).read_text(errors="replace")
        stop=stop and "V4_PUBLIC_SHARED_TUN_STOP generation=" in log
        assert "V4_PUBLIC_LEASE_APPLIED role=client" in log
        if who=="carol":
            assert "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=2 mode=fixed profile=6" in log
            assert "V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes=2" in log
        if who=="dave":
            assert "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=off profile=0" in log
        r=prior["clients"][who]["rotation"]
        rotation[who]=r
        if r["result"]!="PASS_SCOPED":
            errors.append({"who":who,"rotation":r})
        if who=="dave":
            if (r.get("single_lane_successful",0)<2 or
                r.get("native_server_confirmed_hot_slots",0)<2 or
                sum(v>0 for v in r.get("per_lane_success",{}).values())<2):
                errors.append({"who":who,"single_lane_real_handover_shortfall":r})
        else:
            gens=r["authenticated_generation_sequence"]
            stops=r["old_generation_stop_sequence"]
            if len(gens)<3 or stops!=gens[:-1] or r.get("server_normal_m4_rejections"):
                errors.append({"who":who,"two_owned_handovers_missing":r})
        business[who]={}
        for direction,tx,rx in (("uplink",c,s),("downlink",s,c)):
            sent=tx["tx_bytes_bins_10ms"]["udp"];got=rx["rx_bytes_bins_10ms"]["udp"]
            assert len(sent)==len(got)==19001
            a=sum(sent[:18000]);b=sum(got[:18000])
            frac=b/a if a else 0
            gap=gap_ms(sent,got)
            row={"actual_udp_sent_bytes":a,"actual_udp_received_bytes":b,
                 "delivered_fraction":round(frac,5),"max_active_no_receive_gap_ms":gap}
            if a<100000 or frac<.995 or gap>=750:
                errors.append({"who":who,"direction":direction,"business_failure":row})
            business[who][direction]=row
        if who in ("alice","bob"):
            for direction,tx,rx in (("uplink",c,s),("downlink",s,c)):
                count=sum(x["tx_packets"] for x in tx["stats"]["tcp"])
                recv=sum(x["rx_packets"] for x in rx["stats"]["tcp"])
                if count<1 or count!=recv or tx["tcp_pending_at_deadline"]:
                    errors.append({"who":who,"direction":direction,"framed_TCP":(count,recv,tx["tcp_pending_at_deadline"])})
    if not stop:errors.append({"owned_stop":"missing"})
    queue=prior["server_per_authenticated_lease_tun"]
    if set(queue)!={c["lease"] for c in plan["clients"]}:
        errors.append({"server_leases":"missing"})
    if any(q["pending_overflow"]!=0 or q["offered"]!=q["direct_delivered"] for q in queue.values()):
        errors.append({"server_per_lease_queue":queue})
    classification=("FAIL_L1_OWNER_BUSINESS_OR_CONFIG" if errors else
                    "CAPACITY_LIMITED" if capacity else
                    "PASS_SCOPED_NATIVE_ARM64_GAME4_OFF_TWO_REAL_ROTATIONS_FIVE_CLIENT")
    return {"schema_version":1,"classification":classification,
      "source_sha":SOURCE,"wrapper_source":spec["wrapper_source"],
      "original_single_tls_port":443,"five_auth_clients":list(NAMES),
      "true_Carol_game2_fixed6_and_Dave_game4_off":True,
      "real_authenticated_owner_rotations":rotation,
      "original_native_duplex_business":business,
      "all_exact_final_stop":stop,"five_per_lease_queue":queue,
      "native_app_or_owner_errors":errors,"capacity_limit_clients":capacity,
      "raw_original_report_alerts":prior["alerts"],
      "limits":["No independent two physical paths: unchanged native veth only; ARM64 scalar FEC backend for Carol",
                "Only Dave Game4 Off newly checked at native ARM64 source24e1; not identical to x86 binary source6c5",
                "Only two-plus timed handovers for five users, Game4 separate live slot unit",
                "Linux native ARM64 hosted, not Windows/physical WAN/1800s"]}
def main():
    p=argparse.ArgumentParser();p.add_argument("--art",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();r=assess(pathlib.Path(a.art))
    pathlib.Path(a.out).write_text(json.dumps(r,indent=2)+"\n")
    print("M0_PLAN028_H1357_NATIVE_ARM64_L1_TRUE_GAME4_OFF_AND_FIVE_OWNER_ROTATIONS",
          r["classification"],flush=True)
if __name__=="__main__":
    main()
