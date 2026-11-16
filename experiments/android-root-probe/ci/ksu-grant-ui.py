#!/usr/bin/env python3
"""Grant only our installed diagnostic app through the *real* KernelSU Manager UI.
No ksud/kernel allowlist writes, patched su binary, fake service, or adb UID impersonation.
Fail closed and preserve UI XML/screenshot for API differences.
"""
import json, re, subprocess, time, xml.etree.ElementTree as ET
from pathlib import Path
OUT=Path("out/ksu")
PKG="org.wbdnext.rootprobe"
APP_LABEL="WBD app su probe"

def adb(*args, check=True, timeout=35):
    p=subprocess.run(["adb",*args],capture_output=True,text=True,timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(f"adb {args} exited {p.returncode}: {p.stderr[:500]}")
    return p.stdout
def capture(stage):
    try:
        adb("shell","screencap","-p","/sdcard/ksu-screen.png",check=False)
        adb("pull","/sdcard/ksu-screen.png",str(OUT/f"screen-{stage}.png"),check=False)
    except Exception:
        pass
    last=""
    for _ in range(3):
        try:
            adb("shell","uiautomator","dump","/sdcard/ksu-ui.xml",timeout=35)
            last=adb("shell","cat","/sdcard/ksu-ui.xml",timeout=20)
            if "<hierarchy" in last:break
        except Exception as e:
            last=str(e)
        time.sleep(2)
    (OUT/f"ui-{stage}.xml").write_text(last)
    if "<hierarchy" not in last:
        raise RuntimeError(f"no UI hierarchy in {stage}: {last[:150]}")
    nodes=list(ET.fromstring(last).iter("node"))
    records=[{k:n.get(k,"") for k in ("text","content-desc","class","resource-id","bounds","checked","clickable")} for n in nodes]
    (OUT/f"ui-{stage}-nodes.json").write_text(json.dumps(records,indent=2))
    return records

def choose(records, needles, stage, expect_app=False):
    if expect_app:
        page=" ".join(n["text"]+" "+n["content-desc"] for n in records).casefold()
        if APP_LABEL.casefold() not in page and PKG not in page:
            raise RuntimeError(f"refuse grant outside verified {PKG} details on {stage}")
    for term in needles:
        matches=[n for n in records if term in (n["text"]+" "+n["content-desc"]).casefold()]
        for n in matches:
            m=re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",n["bounds"])
            if not m:continue
            a,b,c,d=map(int,m.groups())
            if c-a<10 or d-b<10:continue
            adb("shell","input","tap",str((a+c)//2),str((b+d)//2))
            time.sleep(2)
            return n
    raise RuntimeError(f"no UI node {needles} on {stage}")

result={"manager":"me.weishu.kernelsu","app":PKG,"outcome":"NOT_GRANTED"}
try:
    installed=adb("shell","pm","path","me.weishu.kernelsu",check=False,timeout=20)
    if "package:" not in installed:
        raise RuntimeError("KernelSU official manager not installed in user0 after second boot")
    # Explicit official activity; avoid monkey package resolution ambiguity.
    adb("shell","am","start","-n","me.weishu.kernelsu/me.weishu.kernelsu.ui.MainActivity",timeout=25)
    time.sleep(4)
    home=capture("home")
    choose(home,["superuser","超级用户"],"home")
    listing=capture("superuser")
    try:
        choose(listing,[APP_LABEL.casefold(),PKG.casefold()],"superuser")
        result["selection"]="ACCESSIBILITY_NODE"
    except RuntimeError:
        # KernelSU v3.3.1 Compose UI visually shows our app second row on this
        # exact 320x640 fresh AVD, while uiautomator can expose only bottom tabs.
        # This is a SINGLE package-specific visual-layout fallback, not grant.
        # The next details page MUST explicitly identify our exact package
        # before the grant switch can be touched.
        size=adb("shell","wm","size").strip()
        target=adb("shell","pm","path",PKG,check=False).strip()
        texts=" ".join(n["text"]+" "+n["content-desc"] for n in listing).casefold()
        if "320x640" not in size or not target.startswith("package:") or "superuser" not in texts:
            raise RuntimeError("refuse coordinate fallback: unexpected AVD size, app package or UI state")
        result["selection"]="APP_ROW_SECOND_320x640_VERIFY_ON_DETAIL"
        adb("shell","input","tap","160","295")
        time.sleep(3)
    detail=capture("app-detail")
    label=(APP_LABEL.casefold() in " ".join(n["text"]+" "+n["content-desc"] for n in detail).casefold()
           or PKG in " ".join(n["text"]+" "+n["content-desc"] for n in detail))
    if not label:raise RuntimeError("detail page did not identify our exact test package; no grant")
    # Prefer explicit root-grant UI labels; a switch is touched only within verified app details.
    positive=[n for n in detail if n["checked"]=="true" and
              ("switch" in n["class"].lower() or "allow" in n["text"].lower())]
    if positive:
        result["outcome"]="ALREADY_GRANTED_IN_MANAGER_UI"
    else:
        try:
            choose(detail,["allow root","grant root","allow su","root access",
                  "授权超级用户","允许超级用户","允许 root","grant","allow","允许"],
                  "app-detail",expect_app=True)
        except RuntimeError:
            switches=[n for n in detail if "switch" in n["class"].lower() and
                      n["checked"]!="true"]
            if len(switches)==1:
                n=switches[0]
                m=re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",n["bounds"])
                if not m:raise RuntimeError("grant toggle bounds unavailable")
                a,b,c,d=map(int,m.groups())
                adb("shell","input","tap",str((a+c)//2),str((b+d)//2))
                result["grant_action"]="ACCESSIBILITY_SWITCH"
            else:
                # Actual KSU 3.3.1 Compose detail screenshot from pinned AVD:
                # "Superuser" row [12,230]-[308,290], OFF toggle x268,y260.
                # Android UIAutomator sees the row, but not a Switch class.
                # The exact PKG has already been verified on THIS detail page.
                size=adb("shell","wm","size").strip()
                superuser=[n for n in detail if n["text"].casefold()=="superuser"
                          and "[66,250][143,270]"==n["bounds"]]
                row=[n for n in detail if n["clickable"]=="true"
                     and n["bounds"]=="[12,230][308,290]"]
                pkglabel=[n for n in detail if PKG==n["text"]]
                if "320x640" not in size or len(superuser)!=1 or len(row)!=1 or len(pkglabel)!=1:
                    raise RuntimeError("refuse Compose toggle fallback: exact package, Superuser row or size differs")
                adb("shell","input","tap","267","260")
                result["grant_action"]="VERIFIED_PACKAGE_COMPOSE_SUPERUSER_TOGGLE_267_260"
            time.sleep(2)
        after=capture("after-grant")
        # A confirmation dialog may be shown, only confirm if visible.
        page=" ".join(n["text"]+" "+n["content-desc"] for n in after).casefold()
        if any(term in page for term in ["confirm","确认","yes, grant"]):
            try:
                choose(after,["confirm","确认","yes, grant"],"confirmation")
                after=capture("after-confirm")
            except RuntimeError:
                pass
        checked=[n for n in after if n["checked"]=="true" and
                 ("switch" in n["class"].lower() or "allow" in n["text"].lower())]
        if not checked:
            # Some manager versions use declarative Compose toggles with no checked switch.
            # The actual native app-su check below must still prove the permission was really granted.
            result["outcome"]="GRANT_TAP_WITHOUT_UI_READBACK"
        else:
            result["outcome"]="GRANTED_IN_MANAGER_UI"
    result["ui_result"]="APP_PACKAGE_CONFIRMED"
except Exception as e:
    result["outcome"]="MANAGER_UI_BLOCKED"
    result["error"]=str(e)
finally:
    (OUT/"grant-ui-result.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
if result["outcome"]=="MANAGER_UI_BLOCKED":
    raise SystemExit("KernelSU manager app grant could not be proven via UI")
