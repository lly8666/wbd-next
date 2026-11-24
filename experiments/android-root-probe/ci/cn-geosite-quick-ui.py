#!/usr/bin/env python3
"""Real on-screen Android SplitSettings quick DNS validation; no keyboard.

Android API36 low-memory guest intermittently ignores IME and scroll touches.
This fixture uses a visible one-click Root validation control with the same
saveButton.onClick action as manual Save; never ADB-pushes native binaries,
fabricates JSON, or mutates the main Android netd. Per-App manual editing is
separate and had a same-branch real UI positive in SOURCE 75b5596.
"""
import json,re,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
P="org.wbdnext.rootprobe"
O=Path("out/device-diag");O.mkdir(parents=True,exist_ok=True)
def adb(*args,check=True,timeout=35):
 p=subprocess.run(["adb",*args],capture_output=True,text=True,timeout=timeout)
 if check and p.returncode:
  raise RuntimeError(f"adb {args!r} rc={p.returncode}: {p.stdout[:200]} {p.stderr[:200]}")
 return p.stdout
def get_json(name):
 try:return json.loads(adb("shell","run-as",P,"cat","files/"+name,check=False))
 except (ValueError,TypeError):return {}
def tap(rect,label):
 l,t,r,b=(int(rect[k]) for k in ("left","top","right","bottom"))
 if not rect.get("visible") or r-l<45 or b-t<28 or t<80 or b>640:
  raise RuntimeError(f"actual view {label} not clickable: {rect}")
 adb("shell","input","tap",str((l+r)//2),str((t+b)//2))
def snapshot():
 v=get_json("wbd-split-ui-bounds.json")
 if v.get("schema")!="wbd-split-real-android-view-bounds/v1":return {}
 return v
def failure(reason):
 evidence={
  "reason":reason,
  "view":snapshot(),
  "config":get_json("wbd-split-settings.json"),
  "validation":get_json("wbd-split-validation.json"),
  "recent_logcat":adb("logcat","-d","-t","200",check=False)[-12000:],
  "activity":adb("shell","dumpsys","activity","activities",check=False)[-9000:]
 }
 (O/"cn-geosite-quick-failure.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n")
 raise RuntimeError(f"{reason}: {str(evidence)[:1100]}")
# Original full diagnostic UI was genuinely dumped once on this exact boot.
ui=O/"ui.xml"
if not ui.is_file():failure("original UIAutomator one-shot snapshot missing")
nodes=list(ET.fromstring(ui.read_text()).iter("node"))
matches=[x for x in nodes if
  "Android 分流/全局设置" in x.get("text","") and
  "Button" in x.get("class","") and x.get("enabled")=="true"]
if len(matches)!=1:failure("cannot locate original real Settings entry")
bounds=re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",matches[0].get("bounds",""))
if not bounds:failure("original button bounds invalid")
l,t,r,b=map(int,bounds.groups())
if l<0 or t<80 or b>640 or r>320:failure("original Settings button not on AVD screen")
adb("shell","run-as",P,"rm","-f","files/wbd-split-settings.json",
    "files/wbd-split-validation.json","files/wbd-split-ui-bounds.json")
adb("shell","am","start","-W","-n",P+"/.DeviceDiagnosticActivity")
time.sleep(.5)
adb("shell","input","tap",str((l+r)//2),str((t+b)//2))
state={}
for i in range(35):
 state=snapshot()
 if (state.get("window_focused") is True and
     state.get("controls",{}).get("quick_dns_check",{}).get("visible") is True):
  break
 time.sleep(.25)
else:failure("Split Settings actual UI quick button not focused/visible")
# Wait for layout to settle; no ScrollView momentum or IME interaction.
time.sleep(.65)
state=snapshot()
if not state.get("window_focused") or state.get("ime_visible"):
 failure("quick DNS view has unexpected foreground/IME state")
tap(state["controls"]["quick_dns_check"],"quick_dns_check")
config=report=None
for _ in range(100):
 config=get_json("wbd-split-settings.json")
 report=get_json("wbd-split-validation.json")
 if report.get("status")=="SUPPORTED_IN_SCOPE":break
 if report.get("status") in ("FAIL","UNAVAILABLE","PERMISSION_DENIED"):
  failure("native Root CN geosite or DNS kernel rejected config")
 time.sleep(.4)
else:failure("real top Save/Root check never emitted complete successful App JSON")
(O/"split-settings.json").write_text(json.dumps(config,ensure_ascii=False,indent=2)+"\n")
(O/"split-validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
m=json.load(open("out/diag/cn-geosite-provenance.json"))
assert config.get("schema")=="wbd-android-split/v1"
assert config.get("default_mode")=="split"
assert config.get("direct_dns")=="223.5.5.5" and config.get("tunnel_dns")=="1.1.1.1"
assert config.get("no_fakeip") is True
assert len(config.get("cn_ipv4",[]))>1000
assert config.get("geosite_sha256")==m["text_sha256"]
assert report.get("status")=="SUPPORTED_IN_SCOPE" and report.get("installed") is False
assert report.get("fakeip") is False
assert report.get("compiled_cn_ipv4_intervals",0)>500
assert report.get("geosite",{}).get("sha256")==m["text_sha256"]
assert report.get("geosite",{}).get("total_rules")==m["output_distinct_rules"]>=8000
assert report.get("geosite_cn_com_direct_dns_verified") is True
assert report.get("server_bootstrap_dns")=="DIRECT_IN_ALL_MODES"
dns=report.get("dns_udp_gate",{})
assert dns.get("status")=="SUPPORTED_IN_SCOPE",dns
evidence=dns.get("evidence",{})
assert evidence.get("actual_kernel_dns_udp") is True
assert evidence.get("check_count")==6
checks=evidence.get("checks",[])
assert len(checks)==6 and all(x.get("dns_transaction_verified") is True for x in checks)
assert sum("direct" in x.get("purpose_egress","") for x in checks)==4
assert sum("tunnel" in x.get("purpose_egress","") for x in checks)==2
assert all(x.get("answer_A")=="8.8.8.8" for x in checks)
assert evidence.get("real_upstream_direct_DNS")=="NOT_RUN"
assert evidence.get("android_system_dns_interception")=="NOT_RUN"
(O/"cn-geosite-quick-summary.json").write_text(json.dumps({
  "status":"APP_ONSCREEN_ROOT_CN_GEOSITE_DNS_PRIVATE_KERNEL_PASS",
  "source":config.get("schema"),"app_ui":"ACTUAL_VISIBLE_QUICK_BUTTON_TAP",
  "saved_config":True,"app_su_native_validation":True,
  "full_cn_geosite_rules":m["output_distinct_rules"],
  "real_kernel_udp_dns_cases":evidence["check_count"],
  "fakeip":False,"real_android_main_network_installed":False,
  "per_app_text_editor_on_this_source":"NOT_RUN",
  "real_direct_dns_223_5_5_5":"NOT_RUN",
  "real_tunnel_dns_1_1_1_1":"NOT_RUN"
 },ensure_ascii=False,indent=2)+"\n")
print("APP_ONSCREEN_ROOT_CN_GEOSITE_DNS_PRIVATE_KERNEL_PASS")
print("CN geosite rules",m["output_distinct_rules"],"actual private kernel DNS cases",evidence["check_count"],
      "real Android main network installed",report["installed"])
