#!/usr/bin/env python3
"""H1745: genuine Windows application UDP53 -> Wintun -> original Rust direct."""
import json,socket,struct,sys,time,math
def ping_body(arm,size,seq):
    if arm not in (b"P",b"D") or size not in (96,512,1200) or seq<0 or seq>=120:
        raise RuntimeError("H1999 invalid UDP identity")
    hdr=b"P29U"+arm+struct.pack("!HH",size,seq)
    return hdr+bytes([(size+17*seq)&255])*(size-len(hdr))

lease,expected_dns=sys.argv[1:3]
cache_mode=__import__("os").environ.get("WBD_PLAN029_DNS_CACHE_SCENE")=="1"
multia_mode=__import__("os").environ.get("WBD_PLAN029_D3_MULTIA_SCENE")=="1"
ping_mode=__import__("os").environ.get("WBD_PLAN029_DIRECT_UDP_RTT_SCENE")=="1"
physical_host=__import__("os").environ.get("WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4","")
if ping_mode and not physical_host:
    raise RuntimeError("H1999 original Windows physical NIC binding absent")
if multia_mode and cache_mode:raise RuntimeError("D3 multi-A is exclusive of cache test")
name=b"\x03www\x02cn\x07example\x00"
question=name+b"\x00\x01\x00\x01"
txid=b"\x17\x45"
query=txid+b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"+question
sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
sock.bind((lease,0))
sock.settimeout(1.2)
response=None
dns_started=time.monotonic()
dns_attempts=0
dns_completed=None
deadline=dns_started+24
while time.monotonic()<deadline:
    try:
        dns_attempts+=1
        sock.sendto(query,("8.8.8.8",53))
        data,remote=sock.recvfrom(2048)
        if remote!=("8.8.8.8",53) or data[:2]!=txid:continue
        response=data
        dns_completed=time.monotonic()
        break
    except socket.timeout:continue
if response is None:
    raise RuntimeError("real Windows Wintun client received no CN DNS result")
if len(response)<len(query) or response[3]&15 or response[6:8]==b"\x00\x00":
    raise RuntimeError("native direct CN fake DNS reply missing or SERVFAIL")
def read_name(packet,pos):
    for _ in range(80):
        if pos>=len(packet):raise RuntimeError("truncated DNS name")
        n=packet[pos]
        if n&0xc0==0xc0:
            if pos+2>len(packet):raise RuntimeError("bad DNS pointer")
            return pos+2
        if n==0:return pos+1
        if n&0xc0 or n>63:raise RuntimeError("invalid DNS label")
        pos+=1+n
    raise RuntimeError("DNS name depth exceeded")
cursor=12
for _ in range(struct.unpack("!H",response[4:6])[0]):
    cursor=read_name(response,cursor)+4
addresses=[]
for _ in range(struct.unpack("!H",response[6:8])[0]):
    cursor=read_name(response,cursor)
    if cursor+10>len(response):raise RuntimeError("truncated DNS RR")
    rtype,rclass,ttl,rdlength=struct.unpack("!HHIH",response[cursor:cursor+10])
    cursor+=10
    if cursor+rdlength>len(response):raise RuntimeError("DNS RDATA overread")
    if (rtype,rclass,rdlength)==(1,1,4):
        addresses.append(socket.inet_ntoa(response[cursor:cursor+4]))
    cursor+=rdlength
expected=2 if multia_mode else 1
if (len(addresses)!=expected or len(set(addresses))!=expected or
    not all(ip.startswith("198.18.") for ip in addresses) or
    expected_dns in addresses or "203.0.113.89" in addresses):
    raise RuntimeError("CN CDN multi-A was not durably remapped to separate owned FakeIPs")
fake=addresses[0]
cache_reply=False
cache_different_source=False
if cache_mode:
    # Different actual Windows original app socket + DNS ID, same CN name.
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as new:
        new.bind((lease,0));new.settimeout(.85)
        cache_different_source=new.getsockname()[1]!=sock.getsockname()[1]
        if not cache_different_source:raise RuntimeError("second DNS source port reused")
        next_id=b"\x17\x83"
        next_query=next_id+query[2:]
        answer2=None
        until=time.monotonic()+7
        while time.monotonic()<until:
            new.sendto(next_query,("8.8.8.8",53))
            try:data2,from2=new.recvfrom(2048)
            except socket.timeout:continue
            if from2==("8.8.8.8",53) and data2[:2]==next_id:
                answer2=data2;break
        if answer2 is None:raise RuntimeError("second genuine Wintun client DNS reply missing")
        if (answer2[2]&0x80==0 or answer2[3]&15 or
            answer2[4:6]!=b"\x00\x01" or
            answer2[6:8]!=response[6:8] or
            not answer2.endswith(socket.inet_aton(fake))):
            raise RuntimeError("cached CN fake DNS result changed or escaped CDN")
        cache_reply=True
business=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
business.bind((lease,0))
business.settimeout(1.5)
marker=b"PLAN029-H1745-CN-DIRECT-UDP"
reply=None
end=time.monotonic()+20
while time.monotonic()<end:
    business.sendto(marker,(fake,46111))
    try:
        data,remote=business.recvfrom(2048)
        if data==marker+b"-reply" and remote==(fake,46111):
            reply=data;break
    except socket.timeout:continue
if reply is None:raise RuntimeError("real Windows application never received Direct FakeIP UDP reverse")
pings={}
if ping_mode:
    def q_ms(samples,fraction):
        ordered=sorted(samples)
        return round(ordered[math.ceil(len(ordered)*fraction)-1],3)
    for size in (96,512,1200):
        both={}
        for arm in (b"P",b"D"):
            is_direct=arm==b"D"
            address=fake if is_direct else expected_dns
            c=business if is_direct else socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            if not is_direct:c.bind((physical_host,0))
            c.settimeout(1.5)
            rtt=[]
            try:
                for seq in range(120):
                    pkt=ping_body(arm,size,seq)
                    start=time.perf_counter_ns()
                    if c.sendto(pkt,(address,46111))!=len(pkt):
                        raise RuntimeError("H1999 short Win UDP send")
                    try:data,peer=c.recvfrom(2048)
                    except socket.timeout as exc:
                        raise RuntimeError("H1999 UDP timeout "+str((arm,size,seq))) from exc
                    elapsed=(time.perf_counter_ns()-start)/1000000
                    if data!=pkt or peer!=(address,46111):
                        raise RuntimeError("H1999 wrong physical/Direct source or bytes")
                    rtt.append(elapsed)
            finally:
                if not is_direct:c.close()
            both["direct" if is_direct else "physical"]={
                "unique":len(rtt),"loss":0,"p50_ms":q_ms(rtt,.50),
                "p95_ms":q_ms(rtt,.95),"p99_ms":q_ms(rtt,.99),
                "max_ms":q_ms(rtt,1.0),
                "over8ms":sum(x>=8 for x in rtt)}
        both["direct_to_physical_p99_ratio"]=round(
            both["direct"]["p99_ms"]/both["physical"]["p99_ms"],3
        ) if both["physical"]["p99_ms"] else None
        pings[str(size)]=both
print("PLAN029_H1745_REAL_WINDOWS_CN_DNS_FAKE_DIRECT_UDP "+json.dumps(
    {"dns_presented":"8.8.8.8","dns_wire_id":txid.hex(),"fake4":fake,
     "business_reply":reply.decode(),"source_lease":lease,
     "source_route":"ACTUAL_ORIGINAL_WINDOWS_WINTUN_SINGLE_RUST_OWNER",
     "direct_resolver":expected_dns,"cache_second_reply":cache_reply,
     # End-to-end application DNS delay, including real retries and async
     # durable FakeIP fsync; NOT isolated local classifier or disk latency.
     "dns_app_elapsed_ms":round((dns_completed-dns_started)*1000,3),
     "dns_app_attempts":dns_attempts,
     "cache_second_source_distinct":cache_different_source,
     "multi_a_mode":multia_mode,
     "multi_a_fake_addresses":addresses if multia_mode else [],
     "udp_p99_real_samples":720 if ping_mode else 0,
     "udp_p99_results":pings,
     "udp_p99_scope":"REAL_WINDOWS_PHYSICAL_VS_FAKEIP_DIRECT_APPLICATION_RTT" if ping_mode else "NOT_RUN"
     },sort_keys=True),flush=True)
sock.close();business.close()
