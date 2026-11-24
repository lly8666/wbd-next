#!/usr/bin/env python3
"""Exercise real CLI menu and interactive config on a real PTY.
Fixture inputs are synthetic; do not print the captured password dialog.
"""
import os,pty,select,subprocess,time,errno,json,sys
from pathlib import Path
tmp=Path(sys.argv[1])
def session(args,steps):
    master,slave=pty.openpty()
    p=subprocess.Popen(args,stdin=slave,stdout=slave,stderr=slave,start_new_session=True)
    os.close(slave);buf=b""
    try:
        for marker,value in steps:
            marker=marker.encode()
            until=time.monotonic()+15
            while marker not in buf:
                if time.monotonic()>until:raise AssertionError("missing real prompt "+str(marker))
                if p.poll() is not None:raise AssertionError("early exit "+str(p.returncode))
                if select.select([master],[],[],.1)[0]:
                    buf+=os.read(master,65536)
            buf=buf.split(marker,1)[1]
            if value is not None:
                if "密码" in marker.decode():time.sleep(.15)
                os.write(master,(value+"\n").encode())
        if p.wait(timeout=15):raise AssertionError("interactive command failed")
    finally:
        if p.poll() is None:p.kill();p.wait()
        os.close(master)
def check_roster(expected):
    cfg=json.load(open("/etc/wbd-next/server.json"))
    assert {u["username"]:u["password"] for u in cfg["users"]}==expected
def config(action,name,password=None):
    seq=[("监听",""),("借站域名",""),("客户端连接地址",""),("网卡",""),("账号操作",action),("账号 [",name)]
    if password is not None:seq.append(("密码（不回显）",password))
    seq.append(("开机启动","keep"))
    session(["wbd-next","config"],seq)
session(["wbd-next"],[("请选择","3"),("请选择","7"),("请选择","0")])
subprocess.run(["systemctl","is-active","--quiet","wbd-next.service"],check=True)
check_roster({"alice":"fixture-only-plan030"})
config("add","bob","fixture-only-bob")
check_roster({"alice":"fixture-only-plan030","bob":"fixture-only-bob"})
config("replace","bob","fixture-only-bob-new")
check_roster({"alice":"fixture-only-plan030","bob":"fixture-only-bob-new"})
out=tmp/"bob-export.json"
subprocess.run(["wbd-next","config","export","bob","--output",str(out)],check=True)
assert json.load(open(out))["password"]=="fixture-only-bob-new"
config("delete","bob")
check_roster({"alice":"fixture-only-plan030"})
assert subprocess.run(["wbd-next","config","export","bob","--output",str(out)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
print("PLAN030_REAL_PTY_MENU_CONFIG_ADD_REPLACE_DELETE_EXPORT_LOGS_PASS")
