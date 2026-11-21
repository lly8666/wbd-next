#!/usr/bin/env python3
"""Tap the exact real diagnostic App button; never use ADB to start native code.
Prove actual app->su->embedded libwbdprobe.so in the same KSU AVD.
"""
import json,re,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
O=Path("out/device-diag");O.mkdir(parents=True,exist_ok=True)
P="org.wbdnext.rootprobe"
def adb(*args,check=True,timeout=25):
    p=subprocess.run(["adb",*args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                     text=True,timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(f"adb {args!r}: {p.returncode} {p.stdout[:400]}")
    return p.stdout
s=adb("shell","pm","path",P)
if "package:" not in s:raise RuntimeError("diagnostic package not installed")
adb("shell","run-as",P,"rm","-f","files/last-device-diagnostic.json")
adb("shell","am","start","-W","-n",P+"/.DeviceDiagnosticActivity")
nodes=[]
for k in range(3):
    adb("shell","uiautomator","dump","/sdcard/wbd-diag-ui.xml",timeout=40)
    raw=adb("shell","cat","/sdcard/wbd-diag-ui.xml")
    (O/"ui.xml").write_text(raw)
    if "<hierarchy" in raw:
        nodes=list(ET.fromstring(raw).iter("node"))
        break
    time.sleep(2)
matches=[n for n in nodes if "运行短时 Root / TUN / RAW / NAT 完整检测" in n.get("text","") and
         "Button" in n.get("class","") and n.get("enabled")=="true"]
if len(matches)!=1:
    raise RuntimeError("actual diagnostic UI button missing/ambiguous")
b=matches[0].get("bounds","")
m=re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",b)
if not m:raise RuntimeError("invalid button bounds")
l,t,r,d=map(int,m.groups())
if r-l<30 or d-t<30 or t<80:raise RuntimeError("actual button obscured by system ActionBar")
adb("shell","input","tap",str((l+r)//2),str((t+d)//2))
report=None
for i in range(160):
    s=adb("shell","run-as",P,"cat","files/last-device-diagnostic.json",check=False)
    if s.strip().startswith("{"):
        try:
            report=json.loads(s)
            break
        except json.JSONDecodeError:pass
    time.sleep(0.3)
if report is None:raise RuntimeError("no complete private Android App diagnostic JSON")
(O/"device-report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
print("APP_ROOT_DIAGNOSTIC_STATUS",report.get("overall"),
      report.get("core_ipv4_eligibility"),"source",report.get("source"))
for x in report.get("tests",[]):
    print(x.get("id"),x.get("status"),str(x.get("reason",""))[:240])
