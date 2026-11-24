#!/usr/bin/env python3
"""Run the installed ordinary UID fixture; no install, root or route mutation."""
import argparse
import json
import ipaddress
import re
import shlex
import subprocess
import sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--serial")
    p.add_argument("--host",required=True,help="tunnel-side service address, NOT outer peer")
    p.add_argument("--port",type=int,default=18080)
    p.add_argument("--dns",default="",help="optional comma-separated names for Android OS resolver; not path proof")
    p.add_argument("--samples",type=int,default=32)
    p.add_argument("--mib",type=int,default=4)
    p.add_argument("--label",required=True,help="operator scene label, not mode readback")
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--expect-uid",type=int,help="compare with UID selected in the Root App")
    a=p.parse_args()
    if a.output.exists():p.error("output already exists")
    if not 1<=a.samples<=1000 or not 1<=a.mib<=256:p.error("invalid sample/size")
    try:ipaddress.ip_address(a.host)
    except ValueError:p.error("--host must be the literal tunnel-side test service IP")
    adb=["adb"]+(["-s",a.serial] if a.serial else [])
    args=["am","instrument","-w","-r","-e","host",a.host,
      "-e","port",str(a.port),"-e","samples",str(a.samples),"-e","mib",str(a.mib)]
    if a.dns:args+=["-e","dns",a.dns]
    args+=["org.wbdnext.testtraffic/.TrafficInstrumentation"]
    proc=subprocess.run(adb+["shell",shlex.join(args)],text=True,capture_output=True,
        timeout=45+a.samples*2+a.mib*5)
    match=re.search(r"^INSTRUMENTATION_RESULT: report=(.+)$",proc.stdout,re.M)
    report={"scene":a.label,"scope":"ordinary Android App socket byte echo; mode/lease/M4/Stop separately observed",
      "instrumentation_exit":proc.returncode,"result":"FAIL"}
    if match:
        for field in match.group(1).split():
            key,value=field.split("=",1)
            report[key]=float(value) if "." in value else int(value)
        uid_ok=a.expect_uid is None or report["uid"]==a.expect_uid
        if (proc.returncode==0 and uid_ok and "INSTRUMENTATION_CODE: -1" in proc.stdout
          and report["tcp_ok"]==a.samples and report["udp_ok"]==a.samples
          and (not a.dns or report.get("dns_ok",-1)==report.get("dns_count",-2))):
            report["result"]="PASS"
    else:
        report["instrumentation_output"]=proc.stdout[-1500:]
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    return 0 if report["result"]=="PASS" else 1

if __name__=="__main__":sys.exit(main())
