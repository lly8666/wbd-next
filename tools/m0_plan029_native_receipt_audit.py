#!/usr/bin/env python3
"""PLAN029 read-only signed native artifact triage.

No network, GitHub API, product runtime or OS mutations. An Action's own
conclusion must be supplied separately; a ZIP cannot prove it. Never forgive
a red Action automatically, and never call a scoped 4MiB test full PLAN029.
"""
import argparse
import json
import math
import pathlib
import re
import sys
import zipfile

SHA=re.compile(r"^[0-9a-f]{40}$")
ONE_WAY=2*1024**3
DUPLEX=1536*1024**2
BULK=4*1024**2
STAGES=("oneway_500mbps","duplex_700mbps_aggregate")
RATE_PASS="PASS_SIGNED_LONG_SAME_VM_PHYSICAL_VS_DIRECT_CPU_UDP_STOP"


class AuditError(Exception):
    pass


class Artifact:
    def __init__(self,path):
        self.path=pathlib.Path(path)
        self.z=zipfile.ZipFile(self.path) if self.path.is_file() else None
        if self.z is None and not self.path.is_dir():
            raise AuditError("artifact ZIP/directory absent")
    def read(self,name):
        try:
            return self.z.read(name) if self.z else (self.path/name).read_bytes()
        except (KeyError,FileNotFoundError):
            return None
    def json(self,*candidates):
        for name in candidates:
            data=self.read(name)
            if data is not None:
                try:return json.loads(data)
                except (ValueError,UnicodeError) as e:
                    raise AuditError("invalid JSON in "+name) from e
        return None
    def close(self):
        if self.z:self.z.close()


def must(ok,reason):
    if not ok:raise AuditError(reason)


def sha_equal(actual,want,field):
    must(actual==want,"SOURCE_MISMATCH:"+field)


def number(n,name):
    must(isinstance(n,(int,float)) and not isinstance(n,bool)
         and math.isfinite(n) and n>=0,"invalid numeric "+name)
    return n


def analyse(path,expected_source,action_conclusion="unknown"):
    must(SHA.fullmatch(expected_source) is not None,
         "--expected-source must be exact 40-hex SHA")
    must(action_conclusion in ("success","failure","cancelled","timed_out","unknown"),
         "invalid Action conclusion")
    result={"expected_source":expected_source,"action_conclusion":action_conclusion,
            "verdict":"INCOMPLETE_ARTIFACT","scope":"NOT_PROVEN","metrics":{},
            "limitations":["NO_NEW_PRODUCT_TESTS","NOT_FULL_PLAN029","NOT_SAME_VM_OLD_NEW_BINARY_CPU_AB"]}
    a=Artifact(path)
    try:
        report=a.json("report.json","mode-results/normal/report.json")
        if not isinstance(report,dict):
            result["reason"]="missing original native report.json"
            return result
        result["observed_source"]=report.get("source")
        try:sha_equal(report.get("source"),expected_source,"report.source")
        except AuditError as e:
            result["verdict"]="SOURCE_MISMATCH"
            result["reason"]=str(e)
            return result
        manifest=a.json("mode-results/normal/artifact-manifest.json")
        if manifest is not None:
            try:
                sha_equal(manifest.get("source"),expected_source,"manifest.source")
                must(manifest.get("mode")=="normal","manifest mode is not normal")
            except AuditError as e:
                result["verdict"]="SOURCE_MISMATCH_OR_MANIFEST_ERROR"
                result["reason"]=str(e)
                return result
        public=report.get("mode_public","")
        if isinstance(public,str) and "FAIL" in public:
            result["verdict"]="TRUE_NATIVE_PRODUCT_FAILURE"
            result["reason"]="original signed mode reports "+public
            result["first_failure"]=str(report.get("error") or report.get("first_failure")
                                          or "inspect original normal client.log")[:550]
            return result
        if public!="PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal":
            result["reason"]="original normal public mode not proven"
            return result
        p=report.get("plan029_p2_mixed_real")
        if not isinstance(p,dict):
            result["verdict"]="NOT_RUN_P2"
            result["reason"]="actual native mode passed; PLAN029 P2 receipt absent"
            return result
        try:
            for f in ("source_sha","binary_source_sha"):
                sha_equal(p.get(f),expected_source,"p2."+f)
            for k in ("physical_baseline","direct_windows"):
                stage=p[k]
                must(stage["echo_bytes"]==BULK and stage.get("half_close") is True,
                     "4MiB "+k+" bytes/FIN incomplete")
                must(stage.get("throughput_scope")=="UNPACED_4M_BULK",
                     "not actual unpaced 4MiB "+k)
                must(re.fullmatch(r"[0-9a-f]{64}",stage.get("payload_sha256","")) is not None,
                     "invalid 4MiB SHA "+k)
                number(stage["elapsed_ms"],k+".elapsed_ms")
            must(p["physical_baseline"]["payload_sha256"]==
                 p["direct_windows"]["payload_sha256"],"4MiB physical/Direct SHA mismatch")
            must(p["physical_guest"]["received_bytes"]==[BULK,BULK],
                 "Linux did not receive both real 4MiB streams")
            must(p.get("overlap") is True and p.get("covered_whole_direct_tcp") is True,
                 "96B Tunnel UDP not overlapped with full Direct TCP")
            must(p.get("stop")=="PASS_BOTH_OWNED" and
                 report.get("stop")=="PASS_BOTH_OWNED","both OS owned Stop missing")
            must(manifest is None or
                 (manifest.get("product_pass") is True and manifest.get("exit_code")==0),
                 "native per-mode artifact manifest does not prove product success")
        except (AuditError,KeyError,TypeError,ValueError) as e:
            result["verdict"]="INCOMPLETE_OR_INCONSISTENT_P2"
            result["reason"]=str(e)
            return result
        result["scope"]="REAL_4M_PHYSICAL_VS_WINTUN_DIRECT_AND_TUNNEL_UDP_STOP"
        result["metrics"]["4m"]={
            "physical_elapsed_ms":p["physical_baseline"]["elapsed_ms"],
            "direct_elapsed_ms":p["direct_windows"]["elapsed_ms"],
            "bytes_each":BULK,
            "sha256":p["direct_windows"]["payload_sha256"]}
        rate=p.get("highrate_direct_tcp")
        if rate is None:
            result["verdict"]="PASS_SCOPED_4M_PENDING_ACTION"
        else:
            try:
                sha_equal(rate.get("source_sha"),expected_source,"rate.source")
                sha_equal(rate["windows"].get("source_sha"),expected_source,"windows.source")
                sha_equal(rate["linux"].get("source_sha"),expected_source,"linux.source")
                sha_equal(rate["physical_control"].get("source_sha"),expected_source,
                          "physical.source")
                must(rate.get("status")==RATE_PASS and
                     rate.get("owner_stop")=="PASS_BOTH_OWNED" and
                     rate.get("tunnel_udp_covers_rate") is True,
                     "long real rate/UDP/Stop receipt not qualified")
                must([s["path"] for s in rate["linux"]["sessions"]]==["physical","direct"],
                     "physical then Direct Linux sessions not proven")
                must(all(s["half_close"] is True and
                         s["oneway_received_bytes"]==ONE_WAY and
                         s["duplex"]["local_received_bytes"]==DUPLEX and
                         s["duplex"]["local_sent_bytes"]==DUPLEX
                         for s in rate["linux"]["sessions"]),
                     "Linux 10GiB SHA/FIN/bytes sessions incomplete")
                udp=rate["tunnel_udp_per_stage"]
                compiled={}
                for name in STAGES:
                    ph=rate["physical_control"]["stages"][name]
                    di=rate["windows"]["stages"][name]
                    delta=rate["same_vm_original_process_cpu_increment"][name]
                    required=ONE_WAY if name==STAGES[0] else DUPLEX
                    must(ph["local_sent_bytes"]==required and
                         di["local_sent_bytes"]==required,
                         "long TCP Windows upload incomplete "+name)
                    if name==STAGES[1]:
                        must(ph["local_received_bytes"]==DUPLEX and
                             di["local_received_bytes"]==DUPLEX,
                             "long TCP full duplex download incomplete")
                    physical_cpu=number(ph["original_process_cpu"]
                          ["original_process_total_cpu_s_per_gib"],"physical_cpu")
                    direct_cpu=number(di["original_process_cpu"]
                          ["original_process_total_cpu_s_per_gib"],"direct_cpu")
                    added=number(delta["added_process_total_cpu_s_per_gib"],"added_cpu")
                    must(abs((direct_cpu-physical_cpu)-added)<0.005,
                         "CPU delta inconsistent with same-VM stage")
                    for peer in ("physical_"+name,name):
                        sample=udp[peer]
                        must(sample["unique_delivered"]>=25 and
                             number(sample["rtt_p99_ms"],"udp p99")>0,
                             "Tunnel UDP phase missing "+peer)
                    compiled[name]={
                        "physical_mbps":number(ph["actual_aggregate_mbps"],"physical_mbps"),
                        "direct_mbps":number(di["actual_aggregate_mbps"],"direct_mbps"),
                        "physical_original_process_cpu_s_per_gib":physical_cpu,
                        "direct_original_process_cpu_s_per_gib":direct_cpu,
                        "added_original_process_cpu_s_per_gib":added,
                        "physical_tunnel_96b_udp_p99_ms":udp["physical_"+name]["rtt_p99_ms"],
                        "direct_tunnel_96b_udp_p99_ms":udp[name]["rtt_p99_ms"],
                        "target_reached_reported":di["target_reached"],
                    }
                must(rate["linux"]["oneway_received_bytes"]==ONE_WAY and
                     rate["linux"]["duplex"]["local_received_bytes"]==DUPLEX,
                     "Linux Direct endpoint actual bytes missing")
                result["metrics"]["long_10gib"]={
                    "total_bytes_both_paths":10*1024**3,
                    "phases":compiled,
                    "cpu_scope":"ORIGINAL_GO_RUST_PROCESS_NOT_FULL_MACHINE_DRIVER",
                    "old_vs_new_same_VM_AB":"NOT_RUN"}
            except (AuditError,KeyError,TypeError,ValueError) as e:
                result["verdict"]="INCOMPLETE_OR_INCONSISTENT_LONG"
                result["reason"]=str(e)
                return result
            result["scope"]="REAL_SAME_VM_PHYSICAL_DIRECT_10GIB_500_700_UDP_STOP"
            result["verdict"]="PASS_SIGNED_LONG_PENDING_ACTION"
        if action_conclusion=="success":
            result["verdict"]=result["verdict"].replace("_PENDING_ACTION","")
            result["reason"]="scoped signed original native receipt and Action conclusion both PASS"
        elif action_conclusion=="unknown":
            result["verdict"]="ACTION_CONCLUSION_NOT_ATTESTED"
            result["reason"]="artifact cannot establish overall GitHub Action conclusion"
        else:
            result["verdict"]="ACTION_FAILURE_REVIEW_REQUIRED"
            result["reason"]="product receipt scoped PASS but GitHub Action is "+
                             action_conclusion+"; do not auto-claim false red"
        return result
    finally:
        a.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact",help="downloaded signed native ZIP or extracted directory")
    parser.add_argument("--expected-source",required=True)
    parser.add_argument("--action-conclusion",default="unknown",
                        choices=("success","failure","cancelled","timed_out","unknown"))
    parser.add_argument("--output",help="optional machine-readable JSON result")
    args=parser.parse_args()
    try:result=analyse(args.artifact,args.expected_source,args.action_conclusion)
    except (AuditError,OSError,zipfile.BadZipFile) as e:
        result={"verdict":"INVALID_ARTIFACT","reason":str(e),
                "expected_source":args.expected_source}
    rendered=json.dumps(result,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
    if args.output:pathlib.Path(args.output).write_text(rendered,encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if result.get("verdict") in ("PASS_SIGNED_LONG","PASS_SCOPED_4M") else 2


if __name__=="__main__":
    sys.exit(main())
