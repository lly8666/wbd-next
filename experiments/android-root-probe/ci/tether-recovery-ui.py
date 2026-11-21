#!/usr/bin/env python3
"""Click the actual RecoveryActivity Button via UI tree, then read App private result."""
import json,re,subprocess,sys,time,xml.etree.ElementTree as ET
from pathlib import Path
if len(sys.argv)!=3:
    raise SystemExit("usage: tether-recovery-ui.py FIRST|SECOND RESTORED|ALREADY_CLEAN")
phase,expected=sys.argv[1:]
root=Path("out/tether-recovery")
root.mkdir(parents=True,exist_ok=True)
PKG="org.wbdnext.rootprobe"
def adb(*args,timeout=30,check=True):
    p=subprocess.run(["adb",*args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
        text=True,timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(f"adb {args!r}: exit={p.returncode}: {p.stdout[:600]}")
    return p.stdout
pkg=adb("shell","pm","path",PKG)
if "package:" not in pkg:raise RuntimeError("WBD app not installed")
adb("shell","run-as",PKG,"rm","-f","files/recovery-result.json")
adb("shell","am","start","-W","-n",PKG+"/.RecoveryActivity")
time.sleep(2)
raw=""
for attempt in range(3):
    adb("shell","uiautomator","dump","/sdcard/wbd-recovery-ui.xml")
    raw=adb("shell","cat","/sdcard/wbd-recovery-ui.xml")
    if "<hierarchy" in raw:break
    time.sleep(2)
(root/f"ui-{phase}.xml").write_text(raw)
if "<hierarchy" not in raw:
    raise RuntimeError("real UI hierarchy inaccessible")
nodes=list(ET.fromstring(raw).iter("node"))
buttons=[x for x in nodes if x.get("text","")=="一键恢复正常网络"
         and "Button" in x.get("class","") and x.get("enabled")=="true"]
if len(buttons)!=1:
    raise RuntimeError("refuse click: no unique enabled user recovery Button in App UI")
bounds=buttons[0].get("bounds","")
m=re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",bounds)
if not m:raise RuntimeError("no button bounds")
a,b,c,d=map(int,m.groups())
if c-a<20 or d-b<20:raise RuntimeError("invalid recovery tap box")
# On this stock-theme API36 AVD the action bar container sits over the top
# 80 px of content. The first CI proved a visible y=24..72 Button was occluded.
bars=[n for n in nodes if n.get("resource-id","")=="android:id/action_bar_container"]
if bars:
    mbar=re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",bars[0].get("bounds",""))
    if mbar and b<int(mbar.group(4)):
        raise RuntimeError("refuse tap: recovery Button still occluded by Android ActionBar")

adb("shell","input","tap",str((a+c)//2),str((b+d)//2))
data=None
for i in range(135):
    p=adb("shell","run-as",PKG,"cat","files/recovery-result.json",check=False)
    if p.startswith("{"):
        try:
            data=json.loads(p)
            break
        except json.JSONDecodeError:
            pass
    time.sleep(0.2)
if data is None:raise RuntimeError("real App did not write recovery-result.json")
(root/f"button-{phase}.json").write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")
print(json.dumps({"phase":phase,"status":data.get("status"),"uid":data.get("app_uid"),
                  "native":(data.get("native") or {}).get("status"),"expected":expected},indent=2))
if data.get("trigger")!="explicit_user_button" or data.get("status")!=expected:
    raise RuntimeError("App-click recovery result does not match real native evidence")
n=data.get("native") or {}
if n.get("root_uid")!=0 or n.get("uid")!=data.get("app_uid"):
    raise RuntimeError("App->su root identity did not match ordinary app")
if data.get("target_sdk")!=37 or data.get("app_uid",0)<10000:
    raise RuntimeError("not target37 ordinary App")
