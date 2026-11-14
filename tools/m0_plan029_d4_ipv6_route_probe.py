#!/usr/bin/env python3
"""PLAN029 D4 read-only, genuine Windows IPv6 route-scope witness.

This never writes a route, firewall rule, WFP filter, adapter or DNS setting.
IPv6 route readback alone does NOT prove packet delivery or a global block.
One signed Windows original product Connect/Stop owns all OS changes.
"""
from __future__ import annotations
import json,os,subprocess

PS = r'''
$ErrorActionPreference = 'Stop'
$routes = @(Get-NetRoute -AddressFamily IPv6 -PolicyStore ActiveStore |
  Where-Object { @('::/0','::/1','8000::/1') -contains ([string]$_.DestinationPrefix) } |
  ForEach-Object {
    [ordered]@{
      prefix = [string]$_.DestinationPrefix
      ifindex = [int]$_.InterfaceIndex
      next_hop = [string]$_.NextHop
      metric = [int]$_.RouteMetric
    }
  })
$leases = @(Get-NetIPAddress -AddressFamily IPv4 -IPAddress '10.66.0.2' -ErrorAction SilentlyContinue |
  ForEach-Object { [int]$_.InterfaceIndex })
[pscustomobject]@{
  routes = $routes
  wintun_ipv4_lease_indexes = $leases
} | ConvertTo-Json -Depth 5 -Compress
'''

def normalize(data:dict)->dict:
    if not isinstance(data,dict):raise ValueError("route probe must return a JSON object")
    routes=data.get("routes")
    leases=data.get("wintun_ipv4_lease_indexes")
    if not isinstance(routes,list) or not isinstance(leases,list):
        raise ValueError("route probe must return arrays, not guessed presence")
    parsed=[]
    for item in routes:
        if not isinstance(item,dict) or item.get("prefix") not in ("::/0","::/1","8000::/1"):
            raise ValueError("unexpected IPv6 route shape")
        index=int(item["ifindex"])
        if index<1:raise ValueError("invalid route interface index")
        parsed.append({"prefix":item["prefix"],"ifindex":index,
                       "next_hop":str(item["next_hop"]),"metric":int(item["metric"])})
    indexes=sorted(set(int(x) for x in leases))
    if any(i<1 for i in indexes):raise ValueError("invalid Wintun interface index")
    return {"routes":sorted(parsed,key=lambda x:(x["prefix"],x["ifindex"],x["next_hop"],x["metric"])),
            "wintun_ipv4_lease_indexes":indexes}

def snapshot(label:str)->dict:
    if os.name!="nt":raise RuntimeError("real Windows OS required; never synthesize IPv6 routes")
    cp=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",PS],
                      capture_output=True,text=True,timeout=20,check=False)
    if cp.returncode!=0:
        raise RuntimeError("read-only PowerShell IPv6 route probe failed: "+(cp.stderr or cp.stdout)[-350:])
    lines=[line.strip() for line in cp.stdout.splitlines() if line.strip()]
    if not lines:raise RuntimeError("empty Windows IPv6 route readback")
    result=normalize(json.loads(lines[-1]))
    return {"phase":label,**result}

def evaluate(before:dict,active:dict,after:dict)->dict:
    for value in (before,active,after):
        if not isinstance(value,dict) or "routes" not in value or "wintun_ipv4_lease_indexes" not in value:
            raise ValueError("all three original OS readbacks are required")
    indexes=set(active["wintun_ipv4_lease_indexes"])
    if len(indexes)!=1:
        raise ValueError("active signed Wintun IPv4 lease interface not uniquely read back")
    idx=next(iter(indexes))
    def indexed_routes(value):
        return {r["prefix"] for r in value["routes"] if r["ifindex"]==idx}
    sink=indexed_routes(active)
    sink_pair={"::/1","8000::/1"}.issubset(sink)
    stray=indexed_routes(after)-indexed_routes(before)
    physical_default=[r for r in active["routes"] if r["prefix"]=="::/0" and r["ifindex"]!=idx]
    return {
      "source_sha":os.environ.get("GITHUB_SHA","NOT_SET"),
      "phase":"AFTER_REAL_SIGNED_OS_APPLY_BEFORE_OWNED_STOP",
      "wintun_ifindex":idx,
      "default_routes_before":len([r for r in before["routes"] if r["prefix"]=="::/0"]),
      "default_routes_during":len([r for r in active["routes"] if r["prefix"]=="::/0"]),
      "physical_default_route_observed":bool(physical_default),
      "both_non_onlink_ipv6_sinks_to_wintun":sink_pair,
      "ipv6_policy_scope":"ROUTE_ONLY_PRESENT_PACKET_NOT_TESTED" if sink_pair
          else "OPEN_NO_GENERAL_IPV6_WINTUN_SINK",
      "owned_ipv6_route_after_stop_new_prefixes":sorted(stray),
      "stop_route_baseline_readback":"PASS_NO_NEW_PREFIX_ON_WINTUN" if not stray
          else "FAIL_NEW_WINTUN_PREFIX_REMAINED",
      "on_link_and_physical_bound_ipv6":"NOT_PROVEN_BLOCKED_BY_ROUTE_ONLY",
      "actual_ipv6_app_packets":"NOT_RUN_NO_EXTERNAL_IPV6_PRECONDITION",
      "interpretation":"Route readback only. A physical IPv6 default route is a bypass risk, not proof a packet succeeded; firewall and explicit physical interface binding remain unverified."
    }

if __name__=="__main__":
    result=snapshot("standalone_read_only_no_product")
    print(json.dumps(result,sort_keys=True))
