#!/usr/bin/env python3
"""Read-only actual Windows NPF link trace while PUBLIC original Go runs.

No packet generation, traffic proxy, fake SYN, packet payloads, injected ACKs,
TLS contents, or OS mutation. This is a wire witness in the SAME full job.
"""
import ctypes as c,os,subprocess,json,sys,time
def ps(script):
 p=subprocess.run(["pwsh","-NoProfile","-NonInteractive","-Command",script],capture_output=True,text=True,timeout=18)
 if p.returncode:raise RuntimeError(p.stderr[-350:])
 return p.stdout.strip()
q=ps("$n=@(Get-NetAdapter -IncludeHidden | Where-Object {$_.Name -match 'WSL' -and $_.InterfaceGuid -ne $null}); @($n|Select-Object Name,InterfaceGuid,InterfaceIndex,MacAddress,Status) | ConvertTo-Json -Compress")
a=json.loads(q)
if isinstance(a,dict):a=[a]
print("WL_WINDOWS_TRUE_WSL_ADAPTERS="+json.dumps(a),flush=True)
if not a:raise RuntimeError("no real Windows WSL native NIC")
dll=c.WinDLL(os.path.join(os.environ["WINDIR"],"System32","Npcap","wpcap.dll"))
dll.pcap_open_live.argtypes=[c.c_char_p,c.c_int,c.c_int,c.c_int,c.c_void_p]
dll.pcap_open_live.restype=c.c_void_p
dll.pcap_next_ex.argtypes=[c.c_void_p,c.POINTER(c.c_void_p),c.POINTER(c.c_void_p)]
dll.pcap_next_ex.restype=c.c_int
dll.pcap_close.argtypes=[c.c_void_p]
dll.pcap_close.restype=None
opened=[]
for x in a:
 if x.get("Status") not in ("Up","Connected"):continue
 guid=str(x["InterfaceGuid"]).strip("{}").upper()
 dev=("\\Device\\NPF_{"+guid+"}").encode("ascii")
 err=c.create_string_buffer(512)
 h=dll.pcap_open_live(dev,2048,1,50,err)
 if h:
  opened.append((x["Name"],h))
  print("WL_WINDOWS_NPF_MONITOR_ARMED name="+x["Name"],flush=True)
 else:
  print("WL_WINDOWS_NPF_MONITOR_UNAVAILABLE name="+x["Name"]+" reason="+err.value.decode(errors="replace")[:100],flush=True)
if not opened:raise RuntimeError("no Windows WSL Npcap handle opened")
seen=0;deadline=time.monotonic()+52
try:
 while time.monotonic()<deadline and seen<200:
  for name,h in opened:
   header=c.c_void_p();payload=c.c_void_p()
   rc=dll.pcap_next_ex(h,c.byref(header),c.byref(payload))
   if rc!=1 or not header.value or not payload.value:continue
   length=c.c_uint32.from_address(header.value+8).value
   if length<54 or length>2048:continue
   data=c.string_at(payload.value,length)
   if data[12:14]!=b"\x08\x00" or data[23]!=6:continue
   ihl=(data[14]&15)*4
   if len(data)<14+ihl+20:continue
   pos=14+ihl
   sp=int.from_bytes(data[pos:pos+2],"big")
   dp=int.from_bytes(data[pos+2:pos+4],"big")
   if sp!=443 and dp!=443:continue
   seen+=1
   if seen<=48 or seen%20==0:
    fmt=lambda b:".".join(map(str,b))
    print("WL_WINDOWS_NPF_TCP443 "+json.dumps({"device":name,"src":fmt(data[26:30]),"dst":fmt(data[30:34]),"source_mac":data[6:12].hex(":"),"dest_mac":data[:6].hex(":"),"sport":sp,"dport":dp,"flags":data[pos+13],"eth_src_mac":":".join(f"{v:02x}" for v in data[6:12]),"eth_dst_mac":":".join(f"{v:02x}" for v in data[0:6]),"num":seen}),flush=True)
finally:
 for _,h in opened:dll.pcap_close(h)
print("WL_WINDOWS_NPF_TCP443_COUNT="+str(seen),flush=True)
