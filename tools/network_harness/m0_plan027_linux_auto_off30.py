"""PLAN027 N: single-lane Normal Auto FEC at true 30%/250ms, outer DATA OFF.
Source-frozen original Go TLS + Rust M4; reuse Fixed6 exact traffic and binary.
"""
import argparse
import copy
import hashlib
import json
import os
import platform
from pathlib import Path

from tools.network_harness.config import validate
from tools.network_harness.m0_plan027_linux_fixed6_off30 import configuration as fixed_configuration
from tools.network_harness.runner import LinuxExperiment


def configuration(scene, source, run_id):
    cfg = fixed_configuration(scene, source, run_id)
    # Exactly one change from matched-mix Fixed6 control: real Auto product
    # policy, profile=1 startup. Keep network/packet mix/repair OFF identical.
    cfg["id"] = "M0_PLAN027_N_AUTO_10M_250MS_LOSS30_OUTER_OFF"
    cfg["product"]["mode"] = "fec-auto"
    cfg["product"]["fec_profile"] = 1
    assert cfg["product"]["game_fec"] == "off"
    assert cfg["product"]["repair_enabled"] is False
    tmp = copy.deepcopy(cfg)
    tmp["bundles"]["A"].update(run_id=run_id, artifact_id=run_id, attempt=1,
                                sha256="0"*64)
    validate(tmp)
    return cfg


def main():
    parser = argparse.ArgumentParser()
    for key in ("bundle", "product-source", "scenario", "out"):
        parser.add_argument("--"+key, required=True)
    args = parser.parse_args()
    assert platform.machine() == "x86_64"
    assert len(os.environ["GITHUB_SHA"]) == 40 and len(args.product_source) == 40
    assert Path(args.scenario).name == "plan027-c-game2-fec-10m-250ms-loss30-60s.json"
    scene = json.loads(Path(args.scenario).read_text())
    bundle = Path(args.bundle).resolve()
    m = json.loads((bundle/"manifest.json").read_text())
    assert m["source"] == args.product_source and m["architecture"] == "x86_64"
    hashes = {}
    for line in (bundle/"SHA256SUMS").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        hashes[name.lstrip("*")] = digest
    names = ("wbd-v4-client", "wbd-v4-server", "libwbd_engine.so")
    for name in names:
        assert hashlib.sha256((bundle/name).read_bytes()).hexdigest() == hashes[name]
    base = Path(args.out).resolve()
    base.mkdir(parents=True, exist_ok=True)
    home = base/"bundle-A"/"fixed-build"
    home.mkdir(parents=True, exist_ok=True)
    for name in names:
        (home/name).symlink_to(bundle/name)
    cfg = configuration(scene, args.product_source, int(os.environ["GITHUB_RUN_ID"]))
    case = base/"normal-auto-off-loss30"
    leg = LinuxExperiment(cfg, base/"bundle-A", case, "A").run()
    t = leg.get("telemetry", {})
    fec = t.get("fec_final_readback")
    summary = t.get("FEC_k_r_parity_queue_decode")
    real_tx = summary.get("real_tx_owner_end_snapshot") if isinstance(summary,dict) else None
    result = {
        "source_sha": args.product_source,
        "fixture_source_sha": os.environ["GITHUB_SHA"],
        "binary_sha256": {n: hashes[n] for n in names},
        "scope": "Linux original Go TLS+Rust M4 single lane Normal Auto/outer DATA OFF 10Mbps each/250ms one-way/30pct true tc/60s UDP",
        "packet_mix": "96/288/1060/1200B weight10/15/30/45, exactly Fixed6 and Game2FEC6",
        "native_result": leg.get("result"), "failures": leg.get("failures",[]),
        "limits": leg.get("limits",[]),
        "fec_readback": fec, "fec_native_tx": summary,
        "native_outer_off_readback": t.get("outer_repair_native_verified"),
        "native_policy_readback": t.get("recovery_policy_verified"),
        "go_handoff": t.get("go_receive_handoff_verified"),
        "owned_stop": t.get("stop_drained_both"),
        "namespace_cleanup": leg.get("cleanup",{}).get("owned_namespaces_absent"),
        "first_business": {}, "outer_ip_F_R_C": {}, "cpu_s": {}, "rss_bytes": {},
        "real_netem_drops": {}, "verdict": "NOT_RUN"}
    valid = (leg.get("result") == "PASS_SCOPED_OBSERVATION"
             and t.get("effective_config_verified") is True
             and t.get("outer_repair_native_verified") is True
             and t.get("recovery_policy_verified") is True
             and t.get("go_receive_handoff_verified") is True
             and t.get("stop_drained_both") is True
             and leg.get("cleanup",{}).get("owned_namespaces_absent") is True
             and isinstance(fec,dict) and set(fec) == {"client","server"}
             and isinstance(real_tx,dict) and set(real_tx) == {"client","server"})
    for direction, role in (("c2s","client"),("s2c","server")):
        rows = [x for x in leg.get("observed",[]) if x.get("phase") == "iid"
                and x.get("direction") == direction]
        offered = sum(float(x.get("injected_app_mbps") or 0) for x in rows)
        first = sum(float(x.get("cohort_delivered_app_mbps") or 0) for x in rows)
        result["first_business"][direction] = {
            "offered_mbps": offered, "unique_first_mbps": first,
            "first_fraction": first/offered if offered else None,
            "p99_ms": next((x.get("first_arrival_ms",{}).get("p99_ms")
                             for x in rows if x.get("protocol") == "udp"),None),
            "missing_after_drain": sum(int(x.get("missing_after_drain",0)) for x in rows)}
        if offered<9.5 or first<=0: valid=False
        ledger = leg.get("v3_repair_accounting",{}).get(direction,{})
        f = ledger.get("first_wire_bytes")
        repair = ledger.get("conservative_charged_wire_bytes")
        result["outer_ip_F_R_C"][direction] = {
            "F": f, "R": repair, "C": "NOT_MEASURED",
            "scope": "actual M4 IP wire incl warmup"}
        if not isinstance(f,int) or f<=0 or repair!=0:valid=False
        result["cpu_s"][role] = leg.get("measurement_cost",{}).get(role,{}).get("cpu_s")
        result["rss_bytes"][role] = leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes")
        if not isinstance(result["cpu_s"][role],(int,float)):valid=False
        if isinstance(real_tx,dict) and (real_tx.get(role) or {}).get("rsent",0)<=0:
            valid=False
    snapshots = json.loads((case/"network-snapshots.json").read_text())
    before = next((v for v in snapshots if v["name"] == "before-iid"),None)
    after = next((v for v in snapshots if v["name"] == "measurement-end"),None)
    for role in ("client","server"):
        def dropped(s):
            if s is None:return None
            q=[v for v in s["network"][role]["qdisc"] if v.get("kind")=="netem"]
            return q[0].get("drops") if len(q)==1 else None
        b,e=dropped(before),dropped(after)
        count=e-b if isinstance(e,int) and isinstance(b,int) else None
        result["real_netem_drops"][role]=count
        if not isinstance(count,int) or count<=0:valid=False
    result["verdict"]=("PASS_SCOPED_NORMAL_AUTO_FEC_OUTER_OFF_TRUE30"
                        if valid else "FAIL_OR_INCONCLUSIVE")
    (base/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PLAN027_N_AUTO_OFF30_VERDICT",result["verdict"],flush=True)
    if not valid:raise SystemExit(2)

if __name__=="__main__":main()
