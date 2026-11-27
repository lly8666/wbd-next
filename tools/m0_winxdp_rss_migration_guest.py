"""Isolated carrier diagnostic: actual Linux raw IP packets, controlled tuple/sequence.
Not TCP goodput, TLS, or WBD protocol qualification."""
import os,pathlib,socket,struct,sys,time
host,folder=sys.argv[1:];root=pathlib.Path(folder)
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
    s.connect((host,39463));source=s.getsockname()[0]
src,dst=socket.inet_aton(source),socket.inet_aton(host)
def checksum(data):
    if len(data)&1:data+=b"\0"
    n=sum(struct.unpack("!%dH"%(len(data)//2),data))
    while n>>16:n=(n&65535)+(n>>16)
    return (~n)&65535
def frame(port,cmd,seq):
    payload=struct.pack("!III",0x57424450,cmd,seq)+bytes(1100)
    tcp=struct.pack("!HHIIBBHHH",port,39463,seq,0,5<<4,0x10,65535,0,0)
    c=checksum(src+dst+struct.pack("!BBH",0,6,len(tcp)+len(payload))+tcp+payload)
    tcp=tcp[:16]+struct.pack("!H",c)+tcp[18:]
    ip=struct.pack("!BBHHHBBH4s4s",0x45,0,20+len(tcp)+len(payload),seq&65535,0x4000,64,6,0,src,dst)
    ip=ip[:10]+struct.pack("!H",checksum(ip))+ip[12:]
    return ip+tcp+payload
with socket.socket(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_RAW) as s:
    s.setsockopt(socket.IPPROTO_IP,socket.IP_HDRINCL,1)
    deadline=time.monotonic()+240
    cmd=1
    while time.monotonic()<deadline:
        f=root/f"request-{cmd}"
        if not f.exists():time.sleep(.001);continue
        ident,port,n=map(int,f.read_text().split());assert ident==cmd
        for i in range(n):s.sendto(frame(port or 39500+i,cmd,i),(host,0))
        tmp=root/"done.tmp";tmp.write_text(str(n));os.replace(tmp,root/f"done-{cmd}")
        if port==65535:break
        cmd+=1
    else:raise SystemExit("probe timed out")
