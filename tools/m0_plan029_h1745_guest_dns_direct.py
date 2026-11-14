#!/usr/bin/env python3
"""H1745: independent actual WSL2 kernel UDP DNS53 and business recipient."""
import json,select,socket,struct,sys,time
guest,expected_host=sys.argv[1:3]
# Windows-parent environment variables are NOT inherited by wsl.exe --.
# Explicit one-bit scene argument; never pretend an unarmed guest tested cache.
if len(sys.argv)!=4 or sys.argv[3] not in ("0","1","2"):
    raise RuntimeError("H1785 WSL guest CN cache mode argv must be exactly 0 or 1")
cache_mode=sys.argv[3]=="1"
multia_mode=sys.argv[3]=="2"
dns=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
business=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
dns.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,0)
business.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,0)
dns.bind((guest,53))
business.bind((guest,46111))
name=b"\x03www\x02cn\x07example\x00"
question=name+b"\x00\x01\x00\x01"
target=b"\x04edge\x03cdn\x07example\x00"
marker=b"PLAN029-H1745-CN-DIRECT-UDP"
print("PLAN029_H1745_LINUX_REAL_DNS53_AND_UDP46111_READY",flush=True)
observed={"dns":False,"direct_business":False,"dns_client_physical":None,
          "business_client_physical":None,"real_server":guest,
          "target_dns_count":0,"cache_mode":cache_mode,
          "multi_a_mode":multia_mode,"multi_a_answers":0}
settled_at=None
limit=time.monotonic()+60
while time.monotonic()<limit:
    if (observed["dns"] and observed["direct_business"] and
        (not cache_mode or (settled_at is not None and
         time.monotonic()-settled_at>=2.5))):
        break
    ready,_,_=select.select([dns,business],[],[],.5)
    for selected in ready:
        packet,remote=selected.recvfrom(2048)
        if remote[0]!=expected_host:
            raise RuntimeError("physical source not the selected Windows underlay")
        if selected is dns:
            if len(packet)<12 or packet[4:6]!=b"\x00\x01" or packet[12:]!=question:
                if cache_mode:continue # unrelated cold/boot QNAME, not a target cache miss
                raise RuntimeError("CN DNS question did not arrive at exact physical endpoint")
            observed["target_dns_count"]+=1
            if cache_mode and observed["target_dns_count"]!=1:
                raise RuntimeError("second same CN DNS query escaped physical rather than cache")
            answer_count=3 if multia_mode else 2  # CNAME + one/two A
            header=packet[:2]+b"\x81\x80\x00\x01"+struct.pack("!H",answer_count)+b"\x00\x00\x00\x00"
            cname=b"\xc0\x0c"+b"\x00\x05\x00\x01"+struct.pack("!I",30)+struct.pack("!H",len(target))+target
            a=target+b"\x00\x01\x00\x01"+struct.pack("!I",30)+b"\x00\x04"+socket.inet_aton(guest)
            # Non-identical second CDN real A: both are local-only FakeIPs
            # in the original Windows app, not public A leakage.
            other=(target+b"\x00\x01\x00\x01"+struct.pack("!I",30)+
                   b"\x00\x04"+socket.inet_aton("203.0.113.89")) if multia_mode else b""
            dns.sendto(header+question+cname+a+other,remote)
            if multia_mode:observed["multi_a_answers"]+=1
            observed["dns"]=True
            observed["dns_client_physical"]=remote[0]
        elif packet==marker:
            business.sendto(marker+b"-reply",remote)
            observed["direct_business"]=True
            observed["business_client_physical"]=remote[0]
            if cache_mode:settled_at=time.monotonic()
        else:
            raise RuntimeError("unexpected business payload")
dns.close();business.close()
print("PLAN029_H1745_REAL_LINUX_GUEST_DIRECT "+json.dumps(observed,sort_keys=True),flush=True)
if not observed["dns"] or not observed["direct_business"]:sys.exit(8)
if cache_mode and observed["target_dns_count"]!=1:
    raise RuntimeError("H1783 real CN cache physical DNS target count mismatch")
