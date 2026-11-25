#!/usr/bin/env python3
"""Signed-APK complete profile persistence, disposable fixture credentials, no START."""
import argparse
import importlib.util
import json
import re
import time
from pathlib import Path

spec=importlib.util.spec_from_file_location("ui",Path(__file__).with_name("x86-ui-smoke.py"))
ui=importlib.util.module_from_spec(spec);spec.loader.exec_module(ui)
adb,dump=ui.adb,ui.dump
PKG="org.wbdnext.rootclient"

def swipe():
    w,h=map(int,re.findall(r"(\d+)x(\d+)",adb("shell","wm","size").decode())[-1])
    adb("shell","input","swipe",str(w//2),str(h*3//4),str(w//2),str(h//3),"300")
    time.sleep(.25)
def locate(text,partial=False):
    for _ in range(22):
        root=dump()
        for n in root.iter("node"):
            value=n.get("text","")
            if (text in value if partial else value==text):return n
        swipe()
    raise RuntimeError("UI control not found: "+text)
def click(n):
    a,b,c,d=map(int,re.findall(r"\d+",n.get("bounds","")))
    adb("shell","input","tap",str((a+c)//2),str((b+d)//2));time.sleep(.3)
def tap(text,partial=False):click(locate(text,partial))
def page(text):
    # Bottom tabs remain visible; page action resets the ScrollView.
    ui.tap(text);time.sleep(.3)
def field(label):
    for _ in range(22):
        nodes=list(dump().iter("node"))
        for i,n in enumerate(nodes):
            if n.get("text")==label:
                for v in nodes[i+1:]:
                    if v.get("class")=="android.widget.EditText":return v
                    if v.get("class")=="android.widget.TextView" and v.get("text"):break
        swipe()
    raise RuntimeError("edit field not visible: "+label)
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
def complete_backup_roundtrip():
    name="wbd-root-ten-profiles.wbpb"
    page("服务器");tap("导出全部服务器")
    open_downloads()
    click(picker_find(["Save","保存"]))
    time.sleep(1)
    locate("全部服务器已导出",True)
    raw=adb("exec-out","cat","/sdcard/Download/"+name)
    if raw[:4]!=b"WBPC":raise RuntimeError("wrong complete backup format")
    for value in (b"NormalDaily",b"GameDaily",b"TenthDaily",b"ExamplePass123",b"ExampleKey123",
                  b"SecondExamplePass123",b"SecondExampleKey123"):
        if value not in raw:raise RuntimeError("missing complete profile field")
    page("服务器");tap("删除服务器配置");locate("已删除槽位10",True)
    page("服务器");tap("导入服务器备份")
    open_downloads()
    click(picker_find([name],True))
    time.sleep(1);locate("服务器导入完成",True)
    page("服务器");tap("载入并编辑");locate("已载入槽位10：TenthDaily",True)
    page("设置");check_field("外层 MTU（576–1500，默认1460）","1400")
    # Re-export to a fresh filename after import and compare every byte.
    adb("shell","mv","/sdcard/Download/"+name,"/sdcard/Download/original-"+name)
    page("服务器");tap("导出全部服务器");open_downloads()
    click(picker_find(["Save","保存"]));time.sleep(1)
    locate("全部服务器已导出",True)
    actual=adb("exec-out","cat","/sdcard/Download/"+name)
    if actual!=raw:raise RuntimeError("complete backup changed after restore")
    adb("shell","rm","-f","/sdcard/Download/"+name,"/sdcard/Download/original-"+name)
def main(out):
    report={}
    try:
        page("连接");locate("未连接")
        page("服务器");fill("服务器地址（IPv4 / 域名）","192.0.2.10")
        fill("TLS 服务器名称（SNI）","normal.example.test")
        fill("用户名","daily-ci")
        fill("密码","ExamplePass123")
        fill("Route Key（8–32 位字母数字 / 64 位 Hex）","ExampleKey123")
        page("应用");setcheck("全部直连 DNS",True)
        page("服务器");fill("服务器名称","NormalDaily")
        tap("保存全部设置 · 槽",True);locate("已保存槽位1：NormalDaily",True)
        report["save_normal"]="PASS"
        select_mode("normal","game4-fixed")
        page("应用");setcheck("CN 分流 DNS",True)
        page("服务器");fill("服务器地址（IPv4 / 域名）","192.0.2.20")
        fill("TLS 服务器名称（SNI）","game.example.test")
        fill("密码","SecondExamplePass123")
        fill("Route Key（8–32 位字母数字 / 64 位 Hex）","SecondExampleKey123")
        choose_slot("配置槽1 · NormalDaily","配置槽2（空）")
        # spinner and profile fields share the saved-server section.
        fill("服务器名称","GameDaily")
        tap("保存全部设置 · 槽",True);locate("已保存槽位2：GameDaily",True)
        report["save_game"]="PASS"
        # Explicitly save more than MTU: change Health too and read both after restart.
        mtu="外层 MTU（576–1500，默认1460）"
        page("设置");fill(mtu,"1380");tap("15");tap("30")
        tap("保存全部设置 · 槽2")
        locate("已保存槽位2：GameDaily",True)
        page("服务器");choose_slot("配置槽2 · GameDaily","配置槽10（空）")
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
        # Actual unmasked values are verified via the portable backup below.
        report["load_normal"]="PASS"
        choose_slot("配置槽1 · NormalDaily","配置槽2 · GameDaily")
        tap("载入并编辑");locate("已载入槽位2：GameDaily",True)
        page("连接");locate("game4-fixed")
        page("服务器");check_field("服务器地址（IPv4 / 域名）","192.0.2.20")
        page("应用");checkcheck("CN 分流 DNS",True)
        page("服务器")
        # Actual unmasked values are verified via the portable backup below.
        report["load_game"]="PASS"
        choose_slot("配置槽2 · GameDaily","配置槽10 · TenthDaily")
        tap("载入并编辑");locate("已载入槽位10：TenthDaily",True)
        page("设置");check_field(mtu,"1380")
        fill(mtu,"1400");tap("保存全部设置 · 槽10")
        locate("已保存槽位10：TenthDaily",True)
        page("服务器");tap("载入并编辑");locate("已载入槽位10：TenthDaily",True)
        page("设置");check_field(mtu,"1400")
        complete_backup_roundtrip();report["complete_saf_export_import"]="PASS"
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
    finally:
        (out/"b104-ui-profiles.json").write_text(json.dumps(report,indent=2)+"\n")
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    main(p.parse_args().out)
