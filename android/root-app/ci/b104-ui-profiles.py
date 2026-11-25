#!/usr/bin/env python3
"""Signed-APK complete profile persistence, disposable fixture credentials, no START."""
import argparse
import importlib.util
import json
import re
import struct
import subprocess
import tempfile
import time
from io import BytesIO
from pathlib import Path

spec=importlib.util.spec_from_file_location("ui",Path(__file__).with_name("x86-ui-smoke.py"))
ui=importlib.util.module_from_spec(spec);spec.loader.exec_module(ui)
adb,dump=ui.adb,ui.dump
PKG="org.wbdnext.rootclient"

def bounds(n):
    return tuple(map(int,re.findall(r"\d+",n.get("bounds",""))))

def scrollable(root):
    nodes=[n for n in root.iter("node") if n.get("scrollable")=="true" and len(bounds(n))==4]
    return next((n for n in nodes if n.get("class")=="android.widget.ScrollView"),nodes[0] if nodes else None)

def swipe(view,down):
    if view is None:
        w,h=map(int,re.findall(r"(\d+)x(\d+)",adb("shell","wm","size").decode())[-1])
        a,b,c,d=0,h//4,w,h*9//10
    else:
        a,b,c,d=bounds(view)
    # The production page cards have 16dp of inner padding. Start the
    # page gesture in that gutter, not inside an EditText/PEM editor.
    x=a+max(2,(c-a)//40) if view is not None and view.get("class")=="android.widget.ScrollView" else (a+c)//2
    low,high=b+(d-b)*3//4,b+(d-b)//4
    y1,y2=(low,high) if down else (high,low)
    adb("shell","input","swipe",str(x),str(y1),str(x),str(y2),"350")
    time.sleep(.25)

def find_scrolled(match,error):
    # A prior edit can leave the viewport partway down the page.
    for down in (True,False):
        previous=None
        for _ in range(20):
            root=dump()
            for n in root.iter("node"):
                rect=bounds(n)
                if match(n) and len(rect)==4 and rect[2]>rect[0] and rect[3]-rect[1]>=24:
                    return n
            view=scrollable(root)
            signature=tuple((n.get("class"),n.get("bounds"),n.get("content-desc"),n.get("text"))
                            for n in (view if view is not None else root).iter("node"))
            if signature==previous:break
            previous=signature
            swipe(view,down)
    raise RuntimeError(error)

def locate(text,partial=False):
    return find_scrolled(lambda n: text in n.get("text","") if partial else n.get("text","")==text,
                         "UI control not found: "+text)
def click(n):
    a,b,c,d=map(int,re.findall(r"\d+",n.get("bounds","")))
    adb("shell","input","tap",str((a+c)//2),str((b+d)//2));time.sleep(.3)
def tap(text,partial=False):click(locate(text,partial))
def page(text):
    # Navigation tabs remain visible; page action clears the old edit focus.
    ui.tap(text);time.sleep(.3)
def field(label):
    return find_scrolled(lambda n: n.get("class")=="android.widget.EditText" and
                         n.get("content-desc")==label,
                         "edit field not visible: "+label)
def fill(label,value):
    n=field(label);old=n.get("text","");click(n)
    adb("shell","input","keyevent","KEYCODE_MOVE_END")
    if n.get("password")=="true":adb("shell","input","keyevent",*(["KEYCODE_DEL"]*80))
    else:
        for _ in old:adb("shell","input","keyevent","KEYCODE_DEL")
    adb("shell","input","text",value);adb("shell","input","keyevent","4")
    time.sleep(.3)
def check_field(label,value):
    n=field(label)
    if n.get("text")!=value:raise RuntimeError("saved field mismatch: "+label)
def setcheck(label,value):
    n=locate(label,True)
    if (n.get("checked")=="true")!=value:click(n)
def checkcheck(label,value):
    if (locate(label,True).get("checked")=="true")!=value:raise RuntimeError("saved toggle mismatch: "+label)
def select_mode(old,new):
    page("连接");tap(old);tap(new)
def choose_slot(current,target):
    page("服务器");tap(current,True);tap(target,True)

def picker_find(values,partial=False):
    for _ in range(12):
        for n in dump().iter("node"):
            text=n.get("text","").casefold()
            desc=n.get("content-desc","").casefold()
            if any((v.casefold() in text or v.casefold() in desc) if partial else
                   (v.casefold()==text or v.casefold()==desc) for v in values):
                return n
        time.sleep(.4)
    raise RuntimeError("system file picker control not found: "+"/".join(values))
def open_downloads():
    for n in dump().iter("node"):
        if n.get("text","").casefold() in ("downloads","下载") and n.get("class","").endswith("TextView"):
            if n.get("clickable")=="true":click(n)
            return
    click(picker_find(["Show roots","Open navigation drawer","显示根目录"],True))
    click(picker_find(["Downloads","下载"]))
def complete_slots(raw):
    """Decode actual WBPC slots; Properties.store adds a timestamp comment."""
    stream=BytesIO(raw)
    def take(n):
        data=stream.read(n)
        if len(data)!=n:raise RuntimeError("truncated server backup")
        return data
    def u32():return struct.unpack(">I",take(4))[0]
    def utf():return take(struct.unpack(">H",take(2))[0])
    if take(4)!=b"WBPC" or u32()!=10:raise RuntimeError("wrong complete backup format")
    slots=[]
    for _ in range(10):
        present=take(1)
        if present==b"\x00":slots.append(None);continue
        if present!=b"\x01":raise RuntimeError("wrong slot marker")
        profile=BytesIO(take(u32()))
        if profile.read(4)!=b"WBP2":raise RuntimeError("wrong server profile format")
        label=profile.read(struct.unpack(">H",profile.read(2))[0])
        length=struct.unpack(">I",profile.read(4))[0]
        settings=profile.read(length)
        if len(settings)!=length or profile.read():raise RuntimeError("wrong settings length")
        # Ignore only Properties.store comment/empty lines and iteration order.
        fields=tuple(sorted(line for line in settings.splitlines()
                            if line and not line.startswith((b"#",b"!"))))
        slots.append((label,fields,utf(),utf(),take(u32())))
    if stream.read():raise RuntimeError("trailing server backup bytes")
    return slots

def pick_document(name):
    click(picker_find([name]))
    # ACTION_OPEN_DOCUMENT normally returns on a single file tap. Some
    # DocumentsUI layouts present a separate Open button after selection.
    for _ in range(12):
        root=dump()
        if any(n.get("package")==PKG for n in root.iter("node")):
            return
        for n in root.iter("node"):
            if (n.get("text","").casefold() in ("open","打开") and
                n.get("enabled")=="true" and n.get("clickable")=="true"):
                click(n)
                break
        time.sleep(.4)
    raise RuntimeError("system document selection did not return to WBD")

def check_ca(expected):
    n=field("自定义 CA（PEM）")
    density=int(re.findall(r"(\d+)",adb("shell","wm","density").decode())[-1])
    a,b,c,d=bounds(n)
    if d-b>round(120*density/160)+2:
        raise RuntimeError("CA editor expands beyond its bounded viewport")
    # UI hierarchy XML may normalize line breaks; the actual exported CA
    # bytes below must still match the original certificate exactly.
    if "".join(n.get("text","").split())!="".join(expected.decode("ascii").split()):
        raise RuntimeError("selected server CA field does not match fixture")

def import_fixture_ca():
    name="wbd-b124-fixture-ca.pem"
    remote="/sdcard/Download/"+name
    with tempfile.TemporaryDirectory() as tmp:
        cert=Path(tmp)/name
        subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-nodes","-days","2",
                        "-subj","/CN=WBD B124 CI only","-keyout",str(Path(tmp)/"key.pem"),
                        "-out",str(cert)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        expected=cert.read_bytes().strip()
        adb("push",str(cert),remote)
    try:
        page("服务器");tap("导入 CA 证书");open_downloads()
        pick_document(name)
        page("服务器")
        check_ca(expected)
    finally:
        adb("shell","rm","-f",remote)
    return expected

def export_backup(name):
    page("服务器");tap("导出全部服务器");open_downloads()
    if name!="wbd-root-ten-profiles.wbpb":
        n=next((n for n in dump().iter("node") if n.get("class")=="android.widget.EditText"
                and (n.get("resource-id","").endswith(":id/filename") or
                     n.get("text")=="wbd-root-ten-profiles.wbpb")),None)
        if n is None:raise RuntimeError("system file picker filename not visible")
        click(n)
        adb("shell","input","keyevent","KEYCODE_MOVE_END")
        adb("shell","input","keyevent",*(["KEYCODE_DEL"]*80))
        adb("shell","input","text",name)
    click(picker_find(["Save","保存"]))
    # Real file bytes, rather than an Activity status message, qualify
    # export. A successful picker return without a file is still a failure.
    for _ in range(12):
        root=dump()
        if any(n.get("package")==PKG for n in root.iter("node")):
            try:
                raw=adb("exec-out","cat","/sdcard/Download/"+name)
                if raw[:4]==b"WBPC":return raw
            except subprocess.CalledProcessError:
                pass
        time.sleep(.4)
    raise RuntimeError("complete backup file not written: "+name)

def complete_backup_roundtrip(expected_ca):
    name="wbd-root-ten-profiles.wbpb"
    restored_name="wbd-root-ten-profiles-restored.wbpb"
    try:
        slots=complete_slots(export_backup(name))
        expected={0:(b"NormalDaily",b"ExamplePass123",b"ExampleKey123",expected_ca),
                  1:(b"GameDaily",b"SecondExamplePass123",b"SecondExampleKey123",b""),
                  9:(b"TenthDaily",b"SecondExamplePass123",b"SecondExampleKey123",b"")}
        for i,slot in enumerate(slots):
            if i not in expected:
                if slot is not None:raise RuntimeError("unexpected saved server slot")
            elif slot is None or (slot[0],*slot[2:])!=expected[i]:
                raise RuntimeError("complete saved server mismatch at slot "+str(i+1))
            else:
                normal=i==0
                fields=dict(line.split(b"=",1) for line in slot[1])
                required={
                    b"peer":b"192.0.2.10" if normal else b"192.0.2.20",
                    b"sni":b"normal.example.test" if normal else b"game.example.test",
                    b"account":b"daily-ci" if normal else b"daily-game-ci",
                    b"fec_mode":b"normal" if normal else b"game4-fixed",
                    b"physical_dns":b"true" if normal else b"false",
                    b"cn_split_dns":b"false" if normal else b"true",
                    b"tunnel_dns":b"false",
                    b"outer_mtu":{0:b"1460",1:b"1380",9:b"1400"}[i],
                    b"native_health_seconds":b"15" if normal else b"30",
                }
                for key,value in required.items():
                    if fields.get(key)!=value:
                        raise RuntimeError("saved server setting mismatch at slot "+str(i+1)+": "+key.decode())
        page("服务器");tap("删除服务器配置");locate("配置槽10（空）")
        page("服务器");tap("导入服务器备份");open_downloads()
        pick_document(name)
        # The deleted slot must actually be restored; no status-only pass.
        page("服务器");locate("配置槽10 · TenthDaily",True)
        page("服务器");tap("载入并编辑");locate("已载入槽位10：TenthDaily",True)
        page("设置");check_field("外层 MTU（576–1500，默认1460）","1400")
        if complete_slots(export_backup(restored_name))!=slots:
            raise RuntimeError("complete backup fields changed after restore")
    finally:
        adb("shell","rm","-f","/sdcard/Download/"+name,"/sdcard/Download/"+restored_name)

def main(out):
    report={}
    try:
        page("连接");locate("未连接")
        page("服务器");fill("服务器地址（IPv4 / 域名）","192.0.2.10")
        fill("TLS 服务器名称（SNI）","normal.example.test")
        fill("用户名","daily-ci")
        fill("密码","ExamplePass123")
        fill("Route Key（8–32 位字母数字 / 64 位 Hex）","ExampleKey123")
        expected_ca=import_fixture_ca()
        report["ca_saf_import_readback"]="PASS"
        page("应用");setcheck("全部直连 DNS",True)
        page("服务器");fill("服务器名称","NormalDaily")
        tap("保存全部设置 · 槽",True);locate("已保存槽位1：NormalDaily",True)
        report["save_normal"]="PASS"
        select_mode("normal","game4-fixed")
        page("应用");setcheck("CN 分流 DNS",True)
        page("服务器");fill("服务器地址（IPv4 / 域名）","192.0.2.20")
        fill("TLS 服务器名称（SNI）","game.example.test")
        fill("用户名","daily-game-ci")
        fill("密码","SecondExamplePass123")
        fill("Route Key（8–32 位字母数字 / 64 位 Hex）","SecondExampleKey123")
        tap("清空证书")
        check_ca(b"")
        report["ca_clear_readback"]="PASS"
        choose_slot("配置槽1 · NormalDaily","配置槽2（空）")
        # spinner and profile fields share the saved-server section.
        fill("服务器名称","GameDaily")
        tap("保存全部设置 · 槽",True);locate("已保存槽位2：GameDaily",True)
        report["save_game"]="PASS"
        # Explicitly save more than MTU: change Health too and read both after restart.
        mtu="外层 MTU（576–1500，默认1460）"
        page("设置");fill(mtu,"1380");tap("15");tap("30")
        tap("保存全部设置 · 槽2")
        # The footer can be shorter than a tappable control on stock Android.
        # Reload the persisted slot after changing the unsaved MTU, so the
        # real cross-page Save is tested rather than the footer's text.
        fill(mtu,"1390")
        page("服务器");tap("载入并编辑");locate("已载入槽位2：GameDaily",True)
        page("设置");check_field(mtu,"1380");locate("30")
        report["cross_page_save_slot2_readback"]="PASS"
        choose_slot("配置槽2 · GameDaily","配置槽10（空）")
        fill("服务器名称","TenthDaily")
        tap("保存全部设置 · 槽",True);locate("已保存槽位10：TenthDaily",True)
        report["save_tenth"]="PASS"
        adb("shell","am","force-stop",PKG)
        adb("shell","am","start","-W","-n",PKG+"/.RootClientActivity");time.sleep(1)
        page("连接");locate("game4-fixed")
        page("设置");check_field(mtu,"1380");locate("30")
        page("服务器");check_field("服务器地址（IPv4 / 域名）","192.0.2.20")
        page("应用");checkcheck("CN 分流 DNS",True)
        report["ordinary_settings_process_restart"]="PASS"
        choose_slot("配置槽10 · TenthDaily","配置槽1 · NormalDaily")
        tap("载入并编辑");locate("已载入槽位1：NormalDaily",True)
        page("连接");locate("normal")
        page("服务器");check_field("服务器地址（IPv4 / 域名）","192.0.2.10")
        page("应用");checkcheck("全部直连 DNS",True)
        page("服务器");check_field("用户名","daily-ci")
        check_ca(expected_ca)
        # Actual unmasked values are verified via the portable backup below.
        report["load_normal"]="PASS"
        choose_slot("配置槽1 · NormalDaily","配置槽2 · GameDaily")
        tap("载入并编辑");locate("已载入槽位2：GameDaily",True)
        page("连接");locate("game4-fixed")
        page("服务器");check_field("服务器地址（IPv4 / 域名）","192.0.2.20")
        page("应用");checkcheck("CN 分流 DNS",True)
        page("服务器");check_field("用户名","daily-game-ci")
        check_ca(b"")
        # Actual unmasked values are verified via the portable backup below.
        report["load_game"]="PASS"
        choose_slot("配置槽2 · GameDaily","配置槽10 · TenthDaily")
        tap("载入并编辑");locate("已载入槽位10：TenthDaily",True)
        page("设置");check_field(mtu,"1380")
        fill(mtu,"1400");tap("保存全部设置 · 槽10")
        fill(mtu,"1390")
        page("服务器");tap("载入并编辑");locate("已载入槽位10：TenthDaily",True)
        page("设置");check_field(mtu,"1400")
        complete_backup_roundtrip(expected_ca);report["complete_saf_export_import"]="PASS"
        page("设置");tap("诊断与恢复");locate("导出诊断");report["diagnostics_menu"]="PASS"
        page("连接");locate("未连接")
        tap("关闭程序");time.sleep(.5)
        activities=adb("shell","dumpsys","activity","activities").decode()
        if any(PKG in line for line in activities.splitlines() if "topResumedActivity" in line or "mResumedActivity" in line):
            raise RuntimeError("close button left WBD foreground activity running")
        adb("shell","am","start","-W","-n",PKG+"/.RootClientActivity");time.sleep(1)
        page("连接");locate("未连接")
        report["close_and_reopen"]="PASS"
        report["load_tenth_and_save_parameters"]="PASS";report["no_start"]="PASS"
        print("B124_UI_COMPLETE_SERVER_SAVE_AND_SAF_ROUNDTRIP_PASS")
        print("B115_UI_TEN_SLOTS_SAVE_MTU_RESTART_PASS")
        print("B104_UI_TWO_PROFILES_RESTART_PASS")
    except Exception:
        # This fresh CI guest contains only disposable fixture credentials.
        # Capture the failed view before cleanup, not an unrelated home shot.
        try:
            (out/"ui-profile-failure.png").write_bytes(adb("exec-out","screencap","-p"))
        except Exception:
            pass
        raise
    finally:
        (out/"b104-ui-profiles.json").write_text(json.dumps(report,indent=2)+"\n")
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    main(p.parse_args().out)
