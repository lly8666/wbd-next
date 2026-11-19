#!/usr/bin/env python3
"""PLAN029B B3 one genuine Windows AF_INET6 /128 test-owned Wintun route.

No host-global IPv6 disabling, WFP/Defender change, unbinding, new IPv6
module or product packet injection. Always remove the exact test-owned
address/route (including failed pre-Stop operation), never foreign routes.
"""
import hashlib
import hmac
import json
import os
import re
import uuid
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

def read_original_wintun_wal(out):
    """Use Go's existing generation+PnP checksum WAL, never a guessed NIC name.

    H2108 proved the active real Wintun does not necessarily advertise
    "Wintun" through Get-NetAdapter.InterfaceDescription. It DOES have an
    exact source-held Go WAL, interface index, LUID/GUID and pinned PnP hash.
    This is a read-only observation; it cannot authorize network mutation
    without the additional unique live Windows lease+IPv6 interface checks.
    """
    p=out/"owned-wal.json.n4-owned-wal"
    if p.is_symlink() or not p.is_file() or not 0<p.stat().st_size<=65536:
        raise RuntimeError("B3 original Go generation WAL absent/foreign/oversize")
    raw=p.read_bytes().strip()
    prefix=b'{"data":'
    separator=b',"sha256":"'
    at=raw.rfind(separator)
    if not raw.startswith(prefix) or at<len(prefix) or not raw.endswith(b'"}'):
        raise RuntimeError("B3 original Go generation WAL envelope shape invalid")
    payload=raw[len(prefix):at]
    try:
        expected=raw[at+len(separator):-2].decode("ascii")
        envelope=json.loads(raw)
        data=json.loads(payload)
    except (UnicodeError,ValueError,TypeError) as exc:
        raise RuntimeError("B3 original Go WAL is not valid JSON or checksum") from exc
    if (not re.fullmatch(r"[0-9a-f]{64}",expected) or
        not hmac.compare_digest(hashlib.sha256(payload).hexdigest(),expected) or
        not isinstance(envelope,dict) or envelope.get("data")!=data or
        envelope.get("sha256")!=expected or not isinstance(data,dict) or
        data.get("schema")!="wbd-n4-native-network-txn/v2" or
        data.get("phase")!="active"):
        raise RuntimeError("B3 original Go current generation checksum/WAL phase invalid")
    records=data.get("records")
    if (not isinstance(records,list) or len(records)!=4 or
        [x.get("name") for x in records if isinstance(x,dict)]!=
            ["lease","mtu","dns","routes"] or
        any(x.get("state")!="owned" for x in records)):
        raise RuntimeError("B3 original Go four-stage owned WAL not applied")
    identity=data.get("identity")
    if not isinstance(identity,dict):
        raise RuntimeError("B3 original Go Wintun owner identity missing")
    try:
        index=identity["wintun_index"]
        luid=identity["wintun_luid"]
        alias=identity["adapter_alias"]
        guid=str(uuid.UUID(identity["wintun_guid"]))
        pin=identity["pnp_instance_sha256"]
        installation=identity["installation"]
        generation=identity["generation"]
    except (KeyError,TypeError,ValueError,AttributeError) as exc:
        raise RuntimeError("B3 original Go pinned Wintun identity malformed") from exc
    if (type(index) is not int or index<=0 or
        type(luid) is not int or luid<=0 or
        alias!="WBDWLMAIN" or not isinstance(pin,str) or
        not re.fullmatch(r"[0-9a-f]{64}",pin) or
        any(not isinstance(x,list) or len(x)!=16 or
            not all(type(n) is int and 0<=n<=255 for n in x) or
            not any(x) for x in (installation,generation))):
        raise RuntimeError("B3 original Go Wintun PnP/index/alias/epoch not pinned")
    return {"ifindex":index,"wintun_guid":guid,"adapter_alias":alias,
            "wal_sha256":expected,
            "generation_fingerprint":hashlib.sha256(bytes(generation)).hexdigest()}

def source_wintun(owner):
    # The actual OS IPv4 lease and IPv6 interface MUST resolve to the SAME
    # current pinned WAL index. Get-NetAdapter is auxiliary: on this signed
    # runner its friendly description is not the original Wintun driver ID.
    # When visible, its GUID and disabled IPv6 binding are still hard gates.
    if (type(owner.get("ifindex")) is not int or owner["ifindex"]<1 or
        owner.get("adapter_alias")!="WBDWLMAIN"):
        raise RuntimeError("B3 foreign pinned original owner")
    return osjson((r"""
$ip=@(Get-NetIPAddress -AddressFamily IPv4 -IPAddress '10.66.0.2' -ErrorAction SilentlyContinue)
if($ip.Count -ne 1){throw 'B3 no unique live original Wintun IPv4 lease'}
$index=[int]$ip[0].InterfaceIndex
if($index -ne WAL_INDEX -or [string]$ip[0].InterfaceAlias -ne 'WBDWLMAIN'){
 throw 'B3 real IPv4 lease did not match original generation WAL'}
$if6=@(Get-NetIPInterface -AddressFamily IPv6 -InterfaceIndex WAL_INDEX -ErrorAction SilentlyContinue)
if($if6.Count -ne 1 -or [int]$if6[0].InterfaceIndex -ne WAL_INDEX){
 throw 'B3 original owned Wintun has no IPv6 IP stack interface'}
$ad=@(Get-NetAdapter -IncludeHidden | Where-Object { [int]$_.ifIndex -eq $index })
if($ad.Count -gt 1){throw 'B3 duplicate adapter with pinned original Wintun index'}
$bindingEvidence='ORIGINAL_WAL_PLUS_GET_NETIPINTERFACE_IPV6'
$desc='OS_ADAPTER_DESCRIPTION_NOT_AVAILABLE'
if($ad.Count -eq 1){
 $guid=([string]$ad[0].InterfaceGuid).Trim('{}').ToLowerInvariant()
 if($guid -ne 'WAL_GUID'){throw 'B3 real NIC GUID differs from pinned original Go WAL'}
 $desc=[string]$ad[0].InterfaceDescription
 $bind=@(Get-NetAdapterBinding -Name $ad[0].Name -ComponentID ms_tcpip6 -ErrorAction SilentlyContinue)
 if($bind.Count -gt 1){throw 'B3 duplicate current IPv6 binding'}
 if($bind.Count -eq 1){
  if(-not $bind[0].Enabled){throw 'B3 original Wintun IPv6 binding disabled'}
  $bindingEvidence='PINNED_WAL_OS_GUID_AND_NETADAPTERBINDING_ENABLED'
 }
}
$addr=@(Get-NetIPAddress -AddressFamily IPv6 -IPAddress 'fd73:29b:2026::2' -ErrorAction SilentlyContinue)
$route=@(Get-NetRoute -AddressFamily IPv6 -DestinationPrefix 'fd73:29b:2026::1/128' -ErrorAction SilentlyContinue)
if($addr.Count -or $route.Count){throw 'B3 foreign same exact ULA test resource'}
[pscustomobject]@{ifindex=$index;binding_enabled=$true;
  binding_evidence=$bindingEvidence;original_wal_guid='WAL_GUID';
  original_generation_owner=$true;existing_addr=0;existing_route=0;
  wintun_description=$desc} | ConvertTo-Json -Compress
""").replace("WAL_INDEX",str(owner["ifindex"])).replace("WAL_GUID",owner["wintun_guid"]))

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
    owner=read_original_wintun_wal(out)
    pre=source_wintun(owner)
    row={"scope":"PLAN029B_B3_EXACT_SOURCE_OWNED_IPV6","source_sha":os.environ["GITHUB_SHA"],
         "lease4":"10.66.0.2","src6":SRC6,"prefix":PREFIX,"ifindex":int(pre["ifindex"]),
         "original_route_count":0,"original_address_count":0,"ipv6_binding_enabled":True,
         "binding_evidence":pre["binding_evidence"],
         "original_go_wal_sha256":owner["wal_sha256"],
         "generation_fingerprint":owner["generation_fingerprint"],
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
