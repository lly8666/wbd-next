#!/usr/bin/env python3
"""Black-box Android touch regression on a real KernelSU AVD.

Reuse the *already captured* real uiautomator hierarchy from the immediately
preceding diagnostic click. In this API36 guest a second uiautomator process is
OOM-killed (137); repeating it isn't evidence. SplitSettingsActivity exposes
only its real on-screen View rectangles in app-private debug JSON. This script
must send real adb input taps to those rectangles and independently verify
App-saved JSON and Root-native readback. No click handler or config injection.
"""
import json,re,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
P="org.wbdnext.rootprobe"
O=Path("out/device-diag");O.mkdir(parents=True,exist_ok=True)
def adb(*args,check=True,timeout=30):
 p=subprocess.run(["adb",*args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                  text=True,timeout=timeout)
 if check and p.returncode:
  raise RuntimeError(f"adb {args!r}: rc={p.returncode}: {p.stdout[:300]}")
 return p.stdout
def tap_bounds(rect,which):
 l,t,r,b=[int(rect[k]) for k in ("left","top","right","bottom")]
 if not rect.get("visible") or r-l<30 or b-t<24 or t<80 or b>640:
  raise RuntimeError(f"App reported {which} outside real touch area: {rect}")
 adb("shell","input","tap",str((l+r)//2),str((t+b)//2))
def fresh_bounds():
 raw=adb("shell","run-as",P,"cat","files/wbd-split-ui-bounds.json",check=False)
 try:
  v=json.loads(raw)
  if v.get("schema")!="wbd-split-real-android-view-bounds/v1":
   raise RuntimeError("invalid view geometry schema")
  return v
 except (ValueError,TypeError):
  return {}
def scroll_to(which):
 for n in range(10):
  state=fresh_bounds()
  value=state.get("controls",{}).get(which,{})
  if value.get("visible"):
   return value
  adb("shell","input","swipe","160","550","160","195","340")
  time.sleep(0.25)
 raise RuntimeError(f"Cannot reach visible {which} in Android layout, last={state}")
def forensic():
 # Never invoke an additional uiautomator. Retain exactly the app-owned
 # diagnostic and status, so UI/layout errors are not mistaken for su errors.
 files={}
 for name in ("wbd-split-settings.json","wbd-split-validation.json","wbd-split-ui-bounds.json"):
  raw=adb("shell","run-as",P,"cat","files/"+name,check=False)
  files[name]=raw[:9000]
 (O/"split-failure-forensic.json").write_text(json.dumps({
  "files":files,
  "activity":adb("shell","dumpsys","activity","activities",check=False)[-12000:],
  "private_listing":adb("shell","run-as",P,"ls","-l","files",check=False),
  "recent_logcat":adb("logcat","-d","-t","350",check=False)[-25000:]
 },ensure_ascii=False,indent=2)+"\\n")
 return {k:v[:450] for k,v in files.items()}
def wait_config():
 last_raw="";last_val=""
 for _ in range(70):
  last_raw=adb("shell","run-as",P,"cat","files/wbd-split-settings.json",check=False)
  last_val=adb("shell","run-as",P,"cat","files/wbd-split-validation.json",check=False)
  try:
   cfg=json.loads(last_raw);report=json.loads(last_val)
   if report.get("status")=="SUPPORTED_IN_SCOPE":
    return cfg,report
   if report.get("status") in ("FAIL","UNAVAILABLE","PERMISSION_DENIED"):
    raise RuntimeError(f"native Root validation rejected settings: {report}")
  except ValueError:pass
  time.sleep(0.4)
 raise RuntimeError(f"real UI config/native readback incomplete; snapshot={forensic()}")
# Deliberately do NOT rerun the uiautomator service: it was already run
# successfully as part of device-diagnostic-ui.py on this same boot/source.
first=O/"ui.xml"
if not first.is_file():raise RuntimeError("missing first-run authentic uiautomator screen snapshot")
nodes=list(ET.fromstring(first.read_text()).iter("node"))
buttons=[n for n in nodes if "Android 分流/全局设置" in n.get("text","") and
         "Button" in n.get("class","") and n.get("enabled")=="true"]
if len(buttons)!=1:raise RuntimeError("actual first-Activity Split Settings button not identified")
m=re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",buttons[0].get("bounds",""))
if not m:raise RuntimeError("real Split settings button bounds missing")
l,t,r,b=map(int,m.groups())
if l<0 or t<80 or b>640 or r>320 or b-t<24:
 raise RuntimeError("real button obscured/out-of-bounds")
adb("shell","run-as",P,"rm","-f","files/wbd-split-settings.json",
    "files/wbd-split-validation.json","files/wbd-split-ui-bounds.json")
adb("shell","am","start","-W","-n",P+"/.DeviceDiagnosticActivity")
time.sleep(0.25)
adb("shell","input","tap",str((l+r)//2),str((t+b)//2))
# Confirm real Activity transition, not an imaginary click.
for _ in range(15):
 active=adb("shell","dumpsys","activity","activities",check=False)
 if "SplitSettingsActivity" in active:break
 time.sleep(0.25)
else:raise RuntimeError("real tap did not open SplitSettingsActivity")
for _ in range(15):
 if fresh_bounds().get("controls"):break
 time.sleep(0.3)
else:raise RuntimeError("SplitSettingsActivity did not emit its on-screen widget bounds")
tap_bounds(scroll_to("package"),"package")
adb("shell","input","text","uid:10502")
adb("shell","input","keyevent","4") # hide IME
time.sleep(0.3)
state=fresh_bounds()
if state.get("default_mode")!="split" or state.get("app_mode")!="global":
 raise RuntimeError("UI did not select split default / global per-app mode")
tap_bounds(scroll_to("add"),"add")
# Wait for the *actual* App override list to change and for Android to
# finish relayout before tapping Save. A stale coordinate can hit the list.
for _ in range(30):
 state=fresh_bounds()
 if state.get("last_action")=="add_clicked" and state.get("override_count")==1:
  break
 time.sleep(0.2)
else:
 raise RuntimeError(f"Add tap did not update App override list: {forensic()}")
tap_bounds(scroll_to("save"),"save")
# On slow CI emulators native su may take seconds. We require an actual
# App save click witness, rather than presuming a touch was delivered.
for _ in range(20):
 state=fresh_bounds()
 if state.get("last_action") in ("save_clicked","save_started","save_completed","save_config_error"):
  break
 time.sleep(0.2)
else:
 raise RuntimeError(f"Save tap did not reach App button: {forensic()}")
if state.get("last_action")=="save_config_error":
 raise RuntimeError(f"App settings rejected before Root call: {forensic()}")
config,report=wait_config()
(O/"split-settings.json").write_text(json.dumps(config,ensure_ascii=False,indent=2)+"\n")
(O/"split-validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
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
manifest=json.load(open("out/diag/cn-geosite-provenance.json"))
assert manifest["output_distinct_rules"]>1000
assert config.get("geosite_sha256")==manifest["text_sha256"]
assert report.get("geosite",{}).get("sha256")==manifest["text_sha256"]
assert report.get("geosite",{}).get("total_rules")==manifest["output_distinct_rules"]
assert report.get("geosite_cn_com_direct_dns_verified") is True
dns=report.get("dns_udp_gate",{})
assert dns.get("status")=="SUPPORTED_IN_SCOPE",dns
evidence=dns.get("evidence",{})
assert evidence.get("actual_kernel_dns_udp") is True
assert evidence.get("check_count")==6
checks=evidence.get("checks",[])
assert all(x.get("dns_transaction_verified") is True for x in checks)
assert sum("direct" in x.get("purpose_egress","") for x in checks)==4
assert sum("tunnel" in x.get("purpose_egress","") for x in checks)==2
assert all(x.get("answer_A")=="8.8.8.8" for x in checks)
assert evidence.get("real_upstream_direct_DNS")=="NOT_RUN"
assert evidence.get("android_system_dns_interception")=="NOT_RUN"
assert report.get("geosite",{}).get("suffixes",0)>1000
assert any(x.get("uid")==10502 and x.get("mode")=="global" for x in report.get("per_app_modes",[]))
print("ANDROID_SPLIT_PER_APP_SETTINGS_UI_CONFIG_VALIDATION_PASS")
print("CN intervals:",report["compiled_cn_ipv4_intervals"],
      "DNS:",report["dns_direct"],report["dns_tunnel"],
      "OS installed:",report["installed"],"UDP/53 real private netns:",dns["status"])
