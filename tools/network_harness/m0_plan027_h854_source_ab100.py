"""One actual same-VM original Go TLS/Rust M4 Normal ON100 source BEFORE -> AFTER.
Identical real kernel netns, offer, packet mix, loss, TLS and driver config;
source-specific manifests+SHA256 verified independently, no mixed evidence.
"""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
from tools.network_harness.m0_plan027_linux_repair_pair_cap100 import configuration,measure
from tools.network_harness.runner import LinuxExperiment

FILES=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")

def verified_bundle(path,source):
    m=json.loads((path/"manifest.json").read_text())
    assert m["source"]==source and m["architecture"]=="x86_64"
    sums={}
    for line in (path/"SHA256SUMS").read_text().splitlines():
        digest,name=line.split(maxsplit=1);sums[name.lstrip("*")]=digest
    for name in FILES:
        assert hashlib.sha256((path/name).read_bytes()).hexdigest()==sums[name]
    return {name:sums[name] for name in FILES}

def main():
    p=argparse.ArgumentParser()
    for name in ("before-bundle","after-bundle","before-source","after-source",
                 "scenario","out"):p.add_argument("--"+name,required=True)
    args=p.parse_args()
    assert platform.machine()=="x86_64" and len(os.environ["GITHUB_SHA"])==40
    assert Path(args.scenario).name=="plan027-n-normal-off-100m-25ms-loss0-60s.json"
    scene=json.loads(Path(args.scenario).read_text())
    root=Path(args.out).resolve()
    root.mkdir(parents=True,exist_ok=True)
    result={"scenario":scene["scenario_id"],"fixture_source_sha":os.environ["GITHUB_SHA"],
            "one_vm_sequential_order":["BEFORE","AFTER"],
            "sources":{"BEFORE":args.before_source,"AFTER":args.after_source},
            "scope":"Original Linux Go TLS/Rust M4 dual real raw/TUN Normal outer ON, 100Mbps each 25ms 0% 1200B 60s, same single VM, exact before/after source",
            "theory":{"business_pps_per_direction":10416.667,"business_BDP_bytes_each_RTT50ms":625000},
            "legs":{},"cpu_delta":{},"rss_delta":{},"verdict":"NOT_RUN"}
    for label in ("BEFORE","AFTER"):
        src=getattr(args,label.lower()+"_source")
        bundle=Path(getattr(args,label.lower()+"_bundle")).resolve()
        hashes=verified_bundle(bundle,src)
        home=root/("bundle-"+label)/"fixed-build"
        home.mkdir(parents=True,exist_ok=True)
        for name in FILES:(home/name).symlink_to(bundle/name)
        cfg=configuration(scene,src,int(os.environ["GITHUB_RUN_ID"]),True)
        cfg["id"]="M0_PLAN027_H854_R100_SOURCE_"+label+"_NORMAL_REPAIR_ON"
        case=root/("leg-"+label.lower())
        native=LinuxExperiment(cfg,root/("bundle-"+label),case,"A").run()
        leg=measure(native,True)
        leg["source_sha"]=src
        leg["binary_sha256"]=hashes
        result["legs"][label]=leg
        if leg["verdict"]!="PASS_SCOPED_NATIVE_LEG":break
        for direction in ("c2s","s2c"):
            if (leg["first"][direction]["p99_ms"] is None or
                leg["first"][direction]["p99_ms"]>80):
                leg["verdict"]="FAIL_OR_INCONCLUSIVE_P99"
        if leg["verdict"]!="PASS_SCOPED_NATIVE_LEG":break
    if set(result["legs"])=={"BEFORE","AFTER"} and all(
        x["verdict"]=="PASS_SCOPED_NATIVE_LEG" for x in result["legs"].values()):
        b,a=result["legs"]["BEFORE"],result["legs"]["AFTER"]
        for role in ("client","server"):
            x=a["cpu_s"][role]-b["cpu_s"][role]
            result["cpu_delta"][role]={
                "after_minus_before_steady_cpu_s":x,
                "relative_to_before":x/b["cpu_s"][role] if b["cpu_s"][role] else None}
            result["rss_delta"][role]=a["rss_bytes"][role]-b["rss_bytes"][role]
        result["verdict"]="PASS_SCOPED_SOURCE_AB_MEASUREMENT_NOT_AUTOMATIC_BENEFIT"
    else:result["verdict"]="FAIL_OR_INCONCLUSIVE"
    result["limits"]=[
        "Only one sameVM original Linux sequential BEFORE->AFTER lossless source A/B. Variance may need at most one reverse if consequential",
        "Compare 60s original whole-process CPU steady, never use cross-run worker full owner for this delta",
        "No physical Windows, no driver C physical, no real 30pct repair quality from this action"]
    (root/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PLAN027_R100_SOURCE_AB",result["verdict"],flush=True)
    if result["verdict"]!="PASS_SCOPED_SOURCE_AB_MEASUREMENT_NOT_AUTOMATIC_BENEFIT":
        raise SystemExit(2)

if __name__=="__main__":main()
