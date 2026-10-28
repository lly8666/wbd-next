"""Strict signed-Windows Rust NativeOwner outer repair accounting."""
import argparse,json,pathlib,re,sys
from m0_wl_perf_v2_config import read_scenario
MARKER=re.compile(r"WBD_WINDOWS_NATIVE_OUTER_REPAIR source_wire_bytes=(\d+) repair_accepted_wire_bytes=(\d+) repair_uncertain_wire_bytes=(\d+) control_wire_bytes=(\d+) repair_packets=(\d+) r_to_f_ppm=(\d+) r_to_total_ppm=(\d+) joined=true")
def verify(scene,report,client_log,tc):
    matches=[tuple(map(int,m)) for m in MARKER.findall(client_log)]
    if len(matches)!=1:raise ValueError("MISSING_UNIQUE_RUST_JOINED_REPAIR_RECEIPT")
    f,ra,ru,k,packets,rf,rt=matches[0];r=ra+ru;tot=f+r+k
    if not f or not tot:raise ValueError("NO_GENUINE_FIRST_SEND")
    if rf!=r*1_000_000//f or rt!=r*1_000_000//tot:raise ValueError("INVALID_REPAIR_ACCOUNT")
    w=report.get("WL_V2",{})
    if w.get("scenario_sha256")!=scene["scenario_sha256"] or w.get("status")!="MEASURED_BOTH_OS_KERNEL" or w.get("owned_stop")!="PASS_BOTH_OWNED" or report.get("stop")!="PASS_BOTH_OWNED" or report.get("mode")!="normal":raise ValueError("UNVERIFIED_TWO_OS_SESSION_OR_STOP")
    target=scene["windows_to_linux"]["offered_mbps"]
    if any(w["offered_mbps"][side]<target*.95 for side in ("windows","linux")):raise ValueError("GENERATOR_CAPACITY_LIMIT")
    drops={}
    for name in ("eth0","ifb"):
        q=[x for x in tc.get(name,[]) if x.get("kind")=="netem"]
        if len(q)!=1 or not isinstance(q[0].get("drops"),int):raise ValueError("KERNEL_TC_DROP_MISSING")
        drops[name]=q[0]["drops"]
        if scene["windows_to_linux"]["loss_pct"]>0 and not drops[name]:raise ValueError("DECLARED_LOSS_NOT_INJECTED")
    if r*10>tot or r*10>f:raise ValueError("REPAIR_EXCEEDS_TEN_PERCENT")
    capacity_bytes=target*1_000_000*scene["duration_s"]/8
    rc=r/capacity_bytes
    if scene["windows_to_linux"]["loss_pct"]==30 and rc<.06:raise ValueError("HIGH_LOSS_REPAIR_BELOW_6_PERCENT_CAPACITY")
    return {"status":"PASS_SCOPED_WINDOWS_OUTER_REPAIR","source":report.get("source"),"scene":scene["scenario_id"],"scenario_sha256":scene["scenario_sha256"],"wire_bytes":{"first":f,"repair_accepted":ra,"repair_uncertain_charged":ru,"control":k},"ratios":{"R/F":r/f,"R/total":r/tot,"R/C":rc},"repair_packets":packets,"actual_tc_drops":drops,"offered_mbps":w["offered_mbps"],"first_delivery_fraction":w["first_delivery_fraction"],"owned_stop":"PASS_BOTH_OWNED"}
def main():
    p=argparse.ArgumentParser();p.add_argument("--scenario",required=True);p.add_argument("--mode-root",required=True);p.add_argument("--out",required=True);a=p.parse_args()
    scene=read_scenario(a.scenario);root=pathlib.Path(a.mode_root)
    report=json.loads((root/"report.json").read_text(encoding="utf8"))
    try:result=verify(scene,report,(root/"client.log").read_text(encoding="utf8",errors="replace"),json.loads((root/"wl-n0-netem-after.json").read_text()))
    except (ValueError,KeyError,TypeError) as e:result={"status":"FAIL_OR_INCONCLUSIVE","source":report.get("source"),"scenario_sha256":scene["scenario_sha256"],"reason":str(e)}
    dest=pathlib.Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("WL_NATIVE_OUTER_REPAIR_VERDICT",json.dumps(result,sort_keys=True),flush=True)
    return 0 if result["status"]=="PASS_SCOPED_WINDOWS_OUTER_REPAIR" else 2
if __name__=="__main__":sys.exit(main())
