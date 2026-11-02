"""Single original Linux Normal repair-ON high-loss regression on NEW immutable source.
One run only: no separate source/VM CPU comparison or business repair promise.
"""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
from tools.network_harness.m0_plan027_linux_repair_pair_loss30 import paired_config,collect
from tools.network_harness.runner import LinuxExperiment

def main():
    p=argparse.ArgumentParser()
    for k in ("bundle","product-source","scenario","out"):p.add_argument("--"+k,required=True)
    x=p.parse_args()
    assert platform.machine()=="x86_64" and len(os.environ["GITHUB_SHA"])==40
    assert Path(x.scenario).name=="wl-outer-repair-10m-250ms-loss30-60s.json"
    scene=json.loads(Path(x.scenario).read_text())
    product=Path(x.bundle).resolve()
    m=json.loads((product/"manifest.json").read_text())
    assert m["source"]==x.product_source and m["architecture"]=="x86_64"
    hashes={}
    for row in (product/"SHA256SUMS").read_text().splitlines():
        sha,name=row.split(maxsplit=1);hashes[name.lstrip("*")]=sha
    names=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
    for name in names:assert hashlib.sha256((product/name).read_bytes()).hexdigest()==hashes[name]
    root=Path(x.out).resolve()
    root.mkdir(parents=True,exist_ok=True)
    home=root/"bundle-A"/"fixed-build"
    home.mkdir(parents=True,exist_ok=True)
    for name in names:(home/name).symlink_to(product/name)
    cfg=paired_config(scene,x.product_source,int(os.environ["GITHUB_RUN_ID"]),True)
    cfg["id"]="M0_PLAN027_H854_NORMAL_ON_NEW_SHARED_INDEX_TRUE30"
    case=root/"native-on30"
    native=LinuxExperiment(cfg,root/"bundle-A",case,"A").run()
    leg=collect(native,True,case)
    result={"source_sha":x.product_source,"fixture_sha":os.environ["GITHUB_SHA"],
            "binary_sha256":{n:hashes[n] for n in names},
            "scope":"Original Linux Go TLS Rust M4 Normal repair ON 10Mbps each/250ms one-way/30pct real netem/60s UDP64/128/512/1200 weighted10/15/25/50",
            "native":leg,"verdict":"PASS_SCOPED_NEW_SHARED_INDEX_ON30" if leg["verdict"]=="PASS_SCOPED_NATIVE_LEG" else "FAIL_OR_INCONCLUSIVE",
            "limits":["One source true30pct ON integration, no business restoration promise from cosmetic repair",
                      "CPU across different VM/seed from old f5 ON cannot infer optimization ROI",
                      "F/R original M4 IP bytes whole warmup+steady, C physical not measured"]}
    (root/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PLAN027_H854_SHARED_INDEX_ON30",result["verdict"],flush=True)
    if result["verdict"]!="PASS_SCOPED_NEW_SHARED_INDEX_ON30":raise SystemExit(2)

if __name__=="__main__":main()
