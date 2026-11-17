#!/usr/bin/env python3
"""PLAN029B B3 one genuine Windows AF_INET6 /128 test-owned Wintun route.

No host-global IPv6 disabling, WFP/Defender change, unbinding, new IPv6
module or product packet injection. Always remove the exact test-owned
address/route (including failed pre-Stop operation), never foreign routes.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

SRC6="fd73:29b:2026::2"
DST6="fd73:29b:2026::1"
PREFIX=DST6+"/128"
RECEIPT="plan029b-b3-owned-ipv6-route.json"

def ps(cmd):
    proc=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive",
                         "-Command","$ErrorActionPreference='Stop';"+cmd],
                        capture_output=True,text=True,timeout=35,check=False)
    if proc.returncode:
        raise RuntimeError("B3 scoped native IPv6 OS operation: "+
                           (proc.stderr or proc.stdout)[-700:])
    return proc.stdout.strip()

def osjson(cmd):
    rows=[s.strip() for s in ps(cmd).splitlines() if s.strip()]
    if not rows:raise RuntimeError("B3 Windows OS IPv6 snapshot is empty")
    return json.loads(rows[-1])

def source_wintun():
    return osjson(r"""
$ip=@(Get-NetIPAddress -AddressFamily IPv4 -IPAddress '10.66.0.2' -ErrorAction SilentlyContinue)
if($ip.Count -ne 1){throw 'B3 no unique live original Wintun IPv4 lease'}
$index=[int]$ip[0].InterfaceIndex
$ad=@(Get-NetAdapter -IncludeHidden | Where-Object { [int]$_.ifIndex -eq $index })
if($ad.Count -ne 1 -or $ad[0].InterfaceDescription -notmatch 'Wintun'){
  throw 'B3 original lease ifindex not a unique genuine Wintun'}
$bind=@(Get-NetAdapterBinding -Name $ad[0].Name -ComponentID ms_tcpip6)
if($bind.Count -ne 1 -or -not $bind[0].Enabled){
  throw 'B3 Wintun IPv6 must remain bound; no test unbind allowed'}
$addr=@(Get-NetIPAddress -AddressFamily IPv6 -IPAddress 'fd73:29b:2026::2' -ErrorAction SilentlyContinue)
$route=@(Get-NetRoute -AddressFamily IPv6 -DestinationPrefix 'fd73:29b:2026::1/128' -ErrorAction SilentlyContinue)
if($addr.Count -or $route.Count){throw 'B3 foreign same exact ULA test resource'}
[pscustomobject]@{ifindex=$index;binding_enabled=$true;
  existing_addr=0;existing_route=0;wintun_description=$ad[0].InterfaceDescription} |
 ConvertTo-Json -Compress
""")

def add_owned(index):
    return osjson((r"""
New-NetIPAddress -InterfaceIndex IDX -IPAddress 'fd73:29b:2026::2' -PrefixLength 128 -PolicyStore ActiveStore | Out-Null
New-NetRoute -InterfaceIndex IDX -DestinationPrefix 'fd73:29b:2026::1/128' -NextHop '::' -RouteMetric 1 -PolicyStore ActiveStore | Out-Null
$addr=$null;$status=''
for($n=0;$n -lt 40;$n++){
  $addr=Get-NetIPAddress -AddressFamily IPv6 -IPAddress 'fd73:29b:2026::2' -ErrorAction Stop
  $status=[string]$addr.AddressState
  if($status -eq 'Preferred'){break}
  Start-Sleep -Milliseconds 200
}
$r=@(Get-NetRoute -AddressFamily IPv6 -DestinationPrefix 'fd73:29b:2026::1/128' -PolicyStore ActiveStore)
if($status -ne 'Preferred' -or $r.Count -ne 1 -or
   [int]$r[0].InterfaceIndex -ne IDX -or [string]$r[0].NextHop -ne '::'){
 throw 'B3 real Wintun IPv6 route/Preferred state not confirmed'}
[pscustomobject]@{ifindex=IDX;prefix='fd73:29b:2026::1/128';
 source='fd73:29b:2026::2';addr_state=$status;
 route_ifindex=[int]$r[0].InterfaceIndex;route_count=$r.Count} |
 ConvertTo-Json -Compress
""").replace("IDX",str(index)))

def cleanup(out):
    file=out/RECEIPT
    if not file.exists():return "NOT_CREATED"
    row=json.loads(file.read_text(encoding="utf-8"))
    if (row.get("scope")!="PLAN029B_B3_EXACT_SOURCE_OWNED_IPV6" or
        row.get("source_sha")!=os.environ.get("GITHUB_SHA") or
        row.get("lease4")!="10.66.0.2" or
        row.get("src6")!=SRC6 or row.get("prefix")!=PREFIX or
        row.get("original_route_count")!=0 or
        row.get("original_address_count")!=0 or
        not isinstance(row.get("ifindex"),int) or row["ifindex"]<=0):
        raise RuntimeError("B3 invalid/foreign source-owned IPv6 intent; no deletion")
    index=row["ifindex"]
    result=osjson((r"""
$routes=@(Get-NetRoute -AddressFamily IPv6 -DestinationPrefix 'fd73:29b:2026::1/128' -ErrorAction SilentlyContinue)
if(@($routes | Where-Object { [int]$_.InterfaceIndex -ne IDX -or [string]$_.NextHop -ne '::' }).Count -ne 0){
 throw 'B3 found foreign route, refuse cleanup'}
foreach($r in $routes){
 Remove-NetRoute -AddressFamily IPv6 -DestinationPrefix 'fd73:29b:2026::1/128' -InterfaceIndex IDX -NextHop '::' -Confirm:$false -ErrorAction Stop
}
$addr=@(Get-NetIPAddress -AddressFamily IPv6 -IPAddress 'fd73:29b:2026::2' -ErrorAction SilentlyContinue)
if(@($addr | Where-Object {[int]$_.InterfaceIndex -ne IDX}).Count -ne 0){
 throw 'B3 found foreign IPv6 address, refuse cleanup'}
foreach($a in $addr){
 Remove-NetIPAddress -AddressFamily IPv6 -IPAddress 'fd73:29b:2026::2' -InterfaceIndex IDX -Confirm:$false -ErrorAction Stop
}
$remainR=@(Get-NetRoute -AddressFamily IPv6 -DestinationPrefix 'fd73:29b:2026::1/128' -ErrorAction SilentlyContinue)
$remainA=@(Get-NetIPAddress -AddressFamily IPv6 -IPAddress 'fd73:29b:2026::2' -ErrorAction SilentlyContinue)
if($remainR.Count -or $remainA.Count){throw 'B3 exact /128 Stop residue'}
[pscustomobject]@{routes_remaining=0;addresses_remaining=0;
 cleanup='PASS_EXACT_TEST_OWNED_IPV6_ADDRESS_ROUTE_ABSENT'} |
 ConvertTo-Json -Compress
""").replace("IDX",str(index)))
    row["cleanup"]=result["cleanup"]
    file.write_text(json.dumps(row,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("PLAN029B_B3_IPV6_ROUTE_CLEANUP "+json.dumps(result,sort_keys=True),flush=True)
    return row["cleanup"]

def mixed_sockets():
    got4=0;sent6=0
    with socket.socket(socket.AF_INET6,socket.SOCK_DGRAM) as six, \
         socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as four:
        six.bind((SRC6,0))
        four.bind(("10.66.0.2",0))
        four.settimeout(3)
        for i in range(12):
            for j in range(2 if i<8 else 0):
                datagram=("P29B-B3-V6-%d-%d"%(i,j)).encode("ascii")
                if six.sendto(datagram,(DST6,46115))!=len(datagram):
                    raise RuntimeError("B3 original AF_INET6 real send was short")
                sent6+=1
            payload=("P29B-B3-V4-%d"%i).encode("ascii")
            if four.sendto(payload,("10.66.0.1",46114))!=len(payload):
                raise RuntimeError("B3 original AF_INET Wintun send was short")
            reply,peer=four.recvfrom(256)
            if peer!=("10.66.0.1",46114) or reply!=payload+b"-ECHO":
                raise RuntimeError("B3 original IPv4 response invalid after IPv6")
            got4+=1
    if sent6!=16 or got4!=12:
        raise RuntimeError("B3 Windows genuine IPv6/IPv4 mixed loop incomplete")
    return {"kernel_ipv6_sendto":sent6,"kernel_ipv4_echo":got4,
            "ipv6_family":"AF_INET6","ipv4_family":"AF_INET"}

def main():
    if len(sys.argv)!=3 or sys.argv[1] not in ("--execute","--cleanup"):
        raise SystemExit("usage: m0_plan029b_b3_ipv6_windows.py --execute|--cleanup <out>")
    out=Path(sys.argv[2]).resolve()
    if os.name!="nt" or os.environ.get("GITHUB_ACTIONS")!="true" or \
       len(os.environ.get("GITHUB_SHA",""))!=40:
        raise RuntimeError("B3 signed genuine Windows runner only")
    if sys.argv[1]=="--cleanup":
        cleanup(out)
        return
    if (out/RECEIPT).exists():raise RuntimeError("B3 existing intent file, refusing overwrite")
    pre=source_wintun()
    row={"scope":"PLAN029B_B3_EXACT_SOURCE_OWNED_IPV6","source_sha":os.environ["GITHUB_SHA"],
         "lease4":"10.66.0.2","src6":SRC6,"prefix":PREFIX,"ifindex":int(pre["ifindex"]),
         "original_route_count":0,"original_address_count":0,"ipv6_binding_enabled":True,
         "stage":"PRE_MUTATION_INTENT","cleanup":"PENDING"}
    out.mkdir(parents=True,exist_ok=True)
    (out/RECEIPT).write_text(json.dumps(row,indent=2)+"\n",encoding="utf-8")
    try:
        route=add_owned(row["ifindex"])
        info=mixed_sockets()
        row["route"]=route;row["sockets"]=info
        row["stage"]="REAL_AF_INET6_SENT_AND_IPV4_ECHO_CONFIRMED"
        print("PLAN029B_B3_ORIGINAL_WINDOWS_KERNEL_MIX "+
              json.dumps({"route":route,"sockets":info},sort_keys=True),flush=True)
    finally:
        cleanup(out)
    if row.get("stage")!="REAL_AF_INET6_SENT_AND_IPV4_ECHO_CONFIRMED":
        raise RuntimeError("B3 original real IPv6 stage incomplete")
    print("PLAN029B_B3_ORIGINAL_WINDOWS_REAL_IPV6_IPV4 "+
          json.dumps({"result":"PASS_PRE_STOP_AF_INET6_WINTUN_ROUTE_AND_IPV4",
                      "source_sha":row["source_sha"],"ifindex":row["ifindex"],
                      "ipv6_sent":info["kernel_ipv6_sendto"],"ipv4_echo":info["kernel_ipv4_echo"],
                      "route":PREFIX,"cleanup":"PASS"},sort_keys=True),flush=True)

if __name__=="__main__":
    main()
