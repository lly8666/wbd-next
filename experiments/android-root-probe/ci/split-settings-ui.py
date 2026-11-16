#!/usr/bin/env python3
"""True target37 Android UI selection/persistence and native Root policy readback.
No Android main routing, DNS, WBD connection or FakeIP is activated.
"""
import json,re,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
P="org.wbdnext.rootprobe"
O=Path("out/device-diag");O.mkdir(parents=True,exist_ok=True)
def adb(*args,check=True,timeout=30):
 p=subprocess.run(["adb",*args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                  text=True,timeout=timeout)
 if check and p.returncode:raise RuntimeError(f"adb {args}: {p.returncode}: {p.stdout[:320]}")
 return p.stdout
def dump():
 adb("shell","uiautomator","dump","/sdcard/wbd-split-screen.xml",timeout=40)
 raw=adb("shell","cat","/sdcard/wbd-split-screen.xml")
 (O/"split-ui.xml").write_text(raw)
 if "<hierarchy" not in raw:raise RuntimeError("ui hierarchy missing")
 return list(ET.fromstring(raw).iter("node"))
def box(n):
 b=n.get("bounds","")
 m=re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",b)
 if not m:raise RuntimeError(f"invalid view bounds {b}")
 return tuple(map(int,m.groups()))
def valid(n):
 l,t,r,b=box(n);return r>l+20 and b>t+20 and t>=85 and n.get("visible-to-user","true")=="true"
def click(n):
 l,t,r,b=box(n)
 if not valid(n):raise RuntimeError(f"view invisible/covered: {n.attrib}")
 adb("shell","input","tap",str((l+r)//2),str((t+b)//2))
def find(text,klass=None):
 for n in dump():
  if text in n.get("text","") and (klass is None or klass in n.get("class","")) and valid(n):
   return n
 return None
adb("shell","am","start","-W","-n",P+"/.DeviceDiagnosticActivity")
button=find("Android 分流/全局设置","Button")
if button is None:raise RuntimeError("split settings entry missing")
click(button)
if "SplitSettingsActivity" not in adb("shell","dumpsys","activity","activities"):
 raise RuntimeError("split mode SettingsActivity not reached")
# Android's scroll view may expose offscreen nodes, but only click visible views.
def scroll_for(text,klass=None,limit=10):
 for i in range(limit):
  n=find(text,klass)
  if n is not None:return n
  adb("shell","input","swipe","160","690","160","180","300")
 raise RuntimeError("could not scroll to visible "+text)
# Locate the editable directly following the package label in UI tree order.
edit=None
for turn in range(8):
 nodes=dump()
 for i,n in enumerate(nodes):
  if "单独设置某 App" in n.get("text",""):
   for x in nodes[i+1:i+6]:
    if "EditText" in x.get("class","") and valid(x):edit=x;break
   if edit:break
 if edit:break
 adb("shell","input","swipe","160","675","160","190","280")
if edit is None:raise RuntimeError("per-app package editor not reachable")
click(edit)
adb("shell","input","text","uid:10502")
adb("shell","input","keyevent","4")
click(scroll_for("添加/覆盖此 App","Button"))
click(scroll_for("保存并经 Root 验证策略","Button"))
config=report=None
for _ in range(70):
 raw=adb("shell","run-as",P,"cat","files/wbd-split-settings.json",check=False)
 val=adb("shell","run-as",P,"cat","files/wbd-split-validation.json",check=False)
 try:
  config=json.loads(raw);report=json.loads(val)
  if report.get("status")=="SUPPORTED_IN_SCOPE":break
 except ValueError:pass
 time.sleep(0.4)
if config is None or report is None:raise RuntimeError("no saved config/native result")
(O/"split-settings.json").write_text(json.dumps(config,indent=2,ensure_ascii=False)+"\n")
(O/"split-validation.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
assert config.get("schema")=="wbd-android-split/v1"
assert config.get("default_mode")=="split"
assert config.get("no_fakeip") is True
assert config.get("direct_dns")=="223.5.5.5"
assert config.get("tunnel_dns")=="1.1.1.1"
assert len(config.get("cn_ipv4",[]))>1000
assert any(x.get("uid")==10502 and x.get("mode")=="global" for x in config.get("apps",[]))
assert report.get("status")=="SUPPORTED_IN_SCOPE"
assert report.get("installed") is False
assert report.get("server_bootstrap_dns")=="DIRECT_IN_ALL_MODES"
assert report.get("compiled_cn_ipv4_intervals",0)>500
assert any(x.get("uid")==10502 and x.get("mode")=="global" for x in report.get("per_app_modes",[]))
print("ANDROID_SPLIT_PER_APP_SETTINGS_UI_CONFIG_VALIDATION_PASS")
print("CN intervals:",report["compiled_cn_ipv4_intervals"],
      "DNS:",report["dns_direct"],report["dns_tunnel"],
      "OS installed:",report["installed"])
