"""OS-level IPv4 DF0 UDP fragmentation and DF1 oversized local rejection.

Real native Windows Wintun and Linux WSL2 TUN socket processes only.
Never claim userland ICMP3/4 generation from a local EMSGSIZE.
"""
import errno,json,os,pathlib,socket,sys,time
SIZE=1728
PORT=45909

def payload(ip):
    first=("WBD-DF0-"+ip+"-").encode("ascii")
    return first+b"X"*(SIZE-len(first))

def df_option(sock,enabled):
    if os.name=="nt":name,value=getattr(socket,"IP_DONTFRAGMENT",14),int(enabled)
    else:name,value=getattr(socket,"IP_MTU_DISCOVER",10),(2 if enabled else 0)
    sock.setsockopt(socket.IPPROTO_IP,name,value)
    if sock.getsockopt(socket.IPPROTO_IP,name)!=value:
        raise RuntimeError("kernel IP DF option readback mismatch")
    return (name,value)

def main():
    if len(sys.argv)!=4:raise ValueError("real local remote and shared-ready")
    local,remote,gate=sys.argv[1:]
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try:
        s.bind((local,PORT))
        s.settimeout(.4)
        df0=df_option(s,False)
        print(json.dumps({"phase":"bound","local":local}),flush=True)
        deadline=time.monotonic()+25
        while not pathlib.Path(gate).is_file():
            if time.monotonic()>deadline:raise RuntimeError("real peer bind barrier deadline")
            time.sleep(.05)
        sent=payload(local)
        if s.sendto(sent,(remote,PORT))!=SIZE:raise RuntimeError("short DF0 send")
        expected=payload(remote)
        deadline=time.monotonic()+35
        ok=False
        while time.monotonic()<deadline:
            try:data,peer=s.recvfrom(4096)
            except socket.timeout:continue
            if peer[0]==remote and data==expected:ok=True;break
        if not ok:raise RuntimeError("1728 byte DF0 real kernel IP fragments not reassembled")
        test=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        try:
            test.bind((local,0))
            df1=df_option(test,True)
            error_code=None
            try:test.sendto(sent,(remote,PORT))
            except OSError as e:
                error_code=e.winerror if getattr(e,"winerror",None) is not None else e.errno
            if error_code not in (errno.EMSGSIZE,10040):
                raise RuntimeError("DF1 OS over-MTU send not rejected "+repr(error_code))
        finally:test.close()
        print(json.dumps({"result":"REAL_DF0_REASSEMBLED_DF1_EMSGSIZE",
          "host_os":os.name,"df0":df0,"df1":df1,"received_bytes":len(expected),
          "df1_errno":error_code,"icmp_type3_code4":"NOT_MEASURED_LOCAL_EMSGSIZE",
          "source":"REAL_WINDOWS_WINTUN_LINUX_TUN_ORIGINAL_GO_TLS_RUST"}),flush=True)
    finally:s.close()

if __name__=="__main__":main()
