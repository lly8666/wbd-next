#!/usr/bin/env python3
"""Actual Android UI cold interactions, no server credentials or START."""
import argparse
import json
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

def adb(*args, timeout=25):
    return subprocess.check_output(["adb",*args],timeout=timeout)

def dump():
    for _ in range(5):
        try:
            adb("shell","uiautomator","dump","/sdcard/wbd-ui-smoke.xml",timeout=20)
            return ET.fromstring(adb("shell","cat","/sdcard/wbd-ui-smoke.xml"))
        except (subprocess.SubprocessError,ET.ParseError):
            time.sleep(.7)
    raise RuntimeError("Android UI hierarchy unavailable")

def find(text, contains=False, scroll=False):
    for _ in range(4 if scroll else 1):
        root=dump()
        for n in root.iter("node"):
            value=n.get("text","")
            if (text in value if contains else value==text):
                return n
        if scroll:
            # Work in the central scroll viewport; header stays pinned.
            size=adb("shell","wm","size").decode()
            match=re.findall(r"(\d+)x(\d+)",size)
            w,h=map(int,match[-1])
            adb("shell","input","swipe",str(w//2),str(h*3//4),str(w//2),str(h//3),"350")
            time.sleep(.3)
    raise RuntimeError("missing Android UI element: "+text)

def tap(text, scroll=False):
    n=find(text,scroll=scroll)
    nums=list(map(int,re.findall(r"\d+",n.get("bounds",""))))
    if len(nums)!=4:raise RuntimeError("invalid bounds")
    adb("shell","input","tap",str((nums[0]+nums[2])//2),str((nums[1]+nums[3])//2))
    time.sleep(.5)

def shot(out,name):
    (out/("ui-"+name+".png")).write_bytes(adb("exec-out","screencap","-p"))

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    result={}
    try:
        find("未连接");find("全局普通应用",contains=True)
        shot(a.out,"home");result["home"]="PASS"
        tap("选择 / 切换服务器");find("选择服务器");adb("shell","input","keyevent","4");time.sleep(.4)
        tap("服务器");find("已保存服务器");shot(a.out,"servers");result["servers"]="PASS"
        tap("应用");scope=find("全局接管普通应用（默认）")
        if scope.get("checked")!="true":raise RuntimeError("fresh app must default to all ordinary apps")
        tap("全局接管普通应用（默认）")
        if find("全局接管普通应用（默认）").get("checked")!="false":raise RuntimeError("scope toggle")
        tap("CN 分流（国内直连）",scroll=True)
        find("按目标分流",contains=True,scroll=True)
        shot(a.out,"apps-split");result["selected_app_cn_split"]="PASS"
        tap("连接");tap("应用")
        tap("全局接管普通应用（默认）")
        tap("全量隧道",scroll=True);find("全量隧道（下次连接生效）",contains=True,scroll=True)
        shot(a.out,"apps-full");result["global_full"]="PASS"
        tap("设置");find("传输参数");shot(a.out,"settings");result["settings"]="PASS"
        tap("连接");find("未连接");result["no_root_start"]="PASS"
        print("ANDROID_UI_NAVIGATION_PASS")
    finally:
        (a.out/"ui-receipt.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
if __name__=="__main__":main()
