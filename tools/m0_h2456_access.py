"""H2456 short native Windows access qualification, no WSL or WBD changes."""
import ctypes as c, hashlib, json, os, pathlib, socket, struct, subprocess, sys, threading, time, urllib.request

OUT=pathlib.Path("h2456-out")
OUT.mkdir(exist_ok=True)
ISWIN=os.name=="nt"
ZT=pathlib.Path(os.environ.get("ProgramData","C:/ProgramData"))/"ZeroTier/One" if ISWIN else pathlib.Path("/var/lib/zerotier-one")
ORIGIN="192.0.2.245"
GW="10.249.245.1"
WIN="10.249.245.2"
MARK=("H2456/"+os.environ["GITHUB_RUN_ID"]+"/"+os.environ["GITHUB_SHA"]+"/").encode()
def save(name,obj):
    (OUT/name).write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
def run(*args,timeout=20):
    p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError(str(args[0])+": "+p.stderr[-350:])
    return p.stdout.strip()
def ps(code):
    return json.loads(run("pwsh","-NoProfile","-NonInteractive","-Command",code))
def api(path,body=None):
    headers={"X-ZT1-AUTH":(ZT/"authtoken.secret").read_text().strip(),"Content-Type":"application/json"}
    req=urllib.request.Request("http://127.0.0.1:9993"+path,data=None if body is None else json.dumps(body).encode(),headers=headers,method="GET" if body is None else "POST")
    with urllib.request.urlopen(req,timeout=6) as r:return json.load(r)
def retry(fn,seconds=90):
    end=time.monotonic()+seconds
    while True:
        try:
            v=fn()
            if v:return v
        except Exception as e:last=repr(e)
        else:last="not ready"
        if time.monotonic()>end:raise RuntimeError(last)
        time.sleep(1)
def identity():
    row={"sha":os.environ["GITHUB_SHA"],"run":os.environ["GITHUB_RUN_ID"],"tail":run("tailscale","ip","-4")}
    try:
        z=retry(lambda:api("/status"),25)
        row["zt"]={"address":z["address"],"version":z.get("version"),"online":z.get("online")}
    except Exception as e:row["zt_error"]=repr(e)
    return row
def zt_wait(nwid,addr):
    def check():
        z=api("/network/"+nwid)
        return z if z.get("status")=="OK" and any(x.split("/")[0]==addr for x in z.get("assignedAddresses",[])) else None
    return retry(check,90)
def echo(addr):
    def udp():
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
            s.bind((addr,4789))
            while True:
                data,peer=s.recvfrom(2048)
                if data.startswith(MARK):
                    s.sendto(data,peer)
                    print("H2456_UDP_RX "+json.dumps({"bind":addr,"peer":peer,"bytes":len(data),"marker":data[:110].decode(errors="replace")}),flush=True)
    def tcp():
        with socket.socket() as s:
            s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind((addr,18727));s.listen(8)
            while True:
                p,peer=s.accept()
                with p:
                    p.settimeout(5)
                    try:
                        data=p.recv(512)
                        if data.startswith(MARK):p.sendall(data)
                    except OSError:pass
    threading.Thread(target=udp,daemon=True).start()
    threading.Thread(target=tcp,daemon=True).start()
    time.sleep(.3)
    print("H2456_ECHO_READY "+addr,flush=True)
    while True:time.sleep(1)
def arm_setup(client):
    ready=identity()
    assert (ready["sha"],ready["run"])==(client["sha"],client["run"])
    # Independent Tailscale peer on the existing authorized control path.
    f=(OUT/"tail-echo.log").open("w")
    subprocess.Popen([sys.executable,__file__,"echo",ready["tail"]],stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        addr=ready["zt"]["address"];winid=client["zt"]["address"]
        n=api("/controller/network/"+addr+"______",{"name":"H2456-"+ready["run"],"private":True,"v4AssignMode":{"zt":True},"ipAssignmentPools":[{"ipRangeStart":GW,"ipRangeEnd":WIN}],"routes":[{"target":"10.249.245.0/24","via":None}]})
        nwid=n["id"]
        for node,ip in ((addr,GW),(winid,WIN)):
            api("/controller/network/"+nwid+"/member/"+node,{"authorized":True,"ipAssignments":[ip]})
        api("/network/"+nwid,{})
        z=zt_wait(nwid,GW);dev=z["portDeviceName"]
        run("ip","netns","add","h2456origin")
        run("ip","link","add","h2456out","type","veth","peer","name","h2456app")
        run("ip","link","set","h2456app","netns","h2456origin")
        run("ip","addr","add","192.0.2.1/24","dev","h2456out")
        run("ip","link","set","h2456out","up")
        for args in (("link","set","lo","up"),("addr","add",ORIGIN+"/24","dev","h2456app"),("link","set","h2456app","up"),("route","add","default","via","192.0.2.1")):
            run("ip","netns","exec","h2456origin","ip",*args)
        run("sysctl","-qw","net.ipv4.ip_forward=1")
        for iface in (dev,"h2456out"):
            run("tc","qdisc","replace","dev",iface,"root","netem","delay","200ms","limit","65536")
        f=(OUT/"origin-echo.log").open("w")
        subprocess.Popen(["ip","netns","exec","h2456origin",sys.executable,str(pathlib.Path(__file__).resolve()),"echo",ORIGIN],stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        ready["zt"].update(network=nwid,device=dev,addr=GW,client=WIN,origin=ORIGIN)
        ready["qdisc"]={iface:run("tc","-s","qdisc","show","dev",iface) for iface in (dev,"h2456out")}
    except Exception as e:ready["zt_setup_error"]=repr(e)
    save("ready.json",ready)

def mac(s):
    b=bytes.fromhex(s.replace("-","").replace(":",""))
    if len(b)!=6 or b==bytes(6):raise ValueError("no nonzero Ethernet MAC")
    return b
def checksum(b):
    if len(b)%2:b+=b"\0"
    v=sum(struct.unpack("!%dH"%(len(b)//2),b))
    while v>>16:v=(v&65535)+(v>>16)
    return (~v)&65535
def ipv4(src,dst,sport,payload):
    u=struct.pack("!HHHH",sport,4789,8+len(payload),0)+payload
    h=struct.pack("!BBHHHBBH4s4s",0x45,0,20+len(u),42,0x4000,64,17,0,socket.inet_aton(src),socket.inet_aton(dst))
    h=h[:10]+struct.pack("!H",checksum(h))+h[12:]
    return h+u
def adapter_for(src):
    return ps("$i=Get-NetIPAddress -AddressFamily IPv4 -IPAddress '"+src+"' -ErrorAction Stop | Select-Object -First 1; Get-NetAdapter -IncludeHidden | Where-Object {$_.ifIndex -eq $i.InterfaceIndex} | Select-Object -First 1 Name,InterfaceGuid,MacAddress,Status,ifIndex,InterfaceDescription | ConvertTo-Json -Compress")
def pcap():
    lib=c.WinDLL(str(pathlib.Path(os.environ["WINDIR"])/"System32/Npcap/wpcap.dll"))
    sig={"pcap_open_live":([c.c_char_p,c.c_int,c.c_int,c.c_int,c.c_void_p],c.c_void_p),"pcap_datalink":([c.c_void_p],c.c_int),"pcap_setnonblock":([c.c_void_p,c.c_int,c.c_void_p],c.c_int),"pcap_sendpacket":([c.c_void_p,c.c_void_p,c.c_int],c.c_int),"pcap_next_ex":([c.c_void_p,c.POINTER(c.c_void_p),c.POINTER(c.c_void_p)],c.c_int),"pcap_geterr":([c.c_void_p],c.c_char_p),"pcap_close":([c.c_void_p],None)}
    for name,(args,result) in sig.items():
        fn=getattr(lib,name);fn.argtypes=args;fn.restype=result
    return lib
def ordinary(src,dst):
    with socket.socket() as s:
        s.settimeout(5);s.bind((src,0));t=time.monotonic();s.connect((dst,18727));msg=MARK+b"tcp";s.sendall(msg)
        reply=b""
        while len(reply)<len(msg):
            b=s.recv(len(msg)-len(reply))
            if not b:break
            reply+=b
        return {"exact":reply==msg,"elapsed_ms":round((time.monotonic()-t)*1000,1)}
def candidate(src,dst,hop,label):
    row={"source":src,"destination":dst,"next_hop":hop,"scope":"ordinary TCP plus Npcap raw IPv4 UDP exact returned payload; no product PASS"}
    try:row["ordinary_tcp"]=ordinary(src,dst)
    except Exception as e:row["ordinary_error"]=repr(e)
    handle=None
    try:
        adapter=adapter_for(src);row["adapter"]=adapter
        lib=pcap();err=c.create_string_buffer(512)
        device="\\Device\\NPF_{"+str(adapter["InterfaceGuid"]).strip("{}").upper()+"}"
        handle=lib.pcap_open_live(device.encode("ascii"),2048,1,100,err)
        if not handle:raise RuntimeError("pcap_open_live: "+err.value.decode(errors="replace"))
        row["dlt"]=lib.pcap_datalink(handle)
        if row["dlt"]!=1:raise RuntimeError("not DLT_EN10MB; unchanged product expects Ethernet")
        smac=mac(adapter["MacAddress"])
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp:
            udp.bind((src,0));udp.settimeout(2)
            # Ordinary exchange warms the actual on-link neighbor, independent of NPF.
            udp.sendto(MARK+b"warm",(dst,4789))
            try:row["ordinary_udp"]=udp.recvfrom(2048)[0]==MARK+b"warm"
            except OSError:row["ordinary_udp"]=False
            neighbor=ps("Get-NetNeighbor -InterfaceIndex "+str(adapter["ifIndex"])+" -IPAddress '"+hop+"' | Select-Object -First 1 IPAddress,LinkLayerAddress,State | ConvertTo-Json -Compress")
            row["neighbor"]=neighbor;dmac=mac(neighbor["LinkLayerAddress"])
            if lib.pcap_setnonblock(handle,1,err)!=0:raise RuntimeError("pcap nonblock: "+err.value.decode(errors="replace"))
            row["raw"]=[]
            for size in (128,1160,1460):
                for seq in range(3):
                    payload=(MARK+label.encode()+b"/"+str(size).encode()+b"/"+str(seq).encode()+b"/").ljust(size-28,b"x")
                    frame=dmac+smac+b"\x08\x00"+ipv4(src,dst,udp.getsockname()[1],payload)
                    buf=c.create_string_buffer(frame);start=time.monotonic()
                    rc=lib.pcap_sendpacket(handle,buf,len(frame))
                    result={"ip_bytes":size,"seq":seq,"send_rc":rc,"exact_npf_rx":False}
                    if rc!=0:result["send_error"]=lib.pcap_geterr(handle).decode(errors="replace")
                    else:
                        end=start+2
                        header=c.c_void_p();data=c.c_void_p()
                        while time.monotonic()<end:
                            got=lib.pcap_next_ex(handle,c.byref(header),c.byref(data))
                            if got==0:time.sleep(.01);continue
                            if got!=1:break
                            n=c.c_uint32.from_address(header.value+8).value
                            f=c.string_at(data.value,n)
                            if n>=42 and f[:6]==smac and f[12:14]==b"\x08\x00" and f[26:30]==socket.inet_aton(dst) and f[30:34]==socket.inet_aton(src) and f[42:42+len(payload)]==payload:
                                result.update(exact_npf_rx=True,rtt_ms=round((time.monotonic()-start)*1000,1));break
                    row["raw"].append(result)
    except Exception as e:row["npf_error"]=repr(e)
    finally:
        if handle:lib.pcap_close(handle)
    print("H2456_CANDIDATE "+json.dumps({"name":label,**row}),flush=True)
    return row
def windows_test(ready):
    me=identity()
    assert (me["sha"],me["run"])==(ready["sha"],ready["run"])
    result={"source":me,"peer":ready,"no_wsl":True}
    try:result["tailscale_ping"]=run("tailscale","ping","--c=3","--timeout=3s",ready["tail"],timeout=20)
    except Exception as e:result["tailscale_ping_error"]=repr(e)
    result["native_tailscale"]=candidate(me["tail"],ready["tail"],ready["tail"],"tailscale")
    try:
        z=ready["zt"];api("/network/"+z["network"],{})
        zlocal=zt_wait(z["network"],WIN)
        result["zt_network"]={k:zlocal.get(k) for k in ("status","portDeviceName","assignedAddresses","mac","mtu")}
        a=adapter_for(WIN)
        run("pwsh","-NoProfile","-NonInteractive","-Command","New-NetRoute -DestinationPrefix '"+ORIGIN+"/32' -InterfaceIndex "+str(a["ifIndex"])+" -NextHop '"+GW+"' -PolicyStore ActiveStore | Out-Null")
        result["zerotier_routed"]=candidate(WIN,ORIGIN,GW,"zerotier")
        result["zt_peers"]=api("/peer")
    except Exception as e:result["zerotier_error"]=repr(e)
    save("windows-result.json",result)
if __name__=="__main__":
    cmd=sys.argv[1]
    if cmd=="identity":save("identity.json",identity())
    elif cmd=="arm":arm_setup(load(sys.argv[2]))
    elif cmd=="windows":windows_test(load(sys.argv[2]))
    elif cmd=="echo":echo(sys.argv[2])
