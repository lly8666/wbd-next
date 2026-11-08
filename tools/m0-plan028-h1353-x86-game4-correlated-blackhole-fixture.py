#!/usr/bin/env python3
"""H1353: source-locked original Go TLS443/Rust Game4 common-underlay blackhole."""
import json,os,pathlib,runpy,sys
SOURCE="6c5fd909b9f42d1af89c698cdaabc79bbb72e589"
RATES=(4,4,3,6,3)
LOSSES=(0,0,0,0,0)
DELAYS=(0,50,100,150,0)
PHASES=(("first_wave",30,.2),("sustained",60,.35),
        ("overload",30,.5),("recovery",50,.35))
def main():
    assert len(sys.argv)==2
    for key,val in (("WBD_PLAN028_FAST_SCENE","pressure"),
        ("WBD_PLAN028_FAST_CAPACITY_STEPS","2"),
        ("WBD_PLAN028_QDISC_CLOCK_DIAG","1"),
        ("WBD_PLAN028_STATIC_OWNED_NEIGH","1"),
        ("WBD_PLAN028_GAME4_CORRELATED_BLACKHOLE","1")):
        assert os.environ.get(key)==val,key
    context=runpy.run_path("tools/m0-plan028-h1259-five-client-recovery-netns.py",
                           run_name="h1353_no_main")
    fn=context["main"];g=fn.__globals__
    assert g["CORRELATED_GAME4_BLACKHOLE"]=="1"
    assert g["NAMES"]==("alice","bob","carol","dave","erin")
    assert g["MODES"]==("normal","fec-auto","game2","game4","fec-fixed")
    assert g["ONEWAY_APP"]=="" and g["FAST_MTU_SHRINK"]=="" and g["LONG_SCENE"]==""
    g.update(LOSS=LOSSES,DELAY=DELAYS,RATE=RATES,FAST_PHASES=PHASES,
             ROTATION_SECONDS=(600,)*5)
    plan={"profile":"H1353_CORRELATED_GAME4_DOUBLE_BLACKHOLE",
      "product_source":SOURCE,
      "wrapper_source":os.environ.get("WBD_H1353_WRAPPER_SOURCE","PREFLIGHT"),
      "clients":g["NAMES"],"modes":g["MODES"],
      "original_loss_pct":LOSSES,"physical_oneway_delay_ms":DELAYS,
      "base_inner_mbps_each_direction":RATES,
      "phase_seconds":PHASES,"peak_inner_mbps_per_direction":sum(RATES)*.5,
      "100pct_physical_loss":"app t=70..78s Dave client+host veth both egress",
      "scope":"one shared real physical underlay for original four Game4 lanes, not independent paths"}
    assert sum(x[1] for x in PHASES)==170 and sum(RATES)*.5==10
    if sys.argv[1]=="--preflight":
        print("H1353_PHYSICAL_GAME4_BLACKHOLE_PREFLIGHT",json.dumps(plan,sort_keys=True))
        return
    assert os.environ.get("GITHUB_SHA")==SOURCE
    assert len(os.environ.get("WBD_H1353_WRAPPER_SOURCE",""))==40
    fn()
    out=pathlib.Path(os.environ["GITHUB_WORKSPACE"])/"fixed-kernel-result"
    observed=json.loads((out/"h1250-matrix-plan.json").read_text())
    assert observed["source_sha"]==SOURCE
    assert [x["loss_pct"] for x in observed["clients"]]==list(LOSSES)
    assert [x["oneway_delay_ms"] for x in observed["clients"]]==list(DELAYS)
    assert [(x["name"],x["seconds"],x["rate_scale"])
            for x in observed["capacity_phase_schedule"]]==list(PHASES)
    observed["h1353_specialization"]=plan
    (out/"h1250-matrix-plan.json").write_text(json.dumps(observed,indent=2)+"\n")
    print("H1353_NATIVE_GAME4_CORRELATED_REAL_BLACKHOLE_CAPTURED",flush=True)
if __name__=="__main__":
    main()
