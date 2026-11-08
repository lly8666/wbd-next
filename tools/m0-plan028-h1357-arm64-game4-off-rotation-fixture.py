#!/usr/bin/env python3
"""PLAN028 H1357 original native ARM64 TLS/Rust Game4 Off lane rotation.
Prior H1327/H1328 echo receiver limit4000 and wrong whole-group oracle were
test problems. Use actual five-client 10ms UDP/TCP + native Stop gate here.
Product source 24e1fe6c4eab2a1abb7fb8a6d2093abaf57c0f73 is a fully built native ARM64 ELF183 archive;
relative to x86 source6c5, only compiled-out feature cfg+test changes.
"""
import json,os,pathlib,runpy,sys
SOURCE="24e1fe6c4eab2a1abb7fb8a6d2093abaf57c0f73"
RATES=(4,4,3,6,3)
LOSSES=(0,0,0,0,0)
DELAYS=(0,10,20,30,0)
ROTATIONS=(97,101,103,89,107)
PHASES=(("first_wave",30,.2),("sustained",60,.35),
        ("overload",30,.5),("recovery",50,.35))
def main():
    assert len(sys.argv)==2
    for k,v in (("WBD_PLAN028_FAST_SCENE","pressure"),
         ("WBD_PLAN028_FAST_CAPACITY_STEPS","2"),
         ("WBD_PLAN028_QDISC_CLOCK_DIAG","1"),
         ("WBD_PLAN028_STATIC_OWNED_NEIGH","1")):
        assert os.environ.get(k)==v,k
    assert not os.environ.get("WBD_PLAN028_GAME4_CORRELATED_BLACKHOLE")
    assert not os.environ.get("WBD_PLAN028_APP_ONEWAY")
    assert not os.environ.get("WBD_PLAN028_30M_SCENE")
    context=runpy.run_path("tools/m0-plan028-h1259-five-client-recovery-netns.py",
                            run_name="h1357_no_main")
    fn=context["main"];g=fn.__globals__
    assert g["FAST_SCENE"]=="pressure" and g["CAPACITY_STEPS"]=="2"
    assert g["MODES"]==("normal","fec-auto","game2","game4","fec-fixed")
    assert g["STATIC_NEIGH"]=="1" and g["CORRELATED_GAME4_BLACKHOLE"]==""
    assert g["FAST_MTU_SHRINK"]=="" and g["LONG_SCENE"]==""
    extra=list(g["EXTRA"])
    assert extra[2]==("--record-cipher","aes-256-gcm")
    assert extra[3]==("--game-fec","fixed6","--record-cipher","chacha20-poly1305")
    extra[2]=("--game-fec","fixed6","--record-cipher","aes-256-gcm")
    extra[3]=("--game-fec","off","--record-cipher","chacha20-poly1305")
    assert extra[3]==("--game-fec","off","--record-cipher","chacha20-poly1305")
    g.update(LOSS=LOSSES,DELAY=DELAYS,RATE=RATES,FAST_PHASES=PHASES,
             EXTRA=tuple(extra),ROTATION_SECONDS=ROTATIONS)
    plan={"profile":"H1357_NATIVE_ARM64_GAME4_OFF_WITH_FIVE_REAL_ROTATING_CLIENTS",
      "original_product_source":SOURCE,
      "wrapper_source":os.environ.get("WBD_H1357_WRAPPER_SOURCE","PREFLIGHT"),
      "five_client_modes":g["MODES"],
      "two_missing_config_variant":"Dave game4 Off, previously Game4 Fixed6; Carol stays Game2 Fixed6",
      "cli_extra_per_client":dict(zip(g["NAMES"],g["EXTRA"])),
      "rotation_interval_seconds":dict(zip(g["NAMES"],ROTATIONS)),
      "physical_true_loss_pct":LOSSES,"oneway_delay_ms":DELAYS,
      "base_inner_mbps_per_direction":RATES,
      "peak_inner_mbps_per_direction":sum(RATES)*.5,
      "phases":[[n,d,s] for n,d,s in PHASES],
      "sibling_clients":["alice","bob","dave","erin"],
      "scope":"one native ARM64 source locked 180s original TLS443 Rust M4 Five TUN, authentic per-client timer FEC6; Game4 Off original 4-lane owner; Carol Game2 Fixed6 source oracle"}
    assert plan["peak_inner_mbps_per_direction"]==10 and sum(p[1] for p in PHASES)==170
    if sys.argv[1]=="--preflight":
        print("M0_PLAN028_H1357_ARM64_GAME4_OFF_PREFLIGHT",json.dumps(plan,sort_keys=True),flush=True)
        return
    assert os.environ.get("GITHUB_SHA")==SOURCE
    assert len(os.environ.get("WBD_H1357_WRAPPER_SOURCE",""))==40
    fn()
    out=pathlib.Path(os.environ["GITHUB_WORKSPACE"])/"fixed-kernel-result"
    actual=json.loads((out/"h1250-matrix-plan.json").read_text())
    assert actual["source_sha"]==SOURCE
    assert [c["loss_pct"] for c in actual["clients"]]==list(LOSSES)
    assert [c["oneway_delay_ms"] for c in actual["clients"]]==list(DELAYS)
    assert [c["c2s_target_mbps"] for c in actual["clients"]]==list(RATES)
    assert [(p["name"],p["seconds"],p["rate_scale"])
             for p in actual["capacity_phase_schedule"]]==list(PHASES)
    assert actual["rotation_seconds"]==dict(zip(g["NAMES"],ROTATIONS))
    actual["h1357_specialization"]=plan
    (out/"h1250-matrix-plan.json").write_text(json.dumps(actual,indent=2)+"\n")
    print("M0_PLAN028_H1357_NATIVE_ARM64_GAME4_OFF_REAL_ROTATION_CAPTURED",flush=True)
if __name__=="__main__":
    main()
